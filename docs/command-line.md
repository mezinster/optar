# Command line

The `optar` command encodes a file into pages and decodes scans back. It needs
no C compiler, no libpng and no ImageMagick.

    optar encode INPUT [-o BASE] [--paper a4|letter] [--to pdf|png|pgm] [--label TEXT] [--no-tag]
                 [--dots standard|medium|big|large|xlarge] [--protect none|standard|high]
                 [--compatible] [--format STRING]
    optar decode BASE [-o OUTPUT] [--paper a4|letter] [--format STRING] [--debug-images] [--force]
                 [--no-slow-reader]
    optar --version

## encode

`encode` writes `BASE.pdf` by default (`BASE` defaults to `optar_out`), or the
pages `BASE_0001.png` (or `.pgm`), `BASE_0002.png`, ... with `--to`.

| You give | You get |
|---|---|
| neither `--dots` nor `--protect`, or `--compatible` | a printout that 0.2.0 and the C tool read: Standard dots, no protection |
| `--dots X` alone | that dot size with Standard protection |
| `--protect LEVEL` alone | Standard dots with that protection |
| `--protect none` | no protection |

Any of the last three makes self-identifying pages, which need optar 0.3 or
newer to be read. For example:

    optar encode photo.jpg -o photo --dots large --protect high

The dot sizes and protection levels are described under
[Put a file on paper](put-on-paper.md#dot-size).

A compatible printout carries a [tag](identification.md#the-tag) on every
page; add `--no-tag` to leave it out.

`--paper` defaults to A4.

## decode

`decode` reads `BASE_0001.png`, `BASE_0002.png`, ... and writes the data to
`-o OUTPUT`, or to stdout. It reads only files with those names.

What it does depends on the printout. It decides from the first three scans:
if none of them can be identified as a self-identifying page, it treats the
set as a printout from 0.2.0 or earlier.

### Self-identifying pages

`decode` finds out from the scans themselves what they are.

- It takes the scans in any order and any orientation.
- A scan it cannot read counts as a missing page.
- A scan the ordinary reader cannot identify is first given to the
  [slower reader](slower-reader.md), unless you give `--no-slow-reader`.
- It repairs the data, cuts it to its true size and checks the fingerprint.
- It writes the file only if the fingerprint matches, unless you give
  `--force`, which saves what was recovered even if it did not verify. Even
  with `--force` nothing is saved when fewer than half of the pages were read.

### Printouts from 0.2.0 or earlier

- `--paper` must be the same as for encoding.
- The page must be upright (portrait, label at the bottom). Landscape scans
  are not supported here, which is inherited from the C decoder. The desktop
  application accepts any orientation for every printout.
- `decode` does not cut the output to the size in the tag or check the
  fingerprint: the output is always padded with zeros to a whole page. The
  desktop application does both. Pack your data with tar if it is sensitive to
  this.
- `--force` changes nothing, and `decode` says so.

## Exit status

| Status | Meaning |
|---|---|
| 0 | Success. For self-identifying pages: the file verified. |
| 1 | The data was decoded but is uncorrectable, or the page numbering has a gap, or (self-identifying pages) the file did not verify. |
| 2 | A usage or input error. |

## The error-correcting code

The default is the Golay 24/12 code. Hamming codes of order 2 to 5 are also
supported, selected through `--format` (the sixth field of the format
string). The [format specification](format.md) defines the format string.
