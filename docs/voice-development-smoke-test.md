# Development voice smoke test

This procedure deliberately starts a temporary development copy. It does not
run `build.ps1`, install Silly, or write a Windows startup entry.

```powershell
.\scripts\run-dev.ps1 -Keep
```

The launcher publishes to a new `%TEMP%\silly-dev-<guid>` folder, creates a
throwaway virtual environment there from the pinned `requirements.txt`, gives
the copy an isolated `SILLY_DIR`, disables scheduled updates, and points it at
the source helper through `SILLY_SCRIPT`. It leaves the installed application
and its `%APPDATA%\Silly` data untouched. The development command may download
the pinned Python packages into that temporary environment; it does not run
the installer or alter an installed Silly copy.

Before testing voice, ensure the local Whisper model has already been set up
for Silly and microphone permission is enabled. Hold the configured hotkey
(`Ctrl` + `Alt` + `Space` by default), say **Open Notepad**, then release it.
Verify Listening, Transcribing, Acting, and Done appear in the overlay and
that Notepad opens. Press Escape while recording or acting to verify
cancellation. A separate optional test is **Search YouTube for React
tutorials**; it opens the encoded search URL through the registered browser.

These are desktop smoke tests. Unit tests must continue to use mock action
executors and must not launch applications or a browser.

For a repeatable host-to-router smoke test when a microphone model is not
present, start the same isolated build with a final transcript injected by the
host:

```powershell
.\scripts\run-dev.ps1 -Keep -Demo 'Open Notepad'
```

This intentionally launches Notepad through the typed registry. It verifies
the C# host, Python entry point, validated action router, and overlay result,
but it is not a substitute for the microphone smoke test.
