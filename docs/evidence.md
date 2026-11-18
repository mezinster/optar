# What has and has not been shown

This page says what the project's claims rest on. Most of it comes from
simulated scans, not from paper.

## Simulated scans

The automated tests read generated images with blur, noise and rotation. The
simulated blur was fitted to three real 300 dpi scans of one printed page,
made with one printer and one sheet-fed scanner.

- At that blur Standard dots did not decode at 300 dpi with the ordinary
  reader.
- Medium dots with Standard protection verified at 300 dpi and at 200 dpi.
- Big, Large and Extra large dots verified at 200 dpi with no errors.
- A document of 12 pages verified with one page withheld.

## The slower reader

The [slower reader](slower-reader.md) has been shown on one real document and
one simulated one.

**Real.** The owner's document of six A4 pages, Standard dots, High
protection, scanned at about 290 dpi where 600 dpi is advised. The ordinary
reader identified none of the pages. With the slower reader the file was
recovered and verified by its fingerprint: 759,879 bytes, of which 41,495
bytes were repaired by the document's protection, the worst block using 40 of
its budget of 64. This is one document, one printer, one scanner and one
resolution. The scans are not part of the repository.

**Simulated** (`tests/unit/test_coarse_claim.py`). A two-page document of the
same kind, scanned at 290 and at 300 dpi with blur 1.8 printer dots. At
290 dpi the ordinary reader identifies neither page; at 300 dpi it reads each
page's label but no header. In both cases the file verifies with the slower
reader. At the simulator's default blur (1.0) the ordinary reader reads such a
page at 300 dpi on its own.

The simulator is milder than the owner's scanner: at 290 dpi in the simulation
the slower reader repaired nothing, where the real document needed 41,495
bytes repaired.

Standard protection has a budget of 32, below the 40 the real document's worst
block needed. So a Standard-protection document scanned like this is expected
to fail. Old 0.2-style pages are not covered by the slower reader.

## What is not shown

- No real scan of a larger-dot page has been read yet.
- Reading labels and decoding have automated tests only on synthetic scans,
  not on real printed and scanned pages. That includes every printout with
  larger dots or protection.
- Sheet-fed scanners are untested beyond the program finding the grid of dots
  on three real scans.
- Three real 300 dpi scans of one printout measured about 286 dpi, which means
  that printout came out at about 95% of actual size. Smaller dots are harder
  to read, so print at actual size (100%).
- Inkjet printers have not been tested.

## The same pages as the C program

The Python encoder's pages are byte-identical to the output of the original C
`optar` for A4, Letter and all five error-correction modes. The Python
decoder's cross positions and sampled bits are bit-identical to the C
`unoptar` on the synthetic test images. Both are checked against outputs of
the C tools that were recorded once and are kept in `tests/vectors`.

Each page of a self-identifying printout is still an ordinary optar page: a C
`unoptar` built with the same grid size reads its dots exactly (recorded for
Large dots on A4 and Medium dots on Letter). What it returns is the data with
the extra details and protection wrapped around the file, not the file.
