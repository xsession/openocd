set bundle_root [file normalize [file join [file dirname [info script]] ..]]
set tcl_root [file join $bundle_root overlay tcl]
set commands {}

proc record {name args} {
	lappend ::commands [linsert $args 0 $name]
}
proc adapter {args} { record adapter {*}$args }
proc ftdi {args} { record ftdi {*}$args }
proc transport {args} { record transport {*}$args }
proc sleep {args} { record sleep {*}$args }
proc jtag {args} { record jtag {*}$args }
proc find {path} { return [file join $::tcl_root $path] }

proc assert_contains {expected message} {
	foreach command $::commands {
		if {$command eq $expected} { return }
	}
	error "$message; commands were: $::commands"
}

proc test_config {name expected_pid} {
	set ::commands {}
	source [file join $::tcl_root interface ftdi $name]
	assert_contains {adapter driver ftdi} "$name did not select the FTDI driver"
	assert_contains {transport select jtag} "$name did not select JTAG"
	assert_contains {ftdi layout_init 0x0038 0x597b} "$name has the wrong GPIO layout"
	assert_contains {ftdi initial_signal PWR_RST 1} "$name does not clear the power-loss latch before scan"
	assert_contains $expected_pid "$name has the wrong USB identity"
}

test_config xds100v2.cfg {adapter usb vid_pid 0x0403 0xa6d0 0x0403 0x6010}
set ::commands {}
xds100_recover_after_target_power_cycle
assert_contains {ftdi set_signal PWR_RST 0} "recovery did not drive PWR_RST low"
assert_contains {ftdi set_signal PWR_RST 1} "recovery did not drive PWR_RST high"
assert_contains {jtag arp_init} "recovery did not re-examine the JTAG chain"

test_config xds100v3.cfg {adapter usb vid_pid 0x0403 0xa6d1}
test_config xds100.cfg {adapter usb vid_pid 0x0403 0xa6d1 0x0403 0xa6d0 0x0403 0x6010}

puts "XDS100 Tcl configuration tests passed"
