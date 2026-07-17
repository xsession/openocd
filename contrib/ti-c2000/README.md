# TI C2000 support files

This directory collects small metadata files and notes used by the TI C2000
OpenOCD target configurations.

The actual C28x target backend lives in:

```text
src/target/c28x.c
src/target/c28x.h
```

Target/board configuration files live in:

```text
tcl/target/ti/tms320f28069.cfg
tcl/target/ti/tms320f280049.cfg
tcl/target/ti/tms320f28m35x.cfg
tcl/board/ti/tms320f28069-xds110.cfg
tcl/board/ti/tms320f280049-xds110.cfg
tcl/board/ti/tms320f28m35x-xds110.cfg
```

Additional CCS-derived register/routing notes are in:

```text
contrib/ti-c2000/ccs-derived-c28x.md
```
