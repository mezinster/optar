# optar

optar stores a file on paper. It prints the file as pages of small black and
white dots on a 600 dpi laser printer, and reads the file back from scans of
those pages.

![The application after reading two pages: both good, the file verified](img/verified.png)

- **One A4 page holds about 200,000 bytes** with the standard dot size.
- **Larger dots** can be chosen so that a 200 dpi scanner is enough; a page
  then holds less.
- **Protection** is extra data spread over all pages. With it the program
  repairs stains and torn corners, and in a document that is long enough it
  rebuilds a page that is lost.
- **A fingerprint** of the file is printed with it. The recovered file is
  called verified only when it matches that fingerprint.

There are two programs, which use the same code:

- `optar-gui`, a desktop application for Linux, macOS and Windows;
- `optar`, a command-line program.

## Where to start

| You want to | Read |
|---|---|
| Get the programs | [Install](install.md) |
| Print a file | [Put a file on paper](put-on-paper.md) |
| Get a file back from a printout | [Read it back](read-from-paper.md) |
| Read scans made at too low a resolution | [Scans that are too coarse](slower-reader.md) |
| Use it from scripts | [Command line](command-line.md) |
| Know how far to trust it | [What has and has not been shown](evidence.md) |
| Write your own reader or encoder | [Format specification](format.md) |

## In short

1. In the application, open "Put on paper", choose the file, and create the
   PDF.
2. Print the PDF at actual size (100%), not "fit to page", on a 600 dpi laser
   printer.
3. To get the file back, scan the pages in grayscale as PNG or TIFF, at the
   resolution for the dot size (600 dpi for Standard dots).
4. Open "Read from paper", add the scans in any order, and save the file when
   the bar at the bottom says it is verified.

## Where it comes from

optar was written in C by Karel 'Clock' Kulhavy of Twibright Labs in 2007.
This project is a Python version that reads and writes the same pages, and
adds the desktop application, the larger dots, the protection and the
fingerprint. See [History](history.md).
