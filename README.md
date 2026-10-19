# Silly

Silly is a Windows voice assistant. Hold `Ctrl` + `Alt` + `Space`, speak, and release to ask for help with your PC.

## Build and run

From a Silly source checkout, run `build.ps1`. It builds `Silly.exe` and installs only for the current user. The installer script requires an explicit `SILLY_REPOSITORY` value; it does not clone or update the upstream technical-reference repository.

Silly keeps its data separate from other applications:

- Settings, memory, history, and logs: `%APPDATA%\Silly`
- Speech model and virtual environment: `%LOCALAPPDATA%\Silly`
- Program files: `%LOCALAPPDATA%\Programs\Silly`
- Startup entry: `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\Silly`

The build script only stops `Silly.exe` when its executable path is exactly
Silly’s own installation path. It first prepares a complete sibling candidate
and promotes it with a rollback path, rather than copying over a live install.
It does not stop, copy, migrate, or modify any separately installed reference
application.

For a non-installing local verification, run:

```powershell
py -3 -m pytest -q
py -3 silly.py --selftest
dotnet publish win\Atticus -c Release -r win-x64 --self-contained -p:DebugType=none -o <temporary-output-directory>
```

Or run the complete non-installing release check described in
[docs/release-validation.md](docs/release-validation.md).

For the opt-in Gnani cloud speech configuration and its credit-consuming manual
smoke test, see [docs/gnani-voice.md](docs/gnani-voice.md). Local Whisper is
the default and no API credential is stored in this repository.

## Privacy

Silly has no telemetry transport and does not send usage, request, failure, or
diagnostic data to a product analytics service. Cloud speech and account-backed
AI remain explicit user-selected features, described in their respective
settings and documentation.

## Attribution and license

Silly was developed from an open-source Windows technical reference, itself based on the Atticus macOS project by SaarthurR. The included [MIT License](LICENSE) and third-party notices remain applicable.
