Twibright Optar
===============

[![CI](https://github.com/mezinster/optar/actions/workflows/ci.yml/badge.svg)](https://github.com/mezinster/optar/actions/workflows/ci.yml)

_**Special note:** The repository of optar at http://github.com/colindean/optar 
exists because I (@colindean) had difficulties finding the source and it seemed
to be abandoned/dormant. I've made slight improvements over time. Improvements
welcomed as pull requests._

This is a program to store data on paper using a 600 dpi black and white laser
printer and a scanner. With the original dot size the scanner must do 600 dpi
or more. From 0.3.0 the dots can be printed larger, so that a 200 dpi scanner
is enough (see "Dot size and protection" below), and the pages can carry extra
data that repairs damage and even a lost page.

The page format is defined by [docs/format.md](docs/format.md) and by the
conformance vectors in `tests/vectors`. The original C program, kept in
`lega-c`, is where the format comes from; see "History" at the end.

Desktop application
-------------------

From 0.2.0 the Python port also comes with `optar-gui`, a desktop application
with two tabs.

**Put on paper.** Choose a file or drop it on the tab, pick A4 or US Letter
and give the file a name. Then choose the dot size and the protection (see
"Dot size and protection" below). The window starts with Standard dots and
Standard protection. The line "Prints as:" shows the text that will be
printed on each page, and a second line shows how many pages the file needs
and, with protection, how many of those pages can be lost. Ticking "Compatible
with optar 0.2 and the original optar" makes the printout 0.2.0 made, with
Standard dots and no protection. "Create PDF…" saves the PDF. Print it at actual size
(100%), not "fit to page", on a 600 dpi laser printer.

**Read from paper.** Add the scans of the pages ("+ Add scans…", or drop
files or folders on the tab). The program finds out for itself which page each
scan is, which paper it is and which way up it is, so the scans can be added
in any order, upside down or turned sideways. The list shows one row per page
with its state, and a preview of the selected scan with the damaged places
marked (wheel to zoom, drag to move, double-click to fit the page). When the
pages are good, "Save file…" writes the recovered file. The
program works out the dot size and the protection of a printout from the
scans; there is nothing to set. A scan made at too low a resolution for its
page gets a note that names the resolution to use. This is advice only: a
coarse scan that can be read is still used.

From the list you can:

- remove a scan;
- replace the scan of a page, or use a spare scan of that page instead of the
  one in use;
- switch to another document, if the scans you added belong to more than one
  printout;
- assign a scan that could not be identified to a page by hand;
- start a document by hand, when no scan can be identified: you give the paper
  and the number of pages, then assign each scan to its page.

### Installing the application

From 0.2.0, download the file for your system from the GitHub Releases page of
`mezinster/optar`:

- Linux: `optar-gui-<tag>-linux-x86_64`
- macOS (Apple silicon): `optar-gui-<tag>-macos-arm64.zip`
- Windows: `optar-gui-<tag>-windows-x86_64.exe`

On Linux, run `chmod +x` on the file first (this applies to the Linux files
and to the macOS command-line file, not to the zipped application). The
programs are unsigned, so macOS and Windows may warn on first run. On macOS,
unzip the application and try to open it; if macOS refuses, open System
Settings, Privacy & Security, and choose "Open Anyway" (on older macOS
versions, right-click the application and choose Open). The macOS and
Windows builds have not yet run in CI.

Or install from source, from a checkout of the repository (Python 3.12 or
newer):

    pip install '.[gui]'
    optar-gui

`optar-gui --version` prints the version. `optar-gui --self-test` starts the
program without a screen and checks that it can encode and read pages.

### How a scan identifies itself

Every page has a label at the bottom: the page format, the page number and
the number of pages, then free text. The application reads this label from
the scan.

- A label with a tag is accepted when it reads plausibly, the tag's check
  matches the page number and page count, and the file size in the tag fits
  that page count.
- A label without a tag (printouts made by 0.1.0 or by the C tool) has
  nothing to check it against, so it is accepted only when it reads clearly.
- A label that looks like a tag with one damaged character is refused.

A scan that is refused is listed as "Not readable" with the reason, and you
can assign it to a page by hand.

This is how the pages of 0.2.0 and earlier printouts are identified. Pages
made with protection, or with any dot size but Standard, do not depend on the
label: they identify themselves from their data (see "Dot size and
protection" below). A valid tag in the label always wins: a page whose label
has a valid tag is read as a 0.2.0 page, whatever its data holds.

### The tag

From 0.2.0, `optar encode` and the application print a tag at the start of the
free text of every page, in the form `[SIZE:FINGERPRINT:CC]`. `SIZE` is the
size of the file in bytes, `FINGERPRINT` is the first 8 hex digits of its
SHA-256, and `CC` is a check of two hexadecimal digits that depends on the page number and the
number of pages. The tag lets the application:

- keep the pages of different printouts apart;
- refuse a tagged label whose size does not fit the page count;
- refuse a scan whose label was misread, instead of placing it on the wrong
  page (about 1 misread in 256 can still pass the check);
- cut the recovered file to its true size, so it has no zero padding;
- compare the recovered file with the fingerprint, which is the final check
  that the file is the original.

Printouts from 0.1.0 or from the C tool have no tag. The application reads
them, but it cannot tell whether the pages belong together or whether the file
is complete, it cannot verify the file, and the saved file is padded with
zeros to a whole page. Save it only after reading the caution it shows. **Pack
your data with tar if it is sensitive to this.**

To print without a tag, use `optar encode --no-tag`. Pages that identify
themselves from their data print no tag.

### Page states

Each page in the list has one of these states:

- Good: the page was read without any error to correct.
- Repaired · N: N blocks were damaged and the error correction repaired them.
  The data is intact.
- Damaged · N lost: N blocks could not be repaired, so the saved file has
  wrong data there. Rescan the page in grayscale at the resolution for its
  dot size (see "Dot size and protection"), and replace the scan.
- Not readable: the scan could not be identified (for example there is no
  optar page in the image, or the label could not be read). A scan made below
  400 dpi that cannot be read says so instead, for example "Scanned at about
  200 dpi, which is too coarse to read", with the resolution each dot size
  needs. Rescan it, or assign it to a page by hand.
- Missing: no scan of this page has been added. Add one. In a protected
  document the other pages may still be enough to recover the file, and the bar
  then says so.

While scans are still being read, a page shows "Waiting" or "Working…".

The bar at the bottom shows the state of the whole document:

- "Verified · N bytes": all pages were read, and the recovered file matches
  the fingerprint on the paper.
- "Does not match the fingerprint on the paper": all pages were read, but the
  file is not the original, because some data was decoded wrongly. Rescan
  the pages, starting with those marked Repaired.
- "Recoverable: page 3 missing, can be repaired from the others": for a
  protected document, pages are missing but the pages that were read should be
  enough to rebuild them. Once that has been done and checked, the bar says
  "Recoverable: page 3 missing, repaired from the others · matches the
  fingerprint", followed by the size and what the repair did.
- "Working…": scans are still being read.
- "Checking the fingerprint…": the check is running in the background. For
  pages that identify themselves from their data it reads "Repairing and
  checking the fingerprint…".
- "All N pages read · cannot be verified (no tag)": the pages have no tag.
- Otherwise, a count such as "4 of 6 pages good · 1 damaged · 1 missing".

For a protected document the window also shows how many bytes the protection
repaired and how much of its repair capacity the worst place used, for example
"the worst spot used 18 of 32 of its repair capacity". If the repair fails, it
names the pages to add or rescan. "Verified" always means that the fingerprint
of the recovered file matched the one on the paper. It never means only that
the repair reported no failure.

"Save file…" asks for confirmation when the file is not verified, and says
what is wrong with it. A protected document that could not be repaired can
still be saved as far as it was recovered, after a warning that the file may
contain wrong parts, but only when at least half of its pages were read: from
fewer, nothing is saved.

### Scan formats

Scan in grayscale (256 levels) or in colour, at the resolution for the dot size
(see "Dot size and protection"; 600 dpi for Standard dots, where 1200 dpi is
slightly better). Do not scan in black and white, and turn off any "document"
or text clean-up, which turns the dots black or white before the program sees
them. The application accepts PNG, TIFF, BMP, PGM/PPM and JPEG. JPEG is
accepted but is lossy and a poor choice: use PNG or TIFF, and do not save the
pages as one PDF. `optar decode` reads only files named `BASE_0001.png`,
`BASE_0002.png`, ...

### Dot size and protection

From 0.3.0 you choose two things when you put a file on paper.

**Dot size** is how large each data dot is printed. Larger dots survive a
coarser scan, but a page holds fewer of them, so it holds less. A data dot is
3, 4, 5, 6 or 9 dots of a 600 dpi printer. The table gives the scan resolution
to use (three scan pixels per data dot) and the bytes one page holds before
protection is added:

| Dot size | Option | Printer dots per data dot | Scan at | A4 page | Letter page |
|---|---|---|---|---|---|
| Standard | `standard` | 3 | 600 dpi | 199,773 | 192,591 |
| Medium | `medium` | 4 | 450 dpi | 114,904 | 110,463 |
| Big | `big` | 5 | 360 dpi | 73,027 | 69,463 |
| Large | `large` | 6 | 300 dpi | 49,119 | 48,403 |
| Extra large | `xlarge` | 9 | 200 dpi | 21,606 | 21,127 |

**Protection** is extra data, spread over all the pages of the document, with
which the program repairs damaged places and rebuilds pages that are lost. It
takes paper: Standard protection adds about 14% more pages and High about 34%.
The extra data is spread so that a stain, a torn corner or a missing page costs
every part of the file about the same small amount, and that small amount is
what the protection repairs. The choices are None, Standard and High.

The window and `optar encode` promise that a lost page can be recovered only
for documents long enough, and then say "can lose N page(s) of T". With
Standard protection that is 1 page from 12 pages and 2 pages from 24 pages.
With High protection it is 1 page from 6 pages and 2 pages from 12 pages.
Below that, damage within pages is repaired, but losing a whole page loses the
file.
The promise is deliberately cautious, and a document may recover more than it
promises.

A file whose protected printout would be more than 256 MiB on paper is refused.
The window then says whether the file would fit without protection or with
smaller dots.

The pages of a printout made with protection, or with any dot size but
Standard, carry the details of the document in their data: which printout they
belong to, their number, the number of pages, the size of the file and its
fingerprint. The label printed at the bottom is for people and is not used to
identify them. In a PDF it is printed at one size whatever the dot size (the
size of a Standard page's label), so the whole line fits; it is then too small
to be read from a coarse scan, and the window shows "(no name)" until the file
is recovered and its own name is known. PNG and PGM pages have one pixel per
dot, so their label is drawn in the page's dots and grows with them. These are called self-identifying pages here. The room such a document does not use is filled with a fixed pattern that looks like data, so every page prints evenly; 0.3.0 filled it with zeros, which printed as white lines across the pages. Both are read, by 0.3.0 too: no reader looks at the filling. They need optar
0.3 or newer to be read, and reading them needs no setting. The 0.2.0
application cannot read larger-dot pages at all. For Standard dots, 0.2.0 and
the C tool read them as pages without a tag and return the data wrapped in the
extra details and protection, not the file. To make a printout that 0.2.0 and
the C tool read, use the command line without `--dots` and `--protect`, or
tick "Compatible" in the window.

#### What has and has not been shown

The following comes from simulated scans, not from paper. The simulated blur
was fitted to three real 300 dpi scans of one printed page, made with one
printer and one sheet-fed scanner.

- At that blur Standard dots did not decode at 300 dpi.
- Medium dots with Standard protection verified at 300 dpi and at 200 dpi.
- Big, Large and Extra large dots verified at 200 dpi with no errors.
- A document of 12 pages verified with one page withheld.

What is not shown:

- No real scan of a larger-dot page has been read yet.
- Sheet-fed scanners are untested beyond the program finding the grid of dots
  on three real scans.
- Three real 300 dpi scans of one printout measured about 286 dpi, which means
  that printout came out at about 95% of actual size. Smaller dots are harder
  to read, so print at actual size (100%).

### What is not proven

- Reading labels and decoding have automated tests only on synthetic scans
  (generated images with blur, noise and rotation), not on real printed and
  scanned pages. That includes every printout with larger dots or protection
  (see "What has and has not been shown" above).
- The macOS and Windows builds of the application have not yet run in CI.

Python version
--------------

A Python port, `optar`, encodes a file into page images and decodes scans
back, in one command-line program (the desktop application above uses the same
code). It needs no C compiler, no libpng and no ImageMagick.

### Installation

Once a release is published, download the executable for your OS from the
GitHub Releases page of `mezinster/optar`: `optar-<tag>-linux-x86_64`,
`optar-<tag>-macos-arm64` or `optar-<tag>-windows-x86_64.exe`. On Linux and
macOS, run `chmod +x` on the downloaded file; the executables are unsigned, so
macOS and Windows may warn on first run.

Or install from source (Python 3.12 or newer; installs numpy and Pillow):

    pip install .

### Usage

    optar encode INPUT [-o BASE] [--paper a4|letter] [--to pdf|png|pgm] [--label TEXT] [--no-tag]
                 [--dots standard|medium|big|large|xlarge] [--protect none|standard|high]
                 [--compatible] [--format STRING]
    optar decode BASE [-o OUTPUT] [--paper a4|letter] [--format STRING] [--debug-images] [--force]
    optar --version

`encode` writes `BASE.pdf` by default (`BASE` defaults to `optar_out`), or
the pages `BASE_0001.png` (or `.pgm`), `BASE_0002.png`, ... with `--to`.

`decode` reads `BASE_0001.png`, `BASE_0002.png`, ... and writes the data to
`-o OUTPUT`, or to stdout. For printouts from 0.2.0 or earlier it does not cut
the output to the size in the tag or check the fingerprint: the output is
always zero-padded to a whole page. The desktop application does both.

For self-identifying pages (see "Dot size and protection") `decode` finds out
from the scans themselves what they are. It takes the scans in any order and
any orientation, and a scan it cannot read counts as a missing page. (It
decides from the first three scans: if none of them can be identified, it
treats the set as a printout from 0.2.0 or earlier.) It
repairs the data, cuts it to its true size and checks the fingerprint. It
writes the file only if the fingerprint matches, unless you give `--force`,
which saves what was recovered even if it did not verify. Even with `--force`
nothing is saved when fewer than half of the pages were read. The exit status
is 0 only when the file verified. For printouts from 0.2.0 or earlier `--force`
changes nothing, and `decode` says so.

From 0.2.0, `encode` prints the tag (see "The tag" above) on every page of a
compatible printout; add `--no-tag` to leave it out.

Without `--dots` and `--protect`, or with `--compatible`, `encode` makes the
printout 0.2.0 made, which 0.2.0 and the C tool read. `--dots X` alone gives
that dot size with Standard protection, and `--protect LEVEL` alone gives
Standard dots with that protection; `--protect none` asks for none. Any of
these makes self-identifying pages, which need optar 0.3 or newer. For example:

    optar encode photo.jpg -o photo --dots large --protect high

`--paper` defaults to A4 and must be the same for encode and decode of
printouts from 0.2.0 or earlier.

Exit status: 0 on success; 1 if the data was decoded but is uncorrectable or
the page numbering has a gap, or (self-identifying pages) the file did not
verify; 2 for a usage or input error.

### Printing and scanning

Print the PDF at actual size (100%), not "fit to page", on a 600 dpi laser
printer. Each data pixel is 3 x 3 printer dots with Standard dots, and larger
with the other dot sizes.

Scan in grayscale (256 levels) or colour, not black and white and without any
"document" clean-up. Save PNG or TIFF, not JPEG or PDF. Use the resolution for
the dot size (600, 450, 360, 300 or 200 dpi; see "Dot size and protection").
For a 0.2.0 or earlier printout, `optar decode` needs the page upright
(portrait, label at the bottom): landscape scans are not supported there, which
is inherited from the C decoder. For self-identifying pages `optar decode`
accepts any orientation, and the desktop application does for every printout.

The decoded output of `optar decode` for a 0.2.0 or earlier printout is
zero-padded to a whole page and the original length is not stored in the page
data (format version 0, unchanged); only the tag has it. **Pack your data with
tar if it is sensitive to this.** Self-identifying pages store the size.

### Capacity and error correction

One A4 page holds 1,598,184 bits (199,773 bytes) with the default code and
Standard dots; one Letter page holds 1,540,728 bits (192,591 bytes). Larger
dots hold less (see the table in "Dot size and protection"). With protection,
part of the pages carries the protection data, and every page repeats a short
record that says which document and which page it is, so the file gets less
than the pages hold.

The default is the Golay 24/12 code. Hamming codes of order 2 to 5 are also
supported, selected through `--format` (the sixth field of the format string).

### Compatibility with the C version

The Python encoder's pages are byte-identical to the C `optar` output for A4,
Letter and all five error-correction modes. The Python decoder's cross
positions and sampled bits are bit-identical to the C `unoptar` on the
synthetic test images. Both are checked against outputs of the C tools that
were recorded once and are kept in `tests/vectors`; the tests no longer build
or run the C tools.

Each page of a self-identifying printout is still an ordinary optar page: a C
`unoptar` built with the same grid size reads its dots exactly (recorded for
Large dots on A4 and Medium dots on Letter). What it returns is the data
with the extra details and protection wrapped around the file, not the file.

No automated test yet decodes a real print-and-scan.

### Development

    python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
    .venv/bin/pytest -q
    .venv/bin/ruff check .

No test needs a C compiler. `.venv/bin/pytest -q -m gs` checks the PDF output
with Ghostscript, and `.venv/bin/pytest -q -m slow` runs the long tests (add
`-n auto` to use every core). The `slow` marker includes the simulated-scan
tests of the claims under "What has and has not been shown":
`.venv/bin/pytest -q -m slow tests/unit/test_claims.py`.

The application's tests need PySide6 and pytest-qt (`pip install -e '.[dev,gui-dev]'`)
and are skipped without them: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q -m gui`.

Build the one-file executable and smoke-test it:

    .venv/bin/pyinstaller --onefile --name optar --collect-data optar packaging/entry.py
    python packaging/smoke.py dist/optar

History: the original C program
-------------------------------

The original C programs live in the `lega-c` folder, unchanged, and the rest
of this document describes them. They are history: the format is defined by
[docs/format.md](docs/format.md), and nothing in this project builds or runs
them any more. Run the commands below from inside `lega-c`. The C encoder is also called
`optar`: `make` builds it there as `./optar`, so run it as `./optar` to avoid
confusion with the Python command.

Building
--------

You need to install [ImageMagick](https://www.imagemagick.org) so that the 
resulting .pgm image can be converted into PostScript with the right dimensions:
each pixel must be 3x3 600dpi pixels so that there is no unnecessary jitter.

Make sure you have [libpng](http://libpng.org/pub/png/) installed. You'll know
that is is installed correctly if you type `libpng-config` on the commandline, 
there's a program which prints something. Virtually all desktop Linux distros 
and every macOS system has this installed already.

Compile with

    cd lega-c
    make

Note that there may be some hardcoded configuration values that you may need to
change, for example the page size defaults to A4 instead of US Letter. Read on
to learn where to change that.

Installing locally
------------------

It's easiest to install your local build with

    sudo make install

`optar`, `unoptar`, and `pgm2ps` installed on your system in `/usr/local/bin`. 

To uninstall, run

    sudo make uninstall

Encoding (writing)
------------------

Run

    optar other_guys.ogg other_guys.ogg

which will produce files:

```
other_guys.ogg_0001.pgm
other_guys.ogg_0002.pgm
other_guys.ogg_0003.pgm
other_guys.ogg_0004.pgm
other_guys.ogg_0005.pgm
other_guys.ogg_0006.pgm
```

Now convert them into PostScript using the included pgm2ps tool:

    pgm2ps *.pgm

Print these using a 600 dpi (or greater resolution) **laser** printer. Inkjet or
dot matrix was never tested and will not probably work at the pre-defined data 
density. See "Changing the format" below.

Please note that the file will be padded by zeroes and the original length will
be lost. **Pack your data with tar if you store data that are sensitive to
this.**

Decoding (reading)
------------------

Clean and polish the scanner glass with rubbing alcohol and paper towel. Put
yellow pages on the scanner lid to get sharper picture˚. Insert the
page so that the text on the bottom is upright. Scan the pages into
PNG (not JPEG!) on 600dpi (or 1200dpi, slightly better):

```
scan_0001.png
scan_0002.png
scan_0003.png
scan_0004.png
scan_0005.png
scan_0006.png
```

Read the number sequence (format specification) from any of the papers and feed
it as 1st argument to the optar, 2nd argument is the filename part before the
underscore:

    unoptar 0-65-93-24-3-1-2-24 scan > out.ogg

Then play out.ogg with mplayer. You should get first about 41 seconds from the
Ogg Vorbis file.

˚ In the scanner I tried (Canoscan), the lid didn't seem to be heavy enough to
press the paper down completely - there were blurry spots in the picture.
Without yellow pages I got 526 reparable bad bits bad from 3.2 million. With
yellow pages the blurry spots were much sharper and I got only 261 reparably
bad bits!

Please note the data are padded with zeroes so the original information
about file length is lost. **If your data format doesn't like this then first
pack your data with `tar`.**

A4 <-> US Letter
----------------
Change the convert parameters in pgm2ps (see comments). Change XCROSSES
and YCROSSES in optar.h (see comments). Recompile. Then you can use US Letter
instead of A4.

Changing the format
-------------------
If your printer is low quality and you are getting irreparable bits, you can
try to format the media to lower capacity.  Unfortunately, setting by
commandline is not implemented yet.  Change XCROSSES and YCROSSES in optar.h to
lower values which yields bigger pixels and lower capacity per page, but higher
reliability.  Make sure they are in roughly the same proportion as before,
otherwise you get nonsquare pixels and unnecessary waste of channel capacity.

You can also change the decoding parameters in unoptar.c (look for MAGIC
CONSTANTS) in attempt to read a difficult recording: unsharp_mask,
unsharp_dist, sync_white_cut, white_cut, minmax_filter, pixel_blur, cross_trim.

Future improvement
------------------
- manpage could be written for optar and unoptar
- commandline help (-h) could be written for optar and unoptar
- the format could be made configurable. Now it's stored in the optar.h
- the magic constants could be changed by commandline options. Now they are
  stored in unoptar.c.
- Golay code decoding could be rewritten faster, using a sophisticated
  algorithm (Kasami algorithm?)
- Easy support for multiple pages per page, so it can be read by a digital
  camera. Currently it cannot since digital camera blurs at the sides of
  the picture.

Authorship and Licensing
------------------------

© GPL 2007 Karel 'Clock' Kulhavy of Twibright Labs. 

See COPYING for the text of the GPL license.

e-mail: clock (at) twibright (dot) com

Twibright Optar homepage: http://ronja.twibright.com/optar/

Improvements © 2012-2018 Colin Dean

