import warnings
import builtins

builtin_open = builtins.open

bti = lambda bytes_: int.from_bytes(bytes_, "little")
itb = lambda int_, length = 2: int_.to_bytes(length, "little")

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
    """Opens a WAVE-RIFF file for reading or writing.
<mode> can be either (r)ead or (w)rite.
If <mode> is 'w', the following keyword arguments can be set:
<channels> - The number of channels (e.g. 1 == Mono or 2 == Stereo)
<frequency> - The number of samples per second (e.g. 48000)
<bps> (bits_per_sample) - The bit depth of each sample (e.g. 8, 16)
<format> - Which wave format to use (e.g. WAVE_FORMAT_PCM)"""
    def __init__(self, path, auto_read = False, mode = "r", **kwargs):
        assert mode in ("r", "w"), "mode has to be (r)ead or (w)rite"
        
        self.wf = builtin_open(path, mode + "b")

        self.mode = mode

        if mode == "r":
            self._prepare_read(auto_read)

        elif mode == "w":
            self._prepared_for_writing = False
            for keyword in kwargs:
                arg = kwargs[keyword]
                if keyword in ("channels", "Channels"):
                    assert type(arg) == int, "channels have to be of type 'int'"
                    self.channels = arg
                elif keyword in ("samples", "samples_per_sec", "SamplesPerSec", "frequency", "Frequency"):
                    assert type(arg) == int, "frequency / samples_per_sec has to be of type 'int'"
                    self.frequency = self.samples_per_sec = arg
                elif keyword in ("bits_per_sample", "bps", "BitsPerSample"):
                    assert type(arg) == int, "bits_per_sample have to be of type 'int'"
                    self.bits_per_sample = arg
                elif keyword in ("format", "Format", "FormatTag", "format_tag"):
                    assert type(arg) == int, "format has to be of type 'int'"
                    self.format = arg
                else:
                    raise TypeError("Unknown keyword for Wave(): '" + keyword + "'")

            if not hasattr(self, "channels"): self.channels = 2
            if not hasattr(self, "frequency"): self.frequency = 48000
            if not hasattr(self, "bits_per_sample"): self.bits_per_sample = 16
            if not hasattr(self, "format"): self.format = WAVE_FORMAT_PCM

    def _prepare_for_writing(self):
        assert self.mode == "w", "this function can only be called in write mode"

        for member in ("channels", "frequency", "bits_per_sample"):
            assert hasattr(self, member), "The member '{}' is required to be set in order to start writing".format(member)

        self.average_bytes_per_sec = self.frequency * self.channels * self.bits_per_sample // 8
        self.block_align = self.channels * ((self.bits_per_sample + 7) // 8)
        self.format = self.format if hasattr(self, "format") else WAVE_FORMAT_PCM

##        assert self.format == WAVE_FORMAT_PCM, "Sorry, currently only PCM is supported.."

        self.format_chunk_size = 16

        self.riff_chunk_size = 36
        self.data_chunk_size = 0

        self.riff_chunk_size_offset = 4
        self.data_chunk_size_offset = 40

        self.data_starts_at = 44
        self.data_position = 0

        data_as_list = []

        data_as_list.append(fourccRIFF)
        data_as_list.append(itb(self.riff_chunk_size, 4))
        data_as_list.append(fourccWAVE)

        data_as_list.append(fourccFMT)
        data_as_list.append(itb(self.format_chunk_size, 4))
        data_as_list.append(itb(self.format, 2))
        data_as_list.append(itb(self.channels, 2))
        data_as_list.append(itb(self.frequency, 4))
        data_as_list.append(itb(self.average_bytes_per_sec, 4))
        data_as_list.append(itb(self.block_align, 2))
        data_as_list.append(itb(self.bits_per_sample, 2))
        
        data_as_list.append(fourccDATA)
        data_as_list.append(itb(0, 4))

        data = b"".join(data_as_list)

        self.wf.seek(0)
        self.wf.write(data)

    def write(self, data):
        """Writes <data> to the data chunk of the wave file"""
        assert type(data) == bytes, "can only write data as bytes"
        if not self._prepared_for_writing:
            self._prepare_for_writing()
            self._prepared_for_writing = True

        written_bytes = len(data)
        self.wf.seek(self.data_starts_at + self.data_position)
        self.wf.write(data)
        
        self.data_position += written_bytes
        self.data_chunk_size += written_bytes
        self.riff_chunk_size += written_bytes
        
        self.wf.seek(self.riff_chunk_size_offset)
        self.wf.write(itb(self.riff_chunk_size, 4))
        self.wf.seek(self.data_chunk_size_offset)
        self.wf.write(itb(self.data_chunk_size, 4))
        

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
        assert self.mode == "r", "this function can only be called in read mode"
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
        assert self.mode == "r", "this function can only be called in read mode"
        if max_bytes:
            out = self.wf.read(min(max_bytes, self.end_of_data - self.data_position))
        else:
            out = self.wf.read(self.end_of_data - self.data_position)
        bytes_written = len(out)
        
        if bytes_written == 0:
            return b""
        
        self.data_position += bytes_written
        return out

    def read_samples(self, number_of_samples):
        """Returns <number_of_samples> samples"""
        return self.read(self.bytes_per_sample * number_of_samples)

    def tell(self):
        """Returns the current position in the data chunk"""
        return self.data_position

    def close(self):
        """Closes the file pointer"""
        if self.mode == "w" and hasattr(self, "data_chunk_size") and self.data_chunk_size % 2:
            self.wf.write(b"\x00")
        self.wf.close()

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
        self.close()

    __enter__ = lambda self: self
    __exit__ = lambda self, t, v, tr: self.close()

open = lambda path, mode = "r", **kwargs: Wave(path, mode=mode, **kwargs)
