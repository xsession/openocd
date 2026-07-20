$ErrorActionPreference = "Stop"
py -3 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -e .
& .\.venv\Scripts\ti-svd.exe list
Write-Host "Environment ready. Run: .\.venv\Scripts\ti-svd.exe discover --ccs-root C:\ti"
