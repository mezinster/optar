# Put a file on paper

## In the application

Open the tab "Put on paper".

![The "Put on paper" tab with a file chosen](img/put-on-paper.png)

1. Choose a file, or drop it on the tab.
2. Pick A4 or US Letter.
3. Choose the [dot size](#dot-size) and the [protection](#protection). The
   window starts with Standard dots and Standard protection.
4. Give the file a name. The line "Prints as:" shows the text that will be
   printed on each page.
5. Read the line below it: it shows how many pages the file needs and, with
   protection, how many of those pages can be lost.
6. "Create PDF…" saves the PDF.

Ticking "Compatible with optar 0.2 and the original optar" makes a printout
that those older programs can read. It has Standard dots and no protection.

From the command line, see [`optar encode`](command-line.md#encode).

## Printing

Print the PDF at actual size (100%), not "fit to page", on a 600 dpi laser
printer. Inkjet printers have not been tested.

A printout that comes out smaller than actual size has smaller dots, which are
harder to read. One real printout measured about 95% of actual size.

## Dot size

Dot size is how large each data dot is printed. Larger dots survive a coarser
scan, but a page holds fewer of them, so it holds less. A data dot is 3, 4, 5,
6 or 9 dots of a 600 dpi printer.

The table gives the scan resolution to use (three scan pixels per data dot)
and the bytes one page holds before protection is added:

| Dot size | Option | Printer dots per data dot | Scan at | A4 page | Letter page |
|---|---|---|---|---|---|
| Standard | `standard` | 3 | 600 dpi | 199,773 | 192,591 |
| Medium | `medium` | 4 | 450 dpi | 114,904 | 110,463 |
| Big | `big` | 5 | 360 dpi | 73,027 | 69,463 |
| Large | `large` | 6 | 300 dpi | 49,119 | 48,403 |
| Extra large | `xlarge` | 9 | 200 dpi | 21,606 | 21,127 |

Choose the dot size for the scanner that will read the pages, which may be
many years from now. If you do not know, larger dots are the safer choice.

## Protection

Protection is extra data, spread over all the pages of the document, with
which the program repairs damaged places and rebuilds pages that are lost. The
choices are None, Standard and High.

- It takes paper: Standard protection adds about 14% more pages and High
  about 34%.
- The extra data is spread so that a stain, a torn corner or a missing page
  costs every part of the file about the same small amount. That small amount
  is what the protection repairs.
- With protection, part of the pages carries the protection data, and every
  page repeats a short record that says which document and which page it is.
  So the file gets less room than the table above shows.

### Losing a whole page

The window and `optar encode` promise that a lost page can be recovered only
for documents that are long enough, and then say "can lose N page(s) of T".

| Protection | Can lose 1 page from | Can lose 2 pages from |
|---|---|---|
| Standard | 12 pages | 24 pages |
| High | 6 pages | 12 pages |

Below that, damage within pages is repaired, but losing a whole page loses the
file. The promise is deliberately cautious, and a document may recover more
than it promises.

### The largest file

A file whose protected printout would be more than 256 MiB on paper is
refused. The window then says whether the file would fit without protection or
with smaller dots.

## Which programs can read the printout

| Printout | Read by |
|---|---|
| Any dot size but Standard, or any protection | optar 0.3 or newer. Nothing needs to be set when reading. |
| Standard dots, no protection, "Compatible" ticked | every version, and the original C program |

The 0.2.0 application cannot read larger-dot pages at all. For Standard dots
with protection, 0.2.0 and the C tool return the data wrapped in the extra
details and protection, not the file.

The reasons are on the page
[How a page identifies itself](identification.md).

!!! note "Files in a compatible printout are padded"
    A printout made for 0.2 and older programs does not store the length of
    the file in its data; only the tag in the label has it. The command-line
    `optar decode` and the C tool return such a file padded with zeros to a
    whole page. Pack your data with tar if it is sensitive to this.
