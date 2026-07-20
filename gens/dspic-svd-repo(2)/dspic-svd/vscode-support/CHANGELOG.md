# Changelog

## 0.3.0

- Add xsession/renode custom-cores static compatibility validation.
- Add dsPIC30F5011 Renode smoke script and Cortex-Debug launch template.
- Document missing exact platform models and experimental GDB/interrupt limitations.

## 0.2.0

- Validate generated files against the XML shape consumed by Cortex-Debug's peripheral viewer.
- Add all four selected dsPIC devices.
- Add an explicit `svdFile` fallback for Cortex-Debug versions without support-pack registration.
