# Microchip dsPIC SVD files

This directory contains Cortex-Debug-compatible CMSIS-SVD files generated from
the compressed Microchip EDC descriptors in `open_microchip_tools`:

| SVD | Source pack |
|---|---|
| `dspic30f5011.svd` | `Microchip.dsPIC30F_DFP` 1.5.254 |
| `dspic33fj128mc802.svd` | `Microchip.dsPIC33F-GP-MC_DFP` 1.4.235 |
| `dspic33fj128mc804.svd` | `Microchip.dsPIC33F-GP-MC_DFP` 1.4.235 |
| `dspic33ep128gm604.svd` | `Microchip.dsPIC33E-GM-GP-MC-GU-MU_DFP` 1.6.297 |

The files were generated with `dspic-svd` 0.3.0. They pass its structural SVD
validator and its Cortex-Debug compatibility validator. The generator is
Apache-2.0 licensed; the register descriptions remain subject to Microchip's
pack license and are not relicensed as part of OpenOCD.

The local EDC revisions encode some reset values with unknown hexadecimal
nibbles. Those nibbles are represented as unknown bits in each SVD register's
reset mask rather than being treated as zero-valued known bits.
