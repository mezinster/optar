# History

optar was written in C by Karel 'Clock' Kulhavy of Twibright Labs in 2007, as
the programs `optar`, `unoptar` and `pgm2ps`. Its home page is
[ronja.twibright.com/optar](http://ronja.twibright.com/optar/). Colin Dean
kept the source available and improved it from 2012 to 2018 at
[github.com/colindean/optar](https://github.com/colindean/optar).

This project started from that source. The original C programs are kept
unchanged in the folder `lega-c` of the repository. They are history: nothing
in this project builds or runs them any more. The
[README](https://github.com/mezinster/optar#history-the-original-c-program)
keeps their original instructions.

## Versions of this project

| Version | What it added |
|---|---|
| 0.1.0 | The Python `optar` command, which reads and writes the same pages as the C programs. |
| 0.2.0 | The desktop application, and the tag in the label with the file's size and fingerprint. |
| 0.3.0 | Larger dots, protection, and pages that identify themselves from their data. |
| 0.4.0 | The slower reader for scans that are too coarse. |
| 0.5.0 | Progress bars for scans being read, and counts of what the slower reader corrected. |

The format itself, including what came from the C program, is described in
part 8 of the [format specification](format.md).

## Licence

GPL. © 2007 Karel 'Clock' Kulhavy of Twibright Labs; improvements © 2012-2018
Colin Dean. See `COPYING` in the repository.
