import PyWave


# I will try to integrate this in the next iteration of PyWave
def get_format_name(waveformat):
    waveformatnames_dict = {
        0x0000: 'Unknown Wave Format',
        0x0001: 'WAVE_FORMAT_PCM',
        0x0002: 'WAVE_FORMAT_ADPCM',
        0x0003: 'WAVE_FORMAT_IEEE_FLOAT',
        0x0006: 'WAVE_FORMAT_ALAW',
        0x0007: 'WAVE_FORMAT_MULAW',
        0xFFFE: 'WAVE_FORMAT_EXTENSIBLE'
    }
    return waveformatnames_dict.get(waveformat, 'Unknown')


PATH = "path/to/a/wave/file.wav"
PATH_COPY = "path/to/a/wave/file_copy.wav"

wf = PyWave.open(PATH)

print("File '{0}' was opened succesfully.".format(PATH))
print("This WAVE file has the following properties:\n")

print("format code:", wf.format, "({0})\n".format(get_format_name(wf.format)))

print(wf.channels, "channels")
print(wf.frequency, "Hz sample rate")
print(wf.bits_per_sample, "bits ({0} bytes) per sample".format(wf.bytes_per_sample))
print(wf.bitrate, "bits ({0} bytes) per second".format(wf.average_bytes_per_sec))

print(wf.samples, "total samples")
print(wf.data_length, "bytes of data")
print(wf.block_align, "bytes per block (1 sample for each channel)")

wf_copy = PyWave.open(PATH_COPY, 
                      mode = "w",
                      channels = wf.channels,
                      frequency = wf.frequency,
                      bits_per_sample = wf.bits_per_sample,
                      format = wf.format)
wf_copy.write(wf.read())
wf.close()
wf_copy.close()

print("\nA copy of the wav-file was created as: '{0}'".format(PATH_COPY))

if len(wf.messages) > 0:
    print ('\nAll warnings during processing:\n-------------------------------')
    for msg in wf.messages:
        print ('  {}'.format(msg))
