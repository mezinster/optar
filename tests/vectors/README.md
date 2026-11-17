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
