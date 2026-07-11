# Windows build and installation

The maintained Windows instructions are now in the Sphinx/MyST guide:

- [Build the Windows package](docs/deployment/windows.md)
- [Prerequisites](docs/getting-started/prerequisites.md)
- [Troubleshooting](docs/deployment/troubleshooting.md)
- [First debug session](docs/usage/first-session.md)

Quick build:

```powershell
docker compose up --build windows-x86_64
```

Output:

```text
docker\data\dist\windows\openocd-windows-x86_64.zip
```
