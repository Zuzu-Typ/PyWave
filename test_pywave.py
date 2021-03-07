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
    assert (len(wf.messages) > 0)

    assert wfile is not None
    assert len(wfile) == wf.block_align           # make sure we read on BlockAlignments


def test_metadata(wf):
    assert wf.channels == 2
    assert wf.frequency == 44100
    assert wf.bitrate == 2822400
    assert wf.samples == 99328
