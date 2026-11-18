# Install

## Download

Download the file for your system from the
[Releases page](https://github.com/mezinster/optar/releases/latest). `<tag>`
below is the version, for example `v0.5.0`.

| System | Desktop application | Command line |
|---|---|---|
| Linux | `optar-gui-<tag>-linux-x86_64` | `optar-<tag>-linux-x86_64` |
| macOS (Apple silicon) | `optar-gui-<tag>-macos-arm64.zip` | `optar-<tag>-macos-arm64` |
| Windows | `optar-gui-<tag>-windows-x86_64.exe` | `optar-<tag>-windows-x86_64.exe` |

Each is a single file and needs nothing else installed.

- **Linux:** run `chmod +x` on the file first.
- **macOS:** run `chmod +x` on the command-line file. Unzip the application
  and try to open it. The programs are unsigned, so macOS may refuse: open
  System Settings, Privacy & Security, and choose "Open Anyway" (on older
  macOS versions, right-click the application and choose Open).
- **Windows:** the programs are unsigned, so Windows may warn on first run.

## From source

You need Python 3.12 or newer and a checkout of the repository.

The command-line program (installs numpy and Pillow):

    pip install .

The desktop application as well:

    pip install '.[gui]'
    optar-gui

## Check that it works

`optar --version` and `optar-gui --version` print the version.

`optar-gui --self-test` starts the application without a screen and checks
that it can encode and read pages.
