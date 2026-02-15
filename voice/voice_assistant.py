"""
Gee Gee - Voice Assistant for OpenClaw
Listens for wake word, transcribes speech, sends to Telegram, plays responses.
"""

import sys, os, time, struct, wave, json, threading, tempfile, argparse, io
import numpy as np
import pyaudio
import requests
import pygame

# --- Config ---
TELEGRAM_TOKEN = "8528958079:AAF90HSJ5Ck1urUydzS5CUvyf2EEeB7LUwc"
TELEGRAM_CHAT_ID = "5221941584"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK = 512
FORMAT = pyaudio.paInt16

SILENCE_THRESHOLD = 500       # RMS threshold for silence
SILENCE_DURATION = 1.5        # seconds of silence to stop recording
MAX_RECORD_SECONDS = 30       # max recording length
WAKE_ENERGY_THRESHOLD = 600   # minimum energy to start wake word check

WHISPER_MODEL = "tiny"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHIME_PATH = os.path.join(SCRIPT_DIR, "chime.wav")

# --- Globals ---
whisper_model = None
wake_model = None
pa = None
tts_engine = None
last_update_id = 0


def status(msg):
    print(f"[GeeGee] {msg}")


def play_audio_file(path):
    """Play a wav/ogg/mp3 file through speakers."""
    try:
        pygame.mixer.init()
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        pygame.mixer.quit()
    except Exception as e:
        status(f"Audio playback error: {e}")


def play_chime():
    if os.path.exists(CHIME_PATH):
        play_audio_file(CHIME_PATH)


# --- Wake Word Detection ---
def init_wake_word():
    """Try openwakeword, fall back to energy-based detection."""
    global wake_model
    try:
        from openwakeword.model import Model
        wake_model = Model(inference_framework="onnx")
        status("Wake word engine: openwakeword (using 'hey jarvis' as proxy for 'hey gee gee')")
        return "openwakeword"
    except Exception as e:
        status(f"openwakeword not available ({e}), using energy-based wake detection")
        status("Say anything after silence to activate (energy-based trigger)")
        return "energy"


def detect_wake_word_openwakeword(stream):
    """Listen for wake word using openwakeword."""
    wake_model.reset()
    while True:
        audio = np.frombuffer(stream.read(CHUNK, exception_on_overflow=False), dtype=np.int16)
        prediction = wake_model.predict(audio)
        # Check all available models for activation
        for mdl_name, score in prediction.items():
            if score > 0.5:
                return True


def detect_wake_word_energy(stream):
    """Simple energy-based: wait for silence then speech (like someone starting to talk)."""
    # Wait for a burst of energy after relative quiet
    quiet_frames = 0
    while True:
        audio = np.frombuffer(stream.read(CHUNK, exception_on_overflow=False), dtype=np.int16)
        rms = np.sqrt(np.mean(audio.astype(np.float32) ** 2))
        if rms < SILENCE_THRESHOLD:
            quiet_frames += 1
        elif quiet_frames > int(SAMPLE_RATE / CHUNK * 1.0) and rms > WAKE_ENERGY_THRESHOLD:
            # Had at least 1s of quiet, now speech detected
            return True
        else:
            quiet_frames = 0


# --- Recording ---
def record_speech(stream):
    """Record until silence detected. Returns raw audio bytes (16-bit PCM)."""
    status("Recording... (speak now)")
    frames = []
    silent_chunks = 0
    max_chunks = int(SAMPLE_RATE / CHUNK * MAX_RECORD_SECONDS)
    silence_chunks_needed = int(SAMPLE_RATE / CHUNK * SILENCE_DURATION)

    for _ in range(max_chunks):
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)
        audio = np.frombuffer(data, dtype=np.int16)
        rms = np.sqrt(np.mean(audio.astype(np.float32) ** 2))

        if rms < SILENCE_THRESHOLD:
            silent_chunks += 1
            if silent_chunks >= silence_chunks_needed and len(frames) > silence_chunks_needed:
                break
        else:
            silent_chunks = 0

    status(f"Recorded {len(frames) * CHUNK / SAMPLE_RATE:.1f}s of audio")
    return b"".join(frames)


# --- Transcription ---
def init_whisper():
    global whisper_model
    status(f"Loading Whisper model ({WHISPER_MODEL})...")
    from faster_whisper import WhisperModel
    whisper_model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    status("Whisper model ready")


def transcribe(raw_audio):
    """Transcribe raw PCM audio bytes."""
    status("Transcribing...")
    # Save to temp wav
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    try:
        with wave.open(tmp.name, "w") as w:
            w.setnchannels(CHANNELS)
            w.setsampwidth(2)
            w.setframerate(SAMPLE_RATE)
            w.writeframes(raw_audio)

        segments, info = whisper_model.transcribe(tmp.name, language="en", beam_size=1)
        text = " ".join(s.text.strip() for s in segments).strip()
        return text
    finally:
        os.unlink(tmp.name)


# --- Telegram ---
def send_to_telegram(text):
    """Send text message to Telegram."""
    status(f"Sending to Gee Gee: \"{text}\"")
    try:
        r = requests.post(f"{TELEGRAM_API}/sendMessage", json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text
        }, timeout=10)
        r.raise_for_status()
        return True
    except Exception as e:
        status(f"Telegram send error: {e}")
        return False


def poll_telegram_responses():
    """Poll for new messages from the bot. Returns list of responses."""
    global last_update_id
    try:
        r = requests.get(f"{TELEGRAM_API}/getUpdates", params={
            "offset": last_update_id + 1,
            "timeout": 1,
            "allowed_updates": json.dumps(["message"])
        }, timeout=5)
        r.raise_for_status()
        data = r.json()
        responses = []
        for update in data.get("result", []):
            last_update_id = update["update_id"]
            msg = update.get("message", {})
            # Only process messages FROM the bot (not our own)
            if msg.get("from", {}).get("is_bot", False):
                if "voice" in msg:
                    responses.append(("voice", msg["voice"]["file_id"]))
                elif "audio" in msg:
                    responses.append(("audio", msg["audio"]["file_id"]))
                elif "text" in msg:
                    responses.append(("text", msg["text"]))
        return responses
    except Exception:
        return []


def download_telegram_file(file_id):
    """Download a file from Telegram, return local path."""
    try:
        r = requests.get(f"{TELEGRAM_API}/getFile", params={"file_id": file_id}, timeout=10)
        file_path = r.json()["result"]["file_path"]
        url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
        ext = os.path.splitext(file_path)[1] or ".ogg"
        tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
        data = requests.get(url, timeout=30).content
        tmp.write(data)
        tmp.close()
        return tmp.name
    except Exception as e:
        status(f"Download error: {e}")
        return None


def speak_text(text):
    """Use pyttsx3 to speak text."""
    global tts_engine
    try:
        import pyttsx3
        if tts_engine is None:
            tts_engine = pyttsx3.init()
            tts_engine.setProperty("rate", 175)
        status(f"Speaking: \"{text[:80]}...\"" if len(text) > 80 else f"Speaking: \"{text}\"")
        tts_engine.say(text)
        tts_engine.runAndWait()
    except Exception as e:
        status(f"TTS error: {e}")
        print(f"  Response: {text}")


def handle_responses():
    """Check for and play any bot responses."""
    responses = poll_telegram_responses()
    for rtype, rdata in responses:
        if rtype in ("voice", "audio"):
            status("Playing voice response...")
            path = download_telegram_file(rdata)
            if path:
                try:
                    play_audio_file(path)
                finally:
                    os.unlink(path)
        elif rtype == "text":
            speak_text(rdata)


# --- Test Mode ---
def test_mode():
    status("=== TEST MODE ===")

    # Test mic
    status("Testing microphone...")
    try:
        p = pyaudio.PyAudio()
        stream = p.open(format=FORMAT, channels=CHANNELS, rate=SAMPLE_RATE,
                        input=True, frames_per_buffer=CHUNK)
        status("Recording 2 seconds...")
        frames = []
        for _ in range(int(SAMPLE_RATE / CHUNK * 2)):
            frames.append(stream.read(CHUNK, exception_on_overflow=False))
        audio = np.frombuffer(b"".join(frames), dtype=np.int16)
        rms = np.sqrt(np.mean(audio.astype(np.float32) ** 2))
        status(f"Mic OK! Average RMS: {rms:.0f}")
        stream.close()
        p.terminate()
    except Exception as e:
        status(f"Mic error: {e}")
        return

    # Test chime
    status("Playing chime...")
    play_chime()
    time.sleep(0.5)

    # Test Telegram
    status("Testing Telegram connection...")
    try:
        r = requests.get(f"{TELEGRAM_API}/getMe", timeout=5)
        bot = r.json()["result"]
        status(f"Telegram OK! Bot: @{bot['username']}")
    except Exception as e:
        status(f"Telegram error: {e}")

    status("=== TEST COMPLETE ===")


# --- Main Loop ---
def main():
    global last_update_id

    parser = argparse.ArgumentParser(description="Gee Gee Voice Assistant")
    parser.add_argument("--test", action="store_true", help="Test mic and chime")
    parser.add_argument("--push-to-talk", action="store_true", help="Use Enter key instead of wake word")
    args = parser.parse_args()

    if args.test:
        test_mode()
        return

    status("=" * 40)
    status("  Gee Gee Voice Assistant")
    status("=" * 40)

    # Init Whisper
    init_whisper()

    # Init wake word
    wake_mode = init_wake_word()

    # Init audio
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=SAMPLE_RATE,
                    input=True, frames_per_buffer=CHUNK)

    # Skip existing Telegram updates
    try:
        r = requests.get(f"{TELEGRAM_API}/getUpdates", params={"offset": -1}, timeout=5)
        updates = r.json().get("result", [])
        if updates:
            last_update_id = updates[-1]["update_id"]
    except:
        pass

    # Response polling thread
    stop_event = threading.Event()

    def response_poller():
        while not stop_event.is_set():
            handle_responses()
            time.sleep(2)

    poller = threading.Thread(target=response_poller, daemon=True)
    poller.start()

    status("")
    if args.push_to_talk:
        status("Mode: Push-to-talk (press Enter to speak)")
    elif wake_mode == "openwakeword":
        status("Mode: Wake word detection (say 'Hey Jarvis' or similar)")
    else:
        status("Mode: Energy-based (start speaking after a pause)")
    status("Press Ctrl+C to quit")
    status("")

    try:
        while True:
            if args.push_to_talk:
                status("Press Enter to speak...")
                input()
                play_chime()
            else:
                status("Listening for wake word...")
                if wake_mode == "openwakeword":
                    detect_wake_word_openwakeword(stream)
                else:
                    detect_wake_word_energy(stream)

                status("Heard wake word!")
                play_chime()

            # Record
            raw_audio = record_speech(stream)

            # Transcribe
            text = transcribe(raw_audio)
            if not text or len(text.strip()) < 2:
                status("No speech detected, going back to listening...")
                continue

            status(f"You said: \"{text}\"")

            # Send
            send_to_telegram(text)
            status("Waiting for response...")

    except KeyboardInterrupt:
        status("\nShutting down...")
    finally:
        stop_event.set()
        stream.close()
        p.terminate()
        status("Goodbye!")


if __name__ == "__main__":
    main()
