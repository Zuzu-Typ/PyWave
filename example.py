from PyWave import *

PATH = "path/to/a/wave/file.wav"

wf = Wave(PATH)

print("This WAVE file has the following properties:")
print(wf.channels, "channels")
print(wf.frequency, "Hz sample rate")
print(wf.bitrate, "bits per second")
print(wf.samples, "total samples")
