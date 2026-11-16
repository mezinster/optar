Real scans are not kept in this repository. They are measured where they are, on the
machine that made them, and this folder stays empty of scans.

`test_real_scans.py` is kept for that reason only: with no case in this folder it reports
one skip, which is the expected result everywhere, CI included.

To check scans you have, point the `OPTAR_REAL_SCANS` environment variable at a folder
outside the repository that holds them as `*.png`:

    OPTAR_REAL_SCANS=/path/to/scans .venv/bin/pytest -q tests/unit/test_identify.py -k real

The test it turns on, `test_real_coarse_scans_report_their_resolution`, is for
Standard-dot pages scanned at 300 dpi, which do not decode: it checks that each scan is
refused with an estimated resolution between 270 and 330 dpi. Without the variable the
test is skipped.
