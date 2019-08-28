# PyWave  
## Open and read Wave files  
**PyWave** is a small **extension** that enables you to **open** and **read** the data of any **WAVE\-RIFF** file\.  
It supports PCM, IEEE\-FLOAT, EXTENSIBLE and a few other wave formats \(including 32 bit waves\)\.  
  
## Tiny documentation  
### About PyWave  
**PyWave** is supposed to **replace** the builtin Python extension `wave`, which doesn't support 32\-bit wave\.  
  
### Using PyWave  
To install PyWave you can use the PyPI:  

    pip install PyWave
  
To use PyWave in a script, you have to import the package `PyWave` using  

    import PyWave
  
or a wildcard import:  

    from PyWave import *
  
  
  
#### The Wave class  
You can use the `Wave` class to open and read a wave file:  

    
    Wave(path[, auto_read = False])
        path       - File path to a wave file
        auto_read  - (optional) Can be set to True to read the data automatically
  
  
If `auto_read` is enabled, the data will be stored in `Wave.data`  
  
The following methods are provided by the `Wave` class:  

    
    Wave.read([max_bytes = 4096]) -> <bytes> data
        Reads and returns at most <max_bytes> bytes of data.
    
    Wave.read_samples(number_of_samples) -> <bytes> data
        Reads and returns at most <number_of_samples> samples of data.
    
    Wave.seek(offset[, whence = 0]) -> None
        Sets the current position in the data stream.
        If <whence> is 0, <offset> is the absolute position of the
        data stream in bytes.
        If <whence> is 1, <offset> is added to the current position
        in the data stream in bytes.
        If <whence> is 2, the position will be set to the end of
        the file plus <offset>.
        
    Wave.tell() -> <int> position
        Returns the current position in the data stream.
        
    Wave.close() -> None
        Closes the file handle.
  
      
And it has the following members:  

    
    Wave.format <int>
        Format of the audio data. Can be any of:
        - WAVE_FORMAT_PCM
        - WAVE_FORMAT_IEEE_FLOAT
        - WAVE_FORMAT_ALAW
        - WAVE_FORMAT_MULAW
        - WAVE_FORMAT_EXTENSIBLE
        
    Wave.channels <int>
        The number of audio channels present in the audio stream
        
    Wave.frequency <int>
        Sample rate of the audio stream
        
    Wave.bitrate <int>
        Number of bits per second
        
    Wave.bits_per_sample <int>
        Number of bits per sample (usually 8, 16 or 32)
        
    Wave.samples <int>
        Total number of samples in the audio data
        
    Wave.data <bytes>
        (only if <auto_read> was set to True)
        Audio data as bytes
  
  
  
  
### Example  

    
    from PyWave import *
    
    PATH = "path/to/a/wave/file.wav"
    
    wf = Wave(PATH)
    
    print("This WAVE file has the following properties:")
    print(wf.channels, "channels")
    print(wf.frequency, "Hz sample rate")
    print(wf.bitrate, "bits per second")
    print(wf.samples, "total samples")
