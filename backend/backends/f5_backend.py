"""
F5-TTS and E2-TTS backend implementation.
"""

from typing import Optional, List, Tuple
import asyncio
import torch
import numpy as np
from pathlib import Path
import tempfile
import soundfile as sf

from . import TTSBackend
from ..utils.cache import get_cache_key, get_cached_voice_prompt, cache_voice_prompt
from ..utils.audio import normalize_audio, load_audio
from ..utils.progress import get_progress_manager
from ..utils.hf_progress import HFProgressTracker, create_hf_progress_callback
from ..utils.tasks import get_task_manager


class F5TTSBackend:
    """F5-TTS/E2-TTS backend using f5-tts package."""

    def __init__(self, model_type: str = "F5TTS_v1_Base"):
        """
        Initialize F5-TTS backend.

        Args:
            model_type: Model type ('F5TTS_v1_Base' or 'E2TTS_Base')
        """
        self.model = None
        self.model_type = model_type
        self.device = self._get_device()
        self._current_model_type = None

    def _get_device(self) -> str:
        """Get the best available device."""
        if torch.cuda.is_available():
            return "cuda"
        # Intel Arc / Intel Xe GPU via intel-extension-for-pytorch (IPEX)
        try:
            import intel_extension_for_pytorch  # noqa: F401
            if hasattr(torch, 'xpu') and torch.xpu.is_available():
                return "xpu"
        except ImportError:
            pass
        # Any GPU on Windows via DirectML (torch-directml)
        try:
            import torch_directml
            if torch_directml.device_count() > 0:
                return torch_directml.device(0)
        except ImportError:
            pass
        # MPS (Apple Silicon) — kept for completeness but MLX backend is preferred
        if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return "cpu"  # MPS disabled for stability; MLX backend handles Apple Silicon
        return "cpu"

    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self.model is not None

    def _get_model_path(self, model_type: str) -> str:
        """
        Get the model identifier for F5-TTS.

        Args:
            model_type: Model type (F5TTS_v1_Base or E2TTS_Base)

        Returns:
            Model type identifier
        """
        valid_models = ["F5TTS_v1_Base", "E2TTS_Base"]

        if model_type not in valid_models:
            raise ValueError(f"Unknown model type: {model_type}. Valid options: {valid_models}")

        return model_type

    def _is_model_cached(self, model_type: str) -> bool:
        """
        Check if the F5-TTS model is already cached locally.

        Note: F5-TTS downloads models to a different cache location than HuggingFace Hub.
        This is a best-effort check and may not be 100% accurate.

        Args:
            model_type: Model type to check

        Returns:
            True if model appears to be cached, False otherwise
        """
        try:
            # F5-TTS downloads models to ~/.cache/f5_tts/ by default
            # Check if model weights exist
            cache_dir = Path.home() / ".cache" / "f5_tts"

            if not cache_dir.exists():
                return False

            # Look for model-specific files
            # F5-TTS models are typically stored with their model_type name
            model_files = list(cache_dir.rglob("*.pt")) + list(cache_dir.rglob("*.pth"))

            # If we find any model files, assume it's cached
            # This is a conservative check; F5-TTS will handle actual validation
            return len(model_files) > 0

        except Exception as e:
            print(f"[_is_model_cached] Error checking cache for {model_type}: {e}")
            return False

    async def load_model_async(self, model_type: Optional[str] = None):
        """
        Lazy load the F5-TTS model.

        Args:
            model_type: Model type to load (F5TTS_v1_Base or E2TTS_Base)
        """
        if model_type is None:
            model_type = self.model_type

        # If already loaded with correct type, return
        if self.model is not None and self._current_model_type == model_type:
            return

        # Unload existing model if different type requested
        if self.model is not None and self._current_model_type != model_type:
            self.unload_model()

        # Run blocking load in thread pool
        await asyncio.to_thread(self._load_model_sync, model_type)

    # Alias for compatibility
    load_model = load_model_async

    def _load_model_sync(self, model_type: str):
        """Synchronous model loading."""
        try:
            progress_manager = get_progress_manager()
            task_manager = get_task_manager()
            model_name = f"f5-tts-{model_type}"

            # Check if model is already cached
            is_cached = self._is_model_cached(model_type)

            # Set up progress callback and tracker
            progress_callback = create_hf_progress_callback(model_name, progress_manager)
            tracker = HFProgressTracker(progress_callback, filter_non_downloads=is_cached)

            # Patch tqdm BEFORE importing f5_tts
            tracker_context = tracker.patch_download()
            tracker_context.__enter__()

            # Import F5TTS
            from f5_tts.api import F5TTS

            # Validate model type
            validated_model_type = self._get_model_path(model_type)

            print(f"Loading F5-TTS model {model_type} on {self.device}...")

            # Only track download progress if model is NOT cached
            if not is_cached:
                # Start tracking download task
                task_manager.start_download(model_name)

                # Initialize progress state so SSE endpoint has initial data to send
                progress_manager.update_progress(
                    model_name=model_name,
                    current=0,
                    total=0,  # Will be updated once actual total is known
                    filename="Connecting to model repository...",
                    status="downloading",
                )

            # Load the model
            try:
                self.model = F5TTS(
                    model_type=validated_model_type,
                    ckpt_file=None,  # Use default checkpoint
                    vocab_file=None,  # Use default vocab
                    ode_method="euler",
                    use_ema=True,
                    device=str(self.device),
                )
            finally:
                # Exit the patch context
                tracker_context.__exit__(None, None, None)

            # Only mark download as complete if we were tracking it
            if not is_cached:
                progress_manager.mark_complete(model_name)
                task_manager.complete_download(model_name)

            self._current_model_type = model_type
            self.model_type = model_type

            print(f"F5-TTS model {model_type} loaded successfully")

        except ImportError as e:
            print(f"Error: f5-tts package not found. Install with: pip install f5-tts")
            progress_manager = get_progress_manager()
            task_manager = get_task_manager()
            model_name = f"f5-tts-{model_type}"
            progress_manager.mark_error(model_name, str(e))
            task_manager.error_download(model_name, str(e))
            raise
        except Exception as e:
            print(f"Error loading F5-TTS model: {e}")
            print(f"Tip: The model will be automatically downloaded on first use.")
            progress_manager = get_progress_manager()
            task_manager = get_task_manager()
            model_name = f"f5-tts-{model_type}"
            progress_manager.mark_error(model_name, str(e))
            task_manager.error_download(model_name, str(e))
            raise

    def unload_model(self):
        """Unload the model to free memory."""
        if self.model is not None:
            del self.model
            self.model = None
            self._current_model_type = None

            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            print("F5-TTS model unloaded")

    async def create_voice_prompt(
        self,
        audio_path: str,
        reference_text: str,
        use_cache: bool = True,
    ) -> Tuple[dict, bool]:
        """
        Create voice prompt from reference audio.

        For F5-TTS, the voice prompt is simply the audio path and reference text,
        as F5-TTS handles embedding extraction internally during inference.

        Args:
            audio_path: Path to reference audio file
            reference_text: Transcript of reference audio
            use_cache: Whether to use cached prompt if available

        Returns:
            Tuple of (voice_prompt_dict, was_cached)
        """
        await self.load_model_async(None)

        # Check cache if enabled
        if use_cache:
            cache_key = get_cache_key(audio_path, reference_text)
            cached_prompt = get_cached_voice_prompt(cache_key)
            if cached_prompt is not None:
                if isinstance(cached_prompt, dict):
                    return cached_prompt, True

        # F5-TTS doesn't require pre-processing the voice prompt
        # It uses the audio file directly during inference
        # Store the paths for later use
        voice_prompt = {
            "audio_path": str(audio_path),
            "reference_text": reference_text,
        }

        # Cache the prompt
        if use_cache:
            cache_key = get_cache_key(audio_path, reference_text)
            cache_voice_prompt(cache_key, voice_prompt)

        return voice_prompt, False

    async def combine_voice_prompts(
        self,
        audio_paths: List[str],
        reference_texts: List[str],
    ) -> Tuple[np.ndarray, str]:
        """
        Combine multiple reference samples for better quality.

        Note: F5-TTS doesn't natively support multi-sample voice prompts like Qwen3-TTS.
        This method concatenates the audio files as a workaround.

        Args:
            audio_paths: List of audio file paths
            reference_texts: List of reference texts

        Returns:
            Tuple of (combined_audio, combined_text)
        """
        combined_audio = []

        for audio_path in audio_paths:
            audio, sr = load_audio(audio_path)
            audio = normalize_audio(audio)
            combined_audio.append(audio)

        # Concatenate audio
        mixed = np.concatenate(combined_audio)
        mixed = normalize_audio(mixed)

        # Combine texts
        combined_text = " ".join(reference_texts)

        return mixed, combined_text

    async def generate(
        self,
        text: str,
        voice_prompt: dict,
        language: str = "en",
        seed: Optional[int] = None,
        instruct: Optional[str] = None,
    ) -> Tuple[np.ndarray, int]:
        """
        Generate audio from text using voice prompt.

        Args:
            text: Text to synthesize
            voice_prompt: Voice prompt dictionary from create_voice_prompt
            language: Language code (not used by F5-TTS, kept for compatibility)
            seed: Random seed for reproducibility
            instruct: Not supported by F5-TTS (ignored)

        Returns:
            Tuple of (audio_array, sample_rate)
        """
        # Load model
        await self.load_model_async(None)

        # Warn if instruct is provided (F5-TTS doesn't support it)
        if instruct is not None:
            print(f"Warning: F5-TTS does not support 'instruct' parameter. Ignoring value: {instruct}")

        def _generate_sync():
            """Run synchronous generation in thread pool."""
            # Set seed if provided
            if seed is not None:
                torch.manual_seed(seed)
                if torch.cuda.is_available():
                    torch.cuda.manual_seed(seed)
                # Also set numpy seed for F5-TTS
                np.random.seed(seed)

            # Get reference audio path and text from voice prompt
            ref_audio_path = voice_prompt.get("audio_path")
            ref_text = voice_prompt.get("reference_text", "")

            if ref_audio_path is None:
                raise ValueError("Voice prompt must contain 'audio_path' field")

            # Create a temporary file for output
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                output_path = tmp_file.name

            try:
                # Generate audio using F5-TTS
                # If ref_text is empty, F5-TTS will use ASR (higher memory cost)
                wav, sample_rate, _ = self.model.infer(
                    ref_file=ref_audio_path,
                    ref_text=ref_text,
                    gen_text=text,
                    file_wave=output_path,
                    seed=seed if seed is not None else -1,
                )

                # Load the generated audio
                audio, sr = sf.read(output_path)

                # Convert to numpy array if needed
                if not isinstance(audio, np.ndarray):
                    audio = np.array(audio)

                # Ensure it's float32
                if audio.dtype != np.float32:
                    audio = audio.astype(np.float32)

                return audio, sr

            finally:
                # Clean up temporary file
                try:
                    Path(output_path).unlink(missing_ok=True)
                except Exception as e:
                    print(f"Warning: Could not delete temporary file {output_path}: {e}")

        # Run blocking inference in thread pool to avoid blocking event loop
        audio, sample_rate = await asyncio.to_thread(_generate_sync)

        return audio, sample_rate
