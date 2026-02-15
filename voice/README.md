# Gee Gee — Voice Assistant for OpenClaw

Voice interface that listens for a wake word, transcribes your speech, sends it to the OpenClaw Telegram bot, and plays back responses.

## Quick Start

```
1. Double-click setup.bat     (installs deps, generates chime, downloads Whisper model)
2. Double-click run.bat        (starts the assistant)
```

## Modes

| Mode | Flag | How it works |
|------|------|-------------|
| **Wake word** | *(default)* | Uses openwakeword or energy-based detection — speak after a pause |
| **Push-to-talk** | `--push-to-talk` | Press Enter to start recording |
| **Test** | `--test` | Tests mic, chime, and Telegram connection |

## Requirements

- Windows 10/11 x64
- Python 3.12
- Microphone
- Internet connection (for Telegram)
- ~200MB disk (Whisper tiny model + dependencies)

## Troubleshooting

**PyAudio won't install:** `pip install pipwin && pipwin install pyaudio`

**No mic detected:** Check Windows sound settings → Input devices

**openwakeword fails:** The assistant falls back to energy-based detection automatically. Use `--push-to-talk` for most reliable experience.

## Architecture

```
Mic → Wake Word Detection → Record Speech → Whisper Transcription
  → Telegram Bot → OpenClaw Agent → Response → Speakers/TTS
```

## Files

- `voice_assistant.py` — Main script
- `generate_chime.py` — Creates chime.wav
- `requirements.txt` — Python dependencies
- `setup.bat` / `run.bat` — Windows launchers
