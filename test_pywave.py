import PyWave
import pytest


@pytest.fixture
def wf():
    PATH = "path/to/a/wave/file.wav"
    wavefile = PyWave.open(PATH)
    yield wavefile
    wavefile.close()


def test_read(wf):
    wfile = wf.read(1)
    assert wf is not None
    assert isinstance(wf, object)

    # due to the read(1) we should have a warning
    assert wf.data_position == 8            # 32bit float, 2 channels = 8 bytes minimum read for 1 sample
    assert (len(wf.messages) > 0)

    assert wfile is not None
    assert len(wfile) == wf.block_align     # make sure we read on BlockAlignments


def test_metadata(wf):
    assert wf.format == 0x0003              # WAVE_FORMAT_IEEE_FLOAT
    assert wf.channels == 2
    assert wf.frequency == 44100
    assert wf.samples_per_sec == wf.frequency
    assert wf.bitrate == 2822400
    assert wf.bitrate == wf.average_bytes_per_sec * 8

    assert wf.bits_per_sample == 32         # 1 sample = 32 bit float
    assert wf.bits_per_sample == wf.bytes_per_sample * 8
    assert wf.block_align == wf.bytes_per_sample * wf.channels  # 32bit float = 4 bytes * 2 channels = 8 bytes minimum read for 1 sample 

    assert wf.data_length == wf.samples * wf.channels * wf.bytes_per_sample # 99328 * 2 channels * 4 bytes per sample
    assert wf.samples == 99328
    assert wf.samples == (wf.data_length // wf.bytes_per_sample // wf.channels)

    assert wf.data_starts_at == 88
    assert wf.data_length == ( wf.end_of_data - wf.data_starts_at )


def test_static_methods(wf):
    waveformatcode, waveformatname = wf.get_format_name( wf.format)
    assert waveformatcode == 'WAVE_FORMAT_IEEE_FLOAT'
    assert waveformatname == 'IEEE Float'

    assert wf.get_channel_layout(0b111111,6) == ['Front Left', 'Front Right', 'Front Center', 'Low Frequency', 'Back Left (Surround Back Left)', 'Back Right (Surround Back Right)']
    assert wf.get_channel_setup_name(0b111111, 6) == '5.1'


# test if the __del__ on the class does not fail when the file cannot be opened and __init__ fails
# also test whether we get the right exception back
#
# an Attribute Error in PyWave.__del__ indicates failure to correctly initialize variables before opening a wavefile.
# a FileNotFoundError is the expected outcome.
def test_delete():
    with pytest.raises(FileNotFoundError):
        wavefile = PyWave.open("xxxx.yyy")
