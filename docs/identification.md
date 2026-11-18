# How a page identifies itself

The program has to know, for each scan, which document it belongs to and which
page it is. There are two ways a page can say so, depending on how the
printout was made.

| Printout | Identified by |
|---|---|
| Made with protection, or with any dot size but Standard | a header in the page's data ("self-identifying pages") |
| Compatible printout from 0.2.0 or newer | the tag in the label at the bottom |
| From 0.1.0 or from the C tool | the label alone, which has nothing to check it against |

A valid tag in the label always wins: a page whose label has a valid tag is
read as a 0.2.0 page, whatever its data holds.

## Self-identifying pages

The pages of a printout made with protection, or with any dot size but
Standard, carry the details of the document in their data: which printout they
belong to, their number, the number of pages, the size of the file and its
fingerprint.

The label printed at the bottom is for people and is not used to identify
them. In a PDF it is printed at one size whatever the dot size (the size of a
Standard page's label), so the whole line fits. It is then too small to be
read from a coarse scan, and the window shows "(no name)" until the file is
recovered and its own name is known. PNG and PGM pages have one pixel per dot,
so their label is drawn in the page's dots and grows with them.

The room such a document does not use is filled with a fixed pattern that
looks like data, so every page prints evenly. Version 0.3.0 filled it with
zeros, which printed as white lines across the pages. Both are read, by 0.3.0
too: no reader looks at the filling.

A page header is not trusted by itself: one scanned page could claim to belong
to any document. Only the fingerprint of the recovered file makes it verified.

## The label

Every page has a label at the bottom: the page format, the page number and the
number of pages, then free text. For printouts of 0.2.0 and earlier, the
application reads this label from the scan.

- A label with a tag is accepted when it reads plausibly, the tag's check
  matches the page number and page count, and the file size in the tag fits
  that page count.
- A label without a tag (printouts made by 0.1.0 or by the C tool) has nothing
  to check it against, so it is accepted only when it reads clearly.
- A label that looks like a tag with one damaged character is refused.

A scan that is refused is listed as "Not readable" with the reason, and you
can assign it to a page by hand.

## The tag

From 0.2.0, `optar encode` and the application print a tag at the start of the
free text of every page of a compatible printout, in the form
`[SIZE:FINGERPRINT:CC]`.

| Part | Meaning |
|---|---|
| `SIZE` | the size of the file in bytes |
| `FINGERPRINT` | the first 8 hex digits of the file's SHA-256 |
| `CC` | a check of two hexadecimal digits that depends on the page number and the number of pages |

The tag lets the application:

- keep the pages of different printouts apart;
- refuse a tagged label whose size does not fit the page count;
- refuse a scan whose label was misread, instead of placing it on the wrong
  page (about 1 misread in 256 can still pass the check);
- cut the recovered file to its true size, so it has no zero padding;
- compare the recovered file with the fingerprint, which is the final check
  that the file is the original.

To print without a tag, use `optar encode --no-tag`. Pages that identify
themselves from their data print no tag.

The exact definitions are in the [format specification](format.md): part 3
for the tag and part 4 for self-identifying documents.
