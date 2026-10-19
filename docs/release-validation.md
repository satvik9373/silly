# Non-installing release validation

Use this procedure while developing or preparing a release candidate. It does
not run `build.ps1`; therefore it does not install dependencies, write the
startup registry entry, stop a running Silly instance, copy an installed app,
or launch the GUI.

```powershell
.\scripts\validate-release.ps1 -OutputDirectory "$env:TEMP\silly-release-check"
```

The output directory must be new or empty. The script runs Python regressions,
the Python self-test, Release .NET build, native self-test, self-contained
`win-x64` publish, copies the local `ui` asset tree (including Web Awesome),
runs the published native self-test, verifies the bundled Satoshi Fontshare
EULA remains beside the font, and checks the diff.

Latest recorded run: on 2026-10-18 the validator passed 132 Python tests and
8 subtests, both self-tests, a zero-warning native build, and self-contained
publish at `%TEMP%\Silly-onboarding-20261018`. The published output includes
`ui\assets\fonts\Satoshi-Variable.ttf` and the Fontshare EULA.

## Onboarding visual gate

Run the freshly published `%TEMP%\Silly-onboarding-20261018\Silly.exe` with a
new `SILLY_DIR` and `SILLY_DEVELOPMENT=1`. Inspect Welcome, voice setup,
shortcut practice, and completion. Confirm only Microphone and Speech Model
appear in setup; no Claude card, provider installation action, or setup-card
counter is shown. Confirm controls and keycaps use the bundled Satoshi face,
then complete onboarding with **Start Using Silly**. This remains a manual
acceptance check until a native desktop UI automation session can enumerate
the published window.

The separate installer workflow remains `build.ps1` and must be run only when
you intentionally authorize installation. Before any distribution, perform the
manual Gnani/audio procedure in [gnani-voice.md](gnani-voice.md) and record its
result in the engineering log. Review the supplied Satoshi Fontshare EULA with
the product owner before any public distribution that embeds the font.

The installer builds a complete `%LOCALAPPDATA%\Programs\Silly.next` candidate
before it stops only the exact installed `Silly.exe` path. It promotes that
candidate with an `%LOCALAPPDATA%\Programs\Silly.old` rollback directory; do
not use this installer-validation path without explicitly authorizing an
installation test.

Silly's automatic update setting is opt-in by default. A manual **Check now**
can stage an update after the user requests it; an already staged update does
not restart the application unless automatic updates have been enabled.
