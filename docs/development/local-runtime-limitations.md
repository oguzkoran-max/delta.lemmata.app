# Local Runtime Limitations

**Tarih:** 2026-07-10  
**Ticket:** P001

## Current Mac

- macOS 26.5.1, arm64
- Python 3.13.9
- R 4.5.2
- `renv` 1.2.3, `stylo` 0.7.71, and `jsonlite` 2.0.0 are installed and locked
- Docker is not installed
- XQuartz is not installed

## Consequence

`renv` restores the R library successfully and reports a synchronized lock.
Loading the `stylo` namespace on this Mac currently fails because this R build's
`tcltk` library links to X11 and requests XQuartz.

P001 therefore verifies the exact installed package versions and lock state, but
does not claim a successful local `stylo` namespace load or analysis. `stylo`
execution, numerical parity, and headless behavior belong to P006 and must pass in
the canonical Linux x86_64 container. Installing XQuartz is an optional local
development convenience, not a scientific dependency claim.

The canonical container declares Linux Tcl/Tk, X11, and Xvfb system packages, but
its build remains `not verified` until CI or a Docker-capable host runs it.
