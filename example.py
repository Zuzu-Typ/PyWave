import PyWave

PATH = "path/to/a/wave/file.wav"

wf = PyWave.open(PATH)

print("This WAVE file has the following properties:")
print(wf.channels, "channels")
print(wf.frequency, "Hz sample rate")
print(wf.bitrate, "bits per second")
print(wf.samples, "total samples")

wf_copy = PyWave.open("path/to/a/wave/file_copy.wav", 
                      mode = "w",
                      channels = wf.channels,
                      frequency = wf.frequency,
                      bits_per_sample = wf.bits_per_sample,
                      format = wf.format)
wf_copy.write(wf.read())
wf.close()
wf_copy.close()

if len(wf.messages) > 0:
    print ('\nAll warnings during processing:\n-------------------------------')
    for msg in wf.messages:
        print ('  {}'.format(msg))
