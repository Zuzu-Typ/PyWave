import warnings

builtin_open = __builtins__.open

bti = lambda bytes_: int.from_bytes(bytes_, "little")

class WAVEFORMAT:
    FormatTag       = 0
    Channels        = 0
    SamplesPerSec   = 0
    AvgBytesPerSec  = 0
    BlockAlign      = 0

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
fourccLIST  = b"LIST"
fourccINFO  = b"INFO"

OK = 0
ERROR_NOT_A_WAVE_FILE = -1

def _read_chunk_data(file_, size, offset):
    file_.seek(offset)
    return file_.read(size)

def _check_file_format(file_):
    file_.seek(0)
    RIFFChunk = file_.read(4)
    file_.seek(4, 1)
    WAVETag = file_.read(4)

    if RIFFChunk != fourccRIFF or not WAVETag in (fourccWAVE, fourccXWMA):
        return ERROR_NOT_A_WAVE_FILE
    return 0

def _get_chunks(file_):
    file_.seek(4)
    total_size = bti(file_.read(4))
    file_.seek(4, 1)
    
    out = {}
    Offset = 12
    
    read_bytes = 4
    read = True
    while read_bytes < total_size and read:
        read = file_.read(4)
        read_bytes += len(read)
        ChunkType = read

        read = file_.read(4)
        read_bytes += len(read)
        ChunkDataSize = bti(read)
        ChunkDataSize += ChunkDataSize % 2

        Offset += 8
        

        out[ChunkType] = (ChunkDataSize, Offset)

        Offset += ChunkDataSize
        file_.seek(ChunkDataSize, 1)
        read_bytes += ChunkDataSize

    return out

def _get_info_chunks(file_, size, offset):
    file_.seek(offset)
    out = {}
    read_bytes = 4
    while read_bytes < size:
        name    = file_.read(4)
        size_   = bti(file_.read(4))
        data    = file_.read(size_-1)
        file_.seek(1, 1)
        read_bytes += 8 + size_

        out[name.decode()] = data.decode()
    return out

class Wave:
    """Opens a WAVE-RIFF file for reading.
If <mode> is 'r', <Wave.read()> can be used to read data from
the wave file."""
    def __init__(self, path, auto_read = False, mode = "r"):
        assert mode in ("r", "w"), "mode has to be (r)ead or (w)rite"

        assert mode == "r", "the only mode currently supported is (r)ead"
        
        self.wf = builtin_open(path, mode + "b")

        self.mode = mode

        if mode == "r":
            self._prepare_read(auto_read)

##    def save(self):
##        format_chunk = []
##        format_chunk.append(fourccFMT)
##        format_chunk.append((16).to_bytes(4, "little"))
##        format_chunk.append(self.format.to_bytes(2, "little"))
##        format_chunk.append(self.channels.to_bytes(2, "little"))
##        format_chunk.append(self.frequency.to_bytes(4, "little"))
##        format_chunk.append(self.average_bytes_per_sec.to_bytes(4, "little"))
##        format_chunk.append(self.block_align.to_bytes(2, "little"))
##        format_chunk.append(self.bits_per_sample.to_bytes(2, "little"))
##
##        format_chunk_bytes = b"".join(format_chunk)
##
##        data_chunk = []
##        data_chunk.append(fourccDATA)
##        data_chunk.append(len(self.data).to_bytes(4, "little"))
##        data_chunk.append(self.data)
##        if len(self.data) % 2:
##            data_chunk.append(b"\x00")
##
##        data_chunk_bytes = b"".join(data_chunk)
##
##        
##        
##        out = 
            

    def _prepare_read(self, auto_read):
        if _check_file_format(self.wf) != OK:
            raise PyWaveError("'{}' does not appear to be a wave file.".format(path))

        self.chunks = _get_chunks(self.wf)

        if not fourccFMT in self.chunks:
            raise PyWaveError("'{}' is missing the 'fmt ' chunk.".format(path))

        if not fourccDATA in self.chunks:
            raise PyWaveError("'{}' is missing the 'data' chunk.".format(path))

        fmt_size, fmt_position = self.chunks[fourccFMT]

        if fmt_size == 16:
            self.wfx = PCMWAVEFORMAT(_read_chunk_data(self.wf, fmt_size, fmt_position))
        elif fmt_size == 18:
            self.wfx = WAVEFORMATEX(_read_chunk_data(self.wf, fmt_size, fmt_position))
        elif 18 < fmt_size <= 40:
            self.wfx = WAVEFORMATEXTENSIBLE(_read_chunk_data(self.wf, fmt_size, fmt_position))
        else:
            raise PyWaveError("'{}' has an unknown or unsupported format.".format(path))

        self.metadata = {}

        if fourccLIST in self.chunks:
            ChunkSize, ChunkPosition = self.chunks[fourccLIST]
            self.wf.seek(ChunkPosition)
            if self.wf.read(4) == fourccINFO:
                self.metadata = _get_info_chunks(self.wf, ChunkSize, ChunkPosition + 4)
                
        
        self.data_length, self.data_starts_at = self.chunks[fourccDATA]

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
            warnings.warn(DeprecationWarning("auto_read will no longer be supported in a future update.\nUse <Wave.read()> instead"))
            self.data = self.read()
            self.wf.close()

    def read(self, max_bytes = None):
        """Returns data (bytes).
Reads up to <max_bytes> bytes of data and returns it.
If the end of the file is reached, an empty bytes string
is returned (b"")."""
        if max_bytes:
            out = self.wf.read(min(max_bytes, self.end_of_data - self.data_position))
        else:
            out = self.wf.read(self.end_of_data - self.data_position)
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

    __enter__ = lambda self: self
    __exit__ = lambda self, t, v, tr: self.wf.close()

open = lambda path, mode = "r": Wave(path, mode)
