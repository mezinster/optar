# Optar GUI: design

Date: 2026-11-15
Status: awaiting approval

## Intent

Optar 0.1.0 has a library and a command line. The owner wants a graphical application, "flexible and cross-platform", as the next product on the shelf.

The window is for both jobs, but **mostly for getting a file back from paper**: adding scans, seeing the health of each page, finding out why a page is bad, and replacing it. Making the PDF is a small second tab.

One capability does not exist yet and is central to the design: the program cannot tell which scan is which page. The command line goes by file names, and pages assembled in the wrong order give a corrupt file with no warning. This project makes each scan identify itself by reading the label printed at the bottom of the page.

## Goals

- A desktop application, `optar-gui`, for Windows, macOS and Linux.
- Reading from paper:
  - Add scans by file dialog or drag and drop, in any order and any orientation.
  - Each scan identifies itself from its printed label: paper size, page number, total pages, name.
  - A page list showing the health of every page of the document, including pages not scanned yet.
  - A large, zoomable preview of the selected scan with the damaged places marked on it.
  - Replace one page with a new scan without redoing the others.
  - Save the recovered file, with a clear warning if it is incomplete.
- Putting on paper: choose a file and a paper size, get the print-ready PDF.
- **A document tag in the label** (owner's decision): printouts made by the new tools carry the file's exact size and a short fingerprint of its contents. With it, pages from different printouts cannot be mixed, the recovered file is cut to its true size (no zero padding), and the window can state that the file was recovered intact.
- The window never freezes while pages are being processed.
- Published with each release as a separate download next to the command-line tool.

## Non-goals (this project)

- Driving a scanner. Scans arrive as image files.
- Custom page formats in the window. It supports the A4 and US Letter presets; `--format` stays a command-line feature.
- Any change to the page data or its layout. The format string, error correction and bit layout stay as they are, and the C tools still read these pages. Only the free-text part of the label gains a tag. Printouts without a tag are still padded with zeros to a whole page.
- Saving and reopening a session, translations, automatic updates, code signing or notarisation.
- Label reading in `optar decode`. The command line still goes by file names and still pads its output; trimming and verifying there is a natural follow-up. (`optar encode` does change: it adds the tag. See "The document tag".)

## Anti-goals

- **Qt reaching into the library.** Nothing under `src/optar` may import Qt. The command-line executable must not grow.
- **Logic in widgets.** Deciding which scan is which page, which duplicate wins, and what the document's health is must live in plain Python that can be tested without a window.
- **Work on the interface thread.** A page takes seconds to decode; the window must stay responsive and closable throughout.
- **Silent assembly.** The application must never put a scan into a document it cannot show belongs there, and must never save an incomplete file without saying so.
- **Retuning the decoder.** Its algorithm and constants stay as they are.

## Constraints

- Python 3.10+, GPL-2.0, same repository, test-first.
- Qt through PySide6 (LGPL, compatible). PySide6 is an optional extra (`pip install 'optar[gui]'`); the library's own dependencies stay numpy and Pillow.
- The C sources remain the untouched test reference.
- Work lands on `mezinster/optar` only.

## Approaches considered

### What to build the window with

- **Qt through PySide6 (chosen by the owner).** A real desktop window on all three systems, with a ready-made view for zooming and panning a large image and drawing on top of it, drag and drop, and native file dialogs. Cost: size. The PySide6 essentials package alone is 84 MB compressed.
- **Tkinter.** Ships with Python and adds nothing to the download, but has no image viewer suited to a 35-megapixel scan, needs an add-on for drag and drop, and looks dated.
- **A local web page.** Easy zoom and overlays and almost no download cost, but it is a browser tab, not an application, and every scan would have to be uploaded to a local server.

### How the window knows which scan is which page

- **Read the printed label (chosen by the owner).** The label is drawn in a known fixed font at a known place, so it can be read by matching characters. Scans sort themselves, the paper is detected, missing and foreign pages can be shown. Cost: a new library feature with its own tests, and a fallback for unreadable labels.
- **Trust file order.** Far less work, but no "missing" state, no mix-up warnings, and the user picks the paper.

A throwaway experiment (not kept) read the label correctly from every synthetic test scan: clean at two scales, rotated, blurred, noisy, speckled, with flipped pixels, and all combined, on A4 and Letter. The worst character match was 98.4%, and it added about one second per page. That is evidence for synthetic images only; real toner and paper are untested.

### The window's shape

Three layouts were shown as mockups. The owner chose **A: a page list with a large preview**, over a thumbnail contact sheet and a three-step wizard.

## The window

```
+--------------------------------------------------------------------------+
| [ Read from paper ]  [ Put on paper ]                                    |
+---------------------------+----------------------------------------------+
| holiday-photos.tar        |                                              |
| A4 · 5 pages              |                                              |
|                           |          scan of page 4, zoomable            |
|  Page 1   Good            |          damaged places marked in red        |
|  Page 2   Repaired · 198  |                                              |
|  Page 3   Good            |                                              |
| >Page 4   Damaged · 37    +----------------------------------------------+
|  Page 5   Missing         | Page 4 of 5 · scan_0004.png                  |
|                           | 133,182 blocks · 512 repaired · 37 lost      |
|  Not part of this file:   | [ Replace scan… ]  [ Remove ]                |
|   scan_0009.png (other)   |                                              |
|                           |                                              |
| [ + Add scans ]           |                                              |
+---------------------------+----------------------------------------------+
| 3 of 5 pages good · 1 damaged · 1 missing            [ Save file… ]      |
|   (when all pages are good:  "Verified · 2,481,152 bytes")               |
+--------------------------------------------------------------------------+
```

The second tab:

```
+--------------------------------------------------------------------------+
| [ Read from paper ]  [ Put on paper ]                                    |
+--------------------------------------------------------------------------+
|  File:   [ /home/me/holiday-photos.tar            ] [ Choose… ]          |
|  Paper:  (•) A4   ( ) US Letter                                          |
|  Name:   [ holiday-photos.tar ]                                          |
|  Prints as:  [2481152:3f9a2c1b] holiday-photos.tar                       |
|                                                                          |
|  12 pages · 2.4 MB                                                       |
|                                                                          |
|  [ Create PDF… ]                                                         |
|                                                                          |
|  Print at actual size (100%), not "fit to page".                         |
+--------------------------------------------------------------------------+
```

Wording in these sketches is indicative. The states, the information shown and the actions are the requirement.

## Behaviour

### Identifying a scan

For each added image the application works out, without asking:

1. **Portrait first.** The decoder cannot find the corners of an image that is wider than it is tall (inherited from C and kept). So a landscape image is turned by 90° before anything else; both 90° and 270° are then candidates.
2. **Paper.** Levels, dirt removal and corner finding need no format. Find the page outline, compare its width-to-height ratio with the presets (A4 0.690, Letter 0.760), and try the closest first.
3. **Orientation.** If the label does not read, try the scan turned by 180° (for a landscape original, the other quarter turn). The first orientation whose label reads wins.
4. **Identity.** From the label: the format string, page number, total pages and name. The format string read from the paper must equal the preset's own; if not, the scan is not identified.

A scan that cannot be identified in any orientation with either paper is shown as **Not readable**, with the reason (no page outline found, or label unreadable).

**Assigning a page by hand.** The user can give a Not readable scan a page number. Without a label there is no orientation, so the application decodes it in each candidate orientation and keeps the one with the fewest unrecoverable blocks. It uses the document's paper. If no document exists yet (no scan has been identified), the user starts one by hand: paper (pre-selected from the outline's shape) and total pages.

### What the label actually contains

The reader must match what is printed, which is not the full text the encoder builds:

- The band is one cross pitch below the last row of crosses, white glyphs on black. A 265-pixel logo fills its left end; the text starts after it. Reading it means extending the page grid one pitch past its last row, which the existing sampling code already permits.
- Only as many characters as fit on the page are printed: 98 on A4 and 101 on Letter, including the leading spaces, format string and page numbers. A longer name is cut.
- The name's visible length varies from page to page, because "9/12" is one character shorter than "10/12". **Names are compared over their shortest common length**, never exactly.
- Characters outside the font (anything but printable ASCII) are not printed at all, and trailing spaces cannot be seen. "отпуск.tar" prints as ".tar".
- An empty file prints one page labelled `1/0`. The application treats a total of 0 as a one-page document.

### The document tag

**Form.** `[SIZE:FINGERPRINT:CC]`, where SIZE is the file's length in bytes in decimal, FINGERPRINT is the first 8 hexadecimal digits of the SHA-256 of its contents, and CC is a per-page check: the first 2 lower-case hexadecimal digits of the SHA-256 of the ASCII text `SIZE:FINGERPRINT:PAGE/TOTAL`. Example label: `[2481152:3f9a2c1b:7e] holiday-photos.tar`. The two-field form `[SIZE:FINGERPRINT]` is not a tag (it was never released); text of that form is just a name.

- The check covers the size, the fingerprint, the page number and the total pages, and is computed for each page, so it differs from page to page of one printout.
- **Why it is there.** The label is read back by character matching, and no confidence measure fully separates a correct reading from a misread one. The dangerous misread turns one digit into another, because the result is still well-formed: a page number misread this way would put the page in the wrong slot of the right document, and only the final fingerprint would notice, with nothing pointing at the bad page. With the check, a misread label is caught when the scan is identified: a label whose check does not match its own size, fingerprint, page and total is treated exactly like an unreadable label. An accidental misread passes the check about 1 time in 256.
- The tag comes **before** the name, so that when the label is too long for the page it is the name that is cut, never the tag.
- It costs at most 25 of the 66 to 72 characters available to the name on A4 (3 more than without the check). The tag is never cut for any page number up to 9999 on A4 or Letter; in the worst case (page 9999/9999 of a file with a 10-digit size) 41 characters remain for the name on A4 and 44 on Letter.
- It uses only digits, the letters a to f, brackets and colons, all of which are in the label font.

**Writing it.** A library function makes the tag from the file's contents. The window's "Put on paper" tab always adds it. `optar encode` adds it by default and gains `--no-tag` to leave it out. Because each page's check differs, the encoder accepts the label either as text or as a function of the page number and total that returns each page's text; pages produced with the same label text are still byte-identical to the C encoder's.

**Using it.** When a scan's label carries a valid tag (well-formed, fitting the page count and with the right check for the page number and total read):

- The document's identity is the format string, the total pages and the tag. The name is shown but not used for matching.
- A tag is valid only if its size fits the page count: more than `(total - 1)` pages' worth of bytes and at most `total` pages' worth. Otherwise the scan is treated as not identified.
- When every page is present and has no unrecoverable blocks, the recovered data is cut to SIZE and its fingerprint is computed. The window then shows one of two results: **Verified** (the recovered file matches the fingerprint printed on the paper) or **Does not match** (the pages decoded without reported loss, but the result is not the original; this catches the rare block that error correction "repaired" into the wrong value).
- If any page is missing, damaged or unreadable, the file cannot be verified, and the window says so.
- The saved file is cut to SIZE.

**Without a tag** (printouts made by optar 0.1.0 or the C tool): identity is the format string, the total pages and the name compared over its shortest common length. The window shows a standing caution that these pages carry no tag, so it cannot confirm they belong to the same printout or that the file is complete, and the saved file is padded with zeros.

A fingerprint of 8 hexadecimal digits is 32 bits. Two different files share one by chance about once in four billion; that is ample for telling printouts apart and for catching decoding errors, and it is not protection against deliberate tampering.

### The document

- The document is defined by the first identified scan **in the order the scans were added**, not the order in which background work happens to finish, so the result is the same every time.
- A later scan with the same identity goes into its page slot.
- A scan with a different identity is listed under "Not part of this file", grouped with others of the same identity, with what it says it is. It is never decoded into the document. The user can switch to one of those groups, which then becomes the document.
- If two scans claim the same page, the better one is kept (fewer unrecoverable blocks, then fewer repaired) and the other is listed as a spare. The user can switch.
- "Replace scan…" on a page adds a new scan and makes it the one in use for that page if it identifies as that page; if it identifies as something else, the user is told and nothing is replaced.
- Removing the last scan of a document clears it; the earliest-added remaining group, if any, becomes the document.

### Page health

| State | Meaning |
|---|---|
| Good | Every block read correctly with nothing to repair. |
| Repaired | Errors were found and all were corrected. The number of repaired blocks is shown. |
| Damaged | Some blocks could not be recovered. The number is shown. |
| Not readable | The scan could not be identified or decoded. |
| Missing | The document says this page exists, but no scan of it has been added. |

The document as a whole has its own state, shown in the bottom bar: incomplete (with counts), complete but unverifiable (no tag), **Verified**, or **Does not match**.

A "block" is one error-correction codeword. The detail area also shows how many blocks needed one, two or three bits corrected, since a page with many three-bit repairs is close to failing.

### Marking damage on the preview

The page's error correction is interleaved: the bits of one block are spread across the whole page. So damage is marked **per bit**: every bit that error correction changed is drawn at its place on the scan. A stain or crease shows up as a cluster. Blocks that could not be recovered have no known wrong bits; their count is shown in text, and the cluster of corrected bits around them shows where to look. (The positions come from comparing each received block with its corrected form. A block with five or more wrong bits can be "corrected" into the wrong value without the decoder knowing; that is a property of the code. With a document tag, the fingerprint check catches it for the file as a whole.)

### Saving

- "Save file…" is available once at least one page has been decoded. The suggested name is the name from the label, or `recovered.bin` when the label carries none.
- With a tag, the saved file is cut to its true size. Without one, it is padded with zeros to a whole page, as now.
- If the document is Verified, saving needs no confirmation. If it is "Does not match", the confirmation says so plainly.
- If any page is missing, damaged or unreadable, a confirmation says exactly which pages and that the saved file will be incomplete. A missing or unreadable page contributes zero bits, so the pages after it stay at their right positions in the file.
- The file is written through a temporary file and moved into place, as the command line does, so a failed save never damages an existing file.

### Putting on paper

Choose or drop a file; choose A4 or Letter; the label defaults to the file's name; the page count is shown before anything is written; "Create PDF…" asks where to save. The tab shows the label **exactly as it will print** and warns when characters will be dropped or the name will be cut, because the printed name is what identifies the pages later. Errors (too many pages, cannot write) are shown in the window. The same checks as the command line apply.

### Responsiveness

- Identification and decoding run on background workers, more than one page at a time where the machine has the cores and memory.
- Each page shows its own progress state (waiting, working, done).
- Closing the window or removing a scan while it is being processed cancels cleanly.
- Memory: a decoded page keeps only its recovered data packed into bytes (about 200 KB for A4), its statistics and the positions of corrected bits. Both presets hold a whole number of bytes per page, so pages never share a byte and the application can assemble them itself, including gaps. Only the selected scan's image is held for the preview.

## Structure

```
src/optar/                 library (no Qt)
    label.py               reading and parsing the printed label          NEW
    tag.py                 making, parsing and checking the document tag  NEW
    identify.py            paper, orientation and identity of a scan      NEW
    fileio.py              write-through-temporary-file helper            MOVED from cli.py
    decoder/               per-bit correction detail and the page grid    EXTENDED
    imageio.py             safe for use from several threads              FIXED
src/optar_gui/             the application (imports optar and PySide6)
    document.py            which scan is which page, duplicates, health   no Qt
    jobs.py                background identification and decoding
    main_window.py, read_tab.py, write_tab.py, preview.py, ...
    __main__.py            entry point `optar-gui`
```

### Library additions

These are useful without the window and are tested on their own.

1. **Label reading.** Given a scan and a page format, return the label's text and a confidence figure; parse the text into format string, page number, total pages and name. Reading uses the page grid the decoder already finds, the same pixel sampling, and the glyph bitmaps the encoder draws with.
2. **Scan identification.** Given a scan, return its paper preset, the rotation needed, and the parsed label, or a reason it could not be identified.
3. **Decode detail.** On request, `decode_page` also returns the channel positions of every bit that error correction changed, the indices of unrecoverable blocks, and the page grid needed to map a page position to a scan pixel. The default result and its cost are unchanged.
4. **Thread safety of scan loading.** `read_scan` currently changes a Pillow setting for the whole process while it runs. It must be safe to call from several threads at once.
5. **Document tag.** Make a tag from file contents; parse a label's free text into tag, check and name; check a tag against a page count and its check against the page number and total; verify recovered data against a tag.
6. **`optar encode` adds the tag** by default, with `--no-tag` to omit it. Its tests, the README and the release smoke script are updated to match.
7. **Shared safe-write helper.** The temporary-file-and-replace logic moves from `cli.py` to the library so the window uses the same code. The command line's behaviour does not change.

### The application

- **`document.py` holds the rules** in plain Python with no Qt: given scan identities and decode results, which scan fills which page, which is a spare, which is foreign, each page's health, and the document summary. It is the most heavily tested part.
- **Jobs** run library calls on background workers and report back to the interface thread. A job can be cancelled.
- **Widgets** display the document and send user actions to it. They contain no rules.
- **A hidden self-test mode** (`optar-gui --self-test`) runs an encode and a decode through the application's own job and document code without showing a window, and exits 0 or 1. The release workflow uses it to smoke-test each built executable.

## Testing

- **Library additions:** unit tests, plus label reading and identification over the existing set of degraded scans (rotated, blurred, noisy, speckled, flipped pixels, combined), both papers, all four orientations, and scans that are not optar pages. Decode detail is checked by damaging known bits in a synthetic scan and asserting those positions come back.
- **Document tag:** making and parsing; size limits against page counts; a full round trip that ends Verified with a file of the exact original length; a deliberately altered page that ends "Does not match"; a tag misread by one character treated as a different document.
- **Document rules:** table-driven tests with no Qt: ordering, duplicates, foreign scans, missing pages, replacement, manual assignment, removal, tagged and untagged documents, two printouts with the same name and page count but different tags kept apart.
- **Application:** tests with Qt's off-screen mode covering the main flows: add scans and see the list fill, select a page, replace a scan, save with and without missing pages, create a PDF. They assert on the document and on what the widgets show, not on pixels.
- **CI:** the application tests run on Linux, macOS and Windows. The existing jobs keep working without PySide6 installed.
- **Release:** each built `optar-gui` executable must pass `--self-test`.

## Packaging

- Version 0.2.0.
- `release.yml` builds and publishes `optar-gui-<tag>-<platform>` beside the three command-line executables.
- Each download must start by double-click on its platform. What form that takes on macOS (a zipped `.app` is the usual answer) is the builder's to settle and verify.

## Risks

- **Label reading on real scans is unproven.** Toner spread and paper texture may confuse character matching in ways synthetic images do not. Manual page assignment is the fallback, and a real scan in `tests/scans/` would cover both this and decoding.
- **A misread tag character makes a real page look foreign.** The tag has no redundancy of its own. The user can still assign such a scan by hand, and the final fingerprint check then confirms or refutes the choice. How to make tag reading robust (for example, accepting the reading that most pages agree on) is the builder's to design from tests.
- **Download size.** Expect well over 100 MB per platform.
- **macOS and Windows packaging of a Qt application** has never been tried in this project and is the most likely source of release failures. Unsigned applications trigger warnings on both.
- **Off-screen Qt tests on three operating systems in CI** may need platform packages or settings found only by running them.
- **Memory with parallel decoding.** Decoding a 1200 dpi scan peaks above 1 GB. The number of pages processed at once must respect that.

## Left to the builder

- Widget structure, names and exact wording.
- How background work is organised in Qt, and how many pages run at once.
- How the preview draws many marks efficiently.
- The exact shape of the new library functions and result types.
- Confidence thresholds for label reading, chosen from tests.
- Application icon and window details.

## Calls made by the author, not the owner

- The window supports only the A4 and Letter presets.
- Scans in any orientation are accepted and rotated automatically.
- Duplicates: the better scan is used, the other kept as a spare.
- The document is the first identified scan in the order added; the user can switch to another group.
- Names are compared over their shortest common length.
- A scan with no readable label can be assigned by hand; its orientation is chosen by fewest unrecoverable blocks.
- With no identified scan at all, the user can start a document by hand (paper and total pages).
- A page labelled `1/0` (an empty file) is a one-page document.
- The "Put on paper" tab shows the label as it will print and warns about dropped or cut characters.
- The suggested save name falls back to `recovered.bin`.
- A scan from a different document is shown but never used.
- Saving an incomplete file is allowed after an explicit confirmation; missing pages become zeros.
- Damage is marked per corrected bit, not per block.
- The application is a separate package (`optar_gui`) in the same repository and a separate download.
- The label-reading and identification code goes in the library, not the application.
- The tag is `[SIZE:FINGERPRINT]` with 8 hexadecimal digits of SHA-256, placed before the name.
- After review, the tag gained a per-page check code, `[SIZE:FINGERPRINT:CC]`, so that a misread label is caught when the scan is identified.
- `optar encode` adds the tag by default (`--no-tag` omits it); `optar decode` is not changed in this project.
- Untagged printouts still work, with a standing caution and zero padding.
- Version 0.2.0.
