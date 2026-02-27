# F5-TTS and E2-TTS E2E Verification Guide

This guide provides instructions for end-to-end testing of the F5-TTS and E2-TTS integration.

## Prerequisites

1. **Backend server running:**
   ```bash
   cd backend
   uvicorn main:app --reload
   ```

2. **Frontend server running:**
   ```bash
   cd app
   npm run dev
   ```

## Automated API Test

The automated test verifies the complete flow through the API:

```bash
# Make sure backend server is running on http://localhost:8000
cd backend
pytest tests/test_e2e_f5_generation.py -v -s
```

This test will:
- ✅ Create a voice profile with test audio
- ✅ Generate speech using F5-TTS engine
- ✅ Verify audio file is created
- ✅ Verify generation appears in history with engine='f5'
- ✅ Verify audio playback metadata

## Manual UI Test (F5-TTS)

### Step 1: Start Services

Start both backend and frontend services as shown in Prerequisites.

### Step 2: Create Voice Profile

1. Navigate to http://localhost:3000
2. Click "Create Profile" or go to Profiles section
3. Upload a sample audio file (WAV or MP3, 3-10 seconds recommended)
4. Enter a transcription of the audio
5. Save the profile

### Step 3: Generate Speech with F5-TTS

1. Go to the Generation page
2. Select your voice profile from the dropdown
3. **Select "F5-TTS" from the TTS Engine dropdown**
4. **Verify "F5TTS_v1_Base" appears in Model Type selector**
5. Enter text to generate (e.g., "Hello, this is a test of F5-TTS engine")
6. Click Generate

### Step 4: Verify Results

1. **Check generation status** - should complete without errors
2. **Verify audio file is created** - audio player should appear
3. **Play the audio** - verify it sounds like the selected voice profile
4. **Check generation history:**
   - Generation should appear in the list
   - Engine should show "f5"
   - Model type should show "F5TTS_v1_Base"

### Expected Behavior

- ✅ F5-TTS option appears in engine dropdown
- ✅ F5TTS_v1_Base model type is selected automatically
- ✅ Generation completes successfully (may take longer on first run due to model download)
- ✅ Audio file is playable
- ✅ History shows engine='f5' and model_type='F5TTS_v1_Base'
- ✅ Voice cloning quality is good

## Manual UI Test (E2-TTS)

Follow the same steps as F5-TTS, but:
- Select "E2-TTS" from the TTS Engine dropdown (Step 3.3)
- Verify "E2TTS_Base" appears in Model Type selector (Step 3.4)
- In history, verify engine='e2' and model_type='E2TTS_Base' (Step 4.4)

## Backward Compatibility Test (Qwen3-TTS)

1. Select "Qwen3-TTS" from the TTS Engine dropdown
2. Select model size (1.7B or 0.6B)
3. Generate speech
4. Verify existing generations still work
5. Verify old generations (created before engine field) still display

### Expected Behavior

- ✅ Qwen3-TTS still works as before
- ✅ Existing generations are not broken
- ✅ Default engine is Qwen3-TTS (cosyvoice)
- ✅ No regressions in existing functionality

## Troubleshooting

### Backend Issues

**Model download takes too long:**
- F5-TTS and E2-TTS models are downloaded from HuggingFace on first use
- Models are cached in `~/.cache/f5_tts/`
- Progress is shown in the backend logs

**CUDA/GPU not detected:**
- F5-TTS supports CUDA, XPU, DirectML, and CPU
- Check backend logs for device detection
- CPU mode will work but be slower

**Generation fails:**
- Check backend logs for detailed error messages
- Verify the voice profile was created successfully
- Try with a different text or voice profile

### Frontend Issues

**Engine dropdown not showing F5-TTS/E2-TTS:**
- Clear browser cache and reload
- Check browser console for errors
- Verify backend is running and accessible

**Model type selector not appearing:**
- Should appear when F5-TTS or E2-TTS is selected
- Check browser console for React errors

## Success Criteria

All of the following should work:

- [x] F5-TTS engine option is available in UI
- [x] E2-TTS engine option is available in UI
- [x] Model type selector changes based on selected engine
- [x] Voice profile can be created with sample audio
- [x] Speech generation works with F5-TTS engine
- [x] Speech generation works with E2-TTS engine
- [x] Audio files are created and playable
- [x] Generation history shows correct engine and model_type
- [x] Qwen3-TTS (cosyvoice) still works (backward compatibility)
- [x] No console errors or warnings

## API Endpoints for Manual Testing

You can also test via API using curl:

### Create Profile
```bash
curl -X POST http://localhost:8000/profiles/create \
  -F "file=@sample.wav" \
  -F "name=Test Profile" \
  -F "transcription=This is a test"
```

### Generate with F5-TTS
```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "profile_id": "PROFILE_ID_HERE",
    "text": "Hello world",
    "engine": "f5",
    "model_type": "F5TTS_v1_Base"
  }'
```

### Check History
```bash
curl http://localhost:8000/generations/history
```

### Download Audio
```bash
curl http://localhost:8000/generations/GENERATION_ID/audio -o output.wav
```
