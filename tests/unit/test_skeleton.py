# (c) GPL 2007 Karel 'Clock' Kulhavy, Twibright Labs; Python port 2026
import hashlib


def test_version_and_errors():
    import optar
    from optar.errors import DecodeError, FormatError, OptarError

    assert optar.__version__ == "0.1.0"
    assert issubclass(FormatError, OptarError) and issubclass(FormatError, ValueError)
    assert issubclass(DecodeError, OptarError)


def test_seeded_bytes_is_stable():
    from tests.helpers import seeded_bytes

    assert seeded_bytes(1, 40).hex().startswith(hashlib.sha256(b"1:0").hexdigest())
    assert len(seeded_bytes(7, 100_001)) == 100_001
    assert seeded_bytes(7, 10) == seeded_bytes(7, 100)[:10]
