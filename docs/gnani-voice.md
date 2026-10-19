# Gnani cloud voice configuration and smoke test

## Privacy and selection

Silly defaults to **Local Whisper**. Select **Gnani Cloud** in Settings only
when you want microphone PCM audio sent to Gnani for transcription. The
selected cloud language defaults to `en-IN`; choose another supported language
in Settings when appropriate. Local Whisper remains the configured fallback by
default; selecting **Show error** makes a cloud failure stop instead.

During development, set the key only in the launching process:

```powershell
$env:GNANI_API_KEY = '<your Gnani key>'
.\scripts\run-dev.ps1 -Keep
```

Do not put the key in `settings.json`, a source file, a command history shared
with others, or a diagnostic report. The user-facing credential store uses the
current user's Windows Credential Manager rather than application settings. No
automated test connects to Gnani or consumes credits.

The C# speech host removes `GNANI_API_KEY` from every Python helper it starts.
That keeps a development speech key out of the Python brain, text-provider
subprocesses, their diagnostics, and their child environments; the C# Gnani
transport remains the only development process that receives it.

## Protocol implementation

**Documentation review (2026-10-18).** The current official [realtime STT
documentation](https://docs.gnani.ai/api/STT/stt-websocket) confirms the
endpoint, `x-api-key-id` header, 16 kHz signed-16-bit mono PCM, exact
1,024-byte frames, 32 ms real-time cadence, and transcript segment fields used
below. The official [realtime TTS documentation](https://docs.gnani.ai/api/TTS/tts-websocket)
confirms the separate endpoint/header, raw linear PCM request configuration,
ordered Base64 audio chunks, and final `complete` message. This was a
read-only documentation audit; no credential or cloud request was used.

The C# client connects to `wss://api.vachana.ai/stt/v3/stream` with
`x-api-key-id`, `lang_code`, `x-sample-rate: 16000`, and short-command VAD
headers. It sends signed 16-bit little-endian mono PCM in exact 1,024-byte
frames every 32 ms, but only after validating Gnani's initial `connected`
message confirms the expected 16 kHz / 512-sample contract. Gnani transcript
events are ordered by `segment_index`;
identical retransmissions are ignored, while a changed final version of an
existing segment safely replaces its interim text. They are shown live and
dispatched only after the hotkey release finalizes the turn. Connection,
credential, quota, and timeout errors never become a command.

At end-of-turn, any PCM fragment below 1,024 bytes is zero-padded instead of
being discarded, then Silly sends enough complete silent frames to satisfy the
selected VAD silence window. This preserves the tail of short utterances while
keeping Gnani's required binary frame size.

The current Gnani realtime documentation lists individual language codes for
STT; it does not list a separate Hinglish STT code. Silly therefore preserves
the selected supported language and its transcript verbatim rather than
silently mapping a saved `mixed` setting to English. Gnani's `verbatim` format
and optional single-word bias list are used for command names. For short voice
commands Silly requests 100 ms minimum speech/segment and sends enough PCM
silence after hotkey release to satisfy the configured VAD end-of-speech
window. This is protocol compliance, not model fine-tuning.

If the user releases the hotkey during the initial connection, Silly waits a
bounded two seconds for the verified sender to drain the already captured
frames. It then follows the configured local fallback/error path; it never
turns an incomplete cloud turn into a command.

Gnani TTS has a separate provider interface and Windows TTS remains the
default playback path. Before making Gnani the default, compare first-audio
latency, interruption behavior, and streaming PCM playback with Windows TTS
using a short, non-sensitive phrase and record the result.

Gnani server and transport errors are normalized before display or local
diagnostics: invalid-key/authentication, quota/credit, timeout, and connection
failures receive distinct recovery guidance. Silly does not display provider
response text, request data, or credentials. A transcription failure remains a
failure or an explicitly configured local fallback; it is never treated as a
command.

## Speech output

Silly can use **Gnani Cloud** for replies, but Windows local speech remains the
default and configured fallback. Gnani is always opt-in: selecting it sends
the reply text (not the microphone recording) to Gnani. In Settings, choose
the model (`timbre-v2.5` or `timbre-v3.0`), a compatible voice, language
(including `hi-en` for Hinglish), speed, and whether to speak full or brief
answers.

For development, `GNANI_API_KEY` is read only from the process environment.
When a user saves a key in Settings, Silly writes it to the current user's
Windows Credential Manager entry `Silly/GnaniApiKey`; it never writes that key
to `settings.json`, a command line, or a diagnostic log. Leaving the key box
empty deletes the saved Credential Manager entry.

The TTS client uses `wss://api.vachana.ai/api/v1/tts` and the `X-API-Key-ID`
upgrade header. It requests 24 kHz, mono, 16-bit raw linear PCM, validates the
ordered Base64 chunks, and feeds them to a streaming PCM buffer. This avoids
incorrectly concatenating WAV headers. A failed, cancelled, malformed, quota,
or connection response is an explicit outcome. If enabled, Silly then says the
same response through Windows local speech and shows that it used the fallback.

The model and voice are validated together against Gnani's published catalog:
Timbre v2.5 voices cannot be used with Timbre v3.0, or vice versa. Settings
updates the voice list when the model changes, and the Voice diagnostics row
shows the preferred and actual providers plus the active model, voice, language,
credential source, and last sanitized provider error. **Test selected Gnani
voice** is the only settings control that deliberately makes a cloud TTS call;
it uses the exact current model, voice, language, and speed and does not silently
fall back to Windows speech.

The **Voice diagnostics** row also records the last selected request as either
`Test Voice: Gnani Cloud (...)` or `Normal reply: Gnani Cloud (...)`. This
contains only model, voice, language, and speed—never the API key or reply
text. When a normal reply falls back, compare that configuration with the Test
Voice entry and inspect the accompanying sanitized failure reason. The normal
and diagnostic calls share the same Gnani transport and PCM playback path; the
normal call alone may use the explicitly enabled Windows-local fallback.

The response contract separates display/spoken text and confirmed outcome
status from the worker that produced it. Both deterministic actions and AI
answers use this presentation path; no spoken reply can repeat an action.
Starting a new microphone turn or pressing the hotkey while speaking cancels
playback before microphone capture, so Silly does not intentionally transcribe
its own voice.

## Manual real-API smoke test

Use the local-only [voice command corpus](voice-command-corpus.md) to measure
final-transcript routing consistently. Do not add its recordings or transcripts
to the repository.

1. Set `GNANI_API_KEY` in the current PowerShell process; do not paste it into
   logs or source.
2. Run `scripts\run-dev.ps1 -Keep`. It uses an isolated temporary data folder,
   does not install Silly, and does not register startup.
3. In Silly Settings, explicitly select **Gnani Cloud** and confirm the notice
   that microphone audio will be sent to Gnani.
4. Hold the configured hotkey, say **Open Notepad**, and release. Verify live
   words appear, then Acting and Done; verify the log reports zero AI cost.
5. Repeat once with **Search YouTube for React tutorials**. Verify that only
   the encoded search URL opens—not a browser research workflow.
6. Temporarily remove `GNANI_API_KEY` or disconnect network and repeat. Verify
   local fallback or a clear non-command error, according to the setting.

Only run this procedure intentionally: it sends audio to Gnani and can consume
the account's credits.

## Manual TTS smoke test

1. In the same PowerShell session, set `GNANI_API_KEY` only for the process,
   then run `scripts\run-dev.ps1 -Keep`.
2. In **Settings → Sound**, enable **Read answers aloud**, choose **Gnani
   Cloud** under Speech output, and select an appropriate model/voice/language.
3. Hold the hotkey, say **Open Notepad**, and release. Verify Notepad opens
   before the spoken acknowledgement; the overlay should say Gnani Cloud while
   it speaks.
4. Press Esc during a longer spoken response. Verify audio stops and no command
   is replayed.
5. In a separate temporary shell without `GNANI_API_KEY` (or by intentionally
   choosing an invalid saved key), repeat with Windows fallback enabled. Verify
   the overlay explicitly reports Windows local voice rather than Gnani.

No real TTS API smoke test has been run by the automated suite.

## Privacy-preserving latency comparison

`voice-timings.jsonl` stores timing numbers, the selected transcription
provider, outcome, and an optional developer sample label; it never stores
audio or transcript text. To compare the same deliberately consented command
set through Gnani and Local Whisper, set a harmless non-secret label such as
`SILLY_VOICE_SAMPLE_ID=commands-a-01` for each paired run, then summarize the
local log:

```powershell
py -3 scripts\voice_latency_report.py $env:APPDATA\Silly\voice-timings.jsonl
```

The report gives provider-specific sample counts, transcription-error counts,
and p50/p95 timings. It lists only sample labels that have both Gnani and Local
Whisper observations, so it does not imply a fair comparison when the samples
do not match.
