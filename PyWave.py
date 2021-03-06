import warnings
import builtins

builtin_open = builtins.open

# bti(bytes_: bytes) -> int
#     Converts bytes to int (little endian)
bti = lambda bytes_: int.from_bytes(bytes_, "little")

# itb(int_: int, length: int = 2) -> bytes
#     Converts `int_` to a bytes string of the specified `length`
itb = lambda int_, length = 2: int_.to_bytes(length, "little")

# clstr(bytes_: bytes) -> str
#     Takes a null-terminated bytes object and returns the contained string.
#     Used to read null-terminated strings in DISP/bext chunks.
clstr = lambda bytes_: bytes_.decode().replace('\x00','')      

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

# RIFF WAVE chunks
fourccRIFF  = b"RIFF"   # RIFF file tag (1st 4 bytes)
fourccWAVE  = b"WAVE"   # RIFF subchunk: WAVE file tag (3rd 4 bytes)

# WAVE subchunks that are part of the 1991 standard (https://www.aelius.com/njh/wavemetatools/doc/riffmci.pdf)
fourccFMT   = b"fmt "   # format chunk, required for WAV-files
fourccDATA  = b"data"   # data chunk, required for WAV-files
fourccFACT  = b"fact"   # Fact chunks exist in all wave files that are compressed or that have a wave list chunk. 
                        # See https://www.recordingblogs.com/wiki/fact-chunk-of-a-wave-file / https://sites.google.com/site/musicgapi/technical-documents/wav-file-format / http://www-mmsp.ece.mcgill.ca/Documents/AudioFormats/WAVE/WAVE.html
fourccDISP  = b"DISP"   # Clipboard contents (usually CF_TEXT = 0x00000001), see http://netghost.narod.ru/gff/vendspec/micriff/ms_riff.txt and https://docs.microsoft.com/en-us/windows/win32/dataxchg/standard-clipboard-formats

# Chunks used to pad out data when we need more than one byte:
fourccJUNK  = b"JUNK"   # This chunk is there just as placeholder for future data and can always be ignored.
fourccPAD   = b"PAD "   # This chunk is there to pad data to align it on certain boundaries. Used when padding to more than a WORD boundary (like 8 bytes).
fourccFake  = b"Fake"   # Same as the PAD chunk. 

# LIST chunks and subchunks
fourccLIST  = b"LIST"   # AVI MetaEdit LIST chunk
fourccLIST_INFO = b"INFO"   # LIST Subchunk with INFO tags, see https://mediaarea.net/AVIMetaEdit/core_doc_help for values inside the metadata.
fourccLIST_ADTL = b"adtl"   # LIST Subchunk that goes together with a "cue" chunk. It's an Associated Data List that can contain labl, note, ltxt and file subsubchunks
fourccLIST_ADTL_LABL  = b"labl"   # The label chunk is always contained inside of an associated data list chunk. It is used to associate a text label with a Cue Point. 
fourccLIST_ADTL_NOTE  = b"note"   # The note chunk is always contained inside of an associated data list chunk. It is used to associate a text comment with a Cue Point.
fourccLIST_ADTL_LTXT  = b"ltxt"   # The labeled text chunk is always contained inside of an associated data list chunk. It is used to associate a text label with a region or section of waveform data.

# Chunks that are not meant for uncompressed WAV files
fourccXWMA  = b"XWMA"   # XAudio2 compressed data. We can't parse this right now.


OK = 0
ERROR_NOT_A_WAVE_FILE = -1

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

        self.messages = []      # this list will hold our warning messages and even errors (not the type that causes an abort though).
        
        self.wf = builtin_open(path, mode + "b")

        self.path = path
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
            

    def _prepare_read(self, auto_read):
        assert self.mode == "r", "this function can only be called in read mode"
        if self._check_file_format() != OK:
            raise PyWaveError("'{}' does not appear to be a wave file.".format(self.path))

        self.chunks = self._get_chunks()

        if not fourccFMT in self.chunks:
            raise PyWaveError("'{}' is missing the 'fmt ' chunk.".format(self.path))

        if not fourccDATA in self.chunks:
            raise PyWaveError("'{}' is missing the 'data' chunk.".format(self.path))

        fmt_size, fmt_position = self.chunks[fourccFMT]

        if fmt_size == 16:
            self.wfx = PCMWAVEFORMAT(self._read_chunk_data(fmt_size, fmt_position))
        elif fmt_size == 18:
            self.wfx = WAVEFORMATEX(self._read_chunk_data(fmt_size, fmt_position))
        elif 18 < fmt_size <= 40:
            self.wfx = WAVEFORMATEXTENSIBLE(self._read_chunk_data(fmt_size, fmt_position))
        else:
            raise PyWaveError("'{}' has an unknown or unsupported format.".format(self.path))

        self.metadata = {}

        if fourccLIST in self.chunks:
            ChunkSize, ChunkPosition = self.chunks[fourccLIST]
            self.wf.seek(ChunkPosition)
            # correct alignment errors by reading 1 byte more than required and testing it for a null byte.
            fourCC = self.wf.read(5)
            if fourCC[0] == 0:          # the subchunk tag can be misaligned if someone added a "\x00" to the LIST string. If that happened we compensate for that.
                padding = 1
                fourCC = fourCC[1:]
            else:
                padding = 0
                fourCC = fourCC[:4]
            if fourccLIST_INFO == fourCC:
                self.metadata[fourCC.decode()] = self._get_info_chunk(ChunkSize, ChunkPosition + 4 + padding)
            # otherwise read the LIST subchunk adtl as raw metadata
            elif fourccLIST_ADTL == fourCC:
                self.metadata[fourCC.decode()] = self._read_chunk_data(ChunkSize, ChunkPosition)
       
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
            # Software must process a multiple of 1 or more BlockAlign bytes of data at a time.
            # Try using wf.read(3) before you read the rest of the file to see the effect of leaving this out :)
            if max_bytes < self.block_align: 
                max_bytes = self.block_align
                self.messages.append("Warning: attempt to read less bytes than the blockalign size of {}.".format(self.block_align))
            if (max_bytes % self.block_align) != 0:
                max_bytes = ((max_bytes // self.block_align) + 1) * self.block_align
                self.messages.append("Warning: attempt to read a number of bytes that is not a multiple of the blockalign size of {}.".format(self.block_align))
            out = self.wf.read(min(max_bytes, self.end_of_data - self.data_position))
        else:
            out = self.wf.read(self.end_of_data - self.data_position)
        bytes_read = len(out)
        
        if bytes_read == 0:
            return b""
        
        self.data_position += bytes_read
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

        self.data_position = pos - self.data_starts_at
    
        self.wf.seek(pos)

    def _read_chunk_data(self, size, offset):
        """Reads `size` bytes of data at `offset` from `file_`.
Note: Position is not reset after reading."""
        self.wf.seek(offset)
        return self.wf.read(size)


    def _check_file_format(self):
        """Tests if `file_` contains the RIFF and WAVE headers.
Returns `OK` (0) on success and `ERROR_NOT_A_WAVE_FILE` (-1) on failure."""
        self.wf.seek(0)
        RIFFChunk = self.wf.read(4)
        self.wf.seek(4, 1)
        WAVETag = self.wf.read(4)

        if RIFFChunk != fourccRIFF or not WAVETag in (fourccWAVE,):
            return ERROR_NOT_A_WAVE_FILE
        return OK


    def _get_chunks(self):
        """Finds all the chunks in `file_`."""
        self.wf.seek(4)                     # skip 'RIFF' at start of file
        total_size = bti(self.wf.read(4))   # This should be the size of the entire file in bytes minus 8 bytes for the two fields not included in this count. Not always correct!
        self.wf.seek(4, 1)
        
        out = {}                            # WARNING: a set instead of a list only works when each chunk is unique. But it is valid to have more than one LIST chunk.
        Offset = 12
        
        read_bytes = 4
        read = True

        # An incorrect total_size in the file can cause reads past end of file.
        # Fixed by checking for an empty read when trying to read the next chunk (empty read = EOF)
        # We also pre-emptively prevent the scenario where we encounter a double top-level chunk (like two versions of ID3). 
        # We make an exception only for the LIST chunk, that can occur multiple times but with a different form type ID.
        while read_bytes < total_size and read:
            read = self.wf.read(4)
            if read != b'':             # if not EOF
                read_bytes += len(read)
                ChunkType = read
        
                read = self.wf.read(4)
                read_bytes += len(read)         # should always be 4 unless we're at EOF
                ChunkDataSize = bti(read)
       
                Offset += 8
                if out.get(ChunkType) != None and ChunkType != fourccLIST:
                     self.messages.append("ERROR: chunk '{0}' has a duplicate (ignored) chunk of the same type at position {1} with size {2}!".format(ChunkType.decode(),Offset,ChunkDataSize))
                else:
                    out[ChunkType] = (ChunkDataSize, Offset)
        
                self.wf.seek(ChunkDataSize, 1)
                read_bytes += ChunkDataSize
                Offset += ChunkDataSize

                # "All information in a wave file must be word aligned (i.e., aligned at every two bytes)."
                # "If a chunk has an odd number of bytes, then it will be padded with a zero byte, although this byte will not be counted in the size of the chunk."
                # Now, here we have an issue. We should align on words, but if we do that, we may miss the next chunk by 1, for misaligned chunks. 
                # So if we get uneven data, keep it as reported. The parser for the chunk just needs to deal with it and correctly align the data on word boundaries.
                # If our next read is not at the EOF, then check if our next read is another chunk by checking for a null byte read. 
                # If we read a null byte, keep it skipped. Otherwise, go back 1 byte.
                if read_bytes < total_size and (ChunkDataSize % 2 == 1):
                    read = self.wf.read(1)                              # read the padding byte to see if it is actually a padding byte, or the first byte of a chunk
                    if read not in (b'',b'\x00'): 
                        self.wf.seek(-1, 1)                             # if we are aligned on non-word (wrong), then go back 1 byte

        # If the read_bytes are not the same as the total_size at EOF, we need to correct total_size to the real size value in read_bytes.
        if total_size != read_bytes: total_size = read_bytes
        return out


    # Specific function to read the INFO subchunk in the LIST chunk.
    # See for specs: https://www.recordingblogs.com/wiki/list-chunk-of-a-wave-file
    def _get_info_chunk(self, size, offset):
        self.wf.seek(offset)                      # the offset is positioned after the INFO subchunk.
        out = {}
        read_bytes = 4
        while read_bytes < size:
            name    = self.wf.read(4)           # get the info tag (IARL, ISFT, ICR, etc. )
            size_   = bti(self.wf.read(4))      # get the size of the info tag. 
            padbyte = size_ % 2                 # all text must be word aligned, so add 1 byte as required.
            data    = self.wf.read(size_-1)     # do not read the 00 terminator of each line.
            self.wf.seek(padbyte + 1, 1)        # skip 1 character + padding byte if required
            read_bytes += 8 + size_ + padbyte   # don't forget to add the padding byte to the number of bytes read

            out[name.decode()] = clstr(data)
        return out


    def __del__(self):
        self.close()


    __enter__ = lambda self: self
    __exit__ = lambda self, t, v, tr: self.close()

open = lambda path, mode = "r", **kwargs: Wave(path, mode=mode, **kwargs)
