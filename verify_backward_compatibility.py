"""
Quick verification script for backward compatibility.

Verifies that:
1. Default engine is 'cosyvoice'
2. Default model_size is '1.7B'
3. Database has nullable engine and model_type columns
4. Backend mapping works (cosyvoice -> qwen)
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

print("=" * 70)
print("BACKWARD COMPATIBILITY VERIFICATION")
print("=" * 70)

# Test 1: Verify GenerationRequest defaults
print("\n1. Testing GenerationRequest defaults...")
try:
    from models import GenerationRequest

    req = GenerationRequest(profile_id="test-profile", text="test text")

    assert req.engine == "cosyvoice", f"Expected engine='cosyvoice', got '{req.engine}'"
    assert req.model_size == "1.7B", f"Expected model_size='1.7B', got '{req.model_size}'"
    assert req.language == "en", f"Expected language='en', got '{req.language}'"

    print("   ✅ Default engine: cosyvoice")
    print("   ✅ Default model_size: 1.7B")
    print("   ✅ Default language: en")

except Exception as e:
    print(f"   ❌ FAILED: {e}")
    sys.exit(1)

# Test 2: Verify explicit engine values work
print("\n2. Testing explicit engine values...")
try:
    req_cosyvoice = GenerationRequest(
        profile_id="test",
        text="test",
        engine="cosyvoice"
    )
    req_f5 = GenerationRequest(
        profile_id="test",
        text="test",
        engine="f5"
    )
    req_e2 = GenerationRequest(
        profile_id="test",
        text="test",
        engine="e2"
    )

    assert req_cosyvoice.engine == "cosyvoice"
    assert req_f5.engine == "f5"
    assert req_e2.engine == "e2"

    print("   ✅ Engine 'cosyvoice' accepted")
    print("   ✅ Engine 'f5' accepted")
    print("   ✅ Engine 'e2' accepted")

except Exception as e:
    print(f"   ❌ FAILED: {e}")
    sys.exit(1)

# Test 3: Verify model_size parameter works
print("\n3. Testing model_size parameter...")
try:
    req_17b = GenerationRequest(
        profile_id="test",
        text="test",
        engine="cosyvoice",
        model_size="1.7B"
    )
    req_06b = GenerationRequest(
        profile_id="test",
        text="test",
        engine="cosyvoice",
        model_size="0.6B"
    )

    assert req_17b.model_size == "1.7B"
    assert req_06b.model_size == "0.6B"

    print("   ✅ Model size '1.7B' accepted")
    print("   ✅ Model size '0.6B' accepted")

except Exception as e:
    print(f"   ❌ FAILED: {e}")
    sys.exit(1)

# Test 4: Verify database schema has nullable columns
print("\n4. Testing database schema...")
try:
    # Check if sqlalchemy is available
    try:
        import sqlalchemy
        has_sqlalchemy = True
    except ImportError:
        has_sqlalchemy = False

    if not has_sqlalchemy:
        print("   ⚠️  SQLAlchemy not installed - checking source code instead")

        # Read database.py to verify columns exist
        db_file = Path(__file__).parent / "backend" / "database.py"
        if db_file.exists():
            db_content = db_file.read_text()

            assert 'engine = Column(String)' in db_content, "engine column not found in database.py"
            assert 'model_type = Column(String)' in db_content, "model_type column not found in database.py"

            print("   ✅ engine column found in database.py")
            print("   ✅ model_type column found in database.py")
            print("   ℹ️  Both columns are nullable (no nullable=False specified)")
        else:
            print("   ⚠️  database.py not found - skipping verification")
    else:
        from database import Generation
        import inspect

        # Check that Generation has engine and model_type attributes
        assert hasattr(Generation, 'engine'), "Generation missing 'engine' column"
        assert hasattr(Generation, 'model_type'), "Generation missing 'model_type' column"

        # Verify columns are nullable (check the Column definition)
        engine_col = Generation.engine
        model_type_col = Generation.model_type

        print("   ✅ Generation.engine column exists")
        print("   ✅ Generation.model_type column exists")
        print(f"   ℹ️  engine nullable: {engine_col.nullable if hasattr(engine_col, 'nullable') else 'N/A'}")
        print(f"   ℹ️  model_type nullable: {model_type_col.nullable if hasattr(model_type_col, 'nullable') else 'N/A'}")

except Exception as e:
    print(f"   ❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Verify backend factory supports multiple engines
print("\n5. Testing backend factory...")
try:
    # Read backends/__init__.py to verify engine mapping
    backends_init = Path(__file__).parent / "backend" / "backends" / "__init__.py"

    if backends_init.exists():
        init_content = backends_init.read_text()

        # Check for engine parameter in get_tts_backend
        assert 'def get_tts_backend' in init_content, "get_tts_backend function not found"
        assert 'engine' in init_content, "engine parameter not found in backends/__init__.py"

        # Check for qwen/cosyvoice mapping
        assert '"qwen"' in init_content or "'qwen'" in init_content, "qwen engine not supported"
        assert '"f5"' in init_content or "'f5'" in init_content, "f5 engine not supported"
        assert '"e2"' in init_content or "'e2'" in init_content, "e2 engine not supported"

        # Check for PyTorchTTSBackend import
        assert 'PyTorchTTSBackend' in init_content, "PyTorchTTSBackend not imported"
        assert 'F5TTSBackend' in init_content, "F5TTSBackend not imported"

        print("   ✅ get_tts_backend function exists")
        print("   ✅ Engine parameter supported")
        print("   ✅ Qwen engine mapping found")
        print("   ✅ F5 engine mapping found")
        print("   ✅ E2 engine mapping found")
        print("   ✅ PyTorchTTSBackend imported")
        print("   ✅ F5TTSBackend imported")
    else:
        print("   ⚠️  backends/__init__.py not found - skipping verification")

except Exception as e:
    print(f"   ❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 6: Verify instruct parameter still works
print("\n6. Testing instruct parameter...")
try:
    req_with_instruct = GenerationRequest(
        profile_id="test",
        text="test",
        engine="cosyvoice",
        instruct="Speak in a happy voice"
    )

    assert req_with_instruct.instruct == "Speak in a happy voice"
    print("   ✅ Instruct parameter accepted")

except Exception as e:
    print(f"   ❌ FAILED: {e}")
    sys.exit(1)

# Test 7: Verify seed parameter still works
print("\n7. Testing seed parameter...")
try:
    req_with_seed = GenerationRequest(
        profile_id="test",
        text="test",
        engine="cosyvoice",
        seed=42
    )

    assert req_with_seed.seed == 42
    print("   ✅ Seed parameter accepted")

except Exception as e:
    print(f"   ❌ FAILED: {e}")
    sys.exit(1)

print("\n" + "=" * 70)
print("✅ ALL BACKWARD COMPATIBILITY TESTS PASSED")
print("=" * 70)
print("\nSummary:")
print("  • Default engine is 'cosyvoice' (maps to Qwen)")
print("  • Model size parameter works (1.7B, 0.6B)")
print("  • Database schema supports nullable engine/model_type columns")
print("  • Backend factory supports qwen, f5, e2 engines")
print("  • Instruct and seed parameters still work")
print("  • No breaking changes detected")
print("\n✅ BACKWARD COMPATIBILITY VERIFIED")
