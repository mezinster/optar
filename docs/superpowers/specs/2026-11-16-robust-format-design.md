# Optar robust format: design

Date: 2026-11-16
Status: approved by the owner 2026-11-16; corrected after the builder check the same day (see the last section)

## Intent

The owner printed a three-page document with optar 0.2.0 and scanned it with a Brother ADS-1100W sheet-fed scanner through its phone app. The scans came out at about 200 dpi and none could be read. The owner's goal: **a printout that can be read back from a 200–300 dpi scan**, and a format that survives damage better, in the manner of dvdisaster (error-correction data spread over the whole medium).

Two things are needed, and neither is enough alone:

1. **Larger dots.** The decoder needs 2 to 3 scan pixels per printed dot. Today's dot is 1/200 inch, so it needs a 400–600 dpi scan. No error correction recovers a page sampled at one pixel per dot.
2. **Document-wide parity.** Reed-Solomon parity computed over the whole document, with each codeword's bytes spread across every page, repairs what the per-page Golay code cannot: the scattered errors of a marginal scan, a stain, a torn corner, a lost page.

## Evidence

Simulated scans of today's A4 page (print at 600 dpi, Gaussian blur, 0.4° rotation, resampling, noise). These are ideal conditions; a real scanner does worse.

| Scan | Scan pixels per dot | Codewords needing correction | Bytes wrong after Golay |
|---|---|---|---|
| 600 dpi | 3 | 0.01% | 0% |
| 400 dpi | 2 | 5.5% | 0% |
| 300 dpi | 1.5 | 7% | 0% (one codeword lost in one run) |
| 250 dpi | 1.25 | 36% | 0.44% |
| 220 dpi | 1.1 | – | 4.3% |
| 200 dpi | 1 | 65% | 11.75% |

Page geometry for larger dots, computed with the existing format code (cell pitch 24, as today):

| Dots | A4 crosses | A4 bytes per page | Letter crosses | Letter bytes per page | Label characters |
|---|---|---|---|---|---|
| Standard (1/200 in) | 65 × 93 | 199,773 | 67 × 87 | 192,591 | 98 / 101 |
| Medium (1/150 in) | 50 × 70 | 114,904 | 51 × 66 | 110,463 | 70 / 72 |
| Big (1/120 in) | 40 × 56 | 73,027 | 41 × 52 | 69,463 | 52 / 53 |
| Large (1/100 in) | 33 × 46 | 49,119 | 34 × 44 | 48,403 | 39 / 41 |
| Extra large (1/67 in) | 22 × 31 | 21,606 | 23 × 29 | 21,127 | 18 / 20 |

The larger-dot grids are the largest that fit each paper with today's 12-point minimum margin; these grids are final. Byte counts are rounded down: where a page's capacity is not a whole number of bytes, a version-1 page leaves the odd bits unused, so every page's payload stands alone. The Standard grids are today's and do not change.

The last column decides part of the design. The label's fixed part (`0-33-46-24-3-1-2-24 12/12`) takes 25 characters, and up to 29 with large page counts. A large-dot label has 10 to 14 left, too few for the 20-character tag; an extra-large label cannot hold even the 19-character format string, so it shows a cut-off one. **The printed label cannot identify these pages**, so the document's details must travel in the page data.

## Evidence from real scans (2026-11-16)

The owner then scanned the same 0.2.0 Standard-dot printout at 300 dpi in colour (three pages, ADS-1100W). The decoder found the grid on all three, so cross tracking works on a sheet-fed scan, but lost 19% of codewords on each full page. The simulator reproduces that error pattern at a blur of about 1.8 printer dots, not the 1.0 assumed above. At that fitted blur:

| Dots | 600 dpi | 300 dpi | 200 dpi |
|---|---|---|---|
| Standard | 15% of bytes wrong | 32% | 68% |
| Medium | clean | 0.06% of bytes wrong | 1.5% |
| Big | clean | clean | clean |
| Large | clean | clean | clean |
| Extra large | clean | clean | clean |

This is a fit to three scans from one printer and one scanner. It replaces the table above as the basis for the claims: the binding simulated-scan tests use blur 1.8, and blur 1.0 is kept as a second, milder level. The Standard-dot claims at 300 and 250 dpi are withdrawn. The claims are: Medium at 300 dpi and at 200 dpi with Standard protection; Big at 200 dpi; Large at 300 and 200 dpi; Extra large at 200 dpi; one lost page of twelve.

## Goals

- A choice of **dot size** when putting a file on paper: Standard, Large, Extra large. Large is meant for 300 dpi scans, Extra large for 200 dpi.
- A choice of **protection**: None, Standard, High. Parity is spread over all pages of the document.
- Pages that **identify themselves from their data**, not their label: document, page number, page count, size, fingerprint, protection.
- Reading needs no setting. The application and `optar decode` work out dot size and protection from the scan.
- The recovered file is repaired, cut to its true size and verified against its fingerprint, as today.
- The application says what protection achieved: how much was repaired, and how much margin was left.
- **A clear message for a scan that is too coarse** for the page it shows, naming the resolution needed. (Today it says only that the label could not be read.)
- Printouts from 0.1.0, 0.2.0 and the C tool keep working exactly as they do now.

## Non-goals (this project)

- Photographs from a phone camera (perspective, uneven light, lens distortion).
- Changing the page code itself: the Golay code, the cross grid, the bit layout and the label font stay.
- Reading soft values from the scan (confidence per bit) to feed the parity decoder. Erasure hints from Golay are used; gray-level confidence is not.
- Colour, gray-level dots or any denser page.
- Recovering a document from pages of two different printouts of the same file.
- Custom dot sizes or parity amounts in the window; the three presets of each are all it offers.

## Anti-goals

- **Breaking old printouts.** A page without the new header is handled by the 0.2.0 rules, unchanged.
- **A page the C tools cannot read.** Every page stays a valid version-0 optar page. A C `unoptar` built with the same grid size reads its payload bit for bit; what it gets is the wrapped stream.
- **A repair that invents data.** A codeword that cannot be corrected is reported as lost, never guessed. The fingerprint is always the final judge.
- **Retuning the decoder.** Its algorithm and constants stay. Larger dots are a property of the print, not of the decoder.
- **A new runtime dependency.** Reed-Solomon is implemented on numpy.

## Constraints

- Python 3.12+, GPL-2.0, same repository, test-first.
- Runtime dependencies stay numpy and Pillow.
- Format numbers (grid sizes, dot sizes, offsets, parity sizes) live only in `src/optar/format.py`.
- The C sources remain the untouched test reference.
- Nothing under `src/optar` imports Qt. Document rules stay in `optar_gui/document.py`; strings in `text.py`; no scan work on the interface thread.
- Work lands on `mezinster/optar` only.

## Approaches considered

### How to make coarse scans readable

1. **Larger dots with the existing page format (chosen).** The format string already states the grid size, and the decoder does not care how large the page is printed. Cost: capacity falls with the square of the dot size.
2. **A better decoder for today's dots.** At one scan pixel per dot the information is not in the scan. At 1.5 it is marginal and would mean retuning against real scans the project does not have.
3. **A new page code** (larger cells, stronger per-page code). Throws away the C reference and the bit-exact tests for a gain that larger dots give for free.

### Where the extra error correction goes

1. **An outer layer wrapping the file before it is put on pages (chosen).** Pages stay ordinary optar pages. The comparison tests against C still hold. Parity can span pages, which a per-page code cannot.
2. **Replace Golay with a stronger per-page code.** Cannot recover a lost page, and breaks the reference.
3. **Extra parity pages only** (parity kept apart from data). Simpler, but a codeword's bytes then sit close together and one stain defeats it. Spreading is the point of the dvdisaster approach.

### Where a page says what it is

1. **A header in the page data, repeated (chosen).** Forced by the label sizes above; also protected by the Golay code, which the label is not.
2. **The printed label**, as in 0.2.0. Does not fit on larger-dot pages.
3. **A separate cover page.** Lose it and the document is unreadable.

## The wrapped document (container version 1)

Terms: a **document** is one file put on paper. Its **stream** is what the pages carry, in page order: every page's payload, concatenated.

### Page payload

Each page's payload (its capacity in bytes, from the table above) is:

- a **page header**, repeated several times at positions spread through the payload;
- the page's share of the **body**.

The page header carries: a magic value and container version; the document's true size; a fingerprint of the file (SHA-256, at least 8 bytes, more than the 4 printed today because space is no longer tight); page number and page count; the parity size per codeword; and a checksum of the header itself. A page is a version-1 page when any copy of its header passes its checksum. Copies that pass must agree.

The header is deliberately outside the parity layer: it must be readable from one page alone, before the document is assembled.

### Body

The body is the file, followed by a short record with the file's name, followed by parity, padded to fill the last page. It is cut into Reed-Solomon codewords of 255 bytes over GF(256), with 32 (Standard) or 64 (High) parity bytes each.

**Spreading.** The requirement is the property, not one rule: a missing page, and a compact damaged area on any page (a stain, a torn corner), must cost every codeword about the same small number of bytes. The starting point is to treat the body as 255 equal slices in page order and give each codeword one byte from each slice. That alone is even only for damage that is one run of the stream; a stain becomes many periodic runs through the page's bit layout and Golay interleave, and those periods must not line up with the slice length. The builder may add a fixed permutation (a rotation per slice, or a pseudo-random one) to break such alignment, and tests it with simulated blots, not only with the one-byte-per-slice count.

**What it repairs.** Per codeword, Standard corrects 16 wrong bytes at unknown places or 32 at known places; High corrects 32 or 64. Known places come from two sources: bytes inside Golay codewords that Golay reported as uncorrectable, and all bytes of a page that is missing.

| Protection | Extra paper | Wrong bytes it repairs (unknown places) | Share of the document that may be missing |
|---|---|---|---|
| None | 0 | – | 0 |
| Standard | 14% | up to 6% in any codeword | 12.5% |
| High | 34% | up to 12.5% in any codeword | 25% |

Those limits leave nothing for scan errors, so the window promises less. It states that pages can be lost ("can lose 1 page of 12") only when the lost pages take at most three quarters of the known-places budget (24 of 32 bytes, 48 of 64): one page is promised from 12 pages up with Standard and from 6 pages up with High (one byte of the budget is kept for a page that straddles slice boundaries). Below that the window says only that damage within pages is repaired. A document may still recover beyond the promise; the promise is what the window states in advance.

**Protection None** still uses the container (header, true size, fingerprint, name) with no parity. It is the only way a larger-dot page can identify itself.

### What the label says

The label is printed as today, for people: format string, page numbers, and as much of the name as fits (on extra-large pages, only the start of the format string). Version-1 pages print no tag in it. The program does not rely on the label of a version-1 page.

### What old tools make of a version-1 page

For Standard dots, optar 0.2.0 and C `unoptar` see an untagged page and return the stream: headers, file, name record and parity. The file is in there but not usable directly. Larger-dot pages are not read by the 0.2.0 application at all (it tries only today's two grids); its command line and a C build read them only when given the grid. This is the price of the container, and the reason the choice below exists.

## Dot size

A dot size is a print scale, plus the grid that fits the paper at that scale. Each paper gains one entry per dot size (grid from the table above; offsets recomputed so the image is centred and its edges fall on 600 dpi printer dots, as for today's pages). The PDF writer and the PNG writer place and mark the image at the dot size's resolution: 200, 100 or 66⅔ dots per inch.

Standard dots with protection None and no container is exactly a 0.2.0 printout. That combination stays available and is called "Compatible" (see the choice below).

## Behaviour

### Putting on paper

The tab gains two choices, with the page count and the "can lose" statement updating as they change:

- **Dot size:** Standard (scan at 600 dpi), Large (scan at 300 dpi), Extra large (scan at 200 dpi).
- **Protection:** None, Standard, High.
- **Compatible with optar 0.2 and the C tool:** available only with Standard dots and no protection; produces today's tagged printout.

`optar encode` gains `--dots standard|large|xlarge` and `--protect none|standard|high`, and `--compatible`.

### Identifying a scan

1. Find the page outline as today.
2. For each candidate (paper, dot size, rotation), closest shape first, locate the grid.
3. **A valid tag wins.** For a Standard-dot candidate, read the label first. A tag whose check matches makes this a 0.2.0 page, whatever its data holds. (Someone can save the stream an old tool returned and print it again as Compatible; those pages carry old headers in their data and must not be taken for version-1 pages.)
4. Otherwise decode the page. If a header copy passes its checksum, the scan is that page of that version-1 document.
5. Otherwise the 0.2.0 rules for untagged pages apply (Standard-dot candidates only).

A version-1 page is therefore identified by decoding it, which the application does anyway; the result is kept so the page is not decoded twice.

### The document

The 0.2.0 rules hold, with the header taking the tag's place: scans group by fingerprint, size, page count and protection; a scan from another document is shown and never used; one page size per document.

New for protected documents:

- A document can be **complete with pages missing**. The state shows it: "Recoverable: 1 page missing, repaired from the others."
- Page health gains a document-level line: how many bytes parity repaired, and how much of its budget the worst codeword used. The budget is counted as twice the wrong bytes at unknown places plus the bytes at known places, out of 32 or 64 ("used 18 of 32").
- Scanning a missing or poor page still improves the result, and the window says so.
- Saving runs the repair, then the fingerprint check. "Verified" means the same as today. If repair fails, the window says which pages to rescan: those contributing the most errors.

### A scan that is too coarse

From the located grid the program knows how many scan pixels cover one dot. This is advice, never a refusal: a coarse scan is still decoded, counted and used if it reads, and protection may carry it. Below 2, the scan's note says so and names the resolution to use for this page ("Scanned too coarsely for this page: about 200 dpi, needs 600"). When no grid is found at all and the image is smaller than any supported page at 2 pixels per dot, the same message is given from the image size alone.

### Command line

`optar decode` recognises version-1 pages from their headers, takes them in any order, repairs, trims and verifies, and exits non-zero if the fingerprint does not match. Pages without a header are handled as today.

## Structure

- `format.py`: dot sizes and the per-paper grids and offsets; parity sizes.
- New library modules, Qt-free: Reed-Solomon over GF(256) with errors and erasures; the container (header, body layout, spreading, wrap and unwrap).
- `identify.py`: the header route before the label route.
- `pdf.py`, `imageio.py`: print scale.
- `optar_gui/document.py`: grouping by header, the recoverable state, repair results. `work.py`: repair in the save job. `text.py`: new strings. `write_tab.py`: the two choices.

## Testing

- **Reed-Solomon:** known-answer vectors; random errors and erasures up to and just past the limit; a codeword past the limit is reported, never miscorrected silently into a "verified" file (the fingerprint test covers the whole path).
- **Container:** round trip for every paper, dot size and protection; spreading property (each codeword has exactly one byte per slice); header copies, a damaged copy, disagreeing copies.
- **Simulated scans** (the harness behind the Evidence table, made a test fixture): Large dots at 300 and 200 dpi, Extra large at 200 dpi, Standard at 300 and 250 dpi with Standard protection. These are the project's claims and each gets a test. The two Standard-dot cases are below 2 pixels per dot: they carry the coarse-scan note and still verify.
- **A reprinted stream:** the stream of a version-1 document printed as Compatible is identified as a 0.2.0 page.
- **Damage:** a blanked region, a missing page within the limit, a missing page past it.
- **Old printouts:** the existing 0.2.0 tests pass unchanged; golden fixtures unchanged.
- **C comparison:** existing tests unchanged. A larger-dot page compared against C tools built with that grid size, if the build can be given the grid without editing the C sources; otherwise this stays untested and is said so.
- **Application:** off-screen tests for the choices, the recoverable state, the coarse-scan message.
- **Real scans:** the owner's ADS-1100W. See Acceptance.

## Acceptance

What the owner's scanner app produces is not known beyond the first three scans (about 200 dpi), so acceptance covers both sizes:

- **Big dots, Standard protection,** scanned with the ADS-1100W at 200 dpi and at 300 dpi: the application shows Verified. This one must pass.
- **Medium dots, Standard protection,** at 300 dpi: must pass; at 200 dpi the result is recorded.
- **A lost page:** a document of 12 pages or more with one page left out shows Verified.

Scans that fail are kept by the owner outside the repository (owner's decision: real scans are not committed); they are measured in place, and the work is not done until they read or the claim is withdrawn.

## Risks

- **Real scans are worse than simulated ones.** The owner's scans had 44 gray levels: the app sharpens toward black and white. Larger dots tolerate that better than fine ones, but nothing here has been proven on paper. Acceptance is the proof.
- **Sheet-fed stretching.** Rollers stretch the image unevenly. The decoder follows the cross grid, and larger dots make each cross larger in scan pixels, but the 200 dpi case leaves only 2–3 pixels per dot of slack.
- **Locating a page with the wrong grid size.** Candidates are tried in turn; a wrong one must fail quickly and must never produce a header that passes. The header checksum is the guard; its length must make a false pass negligible.
- **Golay miscorrection.** Below 2 pixels per dot Golay returns wrong bytes without flagging them. Parity treats those as errors at unknown places, which cost twice as much as flagged ones. The table's limits already assume this.
- **Memory and time.** Parity spans the document, so repair holds the whole stream. A 9,999-page Standard-dot document is 2 GB. A size limit for protected documents, or repair in pieces, is needed.
- **Paper cost.** Extra large dots with High protection is about 15 kB per A4 page. The window must show the page count before the user commits.

## Left to the builder

- The exact header layout, its length, the number of copies and where they sit.
- The Reed-Solomon implementation and how it is vectorised.
- How the last, shorter codewords and the padding are laid out.
- The order candidates are tried in and how wrong ones are rejected early.
- The limit on the size of a protected document, chosen from measurement.
- Offsets for the new grids, exact wording, option names.

## Calls made by the author, not the owner

- Dot sizes are whole numbers of 600 dpi printer dots: 3 (Standard, today's), 4 (Medium), 5 (Big), 6 (Large) and 9 (Extra large); cell pitch and grid rules are unchanged. Medium and Big were added at the owner's request (2026-11-16) for more capacity per page at in-between scan resolutions; wherever this document lists three sizes, all five are offered. Advised scan resolutions: 600, 450, 360, 300, 200 dpi.
- Parity is Reed-Solomon over 255-byte codewords with 32 or 64 parity bytes.
- Losing a page is not a separate protection level; the window states what the chosen level allows for the document at hand.
- Larger-dot pages and protected pages always use the container; the label tag is dropped on them.
- The file name travels inside the protected body, not only in the label.
- The fingerprint in the header is longer than the 8 hexadecimal digits printed today.
- The default for new printouts is Standard dots, Standard protection (container). "Compatible" is opt-in. **The owner may prefer the reverse**: it decides whether a default printout can be read by 0.2.0.
- `optar decode` learns to read version-1 documents in this project.
- The coarse-scan message is part of this project.
- The new default applies to the window. `optar encode` without the new options keeps producing a 0.2.0-compatible printout, so existing scripts do not change; `--dots` or `--protect` selects the container.
- `optar decode` writes a version-1 file only when it verifies, unless `--force` is given.
- A valid label tag wins over a header found in the data.
- The coarse-scan message is advice; a coarse scan that reads is used.
- The window promises a lost page only with a quarter of the budget to spare.
- Acceptance is on the owner's scanner, with Extra large dots as the case that must pass.
- Version 0.3.0.
