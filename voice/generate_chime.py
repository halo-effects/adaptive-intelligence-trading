"""Generate a pleasant chime sound."""
import numpy as np, wave, struct, os

sr = 22050
dur = 0.4
t = np.linspace(0, dur, int(sr * dur), False)
# Two-tone chime (C5 + E5)
tone = 0.4 * np.sin(2 * np.pi * 523.25 * t) + 0.3 * np.sin(2 * np.pi * 659.25 * t)
# Fade in/out
fade = np.minimum(t / 0.02, 1.0) * np.minimum((dur - t) / 0.1, 1.0)
tone = (tone * fade * 32767).astype(np.int16)

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chime.wav")
with wave.open(path, "w") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(sr)
    w.writeframes(tone.tobytes())
print(f"Created {path}")
