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
    assert wf.block_align == wf.bits_per_sample * wf.channels  # 32bit float, 2 channels = 8 bytes minimum read for 1 sample 

    assert wf.data_length == wf.samples * wf.channels * wf.bytes_per_sample # 99328 * 2 channels * 4 bytes per sample
    assert wf.samples == 99328
    assert wf.samples == (wf.data_length // wf.bytes_per_sample // wf.channels)

    assert wf.data_starts_at == 88
    assert wf.data_length == ( wf.end_of_data - wf.data_starts_at )

