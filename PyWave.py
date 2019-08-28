import warnings

WAVE_FORMAT_PCM         = 0x0001
WAVE_FORMAT_IEEE_FLOAT  = 0x0003
WAVE_FORMAT_ALAW        = 0x0006
WAVE_FORMAT_MULAW       = 0x0007
WAVE_FORMAT_EXTENSIBLE  = 0xFFFE

class PyWaveError(Exception):
    pass

class PyWaveWarning(UserWarning):
    pass

class Wave:
    """Opens a WAVE-RIFF file for reading.
If <auto_read> is set to True, the data of the wave
file <path> is read and put into <Wave.data>.
Otherwise <Wave.read()> can be used to read data from
the wave file."""
    def __init__(self, path, auto_read = False):
        self.wf = open(path, "rb")
        RIFF            = self.wf.read(4).decode()
        ChunkSize       = int.from_bytes(self.wf.read(4), "little")
        WAVE            = self.wf.read(4).decode()
        fmt             = self.wf.read(4).decode()
        
        if RIFF != "RIFF" or WAVE != "WAVE" or fmt != "fmt ":
            raise PyWaveError("'{}' does not appear to be a wave file.".format(path))
        
        Subchunk1Size   = int.from_bytes(self.wf.read(4), "little")
        self.format     = int.from_bytes(self.wf.read(2), "little")
        
        self.channels               = int.from_bytes(self.wf.read(2), "little")
        self.samples_per_sec        = int.from_bytes(self.wf.read(4), "little")
        self.average_bytes_per_sec  = int.from_bytes(self.wf.read(4), "little")
        self.block_align            = int.from_bytes(self.wf.read(2), "little")
        self.bits_per_sample        = int.from_bytes(self.wf.read(2), "little")
        
        if Subchunk1Size >= 18:
            cb_size                 = int.from_bytes(self.wf.read(2), "little")
            if cb_size == 0:
                pass
            elif cb_size == 22:
                self.valid_bits_per_sample  = int.from_bytes(self.wf.read(2), "little")
                self.channel_mask           = int.from_bytes(self.wf.read(4), "little")
                self.sub_format             = int.from_bytes(self.wf.read(16), "little")
            else:
                warnings.warn("Unknown extensions for extensible wave file '{}'".format(path), PyWaveWarning)
                wf.seek(cb_size, 1)
            
        SubchunkID                  = self.wf.read(4).decode()
        while SubchunkID != "data":
            SubchunkSize               = int.from_bytes(self.wf.read(4), "little")
            if SubchunkSize == 0:
                raise PyWaveError("'{}' does not appear to be an extensible wave file.".format(path))
            self.wf.seek(SubchunkSize, 1)
            SubchunkID                 = self.wf.read(4).decode()

        self.data_length            = int.from_bytes(self.wf.read(4), "little")
        
        self.bytes_per_sample = (self.bits_per_sample // 8)

        self.samples = (self.data_length // self.bytes_per_sample // self.channels)

        self.data_position = 0
        self.data_starts_at = self.wf.tell()
        self.end_of_data = self.data_starts_at + self.data_length

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
