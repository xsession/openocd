# SPDX-License-Identifier: GPL-2.0-or-later
#
# Microchip programmer command bridge for OpenOCD.
#
# This script deliberately does not reimplement Microchip's ICSP script
# engines. It provides a stable OpenOCD command surface and invokes one of:
#   * pk2cmd     - PICkit 2 and PICkit 3 scripting firmware
#   * IPECMD     - PICkit 3, PICkit 4 and MPLAB ICD 4
#   * pymcuprog  - PICkit 4 in AVR/CMSIS-DAP mode (limited target support)
#
# Load a programmer preset from programmer/microchip/*.cfg, configure the
# device and run an operation. Example:
#
#   openocd -f programmer/microchip/pickit4.cfg \
#     -c "microchip device dsPIC33EP128GM604" \
#     -c "microchip program firmware.hex" \
#     -c shutdown

namespace eval ::microchip_programmer {
	variable programmer ""
	variable backend auto
	variable device ""
	variable executable auto
	variable serial ""
	variable vdd external
	variable verify_after_program 1
	variable erase_before_program 1
	variable release_reset 1
	variable dry_run 0
	variable working_directory ""
	variable pack_path ""
	variable interface ""
	variable clock ""
	variable verbose 0
}

proc ::microchip_programmer::boolean {value option_name} {
	set normalized [string tolower $value]
	switch -- $normalized {
		1 - on - true - yes { return 1 }
		0 - off - false - no { return 0 }
		default { error "$option_name expects on or off" }
	}
}

proc ::microchip_programmer::require_one_arg {args usage} {
	if {[llength $args] != 1} {
		error "usage: $usage"
	}
	return [lindex $args 0]
}

proc ::microchip_programmer::resolved_backend {} {
	variable programmer
	variable backend

	if {$backend ne "auto"} {
		return $backend
	}

	switch -- $programmer {
		pickit2 { return pk2cmd }
		pickit3 - pickit4 - icd4 { return ipecmd }
		default { error "select a programmer before running an operation" }
	}
}

proc ::microchip_programmer::resolved_executable {selected_backend} {
	variable executable

	if {$executable ne "auto"} {
		return $executable
	}

	switch -- $selected_backend {
		pk2cmd {
			if {[info exists ::env(PK2CMD)] && $::env(PK2CMD) ne ""} {
				return $::env(PK2CMD)
			}
			return pk2cmd
		}
		ipecmd {
			if {[info exists ::env(IPECMD)] && $::env(IPECMD) ne ""} {
				return $::env(IPECMD)
			}
			return ipecmd
		}
		pymcuprog {
			if {[info exists ::env(PYMCUPROG)] && $::env(PYMCUPROG) ne ""} {
				return $::env(PYMCUPROG)
			}
			return pymcuprog
		}
		default { error "unsupported backend '$selected_backend'" }
	}
}

proc ::microchip_programmer::validate_configuration {selected_backend action} {
	variable programmer
	variable device
	variable serial
	variable vdd
	variable pack_path
	variable interface

	if {$programmer eq ""} {
		error "select a programmer with 'microchip programmer <name>'"
	}
	if {$device eq ""} {
		error "select a target with 'microchip device <part>'"
	}

	switch -- $selected_backend {
		pk2cmd {
			if {$programmer ni {pickit2 pickit3}} {
				error "pk2cmd supports PICkit 2 and PICkit 3 only"
			}
			if {$serial ne ""} {
				error "serial selection is not exposed by this pk2cmd bridge"
			}
		}
		ipecmd {
			if {$programmer ni {pickit3 pickit4 icd4}} {
				error "IPECMD supports the PICkit 3, PICkit 4 and ICD 4 presets"
			}
		}
		pymcuprog {
			if {$programmer ne "pickit4"} {
				error "pymcuprog is enabled only for PICkit 4 in AVR/CMSIS-DAP mode"
			}
			if {$action eq "verify"} {
				error "pymcuprog has no independent file verify operation; use program with verification enabled"
			}
			if {$vdd ne "external"} {
				error "set target supply separately when using the pymcuprog backend"
			}
		}
		default { error "unsupported backend '$selected_backend'" }
	}

	if {$vdd ne "external" && $vdd ne "off"} {
		if {![string is double -strict $vdd] || $vdd <= 0.0 || $vdd > 6.0} {
			error "vdd must be external, off, or a voltage from 0.1 to 6.0"
		}
	}
	if {$pack_path ne "" && $selected_backend ne "pymcuprog"} {
		error "pack_path is used only by the pymcuprog backend"
	}
	if {$interface ne "" && $selected_backend ne "pymcuprog"} {
		error "interface is used only by the pymcuprog backend"
	}
}

proc ::microchip_programmer::ipecmd_tool_argument {} {
	variable programmer
	variable serial

	if {$serial ne ""} {
		return "-TS$serial"
	}

	switch -- $programmer {
		pickit3 { return -TPPK3 }
		pickit4 { return -TPPK4 }
		icd4 { return -TPICD4 }
		default { error "IPECMD has no mapping for '$programmer'" }
	}
}

proc ::microchip_programmer::base_ipecmd_command {} {
	variable device
	variable vdd
	set command [list [resolved_executable ipecmd] [ipecmd_tool_argument] "-P$device"]
	if {$vdd ne "external" && $vdd ne "off"} {
		lappend command "-W$vdd"
	}
	return $command
}

proc ::microchip_programmer::build_ipecmd_command {action firmware} {
	variable erase_before_program
	variable verify_after_program
	variable release_reset

	set command [base_ipecmd_command]
	switch -- $action {
		program {
			if {$erase_before_program} { lappend command -E }
			lappend command "-F$firmware" -M
			if {$verify_after_program} { lappend command -Y }
		}
		erase { lappend command -E }
		verify { lappend command "-F$firmware" -Y }
		default { error "IPECMD action '$action' is not implemented" }
	}
	if {$release_reset} { lappend command -OL }
	return $command
}

proc ::microchip_programmer::base_pk2cmd_command {} {
	variable device
	variable vdd
	set command [list [resolved_executable pk2cmd] "-P$device"]
	if {$vdd ne "external" && $vdd ne "off"} {
		lappend command "-A$vdd"
	}
	return $command
}

proc ::microchip_programmer::build_pk2cmd_command {action firmware} {
	variable erase_before_program
	variable verify_after_program
	variable release_reset

	set command [base_pk2cmd_command]
	switch -- $action {
		program {
			if {$erase_before_program} { lappend command -E }
			lappend command "-F$firmware" -M
			if {$verify_after_program} { lappend command -Y }
		}
		erase { lappend command -E }
		verify { lappend command "-F$firmware" -Y }
		default { error "pk2cmd action '$action' is not implemented" }
	}
	if {$release_reset} { lappend command -L }
	return $command
}

proc ::microchip_programmer::base_pymcuprog_command {} {
	variable device
	variable serial
	variable pack_path
	variable interface
	variable clock
	variable verbose

	set command [list [resolved_executable pymcuprog] -t pickit4 -d $device]
	if {$serial ne ""} { lappend command -s $serial }
	if {$pack_path ne ""} { lappend command -p $pack_path }
	if {$interface ne ""} { lappend command -i $interface }
	if {$clock ne ""} { lappend command -c $clock }
	if {$verbose} { lappend command -v debug }
	return $command
}

proc ::microchip_programmer::build_pymcuprog_command {action firmware} {
	variable erase_before_program
	variable verify_after_program

	set command [base_pymcuprog_command]
	switch -- $action {
		program {
			lappend command write -f $firmware
			if {$erase_before_program} { lappend command --erase }
			if {$verify_after_program} { lappend command --verify }
		}
		erase { lappend command erase }
		ping { lappend command ping }
		reset { lappend command reset }
		default { error "pymcuprog action '$action' is not implemented" }
	}
	return $command
}

proc ::microchip_programmer::build_command {action firmware} {
	set selected_backend [resolved_backend]
	validate_configuration $selected_backend $action

	if {$action in {program verify}} {
		if {$firmware eq ""} {
			error "$action requires an Intel HEX file"
		}
		if {![file exists $firmware]} {
			error "firmware file does not exist: $firmware"
		}
	}

	switch -- $selected_backend {
		pk2cmd { return [build_pk2cmd_command $action $firmware] }
		ipecmd { return [build_ipecmd_command $action $firmware] }
		pymcuprog { return [build_pymcuprog_command $action $firmware] }
	}
}

proc ::microchip_programmer::display_argument {argument} {
	if {$argument eq ""} { return {""} }
	if {[regexp {^[A-Za-z0-9_./:+,=@%-]+$} $argument]} {
		return $argument
	}
	return "\"[string map [list "\\" "\\\\" "\"" "\\\""] $argument]\""
}

proc ::microchip_programmer::display_command {command} {
	set output {}
	foreach argument $command {
		lappend output [display_argument $argument]
	}
	return [join $output " "]
}

proc ::microchip_programmer::execute {action firmware} {
	variable dry_run
	variable working_directory

	set command [build_command $action $firmware]
	puts "Microchip programmer: [display_command $command]"
	if {$dry_run} {
		return $command
	}

	set previous_directory [pwd]
	if {$working_directory ne ""} {
		cd $working_directory
	}
	set status [catch {exec {*}$command} output]
	if {$working_directory ne ""} {
		cd $previous_directory
	}
	if {$output ne ""} {
		puts $output
	}
	if {$status} {
		error "Microchip programmer command failed: [display_command $command]"
	}
	return $output
}

proc ::microchip_programmer::show {} {
	variable programmer
	variable backend
	variable device
	variable executable
	variable serial
	variable vdd
	variable verify_after_program
	variable erase_before_program
	variable release_reset
	variable dry_run
	variable working_directory
	variable pack_path
	variable interface
	variable clock
	variable verbose

	puts "programmer: $programmer"
	puts "backend: $backend (resolved: [resolved_backend])"
	puts "device: $device"
	puts "executable: $executable"
	puts "serial: $serial"
	puts "vdd: $vdd"
	puts "erase before program: $erase_before_program"
	puts "verify after program: $verify_after_program"
	puts "release reset: $release_reset"
	puts "dry run: $dry_run"
	puts "working directory: $working_directory"
	puts "pack path: $pack_path"
	puts "interface: $interface"
	puts "clock: $clock"
	puts "verbose: $verbose"
}

proc ::microchip_programmer::help {} {
	puts {Microchip programmer commands:}
	puts {  microchip programmer pickit2|pickit3|pickit4|icd4}
	puts {  microchip backend auto|pk2cmd|ipecmd|pymcuprog}
	puts {  microchip device <part>}
	puts {  microchip executable auto|<path>}
	puts {  microchip serial none|<serial>}
	puts {  microchip vdd external|off|<voltage>}
	puts {  microchip erase_before_program on|off}
	puts {  microchip verify_after_program on|off}
	puts {  microchip release_reset on|off}
	puts {  microchip working_directory none|<path>}
	puts {  microchip pack_path none|<DFP path>}
	puts {  microchip interface none|<interface>}
	puts {  microchip clock none|<Hz>}
	puts {  microchip verbose on|off}
	puts {  microchip dry_run on|off}
	puts {  microchip show}
	puts {  microchip command program|erase|verify|ping|reset [firmware.hex]}
	puts {  microchip program <firmware.hex>}
	puts {  microchip erase}
	puts {  microchip verify <firmware.hex>}
	puts {  microchip ping       (pymcuprog only)}
	puts {  microchip reset      (pymcuprog only)}
}

proc microchip {subcommand args} {
	switch -- $subcommand {
		programmer {
			set value [::microchip_programmer::require_one_arg $args {microchip programmer pickit2|pickit3|pickit4|icd4}]
			if {$value ni {pickit2 pickit3 pickit4 icd4}} { error "unsupported programmer '$value'" }
			set ::microchip_programmer::programmer $value
		}
		backend {
			set value [::microchip_programmer::require_one_arg $args {microchip backend auto|pk2cmd|ipecmd|pymcuprog}]
			if {$value ni {auto pk2cmd ipecmd pymcuprog}} { error "unsupported backend '$value'" }
			set ::microchip_programmer::backend $value
		}
		device { set ::microchip_programmer::device [::microchip_programmer::require_one_arg $args {microchip device <part>}] }
		executable { set ::microchip_programmer::executable [::microchip_programmer::require_one_arg $args {microchip executable auto|<path>}] }
		serial {
			set value [::microchip_programmer::require_one_arg $args {microchip serial none|<serial>}]
			set ::microchip_programmer::serial [expr {$value eq "none" ? "" : $value}]
		}
		vdd { set ::microchip_programmer::vdd [::microchip_programmer::require_one_arg $args {microchip vdd external|off|<voltage>}] }
		erase_before_program {
			set value [::microchip_programmer::require_one_arg $args {microchip erase_before_program on|off}]
			set ::microchip_programmer::erase_before_program [::microchip_programmer::boolean $value erase_before_program]
		}
		verify_after_program {
			set value [::microchip_programmer::require_one_arg $args {microchip verify_after_program on|off}]
			set ::microchip_programmer::verify_after_program [::microchip_programmer::boolean $value verify_after_program]
		}
		release_reset {
			set value [::microchip_programmer::require_one_arg $args {microchip release_reset on|off}]
			set ::microchip_programmer::release_reset [::microchip_programmer::boolean $value release_reset]
		}
		dry_run {
			set value [::microchip_programmer::require_one_arg $args {microchip dry_run on|off}]
			set ::microchip_programmer::dry_run [::microchip_programmer::boolean $value dry_run]
		}
		working_directory {
			set value [::microchip_programmer::require_one_arg $args {microchip working_directory none|<path>}]
			set ::microchip_programmer::working_directory [expr {$value eq "none" ? "" : $value}]
		}
		pack_path {
			set value [::microchip_programmer::require_one_arg $args {microchip pack_path none|<DFP path>}]
			set ::microchip_programmer::pack_path [expr {$value eq "none" ? "" : $value}]
		}
		interface {
			set value [::microchip_programmer::require_one_arg $args {microchip interface none|<interface>}]
			set ::microchip_programmer::interface [expr {$value eq "none" ? "" : $value}]
		}
		clock {
			set value [::microchip_programmer::require_one_arg $args {microchip clock none|<Hz>}]
			if {$value ne "none" && (![string is integer -strict $value] || $value <= 0)} {
				error "clock expects a positive integer in Hz or none"
			}
			set ::microchip_programmer::clock [expr {$value eq "none" ? "" : $value}]
		}
		verbose {
			set value [::microchip_programmer::require_one_arg $args {microchip verbose on|off}]
			set ::microchip_programmer::verbose [::microchip_programmer::boolean $value verbose]
		}
		show {
			if {[llength $args] != 0} { error {usage: microchip show} }
			::microchip_programmer::show
		}
		command {
			if {[llength $args] < 1 || [llength $args] > 2} {
				error {usage: microchip command <action> [firmware.hex]}
			}
			set action [lindex $args 0]
			set firmware [expr {[llength $args] == 2 ? [lindex $args 1] : ""}]
			set command [::microchip_programmer::build_command $action $firmware]
			puts [::microchip_programmer::display_command $command]
			return $command
		}
		program {
			set firmware [::microchip_programmer::require_one_arg $args {microchip program <firmware.hex>}]
			return [::microchip_programmer::execute program $firmware]
		}
		erase {
			if {[llength $args] != 0} { error {usage: microchip erase} }
			return [::microchip_programmer::execute erase ""]
		}
		verify {
			set firmware [::microchip_programmer::require_one_arg $args {microchip verify <firmware.hex>}]
			return [::microchip_programmer::execute verify $firmware]
		}
		ping {
			if {[llength $args] != 0} { error {usage: microchip ping} }
			return [::microchip_programmer::execute ping ""]
		}
		reset {
			if {[llength $args] != 0} { error {usage: microchip reset} }
			return [::microchip_programmer::execute reset ""]
		}
		help {
			if {[llength $args] != 0} { error {usage: microchip help} }
			::microchip_programmer::help
		}
		default {
			error "unknown microchip subcommand '$subcommand'; use 'microchip help'"
		}
	}
}
