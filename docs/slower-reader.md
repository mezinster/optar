# Scans that are too coarse: the slower reader

From 0.4.0 the program has a second, slower reader for scans made at too low
a resolution for their dot size, for example a Standard-dot page scanned at
300 dpi instead of 600.

Scan at the advised resolution when you can. The slower reader recovers some
coarse scans, not all of them (see
[What has and has not been shown](evidence.md#the-slower-reader)).

## When it runs

It runs by itself, in two cases:

- The ordinary reader cannot identify a scan, but finds the outline of a page
  in it.
- A coarse scan (fewer than 2.5 scan pixels to a dot) gave the ordinary reader
  only an untagged label and no header, and the page's data read badly (1% or
  more of its symbols beyond correction). On such a scan the label can still
  be legible where the data is not.

A page whose data reads well is an old page without a header, and is left
alone. If the slower reader finds nothing, the label's reading is kept.

## How it works

The slower reader enlarges the scan. From the dots the ordinary reader is sure
of, it learns how neighbouring dots blur into each other in each part of the
page. It then reads every dot with that knowledge and chooses each symbol as a
whole.

## In the application

![Two pages read by the slower reader, with the corrected dots marked](img/slow-pages.png)

*A generated test page, small and scanned very coarsely. The corrected dots
are marked on the preview.*

- While it is at work, the scan's row shows the slower reader's step and
  progress. Selecting the row says that this takes about a minute.
- Afterwards the row says that the page was read by the slower reader and how
  many dots it corrected, for example "Page 3 · Read by the slower reader ·
  265,112 dots corrected". A corrected dot is one whose own impression lost
  the decision of its symbol.
- The corrected dots are marked on the scan preview, each mark one dot wide.
  On coarse scans that is often several percent of the dots, so seen whole the
  page shows a tint as dense as the corrections. Zooming in shows single dots.
- Once the document is verified, the row adds how many of the page's bytes the
  document's protection repaired ("· 6,912 bytes repaired by the document's
  protection"). Selecting the page shows both figures.

Such a page is never called "Good" and is counted apart in the bar at the
bottom. The slower reader gives every symbol its best guess, so it cannot say
what is beyond repair on the page.

## On the command line

`optar decode` also runs it by itself and says so on stderr for each scan it
is tried on. `--no-slow-reader` turns it off.

## How long it takes

An A4 page took 40 to 70 seconds in all on the development machine: 20 to 35
seconds for the ordinary reader to give up, then 20 to 35 seconds for the
slower reader.

An image that is not an optar page at all, but in which a page outline is
found, costs about 20 to 35 seconds more than it did without the slower
reader.

## Limits

- It identifies a page only by the header in its data. Old 0.2-style pages,
  which are identified by the tag in their label, are not covered.
- A page whose tag the ordinary reader accepted is never given to the slower
  reader.
- Standard protection is expected not to be enough for a Standard-dot page
  scanned at about 290 dpi. The one real document that was recovered this way
  had High protection and needed more repair than Standard protection can
  give.
- It does not make a wrong file look right: as always, only the fingerprint
  makes a file verified.
