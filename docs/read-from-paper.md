# Read it back

## Scanning

- Scan in grayscale (256 levels) or in colour. Do not scan in black and
  white.
- Turn off any "document" or text clean-up. It turns the dots black or white
  before the program sees them.
- Use the resolution for the dot size: 600 dpi for Standard dots, where
  1200 dpi is slightly better. The others are in the
  [dot size table](put-on-paper.md#dot-size).
- Save PNG or TIFF. The application also accepts BMP, PGM/PPM and JPEG. JPEG
  is lossy and a poor choice. Do not save the pages as one PDF.
- Clean the scanner glass, and press the page flat: a lid that does not press
  the paper down leaves blurry spots.

A scan made at too low a resolution gets a note that names the resolution to
use. This is advice only: a coarse scan that can be read is still used, and
one that the ordinary reader cannot read is given to a
[second, slower reader](slower-reader.md).

## In the application

Open the tab "Read from paper" and add the scans of the pages ("+ Add scans…",
or drop files or folders on the tab).

The program finds out for itself which page each scan is, which paper it is
and which way up it is. So the scans can be added in any order, upside down or
turned sideways. It also works out the dot size and the protection; there is
nothing to set.

![Scans being read, each with a progress bar and its step](img/being-read.png)

The list shows one row per page with its state. Selecting a row shows the scan
with the damaged places marked: wheel to zoom, drag to move, double-click to
fit the page.

When the bar at the bottom says the file is verified, "Save file…" writes it.

From the list you can:

- remove a scan;
- replace the scan of a page, or use a spare scan of that page instead of the
  one in use;
- switch to another document, if the scans you added belong to more than one
  printout;
- assign a scan that could not be identified to a page by hand;
- start a document by hand, when no scan can be identified: you give the paper
  and the number of pages, then assign each scan to its page.

## While a scan is being read

Every scan you add is listed under "Being read" until it has been read, with a
progress bar and the step it is at:

| Step | What happens |
|---|---|
| Waiting | The scan waits for its turn. |
| Opening the file | The image is loaded. |
| Finding the page | The program looks for the outline of a page. |
| Identifying the page | It tries each paper, dot size and orientation until one fits. |
| Reading the data | The dots are read and corrected. |
| Slower reader: sampling, then "pass 4 of 5" | Only for a scan the [slower reader](slower-reader.md) takes on. |

The bar counts steps, not seconds: it can rest on a step and then jump, but it
never moves back. "Remove" stops reading the scan. Once read, the scan becomes
its page, or is listed as not readable.

## Page states

| State | Meaning | What to do |
|---|---|---|
| Good | The page was read without any error to correct. | Nothing. |
| Repaired · N | N blocks were damaged and the error correction repaired them. The data is intact. | Nothing. |
| Damaged · N lost | N blocks could not be repaired, so the saved file has wrong data there. | Rescan the page in grayscale at the resolution for its dot size, and replace the scan. |
| Read by the slower reader | The scan was too coarse for the ordinary reader. See [Scans that are too coarse](slower-reader.md). | Check that the document verifies. |
| Not readable | The scan could not be identified: for example there is no optar page in the image, or the label could not be read. | Rescan it, or assign it to a page by hand. |
| Missing | No scan of this page has been added. | Add one. In a protected document the other pages may still be enough, and the bar then says so. |

A scan made below 400 dpi that cannot be read says so, for example "Scanned at
about 200 dpi, which is too coarse to read", with the resolution each dot size
needs.

## The bar at the bottom

The bar shows the state of the whole document.

| The bar says | Meaning |
|---|---|
| Verified · N bytes | All pages were read, and the recovered file matches the fingerprint on the paper. |
| Does not match the fingerprint on the paper | All pages were read, but the file is not the original, because some data was decoded wrongly. Rescan the pages, starting with those marked Repaired. |
| Recoverable: page 3 missing, can be repaired from the others | A protected document: pages are missing, but the pages that were read should be enough to rebuild them. |
| Recoverable: page 3 missing, repaired from the others · matches the fingerprint | That repair has been done and checked. The size and what the repair did follow. |
| Working… 3 of 6 scans read | Scans are still being read. When the document already has a state to show, the count follows it: "Verified · N bytes · 3 of 6 scans read". |
| Checking the fingerprint… | The check is running in the background. |
| All N pages read · cannot be verified (no tag) | The pages come from an old program and carry no fingerprint. |
| 4 of 6 pages good · 1 damaged · 1 missing | Otherwise, a count. |

For a protected document the window also shows how many bytes the protection
repaired and how much of its repair capacity the worst place used, for example
"the worst spot used 18 of 32 of its repair capacity". If the repair fails, it
names the pages to add or rescan.

!!! info "What "verified" means"
    "Verified" always means that the fingerprint of the recovered file matched
    the one on the paper. It never means only that the repair reported no
    failure.

## Saving

"Save file…" asks for confirmation when the file is not verified, and says
what is wrong with it.

A protected document that could not be repaired can still be saved as far as
it was recovered, after a warning that the file may contain wrong parts. This
is possible only when at least half of its pages were read: from fewer,
nothing is saved.

## Printouts from old programs

Printouts from optar 0.1.0 or from the C tool have no tag in their label. The
application reads them, but:

- it cannot tell whether the pages belong together or whether the file is
  complete;
- it cannot verify the file;
- the saved file is padded with zeros to a whole page.

Save such a file only after reading the caution the application shows.
