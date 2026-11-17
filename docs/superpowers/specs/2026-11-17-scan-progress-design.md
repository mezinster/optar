# Progress of each scan in the application: design

Date: 2026-11-17. Status: approved (the owner approved this design in
conversation: "draw the bar").

## Intent

The owner asked: "Can we add some kind of progress bar per page when the
images are getting loaded/processed in the app?" Today a scan has no row at
all while the ordinary reader works on it (only "Working…" in the bottom
bar); only a scan the slower reader is reading is listed. Reading a scan takes
from a few seconds to over a minute.

## What the user sees

Every scan gets a row as soon as it is added, in one section "Being read",
until it becomes its page row (or a "Not readable" row):

```
Being read
  scan-1.png   [██████████░░░░░░░░░░]  Finding the page
  scan-2.png   [████████████████░░░░]  Slower reader, pass 4 of 5
  scan-3.png   [░░░░░░░░░░░░░░░░░░░░]  Waiting
```

The bar is drawn in the row. The bottom bar adds a count for the batch while
scans are being read, for example "Working… 3 of 6 scans read".

Remove on such a row cancels the scan's job, as it does today for a coarse
scan. The section "Coarse scans being read" becomes this section.

## What the bar measures

Steps, not seconds:

1. Opening the file
2. Finding the page
3. Identifying it (label and header)
4. Reading the data
5. If needed, the slower reader: its sampling, then each of its fits

The bar never moves backwards for a scan. The slower reader's part is even
progress; the ordinary part is rough (identifying tries rotations and papers
until one fits, so the bar can rest on a step and then jump). That is shown
honestly by the step's name next to the bar.

## Non-goals

- No time estimate.
- No change to what any reader returns, to the command line's output, or to
  the format.

## Approaches

- **A bar drawn in the row (chosen by the owner).**
- Text only ("scan-2.png · Slower reader, pass 4 of 5"): cheaper, but the
  owner asked for a bar.
- One bar for the whole batch only: does not show which scan is slow.

## How

- The library's `identify_any`, `identify_coarse` and `read_soft` take an
  optional progress callback and report step keys with counts; the library
  holds no user-visible words. With no callback nothing changes.
- `optar_gui/work.py` turns the steps of one scan's job (its own opening and
  reading steps plus the library's) into a fraction and a step key, reported
  through the job runner's existing progress channel.
- `document.py` holds the rule for which scans are listed as being read and
  their progress; `text.py` holds every word; the bar is drawn by a delegate
  of the list in `read_tab.py`.

## Left to the builder

The exact share of the bar given to each step, the wording of the steps, and
how the delegate draws the bar within the existing look of the list.

## Addendum: what a page read by the slower reader shows

The owner, on the text "That reader does not count repairs within the page or
mark them on the scan": "can we improve it? What if to show what's been
recovered and also implement some counters (if possible, of course)", and,
to the proposal below, "yes, go ahead once the progress bar is in".

- **Dots corrected within the page.** The slower reader forms an impression
  of every dot and then decides each symbol as a whole. A dot whose
  impression lost that decision was corrected. The page shows their number
  and marks them on the scan preview, as an ordinary page's corrections are.
  On the owner's coarse scans this is about 8% of the dots (about 265,000 a
  page), so the marks are dense.
- **Bytes repaired by the document's protection.** Once the document is
  verified, the page shows how many of its bytes were wrong and were repaired
  (the repair already knows this per page).
- "Beyond repair" stays unknown for such a page: the slower reader always
  gives a best guess. Such pages stay counted apart from the good ones.

```
Page 3 · Read by the slower reader · 265,112 dots corrected
         · 6,912 bytes repaired by the document's protection

Detail:
  Read by the slower reader for coarse scans.
  Dots corrected within the page: 265,112 of 3,196,368 (8.3%).
  After verification: 6,912 of this page's bytes were wrong and were
  repaired by the document's protection.
```

The second figure appears only once the document is verified.

Also settled here: while scans are being read, the bottom bar keeps the
document's state when it has one (for example "File recovered and verified")
and adds the count of scans read after it, instead of replacing it.
