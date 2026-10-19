# Voice-integration validation

## Automated

- `rtk py -3 -m pytest -q`: **66 passed, 8 subtests passed**.
- `rtk py -3 silly.py --selftest`: `selftest ok`.
- Native `Silly.exe --selftest`: `native selftest ok`.
- Direct .NET publish to a temporary directory succeeded.

## Isolated desktop smoke tests

`scripts\run-dev.ps1 -Keep -Demo 'Open Notepad'` started a temporary
development `Silly.exe` without an installer or startup registration. It
launched real Notepad through `open_application`; the isolated log recorded
zero AI cost, 0.703 ms routing, and 2381.106 ms launch/verification.

`scripts\run-dev.ps1 -Keep -Demo 'Search YouTube for React tutorials'` used
the same C# host and Python `--wait` route. It invoked the registered browser
with the encoded YouTube search URL; the isolated log recorded zero AI cost,
0.184 ms routing, and 120.592 ms action/verification.

Both temporary Silly processes and the Notepad process launched for the first
smoke test were then closed by their exact process IDs. Existing browser
processes were left untouched.

## Not completed here

The local Whisper model was absent, so no microphone speech was transcribed in
this environment. Follow `voice-development-smoke-test.md` after the existing
speech model has been set up to complete that distinct real-voice test.
