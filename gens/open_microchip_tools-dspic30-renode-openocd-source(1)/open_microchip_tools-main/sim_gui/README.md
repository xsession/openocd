# mchp simulator GUI (Reflex)

This is a minimal Reflex UI to load firmware and trace/step through it using the clean-room simulator backend.

## Prereqs

From the repo root:

```powershell
python -m pip install -e ".[gui,elf]"
```

Notes:
- `elf` is optional (adds `pyelftools` for `.elf` loading)
- If you only use `.hex`, you can install just `.[gui]`

## Run

```powershell
Set-Location "c:\GIT\open_microchip_tools\sim_gui"
reflex run
```

Then open the URL Reflex prints (usually http://localhost:3000).
