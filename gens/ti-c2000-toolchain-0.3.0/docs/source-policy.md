# Source and redistribution policy

The generator code is MIT licensed. Generated SVD files are derivative metadata and retain the license and redistribution conditions of the TI files from which they were produced.

MSPM0C1103 is generated from the public Texas Instruments CMSIS device-family pack. The repository pins the pack version and URL in `sources.lock.json`.

C2000 devices are generated from the `devices` and `Modules` directories in a local Code Composer Studio `targetdb`. Those files are not copied into this repository. This avoids silently redistributing a CCS installation and ensures the output matches the user's installed TI device support package.

Before publishing generated files, review the license shipped with the corresponding TI SDK or CCS device support package.
