# E2E Verification Guide: E2-TTS Engine

## Overview
This guide provides step-by-step instructions for manually testing E2-TTS generation via the UI.

## Prerequisites

### 1. Start the Backend Server
```bash
cd backend
python server.py
# Or using uvicorn:
# uvicorn main:app --reload --port 8000
```

Server should start at: http://localhost:8000

### 2. Start the Frontend
```bash
cd app
npm run dev
```

Frontend should start at: http://localhost:3000

### 3. Verify Server Health
Open browser to http://localhost:8000/docs to see the API documentation.

## Test Steps

### Step 1: Create or Select a Voice Profile

#### Option A: Use Existing Profile
1. Navigate to http://localhost:3000
2. Click on the "Voice Profile" dropdown
3. Select any existing profile from the list

#### Option B: Create New Profile
1. Click "Create New Profile" button
2. Fill in profile name (e.g., "E2-TTS Test Voice")
3. Upload a reference audio file (WAV or MP3, 1-25 seconds recommended)
4. Enter the transcription of the audio
5. Click "Create Profile"
6. Wait for profile creation to complete

### Step 2: Select E2-TTS Engine

1. Locate the "TTS Engine" dropdown in the generation form
2. Click on the dropdown to open options
3. Verify these options are available:
   - **Qwen3-TTS** (default)
   - **F5-TTS**
   - **E2-TTS** ← Select this one
4. Click on "E2-TTS"

### Step 3: Verify Model Type Selector

After selecting E2-TTS, verify:
1. A "Model Type" dropdown appears (conditional rendering)
2. The dropdown shows: **E2TTS_Base**
3. This should be auto-selected

### Step 4: Enter Text for Generation

1. In the "Text to Generate" field, enter:
   ```
   Hello, this is a test of the E2-TTS engine for voice cloning.
   ```
2. Or use any other text you want to test (keep it under 500 characters for faster generation)

### Step 5: Generate Speech

1. Click the "Generate Speech" button
2. Observe the following:
   - Loading spinner appears
   - Progress bar may show (for first-time model download)
   - Generation status updates

**First Run Note**: If this is the first time using E2-TTS, the model will download from HuggingFace (~500MB). This may take 2-5 minutes depending on your internet connection.

**Subsequent Runs**: Generation should complete in 10-30 seconds.

### Step 6: Verify Generation Completion

1. Wait for generation to complete
2. Verify success message appears
3. Check that the generated audio appears in the history section below the form

### Step 7: Verify Audio File Creation

1. Locate the new generation in the history/generations list
2. Verify the generation card shows:
   - ✅ Text content matches what you entered
   - ✅ Engine badge shows "**E2**" or "**E2-TTS**"
   - ✅ Model type shows "**E2TTS_Base**"
   - ✅ Timestamp is recent
   - ✅ Profile name matches selected profile

### Step 8: Verify Audio Playback

1. Find the play button (▶) on the generation card
2. Click the play button
3. Verify:
   - ✅ Audio starts playing
   - ✅ Playback controls work (pause, stop, seek)
   - ✅ Voice sounds similar to the reference profile
   - ✅ Text is spoken correctly

### Step 9: Download Audio (Optional)

1. Click the download button (⬇) on the generation card
2. Verify audio file downloads successfully
3. Open the file in an audio player to confirm it's valid

### Step 10: Check Database Record

For advanced verification, check the database:

```bash
cd backend
sqlite3 voicebox.db "SELECT id, text, engine, model_type, created_at FROM generations ORDER BY created_at DESC LIMIT 5;"
```

Expected output:
```
<id>|Hello, this is a test...|e2|E2TTS_Base|2026-02-27 XX:XX:XX
```

## Expected Results

### ✅ Success Criteria

- [x] E2-TTS engine appears in dropdown
- [x] E2TTS_Base model type is shown when E2-TTS is selected
- [x] Generation completes without errors
- [x] Audio file is created and can be played back
- [x] Generation appears in history with engine='e2'
- [x] Generation shows model_type='E2TTS_Base'
- [x] Voice cloning produces recognizable voice similar to reference

### 🔍 Quality Checks

1. **Voice Quality**: Does the generated voice sound natural?
2. **Voice Similarity**: Does it sound like the reference profile?
3. **Text Accuracy**: Is all the text spoken correctly?
4. **Audio Quality**: No distortion, clipping, or artifacts?

## Troubleshooting

### Model Download Issues
**Problem**: Model download fails or times out
**Solution**:
- Check internet connection
- Verify HuggingFace Hub is accessible
- Check available disk space (~1GB needed)
- Try again (downloads are resumable)

### Generation Fails
**Problem**: Error message during generation
**Solution**:
- Check backend logs for detailed error
- Verify f5-tts package is installed: `pip list | grep f5-tts`
- Ensure sufficient RAM (4GB+ recommended)
- Try with shorter text

### Engine Not Showing in Dropdown
**Problem**: E2-TTS option missing from engine dropdown
**Solution**:
- Clear browser cache and reload
- Verify frontend build is up to date: `cd app && npm run build`
- Check browser console for errors

### Audio Playback Issues
**Problem**: Audio doesn't play or download fails
**Solution**:
- Check browser console for errors
- Verify audio file exists in backend/generations/ directory
- Check file permissions
- Try a different browser

## Performance Notes

### E2-TTS vs F5-TTS
- **E2-TTS**: Slower generation but different quality characteristics
- **F5-TTS**: Faster generation (RTF ~0.15)
- Both use the same f5-tts package with different model_type parameter

### Resource Usage
- **GPU Mode**: 2-4GB VRAM
- **CPU Mode**: 4-8GB RAM
- **Disk Space**: ~500MB for model cache

## Advanced Testing

### Test Seed Reproducibility
1. Generate speech with seed=42
2. Note the audio characteristics
3. Generate the same text again with seed=42
4. Compare outputs (should be identical)

### Test Multiple Profiles
1. Create 2-3 different voice profiles
2. Generate same text with each profile using E2-TTS
3. Verify voice characteristics match respective profiles

### Test Long Text
1. Enter text of 200-500 characters
2. Verify generation completes successfully
3. Check audio quality throughout

## Reporting Issues

If you encounter issues:
1. Capture error messages from browser console
2. Check backend logs for stack traces
3. Note your system specs (OS, RAM, GPU)
4. Document the exact steps to reproduce
5. Check if the same issue occurs with F5-TTS or Qwen3-TTS

## Completion

Once all steps pass successfully:
- ✅ E2-TTS engine is fully integrated
- ✅ UI controls work correctly
- ✅ Audio generation is functional
- ✅ Database records are accurate
- ✅ Ready for QA sign-off
