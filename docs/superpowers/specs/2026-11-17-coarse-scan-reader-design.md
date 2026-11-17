# A second, slower reader for scans that are too coarse: design

Date: 2026-11-17. Status: proposed.

## Intent

A page printed with Standard dots needs a 600 dpi scan. The owner scanned a
six-page, High-protection document at about 290 dpi. The application answered
"too coarse to read" for every page and tried nothing more.

A scratch experiment on those scans recovered the file, verified by its
fingerprint: 759,879 bytes, 49,606 bytes repaired, worst block 46 of a budget
of 64. The owner's decision: "i want this built into optar as a fallback".

After this work, a scan the ordinary reader cannot identify gets a second,
slower attempt by the method of that experiment, in the application and on the
command line, with no outside service.

## What the experiment did

For one page:

1. Enlarge the scan three times (Lanczos) and locate the page and its crosses
   with the existing code.
2. Read the page the ordinary way. Symbols the Golay code accepts with at most
   one corrected bit are taken as known.
3. For every dot, sample the scan at a 7 by 7 grid of points half a dot apart
   around the dot's centre, and subtract their mean.
4. Fit, by least squares, a linear filter (plus squares of the centre nine
   samples) from those samples to the known dots: one filter for each of
   16 by 22 regions of the page. This is the "blur-aware" part: the filter
   learns how neighbouring dots bleed into each other in that region.
5. Apply the filters to every dot. This gives a signed confidence for each dot
   instead of black or white.
6. For each symbol, choose the Golay codeword that fits the 24 confidences
   best (all 4096 are tried). Keep the gap to the second best as the symbol's
   confidence.
7. Take the more confident 60% of symbols as known and repeat from step 4,
   five rounds in all.

The payloads of the six pages then went through the existing `unwrap()`
unchanged.

Measured on the owner's six scans: the ordinary reader on the enlarged scan
left about 13% of the symbols of each page unreadable and the document's
repair failed in nearly every block. A small neural network in place of the
linear filter was no better.

## Goals

1. A scan that the ordinary reader cannot identify is tried again by the
   second reader, without the user asking.
2. The owner's six scans produce the verified file through the application
   and through the command line, not only through the scratch script.
3. The user sees that the slower reader is at work, and afterwards that a
   page was read by it.
4. Under one minute a page on an ordinary laptop. (The scratch script took
   about 70 seconds a page run alone.)

## Non-goals

- No change to the page format, to any printed page, or to the ordinary
  reader. The vectors that pin the ordinary decoder stay as they are.
- Old 0.2-style pages (identified by the tag in their label) are not covered:
  a coarse scan's label cannot be read, so such a page cannot be placed. The
  second reader identifies a page by its header only.
- A scan the ordinary reader identifies, whose document then fails to repair,
  is not retried in this work. It can follow once this is shown to hold.
- No new dependency. numpy and Pillow only.

## Anti-goals

- Claiming more than was shown. The evidence is one document, one scanner,
  one resolution, High protection. The README must say so until tests or
  more scans say more.
- A wrong file presented as right. Nothing changes here: only the fingerprint
  makes a file "verified", and a header is accepted only by its check, as now.
- An interface that freezes or a job that cannot be stopped. A page takes
  tens of seconds.

## Approaches considered

**A. Automatic second attempt on a scan that could not be identified
(chosen).** `identify_scan` fails as today; the caller then tries the second
reader. The user does nothing extra. Cost: an unreadable scan that is simply
not an optar page now takes longer to be reported; this is bounded by trying
the second reader only when a page outline was found.

**B. A "Try harder" button, and a `--thorough` option.** Nothing slow happens
unasked. But the user must know the button exists and what it is for, and the
case it serves is exactly the one where the user is already stuck. The owner
asked for a fallback, which is A.

**C. The second reader for every scan.** One path, but every scan becomes
slow, and the ordinary decoder's pinned results would no longer be what the
tools produce.

The owner asked for a fallback and left the how; A is the author's choice.

## What is built

### Library

A new module, `optar/decoder/soft.py` (name is the builder's), with no effect
on the existing decoder:

- `read_soft(grid, image) -> PageResult`: steps 2 to 7 above for a located
  page. The result has the shape `decode_located(..., detail=True)` returns,
  so `container.page_payload` and `unwrap` take it unchanged.
  `lost_symbols` is empty unless the builder's measurements show that marking
  the least confident symbols helps (it was not needed on the owner's scans).
- `identify_coarse(image, options=None) -> ScanIdentity`: enlarges the scan,
  finds the outline, and for the candidate layouts and rotations (the same
  order `identify_scan` uses) locates the page, reads it with `read_soft` and
  accepts the first valid header. Raises `IdentifyError` as `identify_scan`
  does. The identity records that the second reader produced it.

The numbers of the method (enlargement, sample grid, regions, rounds, share
kept) are named constants in that module, not in `format.py`: they are
reader tuning, not format.

The enlargement is chosen from the outline's estimated resolution so that a
dot is at least about four pixels wide; a scan that is already fine enough is
not enlarged.

### Command line

`optar decode` and `optar identify` try the second reader for a scan that
was not identified and whose outline was found, and say so on stderr.
`--no-slow-reader` turns it off.

### Application

- The identification job tries the second reader in the same job, off the
  interface thread, and can be cancelled when the scan is removed.
- While it runs, the scan's row says that a coarse scan is being read and
  that this takes about a minute.
- A page read this way says so in its row and detail text. Every string is in
  `text.py`.
- The "too coarse to read" message stays for a scan that the second reader
  could not read either, and then also says that the slower reader was tried.

### Tests

- Unit tests of `read_soft` on a small custom format: a page blurred and
  resampled so that the ordinary reader fails and the second one succeeds.
- A claims-style test (marked `slow`): a simulated Standard-dot A4 document
  with High protection, scanned at 300 dpi, is recovered and verified. If the
  simulator cannot reproduce what the owner's scanner did at its defaults,
  the test states the simulator settings it holds for and the README states
  the gap. The simulator's defaults and the existing claims are not changed.
- The owner's scans stay outside the repository. They are measured in place
  and the result is reported in the pull request.

### Documents

README: what the second reader is, when it runs, and under "What has and has
not been shown" exactly what the evidence is. `CLAUDE.md`: the second reader
is separate from the ordinary decoder and must not change its results.
`docs/format.md` part 7 (informative): a short description.

## Left to the builder

- Speed work to reach the goal (the sampling and the per-region fits are the
  cost).
- Whether to mark low-confidence symbols as lost, decided by measurement.
- How the identity records which reader produced it.
- Exact wording of the new strings.

## Risks

- **It works on one scanner only.** Mitigated by the simulated test and by
  saying plainly what was shown. Not removed.
- **Standard protection.** On the owner's scans the worst block needed 46;
  Standard protection allows 32. Expect such documents to fail at this
  resolution, and say so.
- **False identification.** The second reader accepts a page by its header
  check, like the ordinary one; the fingerprint still decides "verified".
- **Time.** A folder of scans that are not optar pages at all would each cost
  a slow attempt. Bounded by requiring a page outline first; the builder
  measures the cost on such images.
