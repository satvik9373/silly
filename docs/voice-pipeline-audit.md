# Voice pipeline audit — Silly V1 Milestone 3

## Runtime path

1. `Silly.exe` starts `Overlay` and installs the configured global hotkey through `Hooks`.
2. `Overlay.Start()` immediately renders **Listening**, starts the existing local
   `Speech` microphone capture, and receives partial Whisper transcripts.
3. On hotkey release, `Overlay.StopListening()` renders **Transcribing** and asks
   `Speech.Stop()` for its final local transcript. Repeated hotkeys/callbacks are
   guarded by `shortcutDown`, `listenID`, and `stops`.
4. `Overlay.Run()` renders **Acting**, sends the final transcript to the Python
   `--wait` process, and handles its structured output on the UI thread.
5. `silly.py` is only the installed/development entry shim; it executes
   `atticus.py`, which calls the typed action router before starting an AI
   provider. `✓` produces Done/success; `!` produces a useful failure state;
   Escape produces Cancelled.

## Connection corrected in this milestone

The C# worker had already carried final transcripts to Python, but the Python
`--wait` path initialized its provider and a screenshot worker before trying a
deterministic action. It now defers both until the typed action router declines
the finalized transcript. Deterministic app launches and website searches
therefore make no provider request and do not capture the desktop.

The overlay records activation-to-final-transcript, final-transcript-to-action,
and activation-to-completion timings locally in `voice-timings.jsonl` under
Silly's configured data directory. Python records router, first-action, and
action-verification timings in `log.jsonl`. Neither file is transmitted.

## Current environment limitation

The existing local Whisper model was not present in
`%LOCALAPPDATA%\Silly\models` during validation. The C# host and final-
transcript route were smoke-tested with `SILLY_DEMO`, but a microphone-originated
transcript cannot be honestly claimed until that model is installed and a user
performs the documented voice smoke test.
