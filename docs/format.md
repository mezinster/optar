# The optar format

optar stores a file on paper as pages of black and white dots. This
specification defines what a page is and what a document (a set of pages
that carries one file) is, so that an encoder can be written whose pages
this project reads, and a decoder that reads this project's pages.

The specification has eight parts:

1. Terms and conventions
2. The page (version 0)
3. The document tag (0.2.0 printouts)
4. Self-identifying documents (version 1)
5. Printing
6. What a reader must do
7. Reference decoder (informative)
8. History

Parts 1 to 6 are normative. "Must" is used only for what a page or a document
is, and in part 6 for what a reader does with what it has read. How a reader
finds a page in a scan and samples it is not part of the format; part 7
describes how this project does it.

The format is pinned by test vectors in `tests/vectors`. Each normative
section ends with a line "Vectors:" that names the files which pin it;
`tests/vectors/README.md` says how each file is read. Tables that are preceded
by a `spec-table` comment and the fenced blocks marked `example` are compared
with the code by `tests/unit/test_spec.py`.

## 1. Terms and conventions

### 1.1 Numbers, bits and bytes

- All integers are written in decimal unless they carry the prefix `0x`.
- `a // b` is division rounded down, `a mod b` its remainder, `ceil(a / b)`
  division rounded up. All three are used on non-negative integers only.
- Counts and indices start at 0, except page numbers and the faces of the
  dodecahedron in section 2.5, which start at 1.
- A **bit string** is read most significant bit first: bit `n` of a byte
  string is bit `7 - (n mod 8)` of byte `n // 8`, where bit 7 of a byte is its
  most significant bit. A word of `w` bits taken from a bit string has the
  first bit of the string as its most significant bit.
- Multi-byte integers in the header (section 4.2) are big-endian: most
  significant byte first.
- SHA-256 and CRC-32 are the usual functions. CRC-32 is the one of zlib, PNG
  and Ethernet: reflected polynomial `0xEDB88320`, initial value and final
  XOR `0xFFFFFFFF`.

### 1.2 Pixels and colours

- A **page** is a rectangular image of **page pixels**. Each page pixel is
  either black or white.
- A black data pixel is the bit 1; a white data pixel is the bit 0.
- In 8-bit grey image files a black pixel has the value 0 and a white pixel
  the value 255. This specification uses no other image encoding.
- Page coordinates are `(x, y)`: `x` counts columns from the left edge, `y`
  counts rows from the top edge, both from 0. The page is printed and read
  upright, with the label band (section 2.8) at the bottom.
- **Data-area coordinates** `(u, v)` leave out the border (section 2.2):
  `u = x - border`, `v = y - border`.

### 1.3 Units

- A **point** (pt) is 1/72 inch.
- A **printer dot** is 1/600 inch: one device dot of the 600 dpi printer the
  layouts are made for.
- A **data dot** is one page pixel as printed. It is a square of a whole
  number of printer dots (section 5.1). The **standard** data dot is 3 printer
  dots wide, 1/200 inch.

### 1.4 Kinds of document

A **stream** is the byte string that the pages of a document carry in their
data pixels. Three kinds of document exist; all three are made of the same
version-0 pages (part 2).

| Kind | Written by | The stream is | The label carries |
|---|---|---|---|
| plain | the C program, optar 0.1.0, `--no-tag` | the file | free text only |
| tagged | optar 0.2.0, and later versions as their "compatible" printout | the file | the tag (part 3) |
| self-identifying | optar 0.3.0 and later | the container (part 4) | free text only |

### 1.5 Constants

The names in this table are used throughout this specification.

<!-- spec-table: constants -->
| Name | Value | Meaning |
|---|---|---|
| `PageFormat.version` | 0 | version of the page format |
| `PageFormat.cpitch` | 24 | distance between cross origins, in page pixels |
| `PageFormat.chalf` | 3 | half the side of a cross, in page pixels |
| `PageFormat.fec_order` | 1 | page code: 1 is Golay, 2 to 5 are Hamming codes |
| `PageFormat.border` | 2 | thickness of the border, in page pixels |
| `PageFormat.text_height` | 24 | rows of the label band |
| `LABEL_HEIGHT` | 24 | the only label band height that can be drawn |
| `TEXT_WIDTH` | 13 | width of one label character cell, in label pixels |
| `FIRST_CHAR` | 32 | character code of the first cell of the font strip |
| `GLYPH_CELLS` | 95 | character cells in the font strip |
| `MAX_PAGES` | 9999 | most pages of one document |
| `FINGERPRINT_DIGITS` | 8 | hexadecimal digits of the fingerprint in a tag |
| `CHECK_DIGITS` | 2 | hexadecimal digits of the check in a tag |
| `MAX_SIZE_DIGITS` | 12 | most decimal digits of the size in a tag |
| `HEADER_MAGIC` | "oPt1" | first four bytes of a header, in ASCII |
| `CONTAINER_VERSION` | 1 | version byte of a header |
| `HEADER_SIZE` | 38 | bytes of one header copy |
| `HEADER_COPIES` | 5 | header copies in each page |
| `FINGERPRINT_SIZE` | 16 | bytes of the fingerprint in a header |
| `CODEWORD` | 255 | bytes of one Reed-Solomon codeword |
| `SPREAD_STEP` | 7919 | step of the spread (section 4.6) |
| `NAME_MAX_BYTES` | 255 | most bytes of the stored file name |
| `PADDING_KEY` | "optar padding" | key of the padding stream, in ASCII |
| `PADDING_BLOCK` | 32 | bytes of one block of the padding stream |
| `PROTECTED_MAX_BYTES` | 268435456 | most page bytes of a document with parity |
| `PROMISE_NUM` | 3 | numerator of the share of the parity on which the tools base their promise (4.9) |
| `PROMISE_DEN` | 4 | denominator of that share |
| `PRINTER_DPI` | 600 | printer dots per inch |
| `PIXELS_PER_INCH` | 200 | standard data dots per inch |
| `STANDARD_PRINTER_DOTS` | 3 | printer dots across a standard data dot |
| `POINTS_PER_INCH` | 72 | points per inch |
| `SCAN_PIXELS_PER_DOT` | 3 | scan pixels per data dot at the advised scan resolution |
| `MIN_MARGIN_PT` | 12 | smallest margin around a printed page, in points |

## 2. The page (version 0)

### 2.1 The page format and the format string

A **page format** is eight non-negative integers:

| Field | Name | Meaning | Must be |
|---|---|---|---|
| 1 | `version` | version of the page format | 0 |
| 2 | `xcrosses` | crosses in a row | at least 2 |
| 3 | `ycrosses` | crosses in a column | at least 2 |
| 4 | `cpitch` | distance between cross origins | more than `2 * chalf` |
| 5 | `chalf` | half the side of a cross | at least 1 |
| 6 | `fec_order` | page code | 1 to 5 |
| 7 | `border` | thickness of the border | at least 1 |
| 8 | `text_height` | rows of the label band | `LABEL_HEIGHT` |

The **format string** is the eight fields in this order, in decimal without
leading zeros, joined by `-`. Every page prints its format string in its label
(section 2.8). The pages this project prints differ only in `xcrosses` and
`ycrosses`; the other fields have the values of section 1.5. The ten page
formats it prints are listed in section 5.2. Other values are valid pages and
are read when the reader is given the format string.

All sizes below are in page pixels.

    data_width  = cpitch * (xcrosses - 1) + 2 * chalf
    data_height = cpitch * (ycrosses - 1) + 2 * chalf
    width       = 2 * border + data_width
    height      = 2 * border + data_height + text_height

```example
a4_data_width = 1542
a4_data_height = 2214
a4_width = 1546
a4_height = 2242
```

The names with the prefix `a4_` are for the format `0-65-93-24-3-1-2-24`, the
standard A4 page.

Vectors: `tests/vectors/c/encoder_pages.json`.

### 2.2 The parts of a page

A page is `width` columns by `height` rows. From top to bottom:

| Rows `y` | Content |
|---|---|
| `0` to `border - 1` | border: black |
| `border` to `border + data_height - 1` | columns `0` to `border - 1` and the last `border` columns: black. Between them: the **data area**, `data_width` columns |
| `border + data_height` to `border + data_height + text_height - 1` | the **label band**: black over the whole width, with the label drawn in white in columns `border` to `border + data_width - 1` (section 2.8) |
| the last `border` rows | border: black |

```example
a4_label_top_row = 2216
```

Every pixel of the data area is either part of a cross (section 2.3) or a
data pixel (section 2.4).

Vectors: `tests/vectors/c/encoder_pages.json`.

### 2.3 Crosses

The data area holds `xcrosses * ycrosses` **crosses**, which a reader uses to
find the data pixels. Cross `(i, j)`, `0 <= i < xcrosses`, `0 <= j < ycrosses`,
is the square of `2 * chalf` by `2 * chalf` pixels whose top left pixel, its
**origin**, is at data-area coordinates `(i * cpitch, j * cpitch)`. Its four
quarters of `chalf` by `chalf` pixels are:

| Quarter | Colour |
|---|---|
| top left | black |
| top right | white |
| bottom left | white |
| bottom right | black |

The first cross touches the top left corner of the data area and the last one
its bottom right corner. A pixel `(u, v)` of the data area is part of a cross
exactly when `u mod cpitch < 2 * chalf` and `v mod cpitch < 2 * chalf`.

```example
a4_last_cross_x = 1538
a4_last_cross_y = 2210
```

These are the page coordinates `(x, y)` of the origin of the last cross.

Vectors: `tests/vectors/c/encoder_pages.json`.

### 2.4 Data pixels and their order

The **data pixels** are the pixels of the data area that are not part of a
cross. They are numbered from 0 in reading order: row by row from the top,
and from left to right within a row. The number of a data pixel is its
**channel position**; `total_bits` is the number of data pixels.

The rows of the data area repeat with period `cpitch`:

- a **narrow strip** of `2 * chalf` rows that pass through crosses. Each row
  holds `narrow_width` data pixels, in `xcrosses - 1` gaps of `gap_width`
  pixels between the crosses;
- a **wide strip** of `gap_width` rows without crosses. Each row holds
  `data_width` data pixels.

The last period has a narrow strip only.

    gap_width     = cpitch - 2 * chalf
    narrow_width  = gap_width * (xcrosses - 1)
    narrow_pixels = 2 * chalf * narrow_width
    wide_pixels   = gap_width * data_width
    rep_pixels    = narrow_pixels + wide_pixels
    total_bits    = rep_pixels * (ycrosses - 1) + narrow_pixels

The data-area coordinates `(u, v)` of channel position `n` are:

    rep = n // rep_pixels
    s   = n mod rep_pixels
    if s < narrow_pixels:                      (narrow strip)
        row = s // narrow_width
        r   = s mod narrow_width
        u   = 2 * chalf + (r // gap_width) * cpitch + r mod gap_width
        v   = rep * cpitch + row
    else:                                      (wide strip)
        s   = s - narrow_pixels
        u   = s mod data_width
        v   = rep * cpitch + 2 * chalf + s // data_width

The page coordinates are `(u + border, v + border)`.

```example
a4_narrow_width = 1152
a4_narrow_pixels = 6912
a4_wide_pixels = 27756
a4_rep_pixels = 34668
a4_total_bits = 3196368
a4_xy_of_0 = 6, 0
a4_xy_of_17 = 23, 0
a4_xy_of_18 = 30, 0
a4_xy_of_1152 = 6, 1
a4_xy_of_6912 = 0, 6
a4_xy_of_8454 = 0, 7
a4_xy_of_34668 = 6, 24
a4_xy_of_3196367 = 1535, 2213
```

`a4_xy_of_N` is `u, v` of channel position `N`.

Vectors: `tests/vectors/c/bit_placement.json`.

### 2.5 The page code

The data of a page is cut into **words** of `small` bits. Each word is encoded
into a **symbol** of `large` bits, which can be corrected when a few of its
bits are read wrongly. `fec_order` selects the code:

| `fec_order` | Code | `large` | `small` |
|---|---|---|---|
| 1 | Golay (24, 12) | 24 | 12 |
| 2 to 5 | extended Hamming | `2 ^ fec_order` | `large - 1 - fec_order` |

```example
code_bits_of_order_1 = 24, 12
code_bits_of_order_2 = 4, 1
code_bits_of_order_3 = 8, 4
code_bits_of_order_4 = 16, 11
code_bits_of_order_5 = 32, 26
```

A symbol is written here as an integer of `large` bits; its **bit `b`**, in
the order in which the bits are placed on the page, counts from the most
significant bit: bit 0 is the bit of value `2 ^ (large - 1)`.

#### Golay (24, 12)

The symbol of the 12-bit word `d` is `d * 4096 + p(d)`: the word in the upper
12 bits, 12 parity bits below it. The parity bits come from a dodecahedron
whose faces are numbered 1 to 12. Face `f` stands for the bit of value
`2 ^ (f - 1)` of `d`. Each face has five neighbours:

<!-- spec-table: golay -->
| Face | Neighbours | Mask |
|---|---|---|
| 1 | 2, 3, 4, 5, 6 | `0xfc1` |
| 2 | 1, 3, 6, 7, 8 | `0xf1a` |
| 3 | 1, 2, 4, 8, 9 | `0xe74` |
| 4 | 1, 3, 5, 9, 10 | `0xcea` |
| 5 | 1, 4, 6, 10, 11 | `0x9d6` |
| 6 | 1, 2, 5, 7, 11 | `0xbac` |
| 7 | 2, 6, 8, 11, 12 | `0x35d` |
| 8 | 2, 3, 7, 9, 12 | `0x6b9` |
| 9 | 3, 4, 8, 10, 12 | `0x573` |
| 10 | 4, 5, 9, 11, 12 | `0x2e7` |
| 11 | 5, 6, 7, 10, 12 | `0x58f` |
| 12 | 7, 8, 9, 10, 11 | `0x83f` |

The mask of face `r` has a 1 for every face that is not a neighbour of `r`
(face `r` itself included). The parity bit of face `r` is 1 when `d AND mask`
has an odd number of 1 bits. It is the bit of value `2 ^ (12 - r)` of `p(d)`:
face 1 gives the most significant parity bit, face 12 the least significant.

```example
golay_0x001 = 0x00183f
golay_0x800 = 0x800fc1
golay_0xabc = 0xabca13
golay_0xfff = 0xffffff
```

The code is linear, the word 0 has the symbol 0, and any two symbols differ
in at least 8 bits. A symbol read with up to 3 wrong bits therefore has
exactly one symbol within 3 bits of it, the one that was printed. The vector
file pins all 4096 symbols.

#### Extended Hamming (`fec_order` 2 to 5)

Number the bits of the symbol by their value: position `q` is the bit of
value `2 ^ q`, `0 <= q < large`.

1. The bits of the word, most significant first, go to the positions that are
   neither 0 nor a power of two, from position `large - 1` downwards.
2. For `i` from 0 to `fec_order - 1`, position `2 ^ i` is set so that the
   positions whose number has bit `i` set hold an even number of 1 bits.
3. Position 0 is set so that the whole symbol holds an even number of 1 bits.

Such a symbol can be corrected when one bit is wrong, and two wrong bits are
noticed. With `fec_order` 2 the symbol is the one bit of the word four times.

```example
hamming_2_of_1 = 1111
hamming_3_of_1011 = 10101010
hamming_4_of_10000000001 = 1000000100011000
hamming_5_of_1 = 00000000000000000000000000001111
```

Each line gives a word in binary after `of_` and its symbol in binary, most
significant bit first.

Vectors: `tests/vectors/c/golay.json`, `tests/vectors/c/encoder_pages.json`.

### 2.6 Symbols on the page

A page holds

    symbols   = total_bits // large
    used_bits = symbols * large
    net_bits  = symbols * small

`net_bits` is the number of data bits a page carries. The symbols are
interleaved so that neighbouring pixels belong to different symbols:

    bit b of symbol s is at channel position  s + b * symbols

for `0 <= s < symbols` and `0 <= b < large`. With the Golay code the data
pixels thus form 24 consecutive groups of `symbols` pixels, and every symbol
has one pixel in each group, at the same place in each.

The data pixels at channel positions `used_bits` and above belong to no
symbol and are white.

```example
a4_symbols = 133182
a4_used_bits = 3196368
a4_net_bits = 1598184
a4_position_of_symbol_1000_bit_5 = 666910
a4_xy_of_666910 = 1306, 462
a4_medium_total_bits = 1838484
a4_medium_symbols = 76603
a4_medium_unused_bits = 12
a4_medium_net_bits = 919236
hamming_2_net_bits = 799092
hamming_3_net_bits = 1598184
hamming_4_net_bits = 2197503
hamming_5_net_bits = 2597036
```

The names with `a4_medium_` are for the format `0-50-70-24-3-1-2-24`; the
`hamming_N_net_bits` are for the A4 grid with `fec_order` N.

Vectors: `tests/vectors/c/bit_placement.json`, `tests/vectors/c/encoder_pages.json`.

### 2.7 From a stream to pages

Let the stream be `nbytes` bytes, read as a bit string (section 1.1).

    pages = ceil(8 * nbytes / net_bits)

Page `p` (from 1) carries the bits `(p - 1) * net_bits` to `p * net_bits - 1`
of the stream. Word `s` of the page is the `small` bits that start at bit
`s * small` of the page's bits, and symbol `s` is its code (section 2.5).

- Bits past the end of the stream are 0. The last word that holds stream bits
  is thus filled up with 0 bits at its low end, and every later word of the
  last page is 0. The symbol of the word 0 is 0, so those words print as
  white pixels.
- A document has at most `MAX_PAGES` pages; a longer stream cannot be
  encoded.
- An empty stream (`nbytes = 0`) gives `pages = 0`. It is printed as one page
  whose data pixels are all white and whose label gives the page number 1 and
  the page count 0 (`1/0`).

Reading the pages in order and joining their `net_bits` bits gives the stream
followed by 0 bits. A page does not record where the stream ends: a plain
document gives its file back padded with zero bytes up to the end of its
last page (less the bits that do not fill a byte, when `net_bits` is not a
multiple of 8). The tag (part 3) and the container (part 4) both record the
size of the file.

```example
a4_pages_for_0_bytes = 0
a4_pages_for_1_byte = 1
a4_pages_for_199773_bytes = 1
a4_pages_for_199774_bytes = 2
a4_words_for_1000_bytes = 667
```

A stream of 1000 bytes fills 667 words of the first page; the last of them
holds 8 bits of the stream and four 0 bits.

Vectors: `tests/vectors/c/encoder_pages.json`.

### 2.8 The label

The label band holds one line of text, for people and, in a tagged document,
for the reader. It is always drawn with the same font, which the font strip
below defines.

**The font strip** is an image of `LABEL_HEIGHT` rows and 1500 columns, each
pixel black or white. Columns `0` to `TEXT_WIDTH * GLYPH_CELLS - 1` hold
`GLYPH_CELLS` character cells of `TEXT_WIDTH` columns: the cell of the
character with code `c`, `32 <= c <= 126`, starts at column
`TEXT_WIDTH * (c - FIRST_CHAR)`. The remaining columns hold a logo. Glyphs
and logo are white on black. The strip is the file `src/optar/data/font.png`
of this project (a pixel of it is white when its grey value is 128 or more);
its digest below is the SHA-256 of its pixels as bytes 0 (black) and 255
(white), row by row.

```example
strip_width = 1500
logo_width = 265
glyph_column_of_capital_a = 429
font_strip_sha256 = 481c0abd7884afb5ab6d958fbb95c0d6be97b0e2a7124f57e1abcd118d7d4bc4
```

**The label line** of page `page` of `total` with the free text `text` is

    two spaces, the format string, a space, page, "/", total, a space, text

with `page` and `total` in decimal without leading zeros. The space after
`total` is there even when `text` is empty. The line is then cut to its first
`data_width // TEXT_WIDTH - 1` characters (Unicode code points).

**Drawing.** The band is `data_width` columns wide, numbered from 0 at page
column `border`; everything in it that is not drawn is black.

1. If `logo_width <= data_width`, the logo is copied to band columns `0` to
   `logo_width - 1`.
2. A cursor starts at band column `logo_width`, whether or not the logo was
   drawn.
3. For each character of the cut line, in order: a character whose code is
   below 32 or above 127 is skipped. Otherwise, if the cursor plus
   `TEXT_WIDTH` is at most `data_width`, the `TEXT_WIDTH` strip columns that
   start at `TEXT_WIDTH * (code - FIRST_CHAR)` are copied to the band at the
   cursor; in either case the cursor moves on by `TEXT_WIDTH`.

Three consequences that an encoder must reproduce to print the same pages:

- A page shows at most `(data_width - logo_width) // TEXT_WIDTH` characters,
  which is fewer than the line is cut to; the rest is not drawn.
- Characters outside codes 32 to 127 take no cell, but they count towards
  the length at which the line is cut.
- Code 127 takes a cell and draws the first `TEXT_WIDTH` columns of the logo.
  Such a label cannot be read back.

```example
a4_label_line = "  0-65-93-24-3-1-2-24 3/7 backup.tar"
a4_label_characters = 117
a4_label_cells = 98
a4_xlarge_label_cells = 18
```

`a4_label_characters` is the length the line is cut to and `a4_label_cells`
the number of characters a page shows. A page of the format
`0-22-31-24-3-1-2-24` shows 18 characters, fewer than its format string has;
section 5.4 says how such pages are labelled in print.

Vectors: `tests/vectors/c/label.json`, `tests/vectors/c/encoder_pages.json`.

## 3. The document tag (0.2.0 printouts)

A plain document does not say how long its file is, which pages belong
together or whether the file was read correctly. A **tagged document** says
so in the free text of every label. Its stream is the file itself, so its
pages are also read by programs that know nothing of the tag.

### 3.1 The tag

For a file of `size` bytes:

- `SIZE` is `size` in decimal without leading zeros (`0` for an empty file),
  at most `MAX_SIZE_DIGITS` digits;
- `FINGERPRINT` is the first `FINGERPRINT_DIGITS` characters of the SHA-256
  of the file, written as lower-case hexadecimal;
- `CHECK`, for page `page` of `total`, is the first `CHECK_DIGITS` characters
  of the lower-case hexadecimal SHA-256 of the ASCII text
  `SIZE:FINGERPRINT:page/total`, with `page` and `total` as the label line
  writes them.

The tag of a page is the text `[SIZE:FINGERPRINT:CHECK]`. The free text of
the page's label is the tag, or the tag, one space and a name. `SIZE` and
`FINGERPRINT` are the same on every page of a document; `CHECK` differs from
page to page.

An empty file is one page labelled `1/0` (section 2.7); its check is
computed with `page` 1 and `total` 0.

```example
tag_fingerprint_of_x = 2d711642
tag_check_input = "1:2d711642:1/1"
tag_check_of_x_page_1_of_1 = ca
tag_free_text = "[1:2d711642:ca] name.tar"
tag_of_empty_file = "[0:e3b0c442:e0]"
```

The first four lines are for the one-byte file `x` printed with the name
`name.tar`.

Vectors: `tests/vectors/py/tag.json`.

### 3.2 When a tag is valid

The free text of a label **starts with a tag** when it begins with `[`, a
size as above, `:`, exactly 8 characters from `0-9a-f`, `:`, exactly 2
characters from `0-9a-f` and `]`, and the tag is followed by a space or by
the end of the text.

A tag read from page `page` of `total` in the page format `F` is **valid**
when both hold:

- its check equals the check computed from the size, fingerprint, `page` and
  `total` as read;
- the size fits the page count: `size = 0` and `total = 0`, or `size > 0`,
  `total > 0` and `(total - 1) * capacity < size <= total * capacity` with
  `capacity = net_bits // 8` of `F`.

In the two `standard` layouts (section 5.2) `net_bits` is a multiple of 8,
so a size fits exactly the page count that section 2.7 gives it. This
project's reader identifies pages by their tag in those two layouts only.

Vectors: `tests/vectors/py/tag.json`.

## 4. Self-identifying documents (version 1)

A **self-identifying document** carries, in the data of every page, a header
that says which document the page belongs to and which page it is, and it can
carry parity with which damaged and missing pages are repaired. The file, its
name and the parity are packed into a stream, the **container**, and that
stream is printed as ordinary version-0 pages (part 2). The version 1 is the
version of the container; the page format keeps the version 0.

### 4.1 Sizes

For a page format `F`, a parity level `parity` (section 4.4) and a page count
`T`:

    page_bytes = net_bits // 8                         payload of one page
    page_body  = page_bytes - HEADER_COPIES * HEADER_SIZE
    k          = CODEWORD - parity                     data bytes of a codeword
    m(T)       = T * page_body // CODEWORD             codewords
    D(T)       = m(T) * k                              bytes of the data region

The **payload** of a page is its first `page_bytes * 8` data bits as bytes.
The **body** of a page is its payload without the header copies (section
4.3), `page_body` bytes. The **body of the document** is the bodies of pages
1 to `T` joined, `T * page_body` bytes.

A page format can carry a container only if
`page_bytes // HEADER_COPIES >= HEADER_SIZE`.

```example
a4_page_bytes = 199773
a4_page_body = 199583
```

Vectors: `tests/vectors/py/container.json`.

### 4.2 The header

A header is `HEADER_SIZE` bytes:

<!-- spec-table: header-fields -->
| Offset | Size | Field | Type | Content |
|---|---|---|---|---|
| 0 | 4 | `magic` | bytes | `HEADER_MAGIC` |
| 4 | 1 | `version` | integer | `CONTAINER_VERSION` |
| 5 | 1 | `parity` | integer | parity bytes per codeword: 0, 32 or 64 |
| 6 | 2 | `page` | integer | number of this page, from 1 |
| 8 | 2 | `total` | integer | pages in the document |
| 10 | 8 | `size` | integer | size of the file in bytes |
| 18 | 16 | `fingerprint` | bytes | first `FINGERPRINT_SIZE` bytes of the SHA-256 of the file |
| 34 | 4 | `crc` | integer | CRC-32 of bytes 0 to 33 |

Integers are big-endian. All fields but `page` (and with it `crc`) are the
same on every page of a document.

```example
header_bytes = 6f5074310140000300070000000000086e3c000102030405060708090a0b0c0d0e0f1ef0ca9d
header_crc = 0x1ef0ca9d
```

This is the header of page 3 of 7 of a file of 552508 bytes with parity 64
whose fingerprint is the bytes `00` to `0f`.

Vectors: `tests/vectors/py/container.json`.

### 4.3 The payload of a page

Copy `c` of the page's header, `0 <= c < HEADER_COPIES`, is at payload bytes

    c * (page_bytes // HEADER_COPIES)   to   c * (page_bytes // HEADER_COPIES) + HEADER_SIZE - 1

The other payload bytes, in order, are the body of the page.

```example
a4_header_offsets = 0, 39954, 79908, 119862, 159816
```

Vectors: `tests/vectors/py/container.json`.

### 4.4 Parity levels

<!-- spec-table: parity -->
| Name | Parity bytes | Data bytes |
|---|---|---|
| none | 0 | 255 |
| standard | 32 | 223 |
| high | 64 | 191 |

"Parity bytes" is the header field `parity`; "Data bytes" is `k`. A document
with parity 0 has headers and a name but nothing is repaired.

Vectors: `tests/vectors/py/container.json`.

### 4.5 The Reed-Solomon code

A **codeword** is `CODEWORD` bytes: `k` data bytes followed by `parity`
parity bytes.

- The bytes are elements of GF(256) with the field polynomial
  `x^8 + x^4 + x^3 + x^2 + 1` (`0x11D`): a byte is a polynomial over GF(2)
  whose coefficient of `x^7` is its most significant bit, addition is XOR and
  multiplication is polynomial multiplication modulo the field polynomial.
- `alpha` is the element `0x02`.
- The generator polynomial is
  `g(x) = (x - alpha^0)(x - alpha^1) ... (x - alpha^(parity - 1))`.
- Byte `i` of a codeword, `0 <= i <= 254`, is the coefficient of `x^(254 - i)`
  of the codeword polynomial `c(x)`.
- The data bytes are the coefficients of `x^254` down to `x^parity`. The
  parity bytes are chosen so that `g(x)` divides `c(x)`: they are the
  remainder of the division of the data polynomial (with zero coefficients
  below `x^parity`) by `g(x)`, coefficient of `x^(parity - 1)` first.

A codeword can be repaired when `2 * e + f <= parity`, where `f` is the
number of its bytes that are known to be unreadable (erasures) and `e` the
number of other bytes that are wrong.

```example
gf_alpha_8 = 0x1d
gf_alpha_254 = 0x8e
rs_32_parity_of_one = 744034ae367e10c2a221219db0c5e10c3b37fde4942fb3b9188afd148e37ac58
rs_32_parity_of_counting = 41841183b11fdb537421939696cda70e1db5c86684af222564b89cc6069f172e
```

`rs_32_parity_of_one` is, for parity 32, the parity bytes of the 223 data
bytes that are all zero but for a last byte of 1; these are the coefficients
of `g(x)` from `x^31` down to `x^0`. `rs_32_parity_of_counting` is, for
parity 32, the parity bytes of the data bytes 0, 1, 2, ..., 222.

Vectors: `tests/vectors/py/reed_solomon.json`.

### 4.6 The data region and the spread

The **data region** is `D(T)` bytes:

| Bytes | Content |
|---|---|
| `size` | the file |
| 1 | `L`, the length of the name in bytes, 0 to `NAME_MAX_BYTES` |
| `L` | the name of the file in UTF-8 |
| the rest | padding (section 4.7) |

A name longer than `NAME_MAX_BYTES` bytes in UTF-8 is cut to the longest
whole number of characters that fits. The name is not covered by the
fingerprint. A character of the name that UTF-8 cannot encode (a lone surrogate code
point, U+D800 to U+DFFF) is stored as `?`.

Codeword `j`, `0 <= j < m`, has the bytes `j * k` to `j * k + k - 1` of the
data region as its data bytes. With parity 0 a codeword is its 255 data
bytes.

**The spread.** Byte `i` of codeword `j` is the byte of the document's body
at position

    i * m + (j + i * SPREAD_STEP) mod m

So byte `i` of every codeword lies in the slice `i * m` to `(i + 1) * m - 1`
of the body, and the 255 bytes of one codeword lie in 255 different slices,
spread over the whole document: damage in one place costs every codeword a
few bytes instead of costing a few codewords everything.

The last `T * page_body - CODEWORD * m` bytes of the body (fewer than
`CODEWORD`) belong to no codeword and are padding.

Vectors: `tests/vectors/py/container.json`.

### 4.7 Padding

The padding carries nothing. Two contents exist and both are valid:

- optar 0.3.0 wrote zero bytes;
- optar 0.3.1 and later write the **padding stream**: block `n` of it,
  `n = 0, 1, 2, ...`, is the `PADDING_BLOCK` bytes of the SHA-256 of one
  byte string: `PADDING_KEY` with `n` appended as an integer of 8 bytes,
  big-endian; the stream is the blocks joined. The padding of the data
  region is the stream from its byte
  0; the padding at the end of the body continues the stream where the data
  region's padding stopped. (Zero bytes print as white lines across every
  page; the stream prints like data.)

A document whose padding is anything else is still a valid document for a
reader (section 6.4), but only the padding stream gives the pages that this
project prints.

```example
padding_block_0 = d518824e181c15b2f69e390066efbfa00d73eb8f0c3d932313396940eedd1286
padding_bytes_30_to_33 = 12863e00
```

Vectors: `tests/vectors/py/container.json`.

### 4.8 The page count and the limits

A document has the fewest pages that hold the file, the length byte and the
name:

    need = size + 1 + L
    T    = the smallest T >= 1 with D(T) >= need

The limits are:

- `T <= MAX_PAGES`;
- with `parity > 0`: `T * page_bytes <= PROTECTED_MAX_BYTES`;
- `size < 2^64`, `L <= NAME_MAX_BYTES`.

A file that needs more cannot be put into a document.

```example
plan_need = 1000011
plan_codewords_needed = 4485
plan_pages = 6
plan_codewords = 4696
plan_data_bytes = 1047208
plan_body_bytes = 1197498
plan_spare_bytes = 18
plan_padding_in_region = 47197
plan_position_of_codeword_0_byte_0 = 0
plan_position_of_codeword_5_byte_0 = 5
plan_position_of_codeword_5_byte_1 = 7924
plan_position_of_codeword_5_byte_254 = 1194327
plan_page_of_codeword_5_byte_254 = 6
```

The example is a file of 1000000 bytes named `vector.bin` on standard A4
pages with parity 32. It needs 4485 codewords; five pages hold fewer and six
hold `m = 4696`. The document has all 4696 codewords; those the file does
not need hold padding. `plan_spare_bytes` is the padding at
the end of the body and `plan_padding_in_region` the padding of the data
region. The positions are positions in the document's body (section 4.6).

Vectors: `tests/vectors/py/container.json`.

### 4.9 What the document withstands (informative)

A lost page costs a codeword at most `ceil(page_body / m) + 1` bytes. This
project tells its user that any `n` pages can be lost when
`n * (ceil(page_body / m) + 1) <= PROMISE_NUM * parity // PROMISE_DEN`, which
leaves a quarter of the parity for damage on the pages that remain. This is a
promise of the tools: it is neither a property that a reader may rely on nor
one that a reader must check.

### 4.10 From the container to pages

The stream is `T * net_bits // 8` bytes. Read as a bit string, the payload of
page `p` (from 1) starts at bit `(p - 1) * net_bits`; every bit of the stream
that lies in no payload is 0.
When `net_bits` is a multiple of 8 the stream is simply the payloads joined.
When it is not, each page has `net_bits mod 8` unused bits after its payload
and the payloads of some pages do not start at the first bit of a byte of
the stream.

The stream is printed as section 2.7 says, which gives exactly `T` pages. The
label of a page is an ordinary label line whose free text is for people: it is
the label the user gave or, without one, a name the tool chooses (the window
uses the file's name, the command line the name given with `-o`, which may be
empty), the same on every page, and it carries no tag. (A valid tag would make a reader take the page for a page of
a tagged document, section 6.1.)

With the Golay code `net_bits mod 8` is 0 or 4 and the last payload always
ends within the stream. This project prints self-identifying documents in
the ten page formats of section 5.2 only, and its reader looks for headers
in those formats only.

```example
a4_medium_stream_bytes_for_3_pages = 344713
a4_medium_page_2_starts_at = 114904, 4
a4_medium_page_3_starts_at = 229809, 0
```

A page of the format `0-50-70-24-3-1-2-24` has `net_bits = 919236`, which
leaves 4 bits after its 114904 payload bytes. The two values are the byte of
the stream in which the page's payload starts and the bit within that byte
(0 is the most significant).

Vectors: `tests/vectors/py/container.json`, `tests/vectors/c/container_pages.json`.

## 5. Printing

### 5.1 Dot sizes

A page is printed with one of five dot sizes. A data dot is a square of a
whole number of printer dots, so that every page pixel prints as the same
block of device dots.

<!-- spec-table: dot-sizes -->
| Name | Printer dots per data dot | Data dots per inch | Dot size (pt) | Advised scan (dpi) |
|---|---|---|---|---|
| standard | 3 | 200 | 0.36 | 600 |
| medium | 4 | 150 | 0.48 | 450 |
| big | 5 | 120 | 0.6 | 360 |
| large | 6 | 100 | 0.72 | 300 |
| xlarge | 9 | 200/3 | 1.08 | 200 |

The advised scan resolution gives `SCAN_PIXELS_PER_DOT` scan pixels per data
dot. It is advice; a page is the same page at any scan resolution.

### 5.2 Layouts

A **layout** is a paper, a dot size and the page format printed on it. There
are ten. Papers are named `a4` and `letter`.

<!-- spec-table: layouts -->
| Paper | Dots | Crosses across | Crosses down | Format string | Width (px) | Height (px) | Net bits | Page bytes | Body bytes |
|---|---|---|---|---|---|---|---|---|---|
| a4 | standard | 65 | 93 | `0-65-93-24-3-1-2-24` | 1546 | 2242 | 1598184 | 199773 | 199583 |
| a4 | medium | 50 | 70 | `0-50-70-24-3-1-2-24` | 1186 | 1690 | 919236 | 114904 | 114714 |
| a4 | big | 40 | 56 | `0-40-56-24-3-1-2-24` | 946 | 1354 | 584220 | 73027 | 72837 |
| a4 | large | 33 | 46 | `0-33-46-24-3-1-2-24` | 778 | 1114 | 392952 | 49119 | 48929 |
| a4 | xlarge | 22 | 31 | `0-22-31-24-3-1-2-24` | 514 | 754 | 172848 | 21606 | 21416 |
| letter | standard | 67 | 87 | `0-67-87-24-3-1-2-24` | 1594 | 2098 | 1540728 | 192591 | 192401 |
| letter | medium | 51 | 66 | `0-51-66-24-3-1-2-24` | 1210 | 1594 | 883704 | 110463 | 110273 |
| letter | big | 41 | 52 | `0-41-52-24-3-1-2-24` | 970 | 1258 | 555708 | 69463 | 69273 |
| letter | large | 34 | 44 | `0-34-44-24-3-1-2-24` | 802 | 1066 | 387228 | 48403 | 48213 |
| letter | xlarge | 23 | 29 | `0-23-29-24-3-1-2-24` | 538 | 706 | 169020 | 21127 | 20937 |

"Page bytes" and "Body bytes" are `page_bytes` and `page_body` of section
4.1. This project prints a plain or tagged document in a `standard` layout
(or, when given a format string by hand, in that page format at the standard
dot size and the offsets of the paper's `standard` layout; it refuses such a
format string unless every margin is then at least `MIN_MARGIN_PT`), and a
self-identifying document in any of the ten layouts.

Vectors: `tests/vectors/c/bit_placement.json`, `tests/vectors/py/container.json`.

The page image is placed on the paper with its lower left corner at the
offsets below, measured from the lower left corner of the paper. The margins
are what remains on each side.

<!-- spec-table: layouts -->
| Paper | Dots | Paper width (pt) | Paper height (pt) | Offset x (pt) | Offset y (pt) | Left (mm) | Bottom (mm) | Right (mm) | Top (mm) |
|---|---|---|---|---|---|---|---|---|---|
| a4 | standard | 595.28 | 841.89 | 19.20 | 17.40 | 6.77 | 6.14 | 6.89 | 6.13 |
| a4 | medium | 595.28 | 841.89 | 12.96 | 15.24 | 4.57 | 5.38 | 4.60 | 5.45 |
| a4 | big | 595.28 | 841.89 | 13.80 | 14.64 | 4.87 | 5.16 | 4.90 | 5.24 |
| a4 | large | 595.28 | 841.89 | 17.52 | 19.80 | 6.18 | 6.99 | 6.21 | 7.06 |
| a4 | xlarge | 595.28 | 841.89 | 20.04 | 13.68 | 7.07 | 4.83 | 7.10 | 4.90 |
| letter | standard | 612 | 792 | 19.08 | 18.36 | 6.73 | 6.48 | 6.73 | 6.48 |
| letter | medium | 612 | 792 | 15.60 | 13.44 | 5.50 | 4.74 | 5.50 | 4.74 |
| letter | big | 612 | 792 | 15.00 | 18.60 | 5.29 | 6.56 | 5.29 | 6.56 |
| letter | large | 612 | 792 | 17.28 | 12.24 | 6.10 | 4.32 | 6.10 | 4.32 |
| letter | xlarge | 612 | 792 | 15.48 | 14.76 | 5.46 | 5.21 | 5.46 | 5.21 |

Every offset is a whole number of printer dots, so the edges of the image
fall on device dots. The grids and offsets of the two `standard` layouts are
inherited (part 8). The other eight are derived: the grid is the largest
`xcrosses` and `ycrosses` for which the page, at its dot size, leaves at
least `MIN_MARGIN_PT` on every side, and each offset is half of the free
length, rounded down to a whole printer dot. The tables, not this rule,
define the layouts.

A page is the same page wherever it lies on the paper: a
reader finds the page by its border. The placement matters for printing
only: a page printed at another scale has dots of another size, and one
printed closer to the edge may be clipped.

### 5.3 The PDF this project writes

Each page of the document is one PDF page whose media box is the paper:
`[0 0 width height]`, with the width and height of the paper in points. The
page image is one image of 1 bit per
pixel (1 is white), `width` by `height` page pixels, without interpolation,
drawn with its lower left corner at the layout's offsets and scaled so that
one page pixel is one data dot:

    image width in points  = width  * dot size in points
    image height in points = height * dot size in points

```example
a4_large_image_width_pt = 560.16
a4_large_image_height_pt = 802.08
```

The PDF is meant to be printed at actual size (100%). No vector pins the
PDF; `tests/unit/test_pdf.py` does.

Page images are also written as PNG or PGM files with one image pixel per
page pixel; the vectors identify a page by the SHA-256 of its binary PGM
(`P5`) file, whose exact bytes `tests/vectors/README.md` gives: the header
`P5\n<width> <height>\n255\n` in ASCII, then the pixel bytes row by row.

### 5.4 The label strip

A label is drawn in page pixels (section 2.8), so on a page with larger dots
it holds fewer characters: with the largest dots, too few for its own format
string.
In a PDF, a page of a layout whose dot size is not `standard` therefore has
its label replaced by a **label strip**, a second image drawn in standard
data dots:

- the strip is `LABEL_HEIGHT` rows and
  `floor(data_width * printer dots per data dot / STANDARD_PRINTER_DOTS)`
  columns of strip pixels;
- it holds the label line of the page, cut and drawn as in section 2.8 with
  the strip's width in place of `data_width`;
- in the page image, the label band is made black in columns `border` to
  `border + data_width - 1`;
- the strip is drawn over the band at 0.36 pt per strip pixel, with its left
  edge at the left edge of the band's data columns and centred in the height
  of the band.

Only the label band differs from the page of part 2; the data area and the
border are untouched. A PNG or PGM page of such a layout keeps the label of
section 2.8. The label of a self-identifying page is not used to identify it
(section 6.2), so a reader need not read the strip.

```example
a4_large_strip_width = 1548
a4_large_strip_characters = 118
a4_large_strip_width_pt = 557.28
```

Vectors: `tests/vectors/c/container_pages.json` pins the pages of two layouts
with larger dots as ordinary pages; the strip is pinned by
`tests/unit/test_font.py` and `tests/unit/test_pdf.py`.

## 6. What a reader must do

A reader has scanned pages and has, by any method, read from each one its
data bits and, where it could, its label. This part says what it must
conclude from them. The scans are untrusted: one page can be printed by
anyone and can claim anything.

### 6.1 A valid tag wins over a header

For a page in a `standard` layout, the reader must look at the label first.
If the label has the form of section 2.8, carries the format string of the
layout, a page count of at most `MAX_PAGES`, a page number from 1 to the page
count (or 1 with the page count 0), and its free text starts with a tag that
is valid for that page number and count (section 3.2), the page is a page of
a tagged document. It must be treated as one even if its data holds an
acceptable header (section 6.2).

The reason: the stream of a self-identifying document, as an old program
returns it, can be printed again as a tagged document. Those pages hold old
headers in their data, and they are pages of the tagged document, whose file
is that stream.

### 6.2 A header is untrusted

A header copy is **well-formed** when its CRC is right, its magic is
`HEADER_MAGIC`, its version is `CONTAINER_VERSION`, its parity is 0, 32 or 64
and `1 <= page <= total`.

The **header of a page** exists when at least one of its `HEADER_COPIES`
copies is well-formed and all well-formed copies are equal. A page whose
well-formed copies differ has no header.

A header read from a page of the format `F` is **acceptable** when it
describes a document that section 4.8 allows, that is when all of these
hold (`m`, `D` and `page_bytes` as in section 4.1, for `F` and the header's
parity):

1. `total <= MAX_PAGES`;
2. `page_bytes // HEADER_COPIES >= HEADER_SIZE`;
3. if `parity > 0`: `total * page_bytes <= PROTECTED_MAX_BYTES`;
4. `size + 1 <= D(total)`: the pages hold the file and the length byte;
5. if `total > 1`: `size + 1 + NAME_MAX_BYTES > D(total - 1)`: no name would
   have let the file fit on fewer pages.

A reader must not use a header that is not acceptable. Rules 4 and 5 tie the
page count to the size, so that a header cannot claim many pages for a small
file or few pages for a large file.

A reader must keep its memory and its time in proportion to the pages it was
given, not to what a header claims: one page that claims a document of 9999
pages must not make the reader allocate or process 9999 pages.

Pages belong to one document when their headers agree in `fingerprint`,
`size`, `total` and `parity` and the pages have the same page format. Pages
of another document must not be used.

### 6.3 Only the fingerprint verifies a file

- **Self-identifying document.** A payload byte is an erasure when one of
  its bits lies in a symbol the page code could not correct; every byte of a
  page that was not supplied is an erasure. The file is the first `size`
  bytes of the data region, and it is recovered when, and only when, every
  codeword that holds one of those bytes was read or repaired (with parity
  0, where nothing is repaired: when every such codeword has no erasure).
  The file is **verified** when it is recovered and the first
  `FINGERPRINT_SIZE` bytes of its SHA-256 equal the header's fingerprint.
- **Tagged document.** The file is the first `SIZE` bytes of the stream. It
  is **verified** when it has `SIZE` bytes and the first `FINGERPRINT_DIGITS`
  hexadecimal characters of its SHA-256 equal the tag's fingerprint.
- **Plain document.** Nothing verifies it, and its length is not known
  (section 2.7).

A reader must not call a file verified for any other reason. In particular a
repair that reports no failure does not verify the file: a codeword with
more wrong bytes than its parity can repair may be turned into another valid
codeword, and with parity 0 nothing is checked at all.

The name of the file (section 4.6) is outside the fingerprint. It is
untrusted text even when the file is verified, as is every label.

### 6.4 Padding is never read

A reader must not read, check or depend on the padding of section 4.7. Zero
bytes (0.3.0) and the padding stream (0.3.1) are both valid, and a document
with either is the same document to a reader.

The bytes of the data region after the name are padding. A name record whose
length byte points past the end of the data region, or whose bytes are not
UTF-8, or which lies in a codeword that was not repaired, gives no name; it
does not make the file invalid.

Vectors: `tests/vectors/py/container.json`, `tests/vectors/py/tag.json`.

## 7. Reference decoder (informative)

This part describes how this project reads a scan. None of it is required: a
reader may find and sample a page in any way. The steps and their constants
are those of the C program `unoptar` (part 8); the results of this decoder on
fixed scans are pinned by the vectors named at the end, so that it does not
change by accident.

### 7.1 The scan

A scan is read as an 8-bit grey image in linear light. A sample `v` of the
file becomes `floor(255 * (v / 255) ^ (1 / gamma) + 0.5)`, where `gamma` is
the file's gamma (PNG `gAMA`) or 0.454545 when the file gives none. A colour
image is converted channel by channel and then weighted 0.212671 red,
0.715160 green, 0.072169 blue, rounded to the nearest integer. A 16-bit
sample keeps its upper 8 bits.

```example
linear_light_of_128 = 56
linear_light_of_200 = 149
```

### 7.2 Finding the page

The decoder is given the page format. It works on the upright image.

1. **Grey levels.** The cut level starts at the mean grey value. Up to 32
   times: `black` is the cut minus the root mean square (the square root of
   the mean of the squares) of the distances from the cut of the pixels
   below it, `white` the cut plus the same for the pixels above it; the new
   cut is `sync_white_cut * white + (1 - sync_white_cut) *
   black`, rounded; it stops when the cut no longer changes. A second level,
   the fill cut, is halfway between `black` and `white`.
2. **Isolating the page.** The white around the page is every pixel at or
   above the fill cut that is connected (by edges, not corners) to one of
   the four corners or four edge midpoints of the scan. The page is
   everything else that is connected to the centre of the scan. All other
   pixels (dirt between the page and the edge of the scan) are made white.
3. **A gap in the frame.** If a printer clipped an edge of the page, the
   border has a gap, the white around the page runs in between the dots and
   step 2 finds only a piece of the page. When the area found is less than
   half of what is not the white around the page as step 2 found it, the
   white around the page is taken
   instead as what can be reached through passages at least `2 * r + 1`
   pixels wide, with `r = max(5, longest side // 250) // 2`; the white
   between dots is narrower than that. This result is used only if it gives
   a whole page. It is a tolerance of this decoder, not a property of the
   format: a page has a whole border.
4. **Corners.** From each corner of the scan the decoder walks the diagonals
   inwards and takes the first pixel below the cut. This needs the page
   upright and taller than wide; a scan wider than tall is turned first (7.5).
5. **Pixel size.** The scan pixels per page pixel, horizontally and
   vertically, come from the distances between the corners divided by
   `width` and `height`; the directions of the page's rows and columns come
   from the means of opposite sides. (The horizontal size uses the upper
   left corner twice and the lower left corner not at all. This is inherited
   decoder behaviour and not part of the format.)

### 7.3 Crosses

The first cross is expected `border + chalf` page pixels in from the upper
left corner. Every other cross is expected one pitch to the right of its left
neighbour, and the first of a row one pitch below the one above it, so each
search starts from a cross already found. For each cross:

1. a coarse search over whole scan pixels, up to half of `chalf` (half of
   half the side of a cross) in every direction, for the place where the
   image correlates best with the cross
   pattern (dark, light, light, dark);
2. a fine search within half a scan pixel in steps of a quarter pixel, on a
   cross made smaller by `cross_trim` page pixels on every side;
3. a cut level of its own: from the pixels of the cross, `white` and `black`
   as in 7.2, combined as `white_cut * white + (1 - white_cut) * black`.

### 7.4 Sampling and decoding

1. **Filters.** Dark specks narrower than `minmax_filter` times the size of
   a page pixel are removed (passes of a maximum filter, then as many of a
   minimum filter); the image is then blurred with a 3 by 3 kernel (1 2 1 /
   2 4 2 / 1 2 1), `round(pixel area * pixel_blur ^ 2)` times.
2. **Sampling.** The scan position of each data pixel is interpolated
   between the four crosses around it, and so is its cut level. The sample
   is sharpened: `value + unsharp_mask * (value - mean of the four
   neighbours at unsharp_dist page pixels)`. The bit is 1 when the result is
   below the cut level.
3. **Decoding.** The bits are put back into symbols (section 2.6). A Golay
   symbol is replaced by the nearest symbol if that differs in at most 3
   bits; otherwise the symbol is uncorrectable and its upper 12 bits are
   taken as read. A Hamming symbol has one wrong bit corrected; two wrong
   bits make it uncorrectable.
4. The words of a page are joined into its `net_bits` data bits. For a plain
   or tagged document the bits of the pages are joined in page order and cut
   into bytes; bits that do not fill a last byte are dropped.

```example
decoder_unsharp_mask = 7
decoder_unsharp_dist = 1
decoder_sync_white_cut = 0.1
decoder_white_cut = 0.06
decoder_minmax_filter = 0.5
decoder_pixel_blur = 0.25
decoder_cross_trim = 0.75
```

### 7.5 Identifying a scan

When it is not told the page format, this project works it out:

1. The outline of the page (7.2, steps 1 to 4) gives its shape. The two
   papers are tried in the order of how close the shape is to their
   `standard` page; each is tried upright and turned by half a turn (or by a
   quarter turn either way for a scan wider than tall).
2. For each paper, first its `standard` page: the page is located and its
   label read by matching each character cell against the font. A valid tag
   decides at once (section 6.1). A label without a tag is accepted only
   when it was read clearly, and then the data is still looked at for a
   header, because a self-identifying page with standard dots has such a
   label.
3. Then the layouts of the paper, closest shape first: the page is located,
   decoded, and an acceptable header (section 6.2) decides.

A misread tag passes its check about once in 256 times; a label without a tag has no check at all, which is why it must be read
clearly and why free text that is one misread character away from a valid
tag is refused. These acceptance thresholds belong to this reader, not to
the format.

### 7.6 The slower reader

This project tries a second, slower reader (`src/optar/decoder/soft.py`),
meant for a scan too coarse for its dot size, in two cases. First: the steps
of 7.5 identify nothing, although the outline of a page was found. Second:
all three of these hold: the steps of 7.5 accept a page from an untagged
label alone; a data pixel of that scan is less than 2.5 scan pixels wide; and
1% or more of the page's symbols are uncorrectable. For each candidate
layout and
rotation, in the order of 7.5, it:

1. enlarges the scan so that a data pixel is about four scan pixels wide,
   and locates the page as in 7.2 and 7.3;
2. reads the page as in 7.4 and takes the symbols decoded with at most one
   corrected bit as known;
3. samples a 7 by 7 grid of points half a data pixel apart around every data
   pixel and fits, by least squares, a filter from those samples to the known
   bits, one filter for each of 16 by 22 regions of the page;
4. applies the filters to every data pixel, which gives a signed confidence
   for each bit, and chooses, for each symbol of the page, the Golay symbol
   (section 2.5) that fits its 24 confidences best;
5. takes the more confident 60% of the symbols as known and repeats from
   step 3, five fits in all.

A page is accepted only by an acceptable header (section 6.2). A label is not
read, so a page without a header (a plain or tagged document, part 3) is not
identified this way. A page whose tag was accepted is never read this way,
so section 6.1 holds. The result goes
to the container exactly as the ordinary reader's does, and only the
fingerprint verifies the file (section 6.3). Nothing in this reader is part
of the format, and it does not change the results of the decoder of 7.1 to
7.5.

Vectors: `tests/vectors/c/decoder.json`, `tests/vectors/c/decoder_internals.json`
(they pin this decoder's results on fixed scans, not the format).

## 8. History

The page of part 2 is the format of Twibright Optar, a C program written by
Karel Kulhavy in 2007; it was later maintained, from 2012, at
`colindean/optar`. Its
sources are kept unchanged in the folder `lega-c` of this project, as they
were at commit `9c8379c25466bf142459a26b0f34521bdde2af12` of that repository.
The vectors in `tests/vectors/c` were recorded from that program; those in
`tests/vectors/py` from this project.

| Version | What it added |
|---|---|
| C program | the page (part 2); A4 or Letter chosen when compiling |
| 0.1.0 | the same pages, written and read by this project |
| 0.2.0 | the tag (part 3) |
| 0.3.0 | the container, the dot sizes and the layouts (parts 4 and 5), with zero padding |
| 0.3.1 | the padding stream (section 4.7) |

What the format keeps from the C program:

- the border, the crosses, the order of the data pixels and the interleave;
- the Golay table, built from the dodecahedron, and the Hamming codes;
- the font strip, the label line and its three peculiarities (section 2.8);
- the limit of 9999 pages, and the empty file printed as one page `1/0`;
- that a page does not record the length of its stream;
- the grids of the two `standard` layouts and the offsets of the Letter one.
  The C tools placed the A4 page at 19.22 and 17.44 pt, which is not on
  whole printer dots; this project places it at the offsets of section 5.2.

The C program has one page format compiled in. Its decoder takes the format
string as an argument but uses only the last field.

One difference from the C program remains in the label: the C program cut
the label line by bytes, this format cuts it by characters. The two give
the same page unless both are true: the line is cut, and it holds characters
outside ASCII before the cut.

Decoder behaviour inherited from the C program that is not part of the
format (part 7): the seven constants of section 7.4, the double use of one
corner in the pixel size, the corner search that needs an upright page
taller than wide, and the arithmetic in 32-bit floating point that the
decoder vectors pin.
