"""Legacy namespace shims for `com.microchip.mplab.mdbcore.simulator`.

This namespace is extremely large in Java. We provide a minimal real `Simulator`
implementation plus a lazy stub importer so any `com.microchip.mplab.mdbcore.simulator.*`
imports resolve without needing to generate thousands of files.
"""

from mchp_simulator.stub_importer import install as _install

_install("com.microchip.mplab.mdbcore.simulator")

__all__ = []
