import warnings

bti = lambda bytes_: int.from_bytes(bytes_, "little")

class WAVEFORMAT:
    FormatTag       = 0
    Channels        = 0
    SamplesPerSec   = 0
    AvgBytesPerSec  = 0
    BlockAlign      = 0
##    def __init__(self, data = None):
##        if data:
##            assert type(data) == bytes and len(data) == 14, "expected a data stream of 14 bytes"
##            self.FormatTag      = data[:2]
##            self.Channels       = data[2:4]
##            self.SamplesPerSec  = data[4:8]
##            self.AvgBytesPerSec = data[8:12]
##            self.BlockAlign     = data[12:]

class PCMWAVEFORMAT(WAVEFORMAT):
    BitsPerSample   = 0
    def __init__(self, data = None):
        if data:
            assert type(data) == bytes and len(data) == 16, "expected a data stream of 16 bytes"
            self.FormatTag      = bti(data[:2])
            self.Channels       = bti(data[2:4])
            self.SamplesPerSec  = bti(data[4:8])
            self.AvgBytesPerSec = bti(data[8:12])
            self.BlockAlign     = bti(data[12:14])
            self.BitsPerSample  = bti(data[14:])

class WAVEFORMATEX(PCMWAVEFORMAT):
    cbSize = 0
    def __init__(self, data = None):
        if data:
            assert type(data) == bytes and len(data) == 18, "expected a data stream of 18 bytes"
            self.FormatTag      = bti(data[:2])
            self.Channels       = bti(data[2:4])
            self.SamplesPerSec  = bti(data[4:8])
            self.AvgBytesPerSec = bti(data[8:12])
            self.BlockAlign     = bti(data[12:14])
            self.BitsPerSample  = bti(data[14:16])
            self.cbSize         = bti(data[16:])

class WAVEFORMATEXTENSIBLE(WAVEFORMATEX):
    Samples     = 0
    ChannelMask = 0
    SubFormat   = 0
    def __init__(self, data = None):
        if data:
            assert type(data) == bytes and len(data) == 40, "expected a data stream of 40 bytes"
            self.FormatTag      = bti(data[:2])
            self.Channels       = bti(data[2:4])
            self.SamplesPerSec  = bti(data[4:8])
            self.AvgBytesPerSec = bti(data[8:12])
            self.BlockAlign     = bti(data[12:14])
            self.BitsPerSample  = bti(data[14:16])
            self.cbSize         = bti(data[16:18])
            self.Samples        = bti(data[18:20])
            self.ChannelMask    = bti(data[20:24])
            self.SubFormat      = bti(data[24:])

WAVE_FORMAT_PCM         = 0x0001
WAVE_FORMAT_IEEE_FLOAT  = 0x0003
WAVE_FORMAT_ALAW        = 0x0006
WAVE_FORMAT_MULAW       = 0x0007
WAVE_FORMAT_EXTENSIBLE  = 0xFFFE

class PyWaveError(Exception):
    pass

class PyWaveWarning(UserWarning):
    pass

fourccRIFF  = b"RIFF"
fourccDATA  = b"data"
fourccFMT   = b"fmt "
fourccWAVE  = b"WAVE"
fourccXWMA  = b"XWMA"
fourccDPDS  = b"dpds"

ERROR_NOT_A_WAVE_FILE = -1

def _find_chunk(file_, fourcc):
    file_.seek(0)
    ChunkType       = b""
    ChunkDataSize   = 0
    Offset          = 0

    read = True
    while read:
        read = file_.read(4)
        ChunkType       = read
        
        read = file_.read(4)
        ChunkDataSize   = bti(read)

        if ChunkType == fourccRIFF:
            ChunkDataSize   = 4
            read = file_.seek(4, 1)
            
        else:
            file_.seek(ChunkDataSize, 1)

        Offset += 4 * 2

        if (ChunkType == fourcc):
            ChunkSize           = ChunkDataSize
            ChunkDataPosition   = Offset
            return (ChunkSize, ChunkDataPosition)

        Offset += ChunkDataSize

def _read_chunk_data(file_, size, offset):
    file_.seek(offset)
    return file_.read(size)

def _open_wave_file(path):
    file_ = open(path, "rb")

    fc = _find_chunk(file_, fourccRIFF)
    if type(fc) != tuple:
        raise PyWaveError("'{}' does not appear to be a wave file.".format(path))
    ChunkSize, ChunkPosition = fc

    filetype = _read_chunk_data(file_, 4, ChunkPosition)

    if not filetype in (fourccWAVE, fourccXWMA):
        raise PyWaveError("'{}' does not appear to be a wave file.".format(path))

    fc = _find_chunk(file_, fourccFMT)
    if type(fc) != tuple:
        raise PyWaveError("'{}' is missing the fmt chunk.".format(path))
    ChunkSize, ChunkPosition = fc

    wfx = None

    if ChunkSize == 16:
        wfx = PCMWAVEFORMAT(_read_chunk_data(file_, ChunkSize, ChunkPosition))
    elif ChunkSize == 18:
        wfx = WAVEFORMATEX(_read_chunk_data(file_, ChunkSize, ChunkPosition))
    elif 18 < ChunkSize <= 40:
        wfx = WAVEFORMATEXTENSIBLE(_read_chunk_data(file_, ChunkSize, ChunkPosition))
    else:
        raise PyWaveError("'{}' has an unknown or unsupported format.".format(path))

    fc = _find_chunk(file_, fourccDATA)
    if type(fc) != tuple:
        raise PyWaveError("'{}' is missing the data chunk.".format(path))
    ChunkSize, ChunkPosition = fc

    return (file_, wfx, ChunkSize, ChunkPosition)

class Wave:
    """Opens a WAVE-RIFF file for reading.
If <auto_read> is set to True, the data of the wave
file <path> is read and put into <Wave.data>.
Otherwise <Wave.read()> can be used to read data from
the wave file."""
    def __init__(self, path, auto_read = False):
        self.wf, self.wfx, self.data_length, self.data_starts_at = _open_wave_file(path)

        self.format = self.wfx.FormatTag
        self.channels = self.wfx.Channels
        self.samples_per_sec = self.frequency = self.wfx.SamplesPerSec
        self.average_bytes_per_sec = self.wfx.AvgBytesPerSec
        self.block_align = self.wfx.BlockAlign
        self.bits_per_sample = self.wfx.BitsPerSample

        self.bitrate = self.average_bytes_per_sec * 8

        self.bytes_per_sample = (self.bits_per_sample // 8)

        self.samples = (self.data_length // self.bytes_per_sample // self.channels)

        self.data_position = 0
        self.end_of_data = self.data_starts_at + self.data_length

        self.wf.seek(self.data_starts_at)

        if auto_read:
            self.data = self.wf.read(self.data_length)
            self.data_position = self.data_length
            self.wf.close()

    def read(self, max_bytes = 4096):
        """Returns data (bytes).
Reads up to <max_bytes> bytes of data and returns it.
If the end of the file is reached, an empty bytes string
is returned (b"")."""
        out = self.wf.read(min(max_bytes, self.end_of_data - self.data_position))
        bytes_written = len(out)
        
        if bytes_written == 0:
            return b""
        
        self.data_position += bytes_written
        return out

    read_samples = lambda self, number_of_samples: self.read(self.bytes_per_sample * number_of_samples)

    tell = lambda self: self.data_position

    close = lambda self: self.wf.close()

    def seek(self, offset, whence = 0):
        """Returns None.
Sets the current position in the data stream.
If <whence> is 0, <offset> is the absolute position of the
data stream in bytes.
If <whence> is 1, <offset> is added to the current position
in the data stream in bytes.
If <whence> is 2, the position will be set to the end of
the file plus <offset>."""
        if whence == 0:
            pos = max(min(self.data_starts_at + offset, self.end_of_data), self.data_starts_at)
            
        elif whence == 1:
            pos = max(min(self.data_position + offset, self.end_of_data), self.data_starts_at)
            
        elif whence == 2:
            pos = max(min(self.end_of_data + offset, self.end_of_data), self.data_starts_at)

        else:
            raise AssertionError("whence has to be either 0, 1 or 2")

        self.wf.seek(pos)

    def __del__(self):
        self.wf.close()
