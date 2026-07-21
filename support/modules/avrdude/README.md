# AVRDUDE Module Entry

AVRDUDE is tracked as an external module-style source, similar to how Zephyr
tracks external projects and board roots.

The local OpenOCD integration is delegated through
`tcl/programmer/avrdude/common.tcl`. The audited source checkout under
`artifacts/vendor-sources/avrdude` is not part of the maintained source tree.
