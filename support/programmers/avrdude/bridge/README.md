# AVRDUDE Bridge Programmer Entry

This entry maps AVRDUDE's external programmer ecosystem into OpenOCD's support
index. The runtime bridge is `tcl/programmer/avrdude/common.tcl`.

The bridge delegates to an installed `avrdude` binary. Native OpenOCD ports of
AVRDUDE protocols should be added later as focused backend batches.
