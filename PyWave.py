import warnings
import builtins
import struct       # used for reading the PEAK chunk, as it contains floating point values in the bytestring

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


# I think this may be moved into the class now. However, not sure if required for other stuff if we externalize the chunk parsing for instance.
WAVE_FORMAT_UNKNOWN         = 0x0000      # unknown, unsupported
WAVE_FORMAT_PCM             = 0x0001      # uncompressed, supported
WAVE_FORMAT_ADPCM           = 0x0002      # compressed, unsupported
WAVE_FORMAT_IEEE_FLOAT      = 0x0003      # uncompressed, supported
WAVE_FORMAT_ALAW            = 0x0006      # compressed, unsupported
WAVE_FORMAT_MULAW           = 0x0007      # compressed, unsupported
WAVE_FORMAT_DVI_ADPCM       = 0x0011      # compressed, unsupported
WAVE_FORMAT_G723_ADPCM      = 0x0014      # compressed, unsupported
WAVE_FORMAT_GSM610          = 0x0031      # compressed, unsupported
WAVE_FORMAT_MPEG            = 0x0050      # compressed, unsupported
WAVE_FORMAT_MPEGLAYER3      = 0x0055      # compressed, unsupported
WAVE_FORMAT_DOLBY_AC3_SPDIF = 0x0092      # compressed, unsupported
WAVE_FORMAT_EXTENSIBLE      = 0xFFFE      # reverts to any of the previous wave formats (in the CodecID)


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
            self.BlockAlign     = bti(data[12:14])      # BlockAlign must be equal to the product of Channels and BitsPerSample divided by 8 (bits per byte). Software must process a multiple of nBlockAlign bytes of DATA at a time.
            self.BitsPerSample  = bti(data[14:16])      # BitsPerSample is 8 or 16 for PCM, and the size of the container of a single sample for the EXT format. Must be an integer multiple of 8.
            self.cbSize         = bti(data[16:18])      # cbSize or ExtensionSize should always be (at least) 22 to pad the chunk to length 40 in EXT format
            self.Samples        = bti(data[18:20])      # Samples is a union of three potential fields, depending on the format: validbitspersample, samplesperblock, or reserved
            self.ChannelMask    = bti(data[20:24])      # Indicates which speakers are assigned to which channels
            self.SubFormat      = data[24:]             # Since the format tag indicates EXT format, which can contain numerous formats, we need SubFormat to tell us what we have inside the EXT format.
            #
            # SubFormat is a GUID with template {XXXXXXXX-0000-0010-8000-00AA00389B71} (RFC-2361)
            # MS GUID byte order: the first three groups are native byte order (little endian for us, since we only read RIFF files)
            # The other groups are Big Endian.
            # The GUID indicates the Codec used for compressing the data in the WAV-file. We can only deal with uncompressed data at this point,
            # the rest can only be read and displayed but the recipient needs to decompress it by themselves.
            # Source of this code: https://github.com/scipy/scipy/blob/v1.6.1/scipy/io/wavfile.py#L365-L373
            # See also: https://docs.microsoft.com/en-us/windows-hardware/drivers/audio/converting-between-format-tags-and-subformat-guids
            #
            self.CodecGUID  = '{0}-{1}-{2}-{3}-{4}'.format(data[24:28].hex(), data[28:30].hex(), data[30:32].hex(), data[32:34].hex(), data[34:40].hex())
            tail = b'\x00\x00\x10\x00\x80\x00\x00\xAA\x00\x38\x9B\x71'      # little endian version of KSDATAFORMAT_SUBTYPE_WAVEFORMATEX, minus the first 4 bytes
            if self.SubFormat.endswith(tail):
                self.CodecID = bti(data[24:28])         # first group = little endian
            else:
                self.CodecID = WAVE_FORMAT_UNKNOWN      # unknown codec id, when the GUID doesn't conform to the expected format


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

# LIST subchunks and corresponding subsubchunks of LIST
# Notes:
# 1) The DLS format recognizes a lot more LIST subchunks, but they're not official WAVE LIST subchunks.
# 2) An all-lowercase list type is only supposed to have meaning relative to the form that contains it, uppercase is supposed to be globally unique, but this convention is unlikely to be obeyed.
fourccLIST  = b"LIST"   # AVI MetaEdit LIST chunk
fourccLIST_INFO = b"INFO"   # LIST Subchunk with INFO tags, see https://mediaarea.net/AVIMetaEdit/core_doc_help for values inside the metadata.
fourccLIST_ADTL = b"adtl"   # LIST Subchunk that goes together with a "cue" chunk. It's an Associated Data List that can contain labl, note, ltxt and file subsubchunks
fourccLIST_ADTL_LABL  = b"labl"   # The label chunk is always contained inside of an associated data list chunk. It is used to associate a text label with a Cue Point. 
fourccLIST_ADTL_NOTE  = b"note"   # The note chunk is always contained inside of an associated data list chunk. It is used to associate a text comment with a Cue Point.
fourccLIST_ADTL_LTXT  = b"ltxt"   # The labeled text chunk is always contained inside of an associated data list chunk. It is used to associate a text label with a region or section of waveform data.
fourccLIST_WAVL = b"wavl"   # LIST Subchunk WAVELIST that is a misguided attempt to compress WAVs with data and "silent" chunks. We should probably roll them up into a single data chunk. For now just read the metadata and abort as we cannot parse it yet
fourccLIST_WAVL_DATA = b"data"   # data subsubchunk that is exactly the same as a normal data chunk, except we can have more than one.
fourccLIST_WAVL_SLNT = b"slnt"   # silent subsubchunk that just says for how many samples there is silence, before we get to another data chunk.

# Chunks that are not meant for uncompressed WAV files
fourccXWMA  = b"XWMA"   # XAudio2 compressed data. We can't parse this right now.

# The PEAK chunk indicates peak amplitude of the soundfile for each channel.
# Source: https://web.archive.org/web/20081201144551/http://music.calarts.edu/~tre/PeakChunk.html
# Also present in Apple's Core Audio Format specification (with a better approach to the timer field than the WAV PEAK chunk)
fourccPEAK  = b"PEAK"

# cue chunk and corresponding chunks that depend on the CUE subchunk
fourccCUE   = b"cue "   # Cue sheet, see https://www.recordingblogs.com/wiki/cue-chunk-of-a-wave-file (and https://www.aelius.com/njh/wavemetatools/doc/riffmci.pdf)
# These chunks are only valid if there is also a cue chunk because they refer to the Cue list. See https://sites.google.com/site/musicgapi/technical-documents/wav-file-format
fourccPLST  = b"plst"   # Playlist chunk, the playlist chunk specifies the play order of a series of cue points.
fourccSMPL  = b"smpl"   # Sample chunk containing information about note and pitch of the samples in the cue sheet, see https://sites.google.com/site/musicgapi/technical-documents/wav-file-format#smpl
# See also the very sensible http://www.piclist.com/techref/io/serial/midi/wave.html for info on cue, smpl and plst

# SoundForge chunks, unregistered but public format. Related to cue and plst
fourccTLST  = b"tlst"   # SoundForge chunk: Trigger List (see: http://jdarks.com/files/soundforge5_manual.pdf) - only works if there is either a cue and/or plst chunk present.

# Metadata chunks
fourccXMP   = b"_PMX"   # Adobe XMP specification for XML metadata of (raw) images, see https://wwwimages2.adobe.com/content/dam/acom/en/devnet/xmp/pdfs/XMP%20SDK%20Release%20cc-2016-08/XMPSpecificationPart3.pdf
fourccINST  = b"inst"   # The instrument chunk is used to describe how the waveform should be played as an instrument sound. See https://sites.google.com/site/musicgapi/technical-documents/wav-file-format#inst
fourccID3A  = b"id3 "   # ID3 metadata chunk. See https://en.wikipedia.org/wiki/ID3 and https://id3.org/id3v2.3.0. This can be read by PyTagLib so why bother? It is a very complex format to read and write.
fourccID3B  = b"ID3 "   # Uppercase version of the ID3 fourCC code.

# ACID wav chunks, proprietary format hence not parsed:
fourccACID  = b"acid"   # ACIDized WAVs contain proprietary information that support loops. See https://www.kvraudio.com/forum/viewtopic.php?t=172636
fourccSTRC  = b"strc"   # ACID WAV (sub?)chunk, unknown content


# Broadcast Audio Extension WAVE files can contain the following chunks:
fourccBEXT  = b"bext"   # Broadcast Audio Extension, see https://www.loc.gov/preservation/digital/formats/fdd/fdd000356.shtml / https://tech.ebu.ch/docs/tech/tech3285.pdf
fourccIXML  = b"iXML"   # Broadcast Audio Extension iXML chunk
fourccQLTY  = b"qlty"   # Broadcast Audio Extension Quality chunk
fourccMEXT  = b"mext"   # Broadcast Audio Extension MPEG audio extension chunk
fourccLEVL  = b"levl"   # Peak Envelope chunk, see https://tech.ebu.ch/docs/tech/tech3285s3.pdf
fourccLINK  = b"link"   # Link chunk
fourccAXML  = b"axml"   # AXML chunk, see https://tech.ebu.ch/docs/tech/tech3285s5.pdf

# Radio Industry's Traffic Data WAVE File Standard (AES Standard AES46-2002: paywalled)
fourccCART  = b"cart"   # Often found in BEXT WAV files

# Ignore these chunks in the generic read, as we have dedicated readers for them.
# We read all other chunks with a generic reader.
KNOWN_FOURCC = {fourccFMT, fourccDATA, fourccLIST, fourccDISP, fourccBEXT, fourccCART, fourccPEAK}


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

    # Definitions pulled inside the class so we can use them outside the class as well.
    # If there is a better way of doing this, feel free to fix it :)
    WAVE_FORMAT_UNKNOWN         = WAVE_FORMAT_UNKNOWN
    WAVE_FORMAT_PCM             = WAVE_FORMAT_PCM
    WAVE_FORMAT_IEEE_FLOAT      = WAVE_FORMAT_IEEE_FLOAT
    WAVE_FORMAT_EXTENSIBLE      = WAVE_FORMAT_EXTENSIBLE

    # these wave formats are added mostly for completionist purposes, but we cannot process them.
    WAVE_FORMAT_ADPCM           = WAVE_FORMAT_ADPCM
    WAVE_FORMAT_ALAW            = WAVE_FORMAT_ALAW
    WAVE_FORMAT_MULAW           = WAVE_FORMAT_MULAW
    WAVE_FORMAT_DVI_ADPCM       = WAVE_FORMAT_DVI_ADPCM
    WAVE_FORMAT_G723_ADPCM      = WAVE_FORMAT_G723_ADPCM
    WAVE_FORMAT_GSM610          = WAVE_FORMAT_GSM610
    WAVE_FORMAT_MPEG            = WAVE_FORMAT_MPEG
    WAVE_FORMAT_MPEGLAYER3      = WAVE_FORMAT_MPEGLAYER3
    WAVE_FORMAT_DOLBY_AC3_SPDIF = WAVE_FORMAT_DOLBY_AC3_SPDIF


    def __init__(self, path, auto_read = False, mode = "r", **kwargs):
        assert mode in ("r", "w"), "mode has to be (r)ead or (w)rite"

        self.messages = []      # this list will hold our warning messages and even errors (not the type that causes an abort though).
        
        # set variables before opening, as errors will cause __del__ to be called eventually,
        # which will then raise an exception because mode isn't set.
        self.path = path
        self.mode = mode

        self.wf = builtin_open(path, mode + "b")

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

            # use sensible defaults if the values are missing
            if not hasattr(self, "channels"):           self.channels = 2
            if not hasattr(self, "frequency"):          self.frequency = 48000
            if not hasattr(self, "bits_per_sample"):    self.bits_per_sample = 16
            if not hasattr(self, "format"):             self.format = WAVE_FORMAT_PCM

    @property
    def format_name(self):
        return Wave.get_format_name(self.format)


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

        # first, parse the known and specific tags
        # NOTE: THIS ASSUMES WE ONLY HAVE ONE LIST CHUNK! That is not always true!
        if fourccLIST in self.chunks:
            ChunkSize, ChunkPosition = self.chunks[fourccLIST]
            self.wf.seek(ChunkPosition)
            # correct alignment errors by reading 1 byte more than required and testing it for a null byte.
            fourCC = self.wf.read(5)
            if fourCC[0] == 0:          # the subchunk tag can be misaligned if someone added a "\x00" to the LIST string. If that happened we compensate for that.
                self.messages.append("Warning: subchunk tag for LIST subchunk '{}' is misaligned.".format(fourCC.decode()))
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
            # the wavl (wavelist) subchunk is unsupported and raises an error.
            elif fourccLIST_WAVL == fourCC:
                self.metadata[fourCC.decode()] = _read_chunk_data(self.wf, ChunkSize, ChunkPosition)
                self.messages.append("Error: subchunk tag for LIST subchunk '{}' is unsupported. Please raise an issue on Github.".format(fourCC.decode()))
                raise PyWaveError("'{}' has unsupported WAVELIST chunks. Please raise an issue on Github.".format(self.path))
            else:
                self.messages.append("Warning: subchunk tag for LIST subchunk '{}' is unknown.".format(fourCC.decode()))

        # this could be done using a function map. But for now it will do.
        if fourccDISP in self.chunks:
            ChunkSize, ChunkPosition = self.chunks[fourccDISP]
            self.wf.seek(ChunkPosition)
            self.metadata[fourccDISP.decode()] = self._get_disp_chunk(ChunkSize, ChunkPosition)

        if fourccBEXT in self.chunks:
            ChunkSize, ChunkPosition = self.chunks[fourccBEXT]
            self.wf.seek(ChunkPosition)
            self.metadata[fourccBEXT.decode()] = self._get_bext_chunk(ChunkSize, ChunkPosition)

        if fourccCART in self.chunks:
            ChunkSize, ChunkPosition = self.chunks[fourccCART]
            self.wf.seek(ChunkPosition)
            self.metadata[fourccCART.decode()] = self._get_cart_chunk(ChunkSize, ChunkPosition)

        if fourccPEAK in self.chunks:
            ChunkSize, ChunkPosition = self.chunks[fourccPEAK]
            self.wf.seek(ChunkPosition)
            self.metadata[fourccPEAK.decode()] = self._get_peak_chunk(ChunkSize, ChunkPosition)

        # once we've checked the known chunks, add everything that is not yet parsed to the metadata as bytestring through the generic reader
        for fourCC in self.chunks:
            if fourCC not in KNOWN_FOURCC:
                ChunkSize, ChunkPosition = self.chunks[fourCC]
                self.wf.seek(ChunkPosition)
                self.metadata[fourCC.decode()] = self._read_chunk_data(ChunkSize, ChunkPosition)

        # get the DATA chunk info
        self.data_length, self.data_starts_at = self.chunks[fourccDATA]

        self.format = self.wfx.FormatTag
        if self.format == self.WAVE_FORMAT_EXTENSIBLE:
            self.codec_guid = self.wfx.CodecGUID
            self.subformat = self.codec_id = self.wfx.CodecID   # Since the format tag indicates EXT format, which can contain numerous formats, we need the codec_id or subformat to tell us what we have inside the EXT format.
        else:
            self.subformat = self.WAVE_FORMAT_UNKNOWN           # For other waveformats we do not have a valid subformat, so set it to WAVE_FORMAT_UNKNOWN

        self.compressed = (self.format == WAVE_FORMAT_EXTENSIBLE and self.subformat not in (WAVE_FORMAT_PCM, WAVE_FORMAT_IEEE_FLOAT)) or (self.format not in (WAVE_FORMAT_PCM, WAVE_FORMAT_IEEE_FLOAT, WAVE_FORMAT_EXTENSIBLE))
        if self.compressed:
            if fourccFACT not in self.chunks:
                self.messages.append("Error (recoverable): '{}' is missing the 'fact' chunk while compressed format {}, {} requires it.".format(self.path, self.format, self.subformat))

        self.channels = self.wfx.Channels
        
        # The WAVE_FORMAT_EXTENSIBLE contains a channelmask that shows which speakers are assigned to which channels
        if self.format == self.WAVE_FORMAT_EXTENSIBLE:
            self.channel_mask = self.wfx.ChannelMask
        else:
            if 1 == self.channels:
                self.channel_mask = 0x4  # mono = Front Center
            if 2 == self.channels:
                self.channel_mask = 0x3  # stereo = Front Left, Front Right

        self.samples_per_sec = self.frequency = self.wfx.SamplesPerSec
        self.average_bytes_per_sec = self.wfx.AvgBytesPerSec
        self.block_align = self.wfx.BlockAlign
        self.bits_per_sample = self.wfx.BitsPerSample

        # For WAVEFORMATEXTENSIBLE, decode the Samples field
        # If the subformat indicates a compressed format, Samples contains samples per block, otherwise it contains valid bits per sample. A 0 indicates that neither meaning is applicable.
        self.samples_per_block = 0
        self.valid_bits_per_sample = self.bits_per_sample
        if self.format == WAVE_FORMAT_EXTENSIBLE:
            # if not a compressed format, then it is the valid bits per sample
            if not self.compressed:
                if self.wfx.Samples != 0:                       # if we have valid information, use it
                    self.valid_bits_per_sample = self.wfx.Samples
                    if self.valid_bits_per_sample > self.bits_per_sample:
                        self.messages.append('Warning: the valid bits per sample field in the samples union (WAVEFORMATEXTENSIBLE header) should be <= the bits per sample, but is > bits per sample. Assuming valid bits per sample to be equal to bits per sample.')
                        self.valid_bits_per_sample = self.bits_per_sample
                else:
                    self.messages.append('Warning: the valid bits per sample field in the samples union (WAVEFORMATEXTENSIBLE header) should be non-zero, but is zero. Assuming valid bits per sample to be equal to bits per sample.')
            # if it is a compressed format, then it is the nr of samples per block
            else:
                if self.wfx.Samples != 0:                       # if we have valid information, use it
                    self.samples_per_block = self.wfx.Samples
                else:
                    self.messages.append('Warning: the samples per block field in the samples union (WAVEFORMATEXTENSIBLE header) should be non-zero, but is zero.')

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


    def read(self, max_bytes=None):
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
        # do not attempt to write or close the wavefile if it never initialized correctly.
        if hasattr(self, "wf"):
            if self.mode == "w" and hasattr(self, "data_chunk_size") and self.data_chunk_size % 2:
                self.wf.write(b"\x00")
            self.wf.close()


    def seek(self, offset, whence=0):
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

        if RIFFChunk != fourccRIFF or WAVETag != fourccWAVE:
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
                if out.get(ChunkType) is not None and ChunkType != fourccLIST:
                    self.messages.append("ERROR: chunk '{0}' has a duplicate (ignored) chunk of the same type at position {1} with size {2}!".format(ChunkType.decode(), Offset, ChunkDataSize))
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
                    if read not in (b'', b'\x00'):
                        self.wf.seek(-1, 1)                             # if we are aligned on non-word (wrong), then go back 1 byte

        # If the read_bytes are not the same as the total_size at EOF, we need to correct total_size to the real size value in read_bytes.
        # If they are the same, the statement does not harm anything :)
        total_size = read_bytes
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


    # Specific function to read the DISP chunk
    # See for specs: https://www.recordingblogs.com/wiki/list-chunk-of-a-wave-file
    def _get_disp_chunk(self, size, offset):
        self.wf.seek(offset)                      # the offset is positioned after the DISP tag + size tag.
        out = {}

        disp_type    = bti(self.wf.read(4))      # get the DISP type (see windows.h for the standard windows clipboard type. Expected: 0x01000000 (== 1 == CF_TEXT).
        size += size % 2                        # All text must be word aligned, so add 1 byte as required.
        size -= 4

        if (disp_type == 1):    # CF_TEXT? Then translate the text.
            data    = clstr(self.wf.read(size))
        else:
            data    = self.wf.read(size).decode()

        out['type'] = disp_type
        out['data'] = data
        return out

    # Specific function to read the PEAK chunk
    # See for specs: https://web.archive.org/web/20081201144551/http://music.calarts.edu/~tre/PeakChunk.html
    def _get_peak_chunk(self, size, offset):
        self.wf.seek(offset)                      # the offset is positioned after the DISP tag + size tag.
        out = {}

        version = bti(self.wf.read(4))    # version should be 1
        if version != 1:
            self.messages.append("Warning: chunk 'PEAK' at position {0} (size {1}) has an incorrect version. We expected version 1 but got {2}.".format(offset, size, version))
        timestamp = bti(self.wf.read(4))  # timestamp in seconds after 1-1-1970 (unix timestamp). 1566996638 == Wed Aug 28 2019 12:50:38 GMT+0000

        # for each channel we get a float value and unsigned long position.
        # We can see how many channels we have values for, by subtracting the version and timestamp fields from the size
        # and then dividing by the size of the information for each channel
        channels = (size - 8) // 8

        peaks = []
        for i in range(channels):
            value = struct.unpack('<f', self.wf.read(4))[0]    # little endian. struct returns a tuple, so get first element
            position = bti(self.wf.read(4))
            peaks.append({'value': value, 'position': position})

        out['version'] = version
        out['timestamp'] = timestamp
        out['peaks'] = peaks
        return out

    # Specific function to read the BEXT chunk
    # See for specs: https://tech.ebu.ch/docs/tech/tech3285.pdf
    #
    # Format:
    #   CHAR Description[256];
    #   CHAR Originator[32]; /* ASCII : «Name of the originator» */
    #   CHAR OriginatorReference[32]; /* ASCII : «Reference of the originator» */
    #   CHAR OriginationDate[10]; /* ASCII : «yyyy:mm:dd» */ note: some people put in a "/" as separator! not standard!
    #   CHAR OriginationTime[8]; /* ASCII : «hh:mm:ss» */
    #   DWORD TimeReferenceLow; /* First sample count since midnight, low word */
    #   DWORD TimeReferenceHigh; /* First sample count since midnight, high word */
    #   WORD Version; /* Version of the BWF; unsigned binary number */
    #   BYTE UMID_0 /* Binary byte 0 of SMPTE UMID */
    #   ....
    #   BYTE UMID_63 /* Binary byte 63 of SMPTE UMID */
    #   WORD LoudnessValue; /* WORD : «Integrated Loudness Value of the file in LUFS (multiplied by 100) » */
    #   WORD LoudnessRange; /* WORD : «Loudness Range of the file in LU (multiplied by 100) » */
    #   WORD MaxTruePeakLevel; /* WORD : «Maximum True Peak Level of the file expressed as dBTP (multiplied by 100) » */
    #   WORD MaxMomentaryLoudness; /* WORD : «Highest value of the Momentary Loudness Level of the file in LUFS (multiplied by 100) » */
    #   WORD MaxShortTermLoudness; /* WORD : «Highest value of the Short-Term Loudness Level of the file in LUFS (multiplied by 100) » */
    #   BYTE Reserved[180]; /* 180 bytes, reserved for future use, set to “NULL” */
    #   CHAR CodingHistory[]; /* ASCII : « History coding » */
    #
    def _get_bext_chunk(self, size, offset):
        self.wf.seek(offset)                      # the offset is positioned after the bext tag + size tag.
        out = {}
        data    = self.wf.read(size)

        out['Description'] = clstr(data[0:256])
        out['Originator']  = clstr(data[256:288])
        out['OriginatorReference'] = clstr(data[288:320])
        out['OriginationDate'] = clstr(data[320:330])
        out['OriginationTime'] = clstr(data[330:338])
        out['TimeReferenceLow'] = bti(data[338:342])
        out['TimeReferenceHigh'] = bti(data[342:346])
        out['Version'] = bti(data[346:348])
        out['SMPTE UMID'] = data[348:412]
        out['LoudnessValue'] = bti(data[412:414])
        out['LoudnessRange'] = bti(data[414:416])
        out['MaxTruePeakLevel'] = bti(data[416:418])
        out['MaxMomentaryLoudness'] = bti(data[418:420])
        out['MaxShortTermLoudness'] = bti(data[420:422])
        #   out['Reserved'] = data[422:602]
        out['CodingHistory'] = clstr(data[602:])
        return out


    # Specific function to read the CART chunk
    # See for specs: http://www.cartchunk.org/cc_spec.htm
    # See also: https://github.com/jmcmellen/cdputils (the official specs are paywalled), specifically https://github.com/jmcmellen/cdputils/blob/master/cdpwavefile.py
    #
    # Format:
    # typedef struct cart_extension_tag
    # {
    #    CHAR Version[4];             // Version of the data structure
    #    CHAR Title[64];              // ASCII title of cart audio sequence
    #    CHAR Artist[64];             // ASCII artist/creator name
    #    CHAR CutID[64];              // ASCII cut number identification
    #    CHAR ClientID[64];           // ASCII client identification
    #    CHAR Category[64];           // ASCII Category ID, PSA, NEWS, etc
    #    CHAR Classification[64];     // ASCII Classification or auxiliary key
    #    CHAR OutCue[64];             // ASCII out cue text
    #    CHAR StartDate[10];          // ASCII yyyy/mm/dd
    #    CHAR StartTime[8];           // ASCII hh:mm:ss
    #    CHAR EndDate[10];            // ASCII yyyy/mm/dd
    #    CHAR EndTime[8];             // ASCII hh:mm:ss
    #    CHAR ProducerAppID[64];      // Name of vendor/application
    #    CHAR ProducerAppVersion[64]; // Version of producer application
    #    CHAR UserDef[64];            // User defined text
    #    DWORD dwLevelReference;      // Sample value for 0 dB reference
    #    CART_TIMER PostTimer[8];     // 8 time markers after head
    #    CHAR Reserved[276];          // Reserved for future expansion
    #    CHAR URL[1024];              // Uniform resource locator
    #    CHAR TagText[];              // Free form text for scripts or tags
    # } CART_EXTENSION;
    #
    # typedef struct cart_timer_tag
    # { // Post timer storage unit
    #    FOURCC dwUsage;              // FOURCC timer usage ID
    #    DWORD dwValue;               // timer value in samples from head
    # } CART_TIMER;
    #
    def _get_cart_chunk(self, size, offset):
        # The string representing the fields in a cart chunk as struct formatstring = "<4s64s64s64s64s64s64s64s10s8s10s8s64s64s64sL64s276s1024s{0}s"
        self.wf.seek(offset)                      # the offset is positioned after the bext tag + size tag.
        out = {}
        data = self.wf.read(size)

        out['Version'] = clstr(data[0:4])
        out['Title'] = clstr(data[4:68])
        out['Artist']  = clstr(data[68:132])
        out['CutID'] = clstr(data[132:196])
        out['ClientID'] = clstr(data[196:260])
        out['Category'] = clstr(data[260:324])
        out['Classification'] = clstr(data[324:388])
        out['OutCue'] = clstr(data[388:452])
        out['StartDate'] = clstr(data[452:462])
        out['StartTime'] = clstr(data[462:470])
        out['EndDate'] = clstr(data[470:480])
        out['EndTime'] = clstr(data[480:488])
        out['ProducerAppID'] = clstr(data[488:552])
        out['ProducerAppVersion'] = clstr(data[552:616])
        out['UserDef'] = clstr(data[616:680])
        out['dwLevelReference'] = bti(data[680:684])   # what is the level of the neutral position? Normally the midpoint between the min/max values, but can be different.
        cartTimer = data[684:748]
        postTimer = []              # the postTimer is an array because positioning is important when we are creating an exact copy. We ignore unused timers.
        for i in range(8):
            fourcc = clstr(cartTimer[i * 8:i * 8 + 4])
            if fourcc:
                postTimer.append(fourcc)
                postTimer.append(bti(cartTimer[i * 8 + 4:i * 8 + 8]))
        out['PostTimer'] = postTimer
        # out['Reserved'] = data[748:1024]    # reserved data is ignored and set to \x00 on writing as long as the standard does not dedicate this area.
        out['URL'] = clstr(data[1024:2048])
        out['TagText'] = clstr(data[2048:])
        return out


    # This utility function will enable people to easily convert code to name.
    # Since the method is independent of the instance, we can make it a static function.
    @staticmethod
    def get_format_name(waveformat):
        """
        Function get_format_name(waveformat) returns a tuple with readable descriptions for the waveformat code.

        Example:
            get_format_name(1) returns ('WAVE_FORMAT_PCM', 'Uncompressed Pulse Code Modulated')

        Args:
            waveformat (TYPE): the code of the waveformat as discovered in the wave file.

        Returns:
            A tuple of (`wave format code`, `wave format name`) strings.
        """
        waveformatnames_dict = {
            WAVE_FORMAT_UNKNOWN: ('WAVE_FORMAT_UNKNOWN', 'Unknown Wave Format'),
            WAVE_FORMAT_PCM: ('WAVE_FORMAT_PCM', 'Uncompressed Pulse Code Modulated'),
            WAVE_FORMAT_ADPCM: ('WAVE_FORMAT_ADPCM', 'Microsoft ADPCM'),
            WAVE_FORMAT_IEEE_FLOAT: ('WAVE_FORMAT_IEEE_FLOAT', 'IEEE Float'),
            WAVE_FORMAT_ALAW: ('WAVE_FORMAT_ALAW', 'ITU G.711 a-law'),
            WAVE_FORMAT_MULAW: ('WAVE_FORMAT_MULAW', 'ITU G.711 u-law'),
            WAVE_FORMAT_DVI_ADPCM: ('WAVE_FORMAT_DVI_ADPCM', 'Intel DVI ADPCM'),
            WAVE_FORMAT_G723_ADPCM: ('WAVE_FORMAT_G723_ADPCM', 'ITU G.723 ADPCM'),
            WAVE_FORMAT_GSM610: ('WAVE_FORMAT_GSM610', 'GSM 6.10'),
            WAVE_FORMAT_MPEG: ('WAVE_FORMAT_MPEG', 'MPEG'),
            WAVE_FORMAT_MPEGLAYER3: ('WAVE_FORMAT_MPEGLAYER3', 'MPEG Layer 3'),
            WAVE_FORMAT_DOLBY_AC3_SPDIF: ('WAVE_FORMAT_DOLBY_AC3_SPDIF', 'Dolby AC3 SPDIF'),
            WAVE_FORMAT_EXTENSIBLE: ('WAVE_FORMAT_EXTENSIBLE', )
        }
        return waveformatnames_dict.get(waveformat, 'Unknown')


    # RIFF specs: https://www.aelius.com/njh/wavemetatools/doc/riffmci.pdf
    # See https://ffmpeg.org/doxygen/2.1/channel__layout_8h_source.html for bitmasks used by ffmpeg
    # See https://mediaarea.net/AudioChannelLayout for a chart with layouts for all kinds of music formats
    # See for a very good explanation also: https://wavefilegem.com/how_wave_files_work.html
    # Great info on channel layouts: https://stackoverflow.com/questions/25178167/reading-a-single-channel-from-a-multi-channel-wav-file
    @staticmethod
    def get_channel_layout(channelmask, nr_of_channels):
        master_channel_layout = [
            [0x1, 'Front Left', 'FL'],
            [0x2, 'Front Right', 'FR'],
            [0x4, 'Front Center', 'FC'],
            [0x8, 'Low Frequency', 'LFE'],
            [0x10, 'Back Left (Surround Back Left)', 'BL'],
            [0x20, 'Back Right (Surround Back Right)', 'BR'],
            [0x40, 'Front Left of Center', 'FLC'],
            [0x80, 'Front Right of Center', 'FRC'],
            [0x100, 'Back Center', 'BC'],
            [0x200, 'Side Left (Surround Left)', 'SL'],
            [0x400, 'Side Right (Surround Right)', 'SR'],
            [0x800, 'Top Center', 'TC'],
            [0x1000, 'Top Front Left', 'TFL'],
            [0x2000, 'Top Front Center', 'TFC'],
            [0x4000, 'Top Front Right', 'TFR'],
            [0x8000, 'Top Back Left', 'TBL'],
            [0x10000, 'Top Back Center', 'TBC'],
            [0x20000, 'Top Back Right', 'TBR'],

            # everything after this one is part of the FFMPEG layout specs, but not officially part of the master channel layout masks. Use at your own risk.
            [0x20000000, 'Downmix Left', 'DL'],
            [0x40000000, 'Downmix Right', 'DR'],
            [0x80000000, 'Wide Left', 'WL'],
            [0x100000000, 'Wide Right', 'WR'],
            [0x400000, 'Surround Direct Left', 'SDL'],
            [0x800000, 'Surround Direct Right', 'SDR'],
            [0x1000000, 'Low Frequency 2', 'LFE2']
        ]

        channel_layout = []

        # I hope this obeys the ordering of the list.
        for mclitem in master_channel_layout:
            if channelmask & mclitem[0]:
                channel_layout.append(mclitem[1])

        # if we have more mask than channels, remove all extraneous channels
        if len(channel_layout) < nr_of_channels:
            channel_layout = channel_layout[0:nr_of_channels - 1:1]

        # any channels that are not defined in the mask are undefined. They could be control channels, downsample channels, etc.
        while len(channel_layout) < nr_of_channels:
            channel_layout.append("(undefined)")

        return channel_layout


    @staticmethod
    def get_channel_setup_name(channelmask, nr_of_channels):
        """
        Function get_channel_setup_name(channelmask, nr_of_channels) returns the name of the layout of the channels, i.e. "5.1", "stereo", "quad" etc.

        Example:
            get_channel_setup_name(0b111111, 6) returns '5.1'

        Args:
            channelmask (long): the mask of the channels in the WAVE file, usually only as part of a WAVE_FORMAT_EXTENSIBLE file.
            nr_of_channels (int): the number of channels in the file.

        Returns:
            A string describing the lay-out.
        """

        # This is not really accurate enough right now: we can have 8 channels and a channelmask of 6.
        # In that case we should find the best match. Also, we could have a channelmask of 10 set bits and only 2 channels.
        # We cannot mask them, since downmix only has 2 bits but in the highest places.
        # So we will need an alternative method eventually, but for now it's okay.

        # See for possible channel layouts: https://trac.ffmpeg.org/wiki/AudioChannelManipulation
        # Standard channel layouts:
        # NAME           DECOMPOSITION
        # mono           FC                         0b000000000100
        # stereo         FL+FR                      0b000000000011
        # 2.1            FL+FR+LFE                  0b000000001011
        # 3.0            FL+FR+FC                   0b000000000111
        # 3.0(back)      FL+FR+BC                   0b000100000011
        # 4.0            FL+FR+FC+BC                0b000100000111
        # quad           FL+FR+BL+BR                0b000000110011
        # quad(side)     FL+FR+SL+SR                0b011000000011
        # 3.1            FL+FR+FC+LFE               0b000000001111
        # 5.0            FL+FR+FC+BL+BR             0b000000110111
        # 5.0(side)      FL+FR+FC+SL+SR             0b011000000111
        # 4.1            FL+FR+FC+LFE+BC            0b000100001111
        # 5.1            FL+FR+FC+LFE+BL+BR         0b000000111111
        # 5.1(side)      FL+FR+FC+LFE+SL+SR         0b011000001111
        # 6.0            FL+FR+FC+BC+SL+SR          0b011100000111
        # 6.0(front)     FL+FR+FLC+FRC+SL+SR        0b011011000011
        # hexagonal      FL+FR+FC+BL+BR+BC          0b000100110111
        # 6.1            FL+FR+FC+LFE+BC+SL+SR      0b011100001111
        # 6.1(back)      FL+FR+FC+LFE+BL+BR+BC      0b000100111111
        # 6.1(front)     FL+FR+LFE+FLC+FRC+SL+SR    0b011011001011
        # 7.0            FL+FR+FC+BL+BR+SL+SR       0b011000110111
        # 7.0(front)     FL+FR+FC+FLC+FRC+SL+SR     0b011011000111
        # 7.1            FL+FR+FC+LFE+BL+BR+SL+SR   0b011000111111
        # 7.1(wide)      FL+FR+FC+LFE+BL+BR+FLC+FRC 0b000011111111
        # 7.1(wide-side) FL+FR+FC+LFE+FLC+FRC+SL+SR 0b011011001111
        # octagonal      FL+FR+FC+BL+BR+BC+SL+SR    0b011100110111
        # downmix        DL+DR                      0b01100000000000000000000000000000
        # max value in WAV-file:                    0b11111111111111111111111111111111
        # hexadecagonal  FL+FR+FC+BL+BR+BC+SL+SR+TFL+TFC+TFR+TBL+TBC+TBR+WL+WR
        #                                           0b110000000000000111111011100110111
        master_layout = {
            0b000000000100: 'mono',
            0b000000000011: 'stereo',
            0b000000001011: '2.1',
            0b000000000111: '3.0',
            0b000100000011: '3.0 (back)',
            0b000100000111: '4.0',
            0b000000110011: 'quad',
            0b011000000011: 'quad(side)',
            0b000000001111: '3.1',
            0b000000110111: '5.0',
            0b011000000111: '5.0 (side)',
            0b000100001111: '4.1',
            0b000000111111: '5.1',
            0b011000001111: '5.1 (side)',
            0b011100000111: '6.0',
            0b011011000011: '6.0 (front)',
            0b000100110111: 'hexagonal',
            0b011100001111: '6.1',
            0b000100111111: '6.1 (back)',
            0b011011001011: '6.1 (front)',
            0b011000110111: '7.0',
            0b011011000111: '7.0 (front)',
            0b011000111111: '7.1',
            0b000011111111: '7.1 (wide)',
            0b011011001111: '7.1 (wide-side)',
            0b011100110111: 'octagonal',
            0b01100000000000000000000000000000: 'downmix'
        }
        return master_layout.get(channelmask, 'Unknown layout')

    def __del__(self):
        self.close()


    __enter__ = lambda self: self
    __exit__  = lambda self, t, v, tr: self.close()


open = lambda path, mode = "r", **kwargs: Wave(path, mode=mode, **kwargs)
