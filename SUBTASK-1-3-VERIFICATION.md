# Subtask 1-3 Verification: Backend Factory Engine Selection

## Changes Made

Updated `backend/backends/__init__.py` to support engine selection:

### 1. Global Backend Storage
- Changed from single `_tts_backend` instance to `_tts_backends` dictionary
- Allows caching multiple backend instances (one per engine/model_type combination)

### 2. Updated `get_tts_backend()` Function
**New Signature:**
```python
def get_tts_backend(engine: str = "qwen", model_type: Optional[str] = None) -> TTSBackend
```

**Parameters:**
- `engine`: TTS engine to use ('qwen', 'f5', or 'e2'), defaults to 'qwen'
- `model_type`: Optional model type for F5/E2 engines
  - 'F5TTS_v1_Base' for F5 (default if engine='f5')
  - 'E2TTS_Base' for E2 (default if engine='e2')

**Features:**
- Engine validation: raises ValueError for invalid engines
- Backend caching: reuses existing backend instances
- Default model types: automatically sets appropriate model_type for F5/E2
- Backward compatible: defaults to 'qwen' engine if not specified

### 3. Backend Creation Logic
- **Qwen engine**: Uses platform detection (MLX on Apple Silicon, PyTorch otherwise)
- **F5/E2 engines**: Uses F5TTSBackend with appropriate model_type parameter

### 4. Updated `reset_backends()` Function
- Now resets the `_tts_backends` dictionary instead of single instance

## Verification

### Syntax Check
✓ Python syntax validation passed

### Expected Behavior
```python
# Get Qwen backend (default)
backend1 = get_tts_backend()  # Returns PyTorchTTSBackend or MLXTTSBackend

# Get Qwen backend (explicit)
backend2 = get_tts_backend('qwen')  # Same as above

# Get F5-TTS backend
backend3 = get_tts_backend('f5')  # Returns F5TTSBackend(model_type='F5TTS_v1_Base')

# Get E2-TTS backend
backend4 = get_tts_backend('e2')  # Returns F5TTSBackend(model_type='E2TTS_Base')

# Get F5-TTS with explicit model type
backend5 = get_tts_backend('f5', 'F5TTS_v1_Base')  # Same as backend3

# Invalid engine raises error
get_tts_backend('invalid')  # Raises ValueError
```

### Backend Caching
- Calling `get_tts_backend('qwen')` multiple times returns the same instance
- Calling `get_tts_backend('f5')` returns a different instance from qwen
- Each engine/model_type combination is cached separately

## Integration Points

This change enables:
1. **API Layer** (next subtask): `/generate` endpoint can accept `engine` parameter
2. **Frontend** (later phase): UI can show engine selection dropdown
3. **Multi-Engine Support**: Users can switch between Qwen, F5, and E2 models

## Backward Compatibility

✓ Default behavior unchanged: calling `get_tts_backend()` without arguments still returns Qwen backend
✓ Existing code using `get_tts_backend()` will continue to work
✓ No breaking changes to the TTSBackend protocol
