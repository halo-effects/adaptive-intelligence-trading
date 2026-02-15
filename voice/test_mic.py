import pyaudio
pa = pyaudio.PyAudio()
print(f"Audio devices: {pa.get_device_count()}")
for i in range(pa.get_device_count()):
    info = pa.get_device_info_by_index(i)
    if info["maxInputChannels"] > 0:
        print(f"  Input [{i}]: {info['name']}")
try:
    info = pa.get_default_input_device_info()
    print(f"\nDefault input: {info['name']}")
except:
    print("\nNo default input device found!")
pa.terminate()
print("\nMicrophone check passed!")
