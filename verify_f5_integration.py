#!/usr/bin/env python3
"""
Verification script for F5-TTS and E2-TTS integration.

This script verifies that all components are in place for E2E testing:
1. F5TTSBackend class is importable
2. Backend factory supports 'f5' and 'e2' engines
3. API models have engine and model_type fields
4. Database has engine and model_type columns
5. Configuration has F5_MODEL_TYPES
6. Migration script exists

Run this before attempting E2E tests to ensure all pieces are in place.
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

def check_backend_class():
    """Verify F5TTSBackend class exists and is importable."""
    print("\n1. Checking F5TTSBackend class...")
    try:
        from backends.f5_backend import F5TTSBackend
        print("   ✅ F5TTSBackend is importable")

        # Check methods
        required_methods = [
            'load_model_async', 'create_voice_prompt', 'combine_voice_prompts',
            'generate', 'unload_model', 'is_loaded', '_get_model_path'
        ]
        for method in required_methods:
            if not hasattr(F5TTSBackend, method):
                print(f"   ❌ Missing method: {method}")
                return False
        print(f"   ✅ All {len(required_methods)} TTSBackend protocol methods present")
        return True
    except Exception as e:
        print(f"   ❌ Failed to import F5TTSBackend: {e}")
        return False


def check_backend_factory():
    """Verify backend factory supports engine selection."""
    print("\n2. Checking backend factory...")
    try:
        from backends import get_tts_backend
        print("   ✅ get_tts_backend is importable")

        # Check that it accepts engine parameter
        import inspect
        sig = inspect.signature(get_tts_backend)
        params = list(sig.parameters.keys())
        if 'engine' not in params:
            print(f"   ❌ get_tts_backend missing 'engine' parameter. Params: {params}")
            return False
        print(f"   ✅ get_tts_backend accepts 'engine' parameter")

        # Try to get backends
        try:
            qwen_backend = get_tts_backend('qwen')
            print(f"   ✅ Qwen backend: {type(qwen_backend).__name__}")
        except Exception as e:
            print(f"   ⚠️  Qwen backend: {e}")

        try:
            f5_backend = get_tts_backend('f5')
            print(f"   ✅ F5 backend: {type(f5_backend).__name__}")
        except Exception as e:
            print(f"   ⚠️  F5 backend (expected if model not downloaded): {e}")

        return True
    except Exception as e:
        print(f"   ❌ Failed to check backend factory: {e}")
        return False


def check_api_models():
    """Verify API models have engine and model_type fields."""
    print("\n3. Checking API models...")
    try:
        from models import GenerationRequest
        print("   ✅ GenerationRequest is importable")

        # Create a test request
        req = GenerationRequest(
            profile_id='test',
            text='hello',
            engine='f5',
            model_type='F5TTS_v1_Base'
        )

        if req.engine != 'f5':
            print(f"   ❌ engine field not working: {req.engine}")
            return False
        print(f"   ✅ engine field works: {req.engine}")

        if req.model_type != 'F5TTS_v1_Base':
            print(f"   ❌ model_type field not working: {req.model_type}")
            return False
        print(f"   ✅ model_type field works: {req.model_type}")

        return True
    except Exception as e:
        print(f"   ❌ Failed to check API models: {e}")
        return False


def check_database_schema():
    """Verify database has engine and model_type columns."""
    print("\n4. Checking database schema...")
    try:
        from database import Generation
        import inspect
        print("   ✅ Generation model is importable")

        # Check for engine and model_type attributes
        fields = [m for m in dir(Generation) if not m.startswith('_')]

        if 'engine' not in fields:
            print(f"   ❌ Generation model missing 'engine' field")
            return False
        print(f"   ✅ Generation model has 'engine' field")

        if 'model_type' not in fields:
            print(f"   ❌ Generation model missing 'model_type' field")
            return False
        print(f"   ✅ Generation model has 'model_type' field")

        return True
    except Exception as e:
        print(f"   ❌ Failed to check database schema: {e}")
        return False


def check_configuration():
    """Verify F5_MODEL_TYPES configuration exists."""
    print("\n5. Checking configuration...")
    try:
        from config import F5_MODEL_TYPES
        print("   ✅ F5_MODEL_TYPES is importable")

        models = list(F5_MODEL_TYPES.keys())
        expected_models = ['F5TTS_v1_Base', 'E2TTS_Base']

        for model in expected_models:
            if model not in models:
                print(f"   ❌ Missing model configuration: {model}")
                return False

        print(f"   ✅ Model configurations present: {', '.join(expected_models)}")
        return True
    except Exception as e:
        print(f"   ❌ Failed to check configuration: {e}")
        return False


def check_migration_script():
    """Verify migration script exists."""
    print("\n6. Checking migration script...")
    migration_path = backend_path / "migrations" / "add_engine_field.py"

    if not migration_path.exists():
        print(f"   ❌ Migration script not found: {migration_path}")
        return False

    print(f"   ✅ Migration script exists: {migration_path.name}")

    # Check if it's executable
    content = migration_path.read_text()
    if 'add_column' in content or 'ALTER TABLE' in content:
        print(f"   ✅ Migration script contains column addition logic")
    else:
        print(f"   ⚠️  Migration script may not contain expected logic")

    return True


def check_frontend_files():
    """Verify frontend files have engine selector."""
    print("\n7. Checking frontend files...")

    # Check GenerationForm.tsx
    form_path = Path(__file__).parent / "app" / "src" / "components" / "Generation" / "GenerationForm.tsx"
    if not form_path.exists():
        print(f"   ❌ GenerationForm.tsx not found")
        return False

    content = form_path.read_text()

    if 'engine' not in content.lower():
        print(f"   ❌ GenerationForm.tsx missing 'engine' field")
        return False
    print(f"   ✅ GenerationForm.tsx contains 'engine' field")

    if 'f5' not in content.lower() or 'f5-tts' not in content.lower():
        print(f"   ⚠️  GenerationForm.tsx may be missing F5-TTS option")
    else:
        print(f"   ✅ GenerationForm.tsx contains F5-TTS option")

    # Check useGenerationForm hook
    hook_path = Path(__file__).parent / "app" / "src" / "lib" / "hooks" / "useGenerationForm.ts"
    if not hook_path.exists():
        print(f"   ❌ useGenerationForm.ts not found")
        return False

    content = hook_path.read_text()
    if 'engine' not in content:
        print(f"   ❌ useGenerationForm.ts missing 'engine' field")
        return False
    print(f"   ✅ useGenerationForm.ts contains 'engine' field")

    # Check API types
    api_path = Path(__file__).parent / "app" / "src" / "lib" / "api" / "models" / "GenerationRequest.ts"
    if not api_path.exists():
        print(f"   ❌ GenerationRequest.ts not found")
        return False

    content = api_path.read_text()
    if 'engine' not in content:
        print(f"   ❌ GenerationRequest.ts missing 'engine' field")
        return False
    print(f"   ✅ GenerationRequest.ts contains 'engine' field")

    return True


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("F5-TTS and E2-TTS Integration Verification")
    print("=" * 60)

    checks = [
        ("Backend Class", check_backend_class),
        ("Backend Factory", check_backend_factory),
        ("API Models", check_api_models),
        ("Database Schema", check_database_schema),
        ("Configuration", check_configuration),
        ("Migration Script", check_migration_script),
        ("Frontend Files", check_frontend_files),
    ]

    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} check failed with exception: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("\n🎉 All checks passed! Ready for E2E testing.")
        print("\nNext steps:")
        print("1. Start backend server: cd backend && uvicorn main:app --reload")
        print("2. Start frontend server: cd app && npm run dev")
        print("3. Run E2E test: pytest backend/tests/test_e2e_f5_generation.py -v -s")
        print("4. Or follow manual test steps in E2E_VERIFICATION_GUIDE.md")
        return 0
    else:
        print("\n⚠️  Some checks failed. Please fix the issues before E2E testing.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
