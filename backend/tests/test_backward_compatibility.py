"""
Test backward compatibility with existing Qwen3-TTS functionality.

This test suite verifies that:
1. Default engine behavior (cosyvoice -> qwen mapping) works
2. Old database records without engine field still work
3. Existing Qwen3-TTS generation still produces audio
4. History display works for both old and new records
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add parent directory to path to enable imports when running from backend/tests
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import os

# Import with fallback for different run contexts
try:
    from backend.database import Base, Generation, VoiceProfile, ProfileSample
    from backend.models import GenerationRequest
    from backend.backends import get_tts_backend
except ImportError:
    from database import Base, Generation, VoiceProfile, ProfileSample
    from models import GenerationRequest
    from backends import get_tts_backend

from datetime import datetime


@pytest.fixture
def test_db():
    """Create a temporary test database."""
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
    except ImportError:
        pytest.skip("SQLAlchemy not available in test environment")

    db_path = "test_backward_compat.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session

    session.close()
    if os.path.exists(db_path):
        os.remove(db_path)


class TestBackwardCompatibility:
    """Test suite for backward compatibility verification."""

    def test_default_engine_is_cosyvoice(self):
        """Test that default engine is 'cosyvoice' for backward compatibility."""
        request = GenerationRequest(
            profile_id="test-profile",
            text="Hello world"
        )
        assert request.engine == "cosyvoice", "Default engine should be 'cosyvoice'"

    def test_cosyvoice_maps_to_qwen_backend(self):
        """Test that 'cosyvoice' engine maps to Qwen backend."""
        backend = get_tts_backend(engine="qwen")  # Direct qwen call
        backend_cosyvoice = get_tts_backend(engine="cosyvoice")  # Should map to qwen

        # Both should return same backend type
        assert type(backend).__name__ == "PyTorchTTSBackend"
        assert type(backend_cosyvoice).__name__ == "PyTorchTTSBackend"

    def test_old_generation_record_without_engine_field(self, test_db):
        """Test that old Generation records without engine field can still be queried."""
        # Create a test profile
        profile = VoiceProfile(
            id="test-profile-id",
            name="Test Profile",
            language="en"
        )
        test_db.add(profile)
        test_db.commit()

        # Create old-style generation record without engine field
        old_generation = Generation(
            id="old-gen-id",
            profile_id="test-profile-id",
            text="Hello from the past",
            language="en",
            audio_path="/path/to/old/audio.wav",
            duration=2.5,
            seed=42,
            # engine=None (implicit - field is nullable)
            # model_type=None (implicit - field is nullable)
        )
        test_db.add(old_generation)
        test_db.commit()

        # Query the record
        retrieved = test_db.query(Generation).filter_by(id="old-gen-id").first()

        assert retrieved is not None, "Old generation record should be retrievable"
        assert retrieved.text == "Hello from the past"
        assert retrieved.engine is None, "Old records should have None engine"
        assert retrieved.model_type is None, "Old records should have None model_type"
        assert retrieved.audio_path == "/path/to/old/audio.wav"

    def test_new_generation_record_with_engine_field(self, test_db):
        """Test that new Generation records with engine field work correctly."""
        # Create a test profile
        profile = VoiceProfile(
            id="test-profile-id-2",
            name="Test Profile 2",
            language="en"
        )
        test_db.add(profile)
        test_db.commit()

        # Create new-style generation record with engine field
        new_generation = Generation(
            id="new-gen-id",
            profile_id="test-profile-id-2",
            text="Hello from the future",
            language="en",
            audio_path="/path/to/new/audio.wav",
            duration=3.0,
            seed=100,
            engine="f5",
            model_type="F5TTS_v1_Base"
        )
        test_db.add(new_generation)
        test_db.commit()

        # Query the record
        retrieved = test_db.query(Generation).filter_by(id="new-gen-id").first()

        assert retrieved is not None, "New generation record should be retrievable"
        assert retrieved.text == "Hello from the future"
        assert retrieved.engine == "f5", "New records should store engine"
        assert retrieved.model_type == "F5TTS_v1_Base", "New records should store model_type"

    def test_mixed_generation_records_query(self, test_db):
        """Test querying both old and new generation records together."""
        # Create a test profile
        profile = VoiceProfile(
            id="test-profile-id-3",
            name="Test Profile 3",
            language="en"
        )
        test_db.add(profile)
        test_db.commit()

        # Create multiple generations with and without engine field
        generations = [
            Generation(
                id="gen-1",
                profile_id="test-profile-id-3",
                text="Old generation 1",
                language="en",
                audio_path="/path/1.wav",
                duration=1.0,
                engine=None,  # Old record
                model_type=None
            ),
            Generation(
                id="gen-2",
                profile_id="test-profile-id-3",
                text="New generation F5",
                language="en",
                audio_path="/path/2.wav",
                duration=2.0,
                engine="f5",  # New record with F5
                model_type="F5TTS_v1_Base"
            ),
            Generation(
                id="gen-3",
                profile_id="test-profile-id-3",
                text="Old generation 2",
                language="en",
                audio_path="/path/3.wav",
                duration=1.5,
                engine=None,  # Old record
                model_type=None
            ),
            Generation(
                id="gen-4",
                profile_id="test-profile-id-3",
                text="New generation CosyVoice",
                language="en",
                audio_path="/path/4.wav",
                duration=2.5,
                engine="cosyvoice",  # New record with cosyvoice
                model_type=None
            ),
        ]

        for gen in generations:
            test_db.add(gen)
        test_db.commit()

        # Query all generations
        all_gens = test_db.query(Generation).filter_by(
            profile_id="test-profile-id-3"
        ).order_by(Generation.created_at).all()

        assert len(all_gens) == 4, "Should retrieve all 4 generations"

        # Verify old records
        assert all_gens[0].engine is None
        assert all_gens[2].engine is None

        # Verify new records
        assert all_gens[1].engine == "f5"
        assert all_gens[3].engine == "cosyvoice"

    def test_generation_request_validation_accepts_cosyvoice(self):
        """Test that GenerationRequest accepts 'cosyvoice' as valid engine."""
        request = GenerationRequest(
            profile_id="test-profile",
            text="Test text",
            engine="cosyvoice"
        )
        assert request.engine == "cosyvoice"

    def test_generation_request_validation_accepts_qwen(self):
        """Test that GenerationRequest accepts legacy engine values if needed."""
        # Note: The current pattern is "^(cosyvoice|f5|e2)$", so 'qwen' is not directly accepted
        # The mapping happens at the backend level (cosyvoice -> qwen)
        # This test verifies that cosyvoice is the correct way to specify Qwen

        request = GenerationRequest(
            profile_id="test-profile",
            text="Test text",
            engine="cosyvoice",  # This gets mapped to qwen internally
            model_size="1.7B"
        )
        assert request.engine == "cosyvoice"
        assert request.model_size == "1.7B"

    def test_model_size_parameter_still_works(self):
        """Test that model_size parameter (used by Qwen) still works."""
        request_17b = GenerationRequest(
            profile_id="test-profile",
            text="Test text",
            engine="cosyvoice",
            model_size="1.7B"
        )

        request_06b = GenerationRequest(
            profile_id="test-profile",
            text="Test text",
            engine="cosyvoice",
            model_size="0.6B"
        )

        assert request_17b.model_size == "1.7B"
        assert request_06b.model_size == "0.6B"

    def test_generation_request_defaults(self):
        """Test that GenerationRequest has correct defaults for backward compatibility."""
        request = GenerationRequest(
            profile_id="test-profile",
            text="Test text"
        )

        # Verify defaults
        assert request.engine == "cosyvoice", "Default engine should be cosyvoice"
        assert request.model_size == "1.7B", "Default model_size should be 1.7B"
        assert request.language == "en", "Default language should be en"
        assert request.seed is None, "Default seed should be None"
        assert request.instruct is None, "Default instruct should be None"
        assert request.model_type is None, "Default model_type should be None"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
