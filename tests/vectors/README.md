# Conformance vectors

Frozen results that the Python code must reproduce. Every file has `pins`, `source`
(`c` or `python`), `c_commit` (for C) and `cases`. Digests are SHA-256 hex.
Load them with `tests.vectors.load.load("c/golay")`.

## c/golay.json

Pins the Golay table. `golay_sha256` is the digest of `optar.fec.serialize_table(golay_table())`.

## c/bit_placement.json

Pins where each payload bit goes, for the ten layouts of `optar.format.LAYOUTS` and the
formats 4x4, 7x5 and 65x93 with `fec_order` 3 (13 formats). Cases map a format string to:

- `all_sha256`: the SHA-256 of the channel position of every sequence number, as C
  `seq2xy` gives it: the bytes of `np.stack([x, y]).astype("<i4")` where `x, y =
  channel_xy(fmt)`, that is all `total_bits` x values then all y values, each a
  little-endian 32-bit integer.
- `samples`: `[seq, x, y]` for the first 100 of the sequence numbers the old
  `tests/golden/make_fixtures.py` picked (`seeded_bytes(7, 4 * n)` read as big-endian
  32-bit integers modulo `total_bits`), so that a failure names a bit.

## c/encoder_pages.json

Pins whole encoded pages. Each case gives a format, a label, `seeded_bytes(seed, size)` as
input, and one digest per page: the SHA-256 of `optar.imageio.pgm_bytes(page.pixels)`.
The first eight cases are the old golden fixtures; the others are the inputs of the old
`tests/oracle/test_encoder_oracle.py` (a4, letter, a4 with `fec_order` 2 to 5; sizes 0, 1,
777 and two pages plus 5 bytes, seed = position in that list).

## How the C vectors were recorded

`lega-c/record_vectors/record.py` ran the C tools of commit `c_commit` once (built with
`tests/cbuild.py`, the optar.h grid and `FEC_ORDER` overridden for each format) and wrote
every `c/*.json` file and `c/scans/`. A rerun writes the same files. Each C decoder input
is a PNG written with `tests.helpers.save_scan`; the stored scans are the very files C read.

"Scan" below means a `tests.helpers.fake_scan` of a page, saved with `save_scan` and
loaded with `optar.read_scan`, as C read it. A case gives either `recipe` (the
`fake_scan` keyword arguments; only `scale` 1 or 3, which use no random numbers and no
resampling, so the scan can be made again) or `scan_files` (stored PNGs under `c/`, for
every scan made with noise, rotation, blur, specks or flips, so that a numpy or Pillow
upgrade cannot change it). `test_stored_scans_are_the_only_random_inputs` checks this.

The small format of the stored scans is `0-6-9-24-3-1-2-24` (6 x 9 crosses). 6 x 8 was
tried first: there the "flips" case (200 flipped pixels on a page of about 20,000 channel
bits) leaves an uncorrectable symbol in C and in Python alike, so its output is not the
input. On 6 x 9 C's output begins with the input for every case except the noise-60 ones.

Left out to keep this directory under 2,000,000 bytes: the scale-6 scan of the old slow
test, and the DEGRADED cases "noisy" and "rotated", whose noise and rotation are in
"combined" (and, for rotation, in the degraded scan of `c/decoder_internals.json`).

## c/container_pages.json

Pins container streams on larger-dot layouts: a4 large (33 x 46) and letter medium
(51 x 66). The stream is `optar.container.wrap(seeded_bytes(seed, size), file_name, fmt,
parity)` (`stream_sha256`), printed with the label `label`.

- `page_sha256`: SHA-256 of each page C optar wrote for that stream (PGM bytes, as for
  `c/encoder_pages.json`).
- `c_output_sha256`: SHA-256 of everything C unoptar wrote to stdout for scans
  (`recipe`) of the Python pages. The Python decoder must give the same bytes.

## c/label.json

Pins the label band. For each `text`, page 1 of C optar run on `bytes.fromhex(input_hex)`
with that label (no label argument for `""`). `band_sha256` is the SHA-256 of the band
rows `pixels[border + data_height : border + data_height + text_height, :]` (full page
width, uint8, row-major). The texts: empty, `"my label"`, 200 characters (cut to the band
width) and `"naïve ☃"` (characters outside ASCII are not drawn).

## c/decoder.json

Pins the decoder's output byte for byte. Each case decodes `seeded_bytes(seed, size)`
encoded in `format`, and gives `c_output_sha256` and `c_output_size`: the SHA-256 and
length of everything C unoptar wrote to stdout for the case's scans, one scan per page.
When `starts_with_input` is true, C's output began with the input (checked when
recording); it is false for the noise-60 cases, which have uncorrectable symbols. The
count of uncorrectable symbols is not recorded: C does not print it.

- `group` `full_size`: the inputs of the old `test_c_decodes_python_pages` (seed 21) and
  `test_python_decodes_c_pages` (seed 22) for a4, letter and a4 with `fec_order` 2 to 5,
  all two pages, scans at `scale` 1; and `a4-scale3`, page 1 of `seeded_bytes(11, 150000)`
  at `scale` 3. For the C-made pages, `page_sha256` is the SHA-256 of each C page (PGM
  bytes): the Python pages equal them, so the test encodes with Python, checks those
  digests, and decodes.
- `group` `small`: the small format, page 1 of `seeded_bytes(11, net bytes)` under the
  `DEGRADED` cases of `tests/helpers.py` with `seed=1` (clean1 and clean3 by recipe, the
  others stored); and `noise60-fec1`, `-fec2`, `-fec5`: `seeded_bytes(23, net bytes)` in the
  small format with that `fec_order`, `fake_scan(page, scale=3, noise=60, seed=2)`, stored.

## c/decoder_internals.json

Pins the decoder's intermediate results, from instrumented copies of C unoptar. The page
is page 1 of `seeded_bytes(seed, size)` in `format` (the small format). Cases: `clean`
(recipe `scale` 3) and `degraded` (`fake_scan(page, scale=3, margin=120, rotate=0.4,
blur=1.0, noise=8.0, seed=3)`, stored).

- `crosses`: one row per cross, y outer and x inner, of `[x, y, cut level]` exactly as C
  printed them with `%a` (hex floats; read with `float.fromhex`), right after
  `sync_crosses()`.
- `bits_sha256`: SHA-256 of the `used_bits` sampled channel bits (`pixval < local_cutlevel`
  in `read_syms`), one uint8 0 or 1 per bit, in sequence order (C's loop order reordered:
  `seq = hamming_sym + bit * fec_syms`).


## Vectors made by the Python code

`py/reed_solomon.json`, `py/container.json` and `py/tag.json` are written by
`PYTHONPATH=. .venv/bin/python -m tests.vectors.py.make` and pin what optar 0.3.1 does today. They
do not show the code is right, only that it has not changed; `test_vectors_py.py` recomputes each
result from the inputs stored in the file (the functions are in `py/make.py`). Bytes are hex
strings; large results are SHA-256 hex of the bytes named below. A change to any of them is a
format change.

- `py/reed_solomon.json`: `parity` holds, for parity 32 and 64, the parity bytes (hex) of the
  messages of `255 - parity` bytes `zeros`, `ones` (0xFF), `ramp` (bytes 0..k-1), `seed1` and
  `seed2` (`seeded_bytes(1, k)`, `seeded_bytes(2, k)`). `repairs` encodes `seeded_bytes(3, k)`,
  xors the stored masks into the stored error positions and into the stored erasure positions
  (these are marked erased), and records the outcome of `RSCode.decode`: `ok`, `errors`,
  `erasures`, and SHA-256 of the 255 bytes of the codeword returned, of the original codeword and of
  the damaged one as received. The cases are errors only at the limit `parity // 2`, erasures only at the
  limit `parity`, 5 errors with `parity - 10` erasures, and one error beyond the limit (expected
  to fail, so the word comes back as received).
- `py/container.json`: `header` is the packed bytes of a `Header`; `padding` is
  `padding(0, 100)`; `streams` has one case for every layout (`LAYOUTS`, named `paper-dots`) and
  every parity (0, 32, 64): a file named `vector.bin` of `seeded_bytes(41, size)` where
  `size = int(1.5 * plan_for(1, fmt, parity).data_bytes)`, the page and codeword counts, the
  length and SHA-256 of the stream `wrap()` returns (the bytes given to `encode()`), and
  `positions(plan)` of codewords 0, 1 and the last: the first 16 positions as a list, and `sha256`,
  the digest of the whole row of 255 positions, `array_digest(row, np.int64)` (the SHA-256 of its
  255 little-endian int64 values, 2040 bytes).
- `py/tag.json`: for files of 0 bytes, 1 byte (`x`) and `seeded_bytes(5, 300000)`, the tag's size
  and fingerprint, the printed tag text and `tagged_label(tag, "name.tar", page, 2)` for pages 1
  and 2.

### Outside check of the Reed-Solomon parity

The parity bytes of all 10 messages in `py/reed_solomon.json` were compared with the `reedsolo`
package, version 1.7.0, installed in a throwaway virtual environment (not a dependency, and the
script is not kept). Call: `RSCodec(parity, nsize=255, fcr=0, prim=0x11D, generator=2, c_exp=8)`
and `encode()` of the whole message, which returns the message followed by the parity. All 10
agree, so `rs.py` is the standard systematic code over GF(256) with field polynomial 0x11D,
generator element 2, roots alpha^0 .. alpha^(parity-1) (first consecutive root 0), and the
codeword written with its highest-degree coefficient first. With `fcr=1` only 2 of the 10 agree
(the two all-zero messages, whose parity is zero in any convention), so the agreement depends on
`fcr=0`. Only the encoder was compared; the repair outcomes are pinned by this code alone.
