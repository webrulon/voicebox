"""
End-to-end test for E2-TTS generation via API.

This test verifies the complete flow:
1. Create a voice profile with sample audio
2. Generate speech using E2-TTS engine
3. Verify audio file is created
4. Verify generation appears in history with engine='e2'
"""

import pytest
import requests
import tempfile
import numpy as np
import wave
from pathlib import Path
import time
import json


def create_test_audio(duration=3.0, sample_rate=24000):
    """Create a test audio file with a sine wave."""
    t = np.linspace(0, duration, int(sample_rate * duration))
    # Create a simple sine wave at 440 Hz (A4 note)
    audio = np.sin(2 * np.pi * 440 * t) * 0.3
    # Convert to int16
    audio_int16 = (audio * 32767).astype(np.int16)
    return audio_int16, sample_rate


def save_wav_file(filepath, audio, sample_rate):
    """Save audio data as WAV file."""
    with wave.open(str(filepath), 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 2 bytes per sample (int16)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio.tobytes())


@pytest.fixture
def test_audio_file():
    """Create a temporary test audio file."""
    audio, sample_rate = create_test_audio()
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        save_wav_file(f.name, audio, sample_rate)
        yield f.name
    # Cleanup
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def api_base_url():
    """Base URL for the API."""
    return "http://localhost:8000"


@pytest.fixture
def check_server_running(api_base_url):
    """Check if the server is running."""
    try:
        response = requests.get(f"{api_base_url}/health", timeout=2)
        if response.status_code == 200:
            return True
    except requests.exceptions.RequestException:
        pass
    pytest.skip("Backend server is not running. Start with: uvicorn backend.main:app")


def test_e2e_e2_generation(api_base_url, test_audio_file, check_server_running):
    """
    End-to-end test for E2-TTS generation.

    Steps:
    1. Create a voice profile with sample audio
    2. Generate speech using E2-TTS engine
    3. Verify audio file is created
    4. Verify generation appears in history with engine='e2'
    """
    # Step 1: Create a voice profile
    with open(test_audio_file, 'rb') as audio_file:
        files = {'file': ('test_audio.wav', audio_file, 'audio/wav')}
        data = {
            'name': f'E2E Test Profile E2 {time.time()}',
            'transcription': 'This is a test audio for E2-TTS generation.'
        }
        response = requests.post(
            f"{api_base_url}/profiles/create",
            files=files,
            data=data
        )

    assert response.status_code == 200, f"Failed to create profile: {response.text}"
    profile = response.json()
    profile_id = profile['id']

    print(f"✓ Created voice profile: {profile['name']} (ID: {profile_id})")

    try:
        # Step 2: Generate speech with E2-TTS engine
        generation_request = {
            'profile_id': profile_id,
            'text': 'Hello, this is a test of E2-TTS engine for voice cloning.',
            'engine': 'e2',
            'model_type': 'E2TTS_Base'
        }

        print(f"Generating speech with E2-TTS engine...")
        response = requests.post(
            f"{api_base_url}/generate",
            json=generation_request,
            timeout=300  # E2-TTS may take time for first run (model download)
        )

        assert response.status_code == 200, f"Generation failed: {response.text}"
        generation = response.json()
        generation_id = generation['id']

        print(f"✓ Generated speech (ID: {generation_id})")

        # Step 3: Verify audio file is created
        audio_url = f"{api_base_url}/generations/{generation_id}/audio"
        response = requests.get(audio_url)

        assert response.status_code == 200, f"Audio file not found: {response.text}"
        assert len(response.content) > 0, "Audio file is empty"
        assert response.headers.get('content-type') in ['audio/wav', 'audio/mpeg'], \
            f"Invalid audio type: {response.headers.get('content-type')}"

        print(f"✓ Audio file created ({len(response.content)} bytes)")

        # Step 4: Verify generation appears in history with engine='e2'
        response = requests.get(f"{api_base_url}/generations/history")
        assert response.status_code == 200, f"Failed to get history: {response.text}"

        history = response.json()
        generation_found = None
        for gen in history:
            if gen['id'] == generation_id:
                generation_found = gen
                break

        assert generation_found is not None, f"Generation {generation_id} not found in history"
        assert generation_found['engine'] == 'e2', \
            f"Expected engine='e2', got engine='{generation_found.get('engine')}'"
        assert generation_found['model_type'] == 'E2TTS_Base', \
            f"Expected model_type='E2TTS_Base', got '{generation_found.get('model_type')}'"

        print(f"✓ Generation found in history with engine='e2' and model_type='E2TTS_Base'")

        # Step 5: Verify audio playback metadata
        assert 'audio_file' in generation_found or 'audio_path' in generation_found, \
            "No audio file path in generation"

        print(f"✓ Audio playback metadata verified")

        print("\n=== E2E Test PASSED ===")
        print(f"Profile ID: {profile_id}")
        print(f"Generation ID: {generation_id}")
        print(f"Engine: {generation_found['engine']}")
        print(f"Model Type: {generation_found['model_type']}")
        print(f"Audio Size: {len(response.content)} bytes")

    finally:
        # Cleanup: Delete the test profile
        try:
            requests.delete(f"{api_base_url}/profiles/{profile_id}")
            print(f"✓ Cleaned up test profile")
        except Exception as e:
            print(f"Warning: Failed to cleanup profile: {e}")


if __name__ == "__main__":
    # Allow running this test directly
    pytest.main([__file__, "-v", "-s"])
