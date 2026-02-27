"""
Backend abstraction layer for TTS and STT.

Provides a unified interface for MLX and PyTorch backends.
"""

from typing import Protocol, Optional, Tuple, List
from typing_extensions import runtime_checkable
import numpy as np

from ..platform_detect import get_backend_type


@runtime_checkable
class TTSBackend(Protocol):
    """Protocol for TTS backend implementations."""
    
    async def load_model(self, model_size: str) -> None:
        """Load TTS model."""
        ...
    
    async def create_voice_prompt(
        self,
        audio_path: str,
        reference_text: str,
        use_cache: bool = True,
    ) -> Tuple[dict, bool]:
        """
        Create voice prompt from reference audio.
        
        Returns:
            Tuple of (voice_prompt_dict, was_cached)
        """
        ...
    
    async def combine_voice_prompts(
        self,
        audio_paths: List[str],
        reference_texts: List[str],
    ) -> Tuple[np.ndarray, str]:
        """
        Combine multiple voice prompts.
        
        Returns:
            Tuple of (combined_audio_array, combined_text)
        """
        ...
    
    async def generate(
        self,
        text: str,
        voice_prompt: dict,
        language: str = "en",
        seed: Optional[int] = None,
        instruct: Optional[str] = None,
    ) -> Tuple[np.ndarray, int]:
        """
        Generate audio from text.
        
        Returns:
            Tuple of (audio_array, sample_rate)
        """
        ...
    
    def unload_model(self) -> None:
        """Unload model to free memory."""
        ...
    
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        ...
    
    def _get_model_path(self, model_size: str) -> str:
        """
        Get model path for a given size.
        
        Returns:
            Model path or HuggingFace Hub ID
        """
        ...


@runtime_checkable
class STTBackend(Protocol):
    """Protocol for STT (Speech-to-Text) backend implementations."""
    
    async def load_model(self, model_size: str) -> None:
        """Load STT model."""
        ...
    
    async def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
    ) -> str:
        """
        Transcribe audio to text.
        
        Returns:
            Transcribed text
        """
        ...
    
    def unload_model(self) -> None:
        """Unload model to free memory."""
        ...
    
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        ...


# Global backend instances
# Store backend instances per engine to support multiple engines
_tts_backends: dict[str, TTSBackend] = {}
_stt_backend: Optional[STTBackend] = None


def get_tts_backend(engine: str = "qwen", model_type: Optional[str] = None) -> TTSBackend:
    """
    Get or create TTS backend instance based on engine selection.

    Args:
        engine: TTS engine to use ('qwen', 'f5', or 'e2')
        model_type: Optional model type for F5/E2 engines
                   ('F5TTS_v1_Base' for F5, 'E2TTS_Base' for E2)

    Returns:
        TTS backend instance for the selected engine
    """
    global _tts_backends

    # Normalize engine name
    engine = engine.lower()

    # Validate engine
    valid_engines = ["qwen", "f5", "e2"]
    if engine not in valid_engines:
        raise ValueError(f"Invalid engine '{engine}'. Must be one of: {valid_engines}")

    # For F5 and E2, use model_type to create unique cache key
    # This allows switching between F5 and E2 model types
    if engine in ["f5", "e2"]:
        if model_type is None:
            # Default model types
            model_type = "F5TTS_v1_Base" if engine == "f5" else "E2TTS_Base"
        cache_key = f"{engine}:{model_type}"
    else:
        cache_key = engine

    # Return cached backend if exists
    if cache_key in _tts_backends:
        return _tts_backends[cache_key]

    # Create new backend based on engine
    if engine == "qwen":
        backend_type = get_backend_type()

        if backend_type == "mlx":
            from .mlx_backend import MLXTTSBackend
            backend = MLXTTSBackend()
        else:
            from .pytorch_backend import PyTorchTTSBackend
            backend = PyTorchTTSBackend()

    elif engine in ["f5", "e2"]:
        from .f5_backend import F5TTSBackend
        # F5TTSBackend supports both F5 and E2 via model_type parameter
        backend = F5TTSBackend(model_type=model_type)

    else:
        # Should never reach here due to validation above
        raise ValueError(f"Unsupported engine: {engine}")

    # Cache the backend
    _tts_backends[cache_key] = backend

    return backend


def get_stt_backend() -> STTBackend:
    """
    Get or create STT backend instance based on platform.
    
    Returns:
        STT backend instance (MLX or PyTorch)
    """
    global _stt_backend
    
    if _stt_backend is None:
        backend_type = get_backend_type()
        
        if backend_type == "mlx":
            from .mlx_backend import MLXSTTBackend
            _stt_backend = MLXSTTBackend()
        else:
            from .pytorch_backend import PyTorchSTTBackend
            _stt_backend = PyTorchSTTBackend()
    
    return _stt_backend


def reset_backends():
    """Reset backend instances (useful for testing)."""
    global _tts_backends, _stt_backend
    _tts_backends = {}
    _stt_backend = None
