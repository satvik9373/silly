# Silly V1 action-engine validation

## Final regression run

- `rtk py -3 -m pytest -q`: **64 passed, 8 subtests passed** in 4.32 s.
- `rtk py -3 silly.py --selftest`: `selftest ok`.
- `rtk dotnet publish win\Atticus -c Release -r win-x64 --self-contained -p:DebugType=none -o C:\Users\Satvik chaturvedi\AppData\Local\Temp\silly-action-engine-publish --nologo -v minimal`: succeeded; `Silly.exe` exists in that temporary directory.
- A mock-executor `search_website` action took 0.065 ms to select, validate, construct, and verify its result. This is not an end-to-end desktop latency measurement.

No installer or reference build script was run. Final validation used mock executors for desktop actions and did not stop any processes.

## Scope held back

Arbitrary shell shortcut replay, free-form command shortcuts, shell watchers, and watcher process stopping are disabled until each behavior has a typed action definition and appropriate confirmation policy.
