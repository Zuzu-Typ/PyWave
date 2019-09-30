
######
PyWave
######

********************************
Open\, read and write Wave files
********************************
| **PyWave** is a small **extension** that enables you to **open** and **read** the data of any **WAVE\-RIFF** file\.
| It supports PCM\, IEEE\-FLOAT\, EXTENSIBLE and a few other wave formats \(including 32 and 64 bit waves\)\.
| It can also create and write wave files\, but it\'s currently limited to PCM\-Waves and pure data \(no metadata\)\.
| 

Tiny documentation
==================

About PyWave
------------
| **PyWave** is supposed to **replace** the builtin Python extension :code:`wave`\, which doesn\'t support \>16\-bit wave files\.
| 

Using PyWave
------------
| To install PyWave you can use the PyPI\:


::

    pip install PyWave

 
| To use PyWave in a script\, you have to import the package :code:`PyWave` using


::

    import PyWave

 
| or a wildcard import\:


::

    from PyWave import *

 
| 
| 

The Wave class
^^^^^^^^^^^^^^
| You can use :code:`open(path)` to open and read a wave file\.
| 
| Or you can use


::

    
    open(path[, mode = 'r', channels = 2, frequency = 48000, bits_per_sample = 16, format = WAVE_FORMAT_PCM])

  
| with \<mode\> set to :code:`'w'` to open and create a writable wave file\.
| 
| Both will return an instance of the :code:`Wave` class\.
| 
| The following methods are provided by the :code:`Wave` class\:


::

    
    Wave.read([max_bytes = None]) -> <bytes> data
        Reads and returns at most <max_bytes> bytes of data.
        If <max_bytes> is None, reads until the end.
    
    Wave.read_samples(number_of_samples) -> <bytes> data
        Reads and returns at most <number_of_samples> samples of data.
    
    Wave.write(data) -> None
        Writes <data> to the data chunk of the wave file.
        Before write can be called, the following members have to be set:
        - Wave.channels
        - Wave.frequency
        - Wave.bits_per_sample
    
        This function can only append to the end of the data chunk,
        thus it is not effected by 'seek()'.
    
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

 
|     
| And it has the following members\:


::

    
    Wave.format <int>
        Format of the audio data. Can be any of:
        - WAVE_FORMAT_PCM
        - WAVE_FORMAT_IEEE_FLOAT
        - WAVE_FORMAT_ALAW
        - WAVE_FORMAT_MULAW
        - WAVE_FORMAT_EXTENSIBLE
        Otherwise the format is unknown
    
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
        [Deprecated]
        (only exists if <auto_read> was set to True)
        Audio data as bytes
    
    Wave.metadata <dict>
        A dictionary containing metadata specified in the wave file

 
| 
| 
| 

Example
-------


::

    
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

 