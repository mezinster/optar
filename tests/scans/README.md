Real printed-and-scanned pages, one subdirectory per test case (e.g. `tests/scans/laser-a4/`).
Each subdirectory holds `original.bin` (the encoded file), `paper.txt` (`a4` or `letter`)
and the scans `scan_0001.png`, `scan_0002.png`, ... in page order.
`test_real_scans.py` decodes every subdirectory with `read_scan` and checks the data byte for byte.
With no subdirectories the test reports one skip.
