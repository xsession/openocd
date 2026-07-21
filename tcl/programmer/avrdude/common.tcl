# SPDX-License-Identifier: GPL-2.0-or-later
#
# AVRDUDE programmer command bridge for OpenOCD.
#
# This script deliberately delegates AVR programming protocols to the external
# avrdude executable. It gives OpenOCD users a stable command surface for the
# broad AVRDUDE MCU/programmer catalog while native OpenOCD protocol backends
# are reviewed one family at a time.
#
# Example:
#
#   openocd -f programmer/avrdude/common.tcl \
#     -c "avrdude programmer arduino" \
#     -c "avrdude part atmega328p" \
#     -c "avrdude port COM1" \
#     -c "avrdude baud 115200" \
#     -c "avrdude program blink.hex" \
#     -c shutdown

namespace eval ::avrdude_programmer {
	variable executable auto
	variable programmer ""
	variable part ""
	variable port ""
	variable baud ""
	variable config ""
	variable dry_run 0
	variable disable_auto_erase 0
	variable verbose 0
	variable working_directory ""
	variable extra_options {}
}

proc ::avrdude_programmer::boolean {value option_name} {
	set normalized [string tolower $value]
	switch -- $normalized {
		1 - on - true - yes { return 1 }
		0 - off - false - no { return 0 }
		default { error "$option_name expects on or off" }
	}
}

proc ::avrdude_programmer::require_one_arg {args usage} {
	if {[llength $args] != 1} {
		error "usage: $usage"
	}
	return [lindex $args 0]
}

proc ::avrdude_programmer::resolved_executable {} {
	variable executable

	if {$executable ne "auto"} {
		return $executable
	}
	if {[info exists ::env(AVRDUDE)] && $::env(AVRDUDE) ne ""} {
		return $::env(AVRDUDE)
	}
	return avrdude
}

proc ::avrdude_programmer::validate_base_configuration {} {
	variable programmer
	variable part
	variable baud

	if {$programmer eq ""} {
		error "select a programmer with 'avrdude programmer <id>'"
	}
	if {$part eq ""} {
		error "select an MCU part with 'avrdude part <id>'"
	}
	if {$baud ne "" && (![string is integer -strict $baud] || $baud <= 0)} {
		error "baud expects a positive integer or none"
	}
}

proc ::avrdude_programmer::base_command {} {
	variable programmer
	variable part
	variable port
	variable baud
	variable config
	variable verbose
	variable extra_options

	validate_base_configuration

	set command [list [resolved_executable]]
	if {$config ne ""} { lappend command -C $config }
	lappend command -c $programmer -p $part
	if {$port ne ""} { lappend command -P $port }
	if {$baud ne ""} { lappend command -b $baud }
	if {$verbose} { lappend command -v }
	foreach option $extra_options {
		lappend command $option
	}
	return $command
}

proc ::avrdude_programmer::memory_spec {memory operation file format} {
	if {$memory eq ""} { error "memory name must not be empty" }
	if {$file eq ""} { error "file name must not be empty" }
	if {$format eq ""} { error "format must not be empty" }
	return "${memory}:${operation}:${file}:${format}"
}

proc ::avrdude_programmer::build_command {action args} {
	variable disable_auto_erase

	set command [base_command]
	switch -- $action {
		program {
			if {[llength $args] < 1 || [llength $args] > 3} {
				error {usage: avrdude program <file> [memory] [format]}
			}
			set file [lindex $args 0]
			set memory [expr {[llength $args] >= 2 ? [lindex $args 1] : "flash"}]
			set format [expr {[llength $args] >= 3 ? [lindex $args 2] : "i"}]
			if {![file exists $file]} {
				error "firmware file does not exist: $file"
			}
			if {$disable_auto_erase} { lappend command -D }
			lappend command -U [memory_spec $memory w $file $format]
		}
		read {
			if {[llength $args] < 2 || [llength $args] > 3} {
				error {usage: avrdude read <memory> <file> [format]}
			}
			set memory [lindex $args 0]
			set file [lindex $args 1]
			set format [expr {[llength $args] == 3 ? [lindex $args 2] : "i"}]
			lappend command -U [memory_spec $memory r $file $format]
		}
		verify {
			if {[llength $args] < 1 || [llength $args] > 3} {
				error {usage: avrdude verify <file> [memory] [format]}
			}
			set file [lindex $args 0]
			set memory [expr {[llength $args] >= 2 ? [lindex $args 1] : "flash"}]
			set format [expr {[llength $args] >= 3 ? [lindex $args 2] : "i"}]
			if {![file exists $file]} {
				error "verify file does not exist: $file"
			}
			lappend command -U [memory_spec $memory v $file $format]
		}
		erase {
			if {[llength $args] != 0} { error {usage: avrdude erase} }
			lappend command -e
		}
		raw {
			if {[llength $args] == 0} {
				error {usage: avrdude raw <avrdude-args...>}
			}
			foreach argument $args {
				lappend command $argument
			}
		}
		default {
			error "unsupported AVRDUDE action '$action'"
		}
	}
	return $command
}

proc ::avrdude_programmer::display_argument {argument} {
	if {$argument eq ""} { return {""} }
	if {[regexp {^[A-Za-z0-9_./:+,=@%-]+$} $argument]} {
		return $argument
	}
	return "\"[string map [list "\\" "\\\\" "\"" "\\\""] $argument]\""
}

proc ::avrdude_programmer::display_command {command} {
	set output {}
	foreach argument $command {
		lappend output [display_argument $argument]
	}
	return [join $output " "]
}

proc ::avrdude_programmer::execute {action args} {
	variable dry_run
	variable working_directory

	set command [build_command $action {*}$args]
	puts "AVRDUDE programmer: [display_command $command]"
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
		error "AVRDUDE command failed: [display_command $command]"
	}
	return $output
}

proc ::avrdude_programmer::show {} {
	variable executable
	variable programmer
	variable part
	variable port
	variable baud
	variable config
	variable dry_run
	variable disable_auto_erase
	variable verbose
	variable working_directory
	variable extra_options

	puts "executable: $executable (resolved: [resolved_executable])"
	puts "programmer: $programmer"
	puts "part: $part"
	puts "port: $port"
	puts "baud: $baud"
	puts "config: $config"
	puts "dry run: $dry_run"
	puts "disable auto erase: $disable_auto_erase"
	puts "verbose: $verbose"
	puts "working directory: $working_directory"
	puts "extra options: $extra_options"
}

proc ::avrdude_programmer::help {} {
	puts {AVRDUDE programmer commands:}
	puts {  avrdude executable auto|<path>}
	puts {  avrdude programmer <id>}
	puts {  avrdude part <id>}
	puts {  avrdude port none|<port>}
	puts {  avrdude baud none|<baud>}
	puts {  avrdude config none|<avrdude.conf>}
	puts {  avrdude disable_auto_erase on|off}
	puts {  avrdude verbose on|off}
	puts {  avrdude dry_run on|off}
	puts {  avrdude working_directory none|<path>}
	puts {  avrdude option clear|<single-avrdude-option>}
	puts {  avrdude show}
	puts {  avrdude command program|read|verify|erase|raw <args...>}
	puts {  avrdude program <file> [memory] [format]}
	puts {  avrdude read <memory> <file> [format]}
	puts {  avrdude verify <file> [memory] [format]}
	puts {  avrdude erase}
	puts {  avrdude raw <avrdude-args...>}
}

proc avrdude {subcommand args} {
	switch -- $subcommand {
		executable {
			set ::avrdude_programmer::executable [::avrdude_programmer::require_one_arg $args {avrdude executable auto|<path>}]
		}
		programmer {
			set ::avrdude_programmer::programmer [::avrdude_programmer::require_one_arg $args {avrdude programmer <id>}]
		}
		part - mcu {
			set ::avrdude_programmer::part [::avrdude_programmer::require_one_arg $args {avrdude part <id>}]
		}
		port {
			set value [::avrdude_programmer::require_one_arg $args {avrdude port none|<port>}]
			set ::avrdude_programmer::port [expr {$value eq "none" ? "" : $value}]
		}
		baud {
			set value [::avrdude_programmer::require_one_arg $args {avrdude baud none|<baud>}]
			set ::avrdude_programmer::baud [expr {$value eq "none" ? "" : $value}]
		}
		config {
			set value [::avrdude_programmer::require_one_arg $args {avrdude config none|<avrdude.conf>}]
			set ::avrdude_programmer::config [expr {$value eq "none" ? "" : $value}]
		}
		disable_auto_erase {
			set value [::avrdude_programmer::require_one_arg $args {avrdude disable_auto_erase on|off}]
			set ::avrdude_programmer::disable_auto_erase [::avrdude_programmer::boolean $value disable_auto_erase]
		}
		verbose {
			set value [::avrdude_programmer::require_one_arg $args {avrdude verbose on|off}]
			set ::avrdude_programmer::verbose [::avrdude_programmer::boolean $value verbose]
		}
		dry_run {
			set value [::avrdude_programmer::require_one_arg $args {avrdude dry_run on|off}]
			set ::avrdude_programmer::dry_run [::avrdude_programmer::boolean $value dry_run]
		}
		working_directory {
			set value [::avrdude_programmer::require_one_arg $args {avrdude working_directory none|<path>}]
			set ::avrdude_programmer::working_directory [expr {$value eq "none" ? "" : $value}]
		}
		option {
			set value [::avrdude_programmer::require_one_arg $args {avrdude option clear|<single-avrdude-option>}]
			if {$value eq "clear"} {
				set ::avrdude_programmer::extra_options {}
			} else {
				lappend ::avrdude_programmer::extra_options $value
			}
		}
		show {
			if {[llength $args] != 0} { error {usage: avrdude show} }
			::avrdude_programmer::show
		}
		command {
			if {[llength $args] < 1} {
				error {usage: avrdude command program|read|verify|erase|raw <args...>}
			}
			set action [lindex $args 0]
			set command [::avrdude_programmer::build_command $action {*}[lrange $args 1 end]]
			puts [::avrdude_programmer::display_command $command]
			return $command
		}
		program - read - verify - erase - raw {
			return [::avrdude_programmer::execute $subcommand {*}$args]
		}
		help {
			if {[llength $args] != 0} { error {usage: avrdude help} }
			::avrdude_programmer::help
		}
		default {
			error "unknown avrdude subcommand '$subcommand'; use 'avrdude help'"
		}
	}
}
