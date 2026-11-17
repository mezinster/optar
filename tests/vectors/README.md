# Conformance vectors

Frozen results that the Python code must reproduce. Every file has `pins`, `source`
(`c` or `python`), `c_commit` (for C) and `cases`. Digests are SHA-256 hex.
Load them with `tests.vectors.load.load("c/golay")`.

## c/golay.json

Pins the Golay table. `golay_sha256` is the digest of `optar.fec.serialize_table(golay_table())`.

## c/bit_placement.json

Pins where each payload bit goes. Cases map a format string to a list of
`[seq, x, y]`: the channel position of sequence number `seq` as `channel_xy` returns it.

## c/encoder_pages.json

Pins whole encoded pages. Each case gives a format, a label, `seeded_bytes(seed, size)` as
input, and one digest per page: the SHA-256 of `optar.imageio.pgm_bytes(page.pixels)`.
