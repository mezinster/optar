Twibright Optar
===============

[![CI](https://github.com/mezinster/optar/actions/workflows/ci.yml/badge.svg)](https://github.com/mezinster/optar/actions/workflows/ci.yml)

_**Special note:** The repository of optar at http://github.com/colindean/optar 
exists because I (@colindean) had difficulties finding the source and it seemed
to be abandoned/dormant. I've made slight improvements over time. Improvements
welcomed as pull requests._

optar stores a file on paper. It prints the file as pages of small black and
white dots on a 600 dpi laser printer, and reads the file back from scans of
those pages.

**Documentation: <https://mezinster.github.io/optar/>**

The site is also available in Russian, Ukrainian, Belarusian, Polish, Georgian, Turkish, Italian and Spanish; use the language switcher in its header.

![The application after reading two pages: both good, the file verified](docs/img/verified.png)

- One A4 page holds about 200,000 bytes with the standard dot size.
- Larger dots can be chosen so that a 200 dpi scanner is enough; a page then
  holds less.
- Protection is extra data spread over all pages. With it the program repairs
  stains and torn corners, and in a document that is long enough it rebuilds a
  page that is lost.
- A fingerprint of the file is printed with it. The recovered file is called
  verified only when it matches that fingerprint.

There are two programs, which use the same code: `optar-gui`, a desktop
application for Linux, macOS and Windows, and `optar`, a command-line program.

Getting it
----------

Download the file for your system from the
[Releases page](https://github.com/mezinster/optar/releases/latest), or
install from a checkout with Python 3.12 or newer:

    pip install .          # the optar command
    pip install '.[gui]'   # and the optar-gui application

See [Install](https://mezinster.github.io/optar/install/) for the details of
each system.

Using it
--------

1. In the application, open "Put on paper", choose the file, and create the
   PDF. Or: `optar encode FILE -o BASE --protect standard`.
2. Print the PDF at actual size (100%), not "fit to page", on a 600 dpi laser
   printer.
3. To get the file back, scan the pages in grayscale as PNG or TIFF, at the
   resolution for the dot size (600 dpi for Standard dots).
4. Open "Read from paper", add the scans in any order, and save the file when
   the bar at the bottom says it is verified. Or: `optar decode BASE -o FILE`.

The documentation has the rest:

- [Put a file on paper](https://mezinster.github.io/optar/put-on-paper/): dot
  sizes, protection, printing.
- [Read it back](https://mezinster.github.io/optar/read-from-paper/):
  scanning, page states, what "verified" means.
- [Scans that are too coarse](https://mezinster.github.io/optar/slower-reader/):
  the second, slower reader.
- [Command line](https://mezinster.github.io/optar/command-line/).
- [What has and has not been shown](https://mezinster.github.io/optar/evidence/):
  what the claims rest on. Most of it is simulated scans, not paper.
- [Format specification](docs/format.md): the page format, defined by this
  document and by the conformance vectors in `tests/vectors`.
- [Development](https://mezinster.github.io/optar/development/).

The pages of the documentation are the Markdown files in [docs](docs).

History: the original C program
-------------------------------

The original C programs live in the `lega-c` folder, unchanged, and the rest
of this document describes them. They are history: the format is defined by
[docs/format.md](docs/format.md), and nothing in this project builds or runs
them any more. Run the commands below from inside `lega-c`. The C encoder is also called
`optar`: `make` builds it there as `./optar`, so run it as `./optar` to avoid
confusion with the Python command.

### Building

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

### Installing locally

It's easiest to install your local build with

    sudo make install

`optar`, `unoptar`, and `pgm2ps` installed on your system in `/usr/local/bin`. 

To uninstall, run

    sudo make uninstall

### Encoding (writing)

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

### Decoding (reading)

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

### A4 <-> US Letter
Change the convert parameters in pgm2ps (see comments). Change XCROSSES
and YCROSSES in optar.h (see comments). Recompile. Then you can use US Letter
instead of A4.

### Changing the format
If your printer is low quality and you are getting irreparable bits, you can
try to format the media to lower capacity.  Unfortunately, setting by
commandline is not implemented yet.  Change XCROSSES and YCROSSES in optar.h to
lower values which yields bigger pixels and lower capacity per page, but higher
reliability.  Make sure they are in roughly the same proportion as before,
otherwise you get nonsquare pixels and unnecessary waste of channel capacity.

You can also change the decoding parameters in unoptar.c (look for MAGIC
CONSTANTS) in attempt to read a difficult recording: unsharp_mask,
unsharp_dist, sync_white_cut, white_cut, minmax_filter, pixel_blur, cross_trim.

### Future improvement
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

