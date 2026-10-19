# Silly V1 completion checklist

This checklist distinguishes evidence obtained by mocks from evidence obtained
on a real Windows desktop. A checked item is not a claim that a broader item
has also been verified.

## Current evidence

| Area | Status | Evidence |
| --- | --- | --- |
| Product identity and isolated storage | PASS | `Silly` assembly, `%APPDATA%\\Silly`, `%LOCALAPPDATA%\\Silly`, `silly.v1` pipe, and `Silly` startup entry are covered by regression tests. |
| Typed deterministic action boundary | PASS (mock and isolated desktop) | `open_application`, validated URL/navigation/search, and window arrangement have typed schemas and mock tests. Both native `--wait` and live `--fast` use only that registry plus approved typed shortcuts; the documented `SILLY_DEMO` smoke run opened Notepad and a YouTube search without an AI request. |
| Normal reply delivery is single-shot | PASS (mock) | `ResponseDelivery` deduplicates completed responses before calling the response speaker. |
| Default read-aloud preference | PASS (code/self-test) | `speak` defaults to `true`; an explicit saved `false` remains an opt-out. |
| Gnani STT protocol | PASS (mock protocol); BLOCKED (real API/audio) | Options, frame pacing, transcript parsing and failure handling are native-self-tested. Real credentials/audio validation has not been run in this task. |
| Gnani TTS protocol | PASS (mock protocol); BLOCKED (real API/audio) | Model/voice validation and streamed PCM parsing are native-self-tested. A real selected-voice call and audible normal reply still need manual verification. |
| Normal Gnani response versus Test Voice | PASS (mock); BLOCKED (real audio) | Both routes derive one validated `GnaniTtsOptions` request plan, share the streaming transport, preserve sanitized fallback failure context, and are native-self-tested. A real selected-voice call and audible normal reply still need manual verification. |
| Local speech fallback | PASS (mock selection); BLOCKED (audible desktop) | Fallback is explicit and labelled as Windows local. Audible fallback needs a manual desktop check. |
| Browser/direct app requests without AI | PASS (mock and isolated desktop) | The typed route now precedes instant-command, commit-marker, subscription, and provider gates. The held-out corpus covers navigation versus search, domains, punctuation, Unicode, Hinglish/Hindi, and safe browser dispatch. |
| AI provider router (Claude subscription, ChatGPT plan) | PASS (mock); BLOCKED (account live checks) | Settings selects the text-only router for unresolved requests and validates priority, actual provider/model identity, cancellation, authentication/quota/rate-limit/temporary failover, explicit no-additional-charge policy, and no replay after a started provider request. Direct commands remain independent. Live account validation remains blocked as recorded below. |
| ChatGPT plan authorization | PASS (mock); BLOCKED (current local session) | SIWC has stable host registration, loopback PKCE/state/nonce, callback/identity validation, direct-plan-scope gating, protected per-account records, refresh rotation, revoke-on-disconnect, and `store:false` streaming Responses tests. The user reported a prior smoke test, but it was not recorded; current sanitized status is `Not connected`, so a factual live PASS cannot be claimed. |
| Claude subscription provider | PASS (mock); BLOCKED (current local session) | Claude subscription supports explicit Max/Team Claude Code sessions, has Free-only approval, bounded pre-dispatch failover, and refuses replay after a started request. Current sanitized status says Claude Code is not installed. |
| Cloud consent/settings | PASS (code review); BLOCKED (manual UI) | Defaults are local; Gnani selection and disclosure are explicit in onboarding/settings. Manual persistence verification remains. |
| Security/reliability audit | PARTIAL | Typed direct actions and the active read-only AI tool list were audited; on 2026-10-18 `dotnet list ... --vulnerable --include-transitive` reported no known vulnerable NuGet packages and `py -3 -m pip check` reported no broken requirements. Automatic update staging/restart is opt-in. Legacy helper surfaces and isolated update behavior still need further verification. |
| Packaging/installer | PARTIAL | On 2026-10-18, `scripts/validate-release.ps1` passed 130 tests + 8 subtests, both self-tests, build, isolated self-contained `win-x64` publish at `%TEMP%\Silly-v1-release-20261018-25`, attribution-asset and staged Python-import checks, and diff check without installation. Staging and activation are separate: a manually staged update cannot restart Silly unless automatic updates are enabled. Installer/update and isolated-profile behavior are not yet verified. |

## Required manual acceptance procedure

The exact real Gnani and audible-reply procedure is in
[gnani-voice.md](gnani-voice.md). It deliberately requires a user-initiated
development run with `GNANI_API_KEY` only in that process environment. Do not
run it from CI or automated tests.

## Next work

1. Intentionally run the documented [Gnani STT and TTS smoke tests](gnani-voice.md)
   from a development shell that contains `GNANI_API_KEY` only in its process
   environment. Record only PASS, FAIL, latency, selected/fallback provider,
   and sanitized errors—never a key, transcript, or audio recording.
2. Run the local Whisper microphone and audible Windows-local fallback checks
   from [voice-development-smoke-test.md](voice-development-smoke-test.md).
   Confirm the visible lifecycle, cancellation, and exactly-once action/result
   behavior on a real desktop.
3. Restore/select an authorized ChatGPT-plan account and, separately, install
   and sign in to a supported Claude Code subscription before live provider
   validation. Record only PASS, FAIL, or BLOCKED and never a credential/token.
4. With explicit installation authorization, test the installer/update path in
   an isolated profile and confirm that a separately installed reference app is
   neither stopped nor changed. Do not use the production profile for this test.
5. Before distribution, review the final diff for credentials and accidental
   execution paths, then perform the visual UI acceptance check and supplied
   Satoshi font-license review.
