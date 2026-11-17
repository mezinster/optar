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
