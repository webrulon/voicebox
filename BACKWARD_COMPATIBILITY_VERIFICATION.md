# Backward Compatibility Verification Guide

## Overview

This document provides a comprehensive guide to verify that the existing Qwen3-TTS functionality remains unchanged after adding F5-TTS and E2-TTS support.

## Automated Tests

### Run Unit Tests

```bash
# Run backward compatibility unit tests
pytest backend/tests/test_backward_compatibility.py -v -s

# Expected output: All tests should pass
# - test_default_engine_is_cosyvoice
# - test_cosyvoice_maps_to_qwen_backend
# - test_old_generation_record_without_engine_field
# - test_new_generation_record_with_engine_field
# - test_mixed_generation_records_query
# - test_generation_request_validation_accepts_cosyvoice
# - test_model_size_parameter_still_works
# - test_generation_request_defaults
```

## Manual Verification Steps

### 1. Verify Default Engine Behavior

**Test**: When no engine is specified, system should use Qwen3-TTS (cosyvoice)

**Steps**:
1. Start the backend server:
   ```bash
   cd backend
   python server.py
   ```

2. Create a generation request without specifying engine:
   ```bash
   curl -X POST "http://localhost:8000/generate" \
     -H "Content-Type: application/json" \
     -d '{
       "profile_id": "<your-profile-id>",
       "text": "This is a test of default engine behavior."
     }'
   ```

**Expected Result**:
- ✅ Request succeeds (200 OK)
- ✅ Audio file is generated using Qwen3-TTS
- ✅ Response includes generation ID and audio path
- ✅ Database record has engine='cosyvoice' or engine=NULL (both acceptable)

### 2. Verify Explicit CosyVoice Selection

**Test**: Explicitly selecting "cosyvoice" engine works

**Steps**:
1. Create a generation request with explicit engine:
   ```bash
   curl -X POST "http://localhost:8000/generate" \
     -H "Content-Type: application/json" \
     -d '{
       "profile_id": "<your-profile-id>",
       "text": "Testing explicit cosyvoice selection.",
       "engine": "cosyvoice",
       "model_size": "1.7B"
     }'
   ```

**Expected Result**:
- ✅ Request succeeds (200 OK)
- ✅ Audio is generated with Qwen3-TTS 1.7B model
- ✅ Database record shows engine='cosyvoice'

### 3. Verify Model Size Selection

**Test**: Model size parameter (1.7B vs 0.6B) still works for Qwen3-TTS

**Steps**:
1. Generate with 1.7B model:
   ```bash
   curl -X POST "http://localhost:8000/generate" \
     -H "Content-Type: application/json" \
     -d '{
       "profile_id": "<your-profile-id>",
       "text": "Testing 1.7B model.",
       "engine": "cosyvoice",
       "model_size": "1.7B"
     }'
   ```

2. Generate with 0.6B model:
   ```bash
   curl -X POST "http://localhost:8000/generate" \
     -H "Content-Type: application/json" \
     -d '{
       "profile_id": "<your-profile-id>",
       "text": "Testing 0.6B model.",
       "engine": "cosyvoice",
       "model_size": "0.6B"
     }'
   ```

**Expected Result**:
- ✅ Both requests succeed
- ✅ Different models are loaded based on model_size
- ✅ Audio quality reflects model size difference

### 4. Verify Old Database Records

**Test**: Existing generation records without engine field still work

**Steps**:
1. Check database for old records:
   ```bash
   sqlite3 backend/voicebox.db "SELECT id, text, engine, model_type, created_at FROM generations ORDER BY created_at LIMIT 5;"
   ```

2. Query generations API:
   ```bash
   curl "http://localhost:8000/history?limit=50"
   ```

**Expected Result**:
- ✅ Old records have NULL or empty engine field
- ✅ API returns old records successfully
- ✅ No errors when querying old records
- ✅ History displays correctly for all records

### 5. Verify Audio Playback

**Test**: Audio files from Qwen3-TTS generations still play correctly

**Steps**:
1. Generate audio with default engine:
   ```bash
   curl -X POST "http://localhost:8000/generate" \
     -H "Content-Type: application/json" \
     -d '{
       "profile_id": "<your-profile-id>",
       "text": "This audio should play correctly."
     }' | jq .audio_path
   ```

2. Play the audio file (get path from response):
   ```bash
   # On Linux
   aplay <audio-path>

   # On macOS
   afplay <audio-path>

   # Or check file properties
   file <audio-path>
   soxi <audio-path>  # if sox is installed
   ```

**Expected Result**:
- ✅ Audio file exists
- ✅ Audio file is valid WAV format
- ✅ Audio plays correctly
- ✅ Voice quality matches Qwen3-TTS output

### 6. Verify UI Functionality

**Test**: Frontend UI still allows Qwen3-TTS generation

**Steps**:
1. Start frontend:
   ```bash
   cd app
   npm run dev
   ```

2. Open browser to http://localhost:3000

3. Navigate to generation form

4. Select a voice profile

5. Verify TTS Engine dropdown shows "Qwen3-TTS (CosyVoice)" option

6. Select Qwen3-TTS engine

7. Verify Model Size dropdown appears with 1.7B and 0.6B options

8. Enter text and generate

**Expected Result**:
- ✅ Qwen3-TTS is available in engine dropdown
- ✅ Model size options appear correctly
- ✅ Generation succeeds
- ✅ Audio plays in UI
- ✅ Generation appears in history
- ✅ No console errors

### 7. Verify Seed Reproducibility

**Test**: Seed parameter still works for reproducible generation

**Steps**:
1. Generate with seed=42:
   ```bash
   curl -X POST "http://localhost:8000/generate" \
     -H "Content-Type: application/json" \
     -d '{
       "profile_id": "<your-profile-id>",
       "text": "Reproducible generation test.",
       "engine": "cosyvoice",
       "seed": 42
     }'
   ```

2. Generate same text with same seed again:
   ```bash
   curl -X POST "http://localhost:8000/generate" \
     -H "Content-Type: application/json" \
     -d '{
       "profile_id": "<your-profile-id>",
       "text": "Reproducible generation test.",
       "engine": "cosyvoice",
       "seed": 42
     }'
   ```

**Expected Result**:
- ✅ Both requests succeed
- ✅ Generated audio files are identical (compare waveforms)

### 8. Verify Voice Cloning

**Test**: Voice cloning with reference audio still works

**Steps**:
1. Create a voice profile with reference audio

2. Generate speech using that profile:
   ```bash
   curl -X POST "http://localhost:8000/generate" \
     -H "Content-Type: application/json" \
     -d '{
       "profile_id": "<your-profile-id>",
       "text": "This should use my cloned voice.",
       "engine": "cosyvoice"
     }'
   ```

**Expected Result**:
- ✅ Generation succeeds
- ✅ Generated audio matches reference voice characteristics
- ✅ Voice cloning quality is maintained

### 9. Verify Instruct Parameter

**Test**: Instruct parameter (voice delivery style) still works

**Steps**:
1. Generate with instruct parameter:
   ```bash
   curl -X POST "http://localhost:8000/generate" \
     -H "Content-Type: application/json" \
     -d '{
       "profile_id": "<your-profile-id>",
       "text": "This text will be read happily.",
       "engine": "cosyvoice",
       "instruct": "Please speak in a happy and energetic voice."
     }'
   ```

**Expected Result**:
- ✅ Request succeeds
- ✅ Instruct parameter affects voice delivery
- ✅ Database stores instruct value

### 10. Verify Model Download Flow

**Test**: Model download still works for Qwen3-TTS

**Steps**:
1. Check model status:
   ```bash
   curl "http://localhost:8000/models/status"
   ```

2. If model not cached, trigger download:
   ```bash
   curl -X POST "http://localhost:8000/models/download" \
     -H "Content-Type: application/json" \
     -d '{"model_size": "1.7B"}'
   ```

**Expected Result**:
- ✅ Model status shows Qwen models (1.7B and 0.6B)
- ✅ Download progress tracked via SSE
- ✅ Model caches successfully
- ✅ Subsequent generations use cached model

## Database Schema Verification

### Check Schema

```bash
sqlite3 backend/voicebox.db ".schema generations"
```

**Expected Output**:
```sql
CREATE TABLE generations (
    id VARCHAR NOT NULL,
    profile_id VARCHAR NOT NULL,
    text TEXT NOT NULL,
    language VARCHAR,
    audio_path VARCHAR NOT NULL,
    duration FLOAT NOT NULL,
    seed INTEGER,
    instruct TEXT,
    engine VARCHAR,        -- New column (nullable)
    model_type VARCHAR,    -- New column (nullable)
    created_at DATETIME,
    PRIMARY KEY (id),
    FOREIGN KEY(profile_id) REFERENCES profiles (id)
);
```

**Verify**:
- ✅ `engine` column exists and is nullable
- ✅ `model_type` column exists and is nullable
- ✅ All other columns unchanged

### Check Data Migration

```bash
# Check for records with NULL engine (old records)
sqlite3 backend/voicebox.db "SELECT COUNT(*) FROM generations WHERE engine IS NULL;"

# Check for records with engine value (new records)
sqlite3 backend/voicebox.db "SELECT COUNT(*) FROM generations WHERE engine IS NOT NULL;"

# Sample old and new records
sqlite3 backend/voicebox.db "SELECT id, text, engine, model_type FROM generations ORDER BY created_at DESC LIMIT 10;"
```

**Expected**:
- ✅ Old records have NULL engine
- ✅ New records have engine value
- ✅ Both types coexist without errors

## API Endpoint Verification

### Test /generate Endpoint

```bash
# Test with minimal parameters (backward compatible)
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "profile_id": "<profile-id>",
    "text": "Minimal test."
  }'

# Test with all old parameters
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "profile_id": "<profile-id>",
    "text": "Full parameter test.",
    "language": "en",
    "seed": 100,
    "model_size": "1.7B",
    "instruct": "Speak clearly and slowly."
  }'

# Test with new engine parameter
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "profile_id": "<profile-id>",
    "text": "New parameter test.",
    "engine": "cosyvoice",
    "model_size": "1.7B"
  }'
```

**Expected**:
- ✅ All three requests succeed
- ✅ Audio is generated in all cases
- ✅ No breaking changes

### Test /history Endpoint

```bash
curl "http://localhost:8000/history"
```

**Expected**:
- ✅ Returns all generations (old and new)
- ✅ Old generations display correctly
- ✅ New generations show engine field
- ✅ No errors or missing data

### Test /models/status Endpoint

```bash
curl "http://localhost:8000/models/status"
```

**Expected**:
- ✅ Shows Qwen models (qwen-tts-1.7b, qwen-tts-0.6b)
- ✅ Shows F5/E2 models (f5-tts-base, e2-tts-base)
- ✅ Correct status (cached/not_cached)

## Regression Checklist

Mark each item as you verify:

- [ ] Default engine is cosyvoice (Qwen3-TTS)
- [ ] Explicit cosyvoice engine selection works
- [ ] Model size selection (1.7B vs 0.6B) works
- [ ] Old database records (engine=NULL) display correctly
- [ ] New database records with engine field work
- [ ] Audio generation produces valid output
- [ ] Audio playback works
- [ ] Seed reproducibility maintained
- [ ] Voice cloning functionality unchanged
- [ ] Instruct parameter still functional
- [ ] Model download flow works
- [ ] UI shows Qwen3-TTS option
- [ ] UI model size dropdown works
- [ ] History displays all generations
- [ ] No console errors in browser
- [ ] No errors in backend logs
- [ ] Database schema includes new columns
- [ ] Database migration successful
- [ ] API accepts old request format
- [ ] API accepts new request format

## Success Criteria

All of the following must be true:

1. ✅ Automated tests pass (pytest backend/tests/test_backward_compatibility.py)
2. ✅ All manual verification steps succeed
3. ✅ All regression checklist items verified
4. ✅ No breaking changes to existing Qwen3-TTS functionality
5. ✅ Old and new generation records coexist without errors
6. ✅ UI maintains backward compatibility
7. ✅ API maintains backward compatibility

## Troubleshooting

### Issue: Old records not displaying

**Solution**: Check that database migration ran successfully:
```bash
python backend/migrations/add_engine_field.py
```

### Issue: Default engine not working

**Solution**: Verify GenerationRequest model has default='cosyvoice':
```bash
grep -A 3 "engine.*Field" backend/models.py
```

### Issue: Model size not respected

**Solution**: Check backend mapping logic in main.py:
```bash
grep -A 10 "engine.*cosyvoice" backend/main.py
```

### Issue: Audio files not playing

**Solution**: Check file permissions and paths:
```bash
ls -la backend/outputs/generations/
file backend/outputs/generations/*.wav
```

## Conclusion

After completing all verification steps and checking all items on the regression checklist, document any issues found and confirm that backward compatibility is maintained.

**Sign-off**:

- Date: __________
- Verified by: __________
- Status: [ ] PASS / [ ] FAIL
- Notes: _________________________________________
