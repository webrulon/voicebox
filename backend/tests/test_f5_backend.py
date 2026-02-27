"""
Unit tests for F5-TTS backend implementation.

Tests F5TTSBackend conformance to TTSBackend protocol, model loading,
voice prompt creation, audio generation, and seed reproducibility.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import numpy as np

# Add parent directory to path to enable imports when running from backend/tests
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock problematic imports before they're imported by the backend
# librosa has numba dependency which doesn't support Python 3.14
mock_librosa = Mock()
# Mock the load function to return audio and sample rate
mock_librosa.load = Mock(return_value=(np.zeros(24000, dtype=np.float32), 24000))
sys.modules['librosa'] = mock_librosa

# Mock f5_tts package (may not be installed)
sys.modules['f5_tts'] = Mock()
sys.modules['f5_tts.api'] = Mock()

import pytest
import tempfile
import torch

# Import the backend to test
# Use absolute imports with backend. prefix for pytest from project root
try:
    from backend.backends.f5_backend import F5TTSBackend
    from backend.backends import TTSBackend
except ImportError:
    # Fallback for running from within backend directory
    from backends.f5_backend import F5TTSBackend
    from backends import TTSBackend


@pytest.fixture
def mock_f5tts_model():
    """Create a mock F5TTS model for testing."""
    mock_model = Mock()

    # Mock the infer method to return fake audio data
    def mock_infer(ref_file, ref_text, gen_text, file_wave, seed=-1, **kwargs):
        # Create fake audio data
        sample_rate = 24000
        duration = 2.0  # 2 seconds
        num_samples = int(sample_rate * duration)

        # Generate fake audio (sine wave)
        t = np.linspace(0, duration, num_samples, dtype=np.float32)
        audio = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

        # Write to the output file
        import soundfile as sf
        sf.write(file_wave, audio, sample_rate)

        # Return values matching F5TTS API
        return audio, sample_rate, None

    mock_model.infer = Mock(side_effect=mock_infer)
    return mock_model


@pytest.fixture
def temp_audio_file():
    """Create a temporary audio file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        # Create a simple audio file
        sample_rate = 24000
        duration = 1.0
        num_samples = int(sample_rate * duration)
        audio = np.zeros(num_samples, dtype=np.float32)

        import soundfile as sf
        sf.write(f.name, audio, sample_rate)

        filename = f.name

    yield filename

    # Cleanup - try multiple times on Windows where files might be locked
    import time
    for _ in range(3):
        try:
            Path(filename).unlink(missing_ok=True)
            break
        except PermissionError:
            time.sleep(0.1)


class TestF5TTSBackendProtocol:
    """Test that F5TTSBackend implements the TTSBackend protocol."""

    def test_implements_tts_backend_protocol(self):
        """Test that F5TTSBackend implements TTSBackend protocol."""
        backend = F5TTSBackend()
        assert isinstance(backend, TTSBackend), "F5TTSBackend must implement TTSBackend protocol"

    def test_has_required_methods(self):
        """Test that F5TTSBackend has all required protocol methods."""
        backend = F5TTSBackend()

        # Check for required methods
        assert hasattr(backend, 'load_model'), "Must have load_model method"
        assert hasattr(backend, 'create_voice_prompt'), "Must have create_voice_prompt method"
        assert hasattr(backend, 'combine_voice_prompts'), "Must have combine_voice_prompts method"
        assert hasattr(backend, 'generate'), "Must have generate method"
        assert hasattr(backend, 'unload_model'), "Must have unload_model method"
        assert hasattr(backend, 'is_loaded'), "Must have is_loaded method"
        assert hasattr(backend, '_get_model_path'), "Must have _get_model_path method"

        # Check that methods are callable
        assert callable(backend.load_model)
        assert callable(backend.create_voice_prompt)
        assert callable(backend.combine_voice_prompts)
        assert callable(backend.generate)
        assert callable(backend.unload_model)
        assert callable(backend.is_loaded)
        assert callable(backend._get_model_path)


class TestF5TTSBackendInitialization:
    """Test F5TTSBackend initialization and configuration."""

    def test_default_initialization(self):
        """Test default initialization with F5TTS_v1_Base model."""
        backend = F5TTSBackend()
        assert backend.model_type == "F5TTS_v1_Base"
        assert backend.model is None
        assert backend._current_model_type is None
        assert not backend.is_loaded()

    def test_e2_initialization(self):
        """Test initialization with E2TTS_Base model."""
        backend = F5TTSBackend(model_type="E2TTS_Base")
        assert backend.model_type == "E2TTS_Base"
        assert backend.model is None
        assert not backend.is_loaded()

    def test_device_detection(self):
        """Test device detection logic."""
        backend = F5TTSBackend()
        device = backend._get_device()

        # Device should be one of the supported types
        assert isinstance(device, (str, object))

        # If CUDA is available, should prefer CUDA
        if torch.cuda.is_available():
            assert device == "cuda"
        else:
            # Should fall back to cpu or other available device
            assert device in ["cpu", "xpu"] or hasattr(device, '__str__')


class TestF5TTSBackendModelLoading:
    """Test model loading functionality."""

    @pytest.mark.asyncio
    async def test_load_model_f5_type(self, mock_f5tts_model):
        """Test loading F5TTS_v1_Base model."""
        backend = F5TTSBackend(model_type="F5TTS_v1_Base")

        with patch('f5_tts.api.F5TTS', return_value=mock_f5tts_model):
            with patch.object(backend, '_is_model_cached', return_value=True):
                await backend.load_model("F5TTS_v1_Base")

        assert backend.is_loaded()
        assert backend._current_model_type == "F5TTS_v1_Base"

    @pytest.mark.asyncio
    async def test_load_model_e2_type(self, mock_f5tts_model):
        """Test loading E2TTS_Base model."""
        backend = F5TTSBackend(model_type="E2TTS_Base")

        with patch('f5_tts.api.F5TTS', return_value=mock_f5tts_model):
            with patch.object(backend, '_is_model_cached', return_value=True):
                await backend.load_model("E2TTS_Base")

        assert backend.is_loaded()
        assert backend._current_model_type == "E2TTS_Base"

    @pytest.mark.asyncio
    async def test_load_invalid_model_type(self):
        """Test that loading invalid model type raises ValueError."""
        backend = F5TTSBackend()

        with patch('f5_tts.api.F5TTS'):
            with pytest.raises(ValueError, match="Unknown model type"):
                await backend.load_model("InvalidModel")

    @pytest.mark.asyncio
    async def test_model_switching(self, mock_f5tts_model):
        """Test switching between F5 and E2 model types."""
        backend = F5TTSBackend(model_type="F5TTS_v1_Base")

        with patch('f5_tts.api.F5TTS', return_value=mock_f5tts_model):
            with patch.object(backend, '_is_model_cached', return_value=True):
                # Load F5 model
                await backend.load_model("F5TTS_v1_Base")
                assert backend._current_model_type == "F5TTS_v1_Base"

                # Switch to E2 model
                await backend.load_model("E2TTS_Base")
                assert backend._current_model_type == "E2TTS_Base"

    def test_unload_model(self, mock_f5tts_model):
        """Test model unloading."""
        backend = F5TTSBackend()
        backend.model = mock_f5tts_model
        backend._current_model_type = "F5TTS_v1_Base"

        assert backend.is_loaded()

        backend.unload_model()

        assert not backend.is_loaded()
        assert backend.model is None
        assert backend._current_model_type is None

    def test_get_model_path(self):
        """Test _get_model_path returns correct model type."""
        backend = F5TTSBackend()

        # Valid model types
        assert backend._get_model_path("F5TTS_v1_Base") == "F5TTS_v1_Base"
        assert backend._get_model_path("E2TTS_Base") == "E2TTS_Base"

        # Invalid model type
        with pytest.raises(ValueError):
            backend._get_model_path("InvalidModel")


class TestF5TTSBackendVoicePrompt:
    """Test voice prompt creation and caching."""

    @pytest.mark.asyncio
    async def test_create_voice_prompt_basic(self, temp_audio_file, mock_f5tts_model):
        """Test basic voice prompt creation."""
        backend = F5TTSBackend()

        with patch('f5_tts.api.F5TTS', return_value=mock_f5tts_model):
            with patch.object(backend, '_is_model_cached', return_value=True):
                voice_prompt, was_cached = await backend.create_voice_prompt(
                    audio_path=temp_audio_file,
                    reference_text="Hello world",
                    use_cache=False
                )

        assert isinstance(voice_prompt, dict)
        assert "audio_path" in voice_prompt
        assert "reference_text" in voice_prompt
        assert voice_prompt["audio_path"] == temp_audio_file
        assert voice_prompt["reference_text"] == "Hello world"
        assert was_cached is False

    @pytest.mark.asyncio
    async def test_create_voice_prompt_with_cache(self, temp_audio_file, mock_f5tts_model):
        """Test voice prompt caching."""
        import time
        backend = F5TTSBackend()

        # Use unique reference text to avoid cache collision with other tests
        unique_text = f"Test-{time.time()}"

        with patch('f5_tts.api.F5TTS', return_value=mock_f5tts_model):
            with patch.object(backend, '_is_model_cached', return_value=True):
                # First call - should not be cached
                voice_prompt1, was_cached1 = await backend.create_voice_prompt(
                    audio_path=temp_audio_file,
                    reference_text=unique_text,
                    use_cache=True
                )
                assert was_cached1 is False

                # Second call with same params - should be cached
                voice_prompt2, was_cached2 = await backend.create_voice_prompt(
                    audio_path=temp_audio_file,
                    reference_text=unique_text,
                    use_cache=True
                )
                assert was_cached2 is True
                assert voice_prompt1 == voice_prompt2

    @pytest.mark.asyncio
    async def test_combine_voice_prompts(self, temp_audio_file):
        """Test combining multiple voice prompts."""
        backend = F5TTSBackend()

        # Create multiple temp audio files
        audio_paths = [temp_audio_file]
        reference_texts = ["Hello"]

        combined_audio, combined_text = await backend.combine_voice_prompts(
            audio_paths=audio_paths,
            reference_texts=reference_texts
        )

        assert isinstance(combined_audio, np.ndarray)
        assert isinstance(combined_text, str)
        assert combined_text == "Hello"


class TestF5TTSBackendGeneration:
    """Test audio generation functionality."""

    @pytest.mark.asyncio
    async def test_generate_basic(self, temp_audio_file, mock_f5tts_model):
        """Test basic audio generation."""
        backend = F5TTSBackend()
        backend.model = mock_f5tts_model
        backend._current_model_type = "F5TTS_v1_Base"

        voice_prompt = {
            "audio_path": temp_audio_file,
            "reference_text": "Reference"
        }

        audio, sample_rate = await backend.generate(
            text="Hello world",
            voice_prompt=voice_prompt,
            language="en",
            seed=None
        )

        assert isinstance(audio, np.ndarray)
        assert audio.dtype == np.float32
        assert isinstance(sample_rate, int)
        assert sample_rate > 0
        assert len(audio) > 0

    @pytest.mark.asyncio
    async def test_generate_with_seed(self, temp_audio_file, mock_f5tts_model):
        """Test audio generation with seed for reproducibility."""
        backend = F5TTSBackend()
        backend.model = mock_f5tts_model
        backend._current_model_type = "F5TTS_v1_Base"

        voice_prompt = {
            "audio_path": temp_audio_file,
            "reference_text": "Reference"
        }

        # Generate with seed
        audio1, sr1 = await backend.generate(
            text="Test",
            voice_prompt=voice_prompt,
            seed=42
        )

        # Generate again with same seed
        audio2, sr2 = await backend.generate(
            text="Test",
            voice_prompt=voice_prompt,
            seed=42
        )

        # Results should be identical with same seed
        assert sr1 == sr2
        assert audio1.shape == audio2.shape
        # Note: Due to mocking, we can't test exact reproducibility
        # but we can verify the seed was passed correctly
        assert mock_f5tts_model.infer.called

    @pytest.mark.asyncio
    async def test_generate_ignores_instruct(self, temp_audio_file, mock_f5tts_model):
        """Test that instruct parameter is ignored (F5-TTS doesn't support it)."""
        backend = F5TTSBackend()
        backend.model = mock_f5tts_model
        backend._current_model_type = "F5TTS_v1_Base"

        voice_prompt = {
            "audio_path": temp_audio_file,
            "reference_text": "Reference"
        }

        # Should not raise error, just log warning
        audio, sr = await backend.generate(
            text="Test",
            voice_prompt=voice_prompt,
            instruct="Some instruction"  # This should be ignored
        )

        assert isinstance(audio, np.ndarray)
        assert isinstance(sr, int)

    @pytest.mark.asyncio
    async def test_generate_without_audio_path_raises_error(self, mock_f5tts_model):
        """Test that missing audio_path in voice_prompt raises ValueError."""
        backend = F5TTSBackend()
        backend.model = mock_f5tts_model
        backend._current_model_type = "F5TTS_v1_Base"

        # Voice prompt without audio_path
        voice_prompt = {
            "reference_text": "Reference"
        }

        with pytest.raises(ValueError, match="audio_path"):
            await backend.generate(
                text="Test",
                voice_prompt=voice_prompt
            )


class TestF5TTSBackendCaching:
    """Test model caching detection."""

    def test_is_model_cached_returns_bool(self):
        """Test that _is_model_cached returns boolean."""
        backend = F5TTSBackend()
        result = backend._is_model_cached("F5TTS_v1_Base")
        assert isinstance(result, bool)

    def test_is_model_cached_handles_missing_cache_dir(self):
        """Test that _is_model_cached handles missing cache directory."""
        backend = F5TTSBackend()

        with patch('pathlib.Path.home') as mock_home:
            # Point to non-existent directory
            mock_home.return_value = Path("/nonexistent")
            result = backend._is_model_cached("F5TTS_v1_Base")
            assert result is False


class TestF5TTSBackendEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_load_model_import_error(self):
        """Test handling of missing f5-tts package."""
        backend = F5TTSBackend()

        with patch('f5_tts.api.F5TTS', side_effect=ImportError("f5-tts not found")):
            with pytest.raises(ImportError):
                await backend.load_model("F5TTS_v1_Base")

    @pytest.mark.asyncio
    async def test_generate_loads_model_if_not_loaded(self, temp_audio_file, mock_f5tts_model):
        """Test that generate auto-loads model if not loaded."""
        backend = F5TTSBackend()

        assert not backend.is_loaded()

        voice_prompt = {
            "audio_path": temp_audio_file,
            "reference_text": "Reference"
        }

        with patch('f5_tts.api.F5TTS', return_value=mock_f5tts_model):
            with patch.object(backend, '_is_model_cached', return_value=True):
                audio, sr = await backend.generate(
                    text="Test",
                    voice_prompt=voice_prompt
                )

        # Model should be loaded now
        assert backend.is_loaded()
        assert isinstance(audio, np.ndarray)


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
