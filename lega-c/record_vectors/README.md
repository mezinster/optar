# Recording the C vectors (history)

This folder holds the script that ran the original C tools for the last time and wrote the
conformance vectors in `tests/vectors/c/` (the JSON files and `scans/`). It is kept as a
record of how those files were made. It is not run by the tests or by CI, and nothing in
`tests/` imports it.

- `record.py`: builds the C tools from the sources in `lega-c/` (with the `optar.h` grid
  and `FEC_ORDER` overridden for each format), runs them on the inputs of the old live
  comparisons (`tests/oracle/`, since removed) and writes one vector file per function.
- `cbuild.py`: the build harness `record.py` imports from this folder (formerly
  `tests/cbuild.py`). It compiles `optar` and `unoptar`, and instrumented copies of
  `unoptar` that print the cross positions and the sampled bits.
- `seq2xy_dump.c`: a small C program, linked against `common.o`, that prints the pixel
  position of each channel bit (formerly `tests/oracle/seq2xy_dump.c`).

The C sources are those of commit `9c8379c25466bf142459a26b0f34521bdde2af12`, which every C
vector file names as `c_commit`. The script was last run at commit `91a02a6` ("Lists what
the vectors were shown to catch"), and once more, with `cbuild.py` and `seq2xy_dump.c`
already moved here, in the commit that removed the live comparison. Both runs wrote files
identical to those committed.

It was run from the repository root, with a C compiler and the libpng headers:

    OPTAR_TEST_CFLAGS=-I<libpng>/include OPTAR_TEST_LDFLAGS=-L<libpng>/lib \
    LD_LIBRARY_PATH=<libpng>/lib .venv/bin/python lega-c/record_vectors/record.py

The three variables are needed only when libpng is not installed where the compiler finds
it. The script imports `optar`, `tests.helpers` and `tests.vectors.load` from the
repository, so it is only known to work with a checkout of that period.
