# Silly V1 engineering log

## 2026-10-18 — Gnani key process isolation

**Audit.** The native host inherited a development `GNANI_API_KEY` into every
Python helper. Although the helper does not use Gnani, its unresolved-request
path can start text-provider subprocesses, expanding the secret's process
scope unnecessarily.

**Change.** `Py.Start` now removes `GNANI_API_KEY` from each child environment.
The C# speech transport retains the process-only development key; Python,
Claude, and text-provider paths do not receive it.

**Evidence.** Static regression coverage asserts the filter is applied on every
child path, and the native self-test removes a mock key from an actual child
`ProcessStartInfo` environment. The focused identity/brain/provider suite
passed 79 tests; the native build/self-test passed without reading, logging, or
sending a real key.

## 2026-10-18 — explicit cloud-speech consent regression

**Change.** Added a cross-layer regression for the cloud-speech selection
contract: fresh settings default to local Whisper and Windows-local TTS, the
settings and onboarding UI disclose what Gnani receives, and the native host
accepts only explicit local/Gnani provider values.

**Evidence.** The identity/UI checks passed without a desktop or cloud request.
This guards the opt-in boundary but does not replace manual consent-persistence
or real-audio verification.

## 2026-10-18 — final PCM-fragment preservation

**Change.** Gnani STT now zero-pads the final partial 16-bit PCM buffer to one
valid 1,024-byte frame when the hotkey is released. Previously, a buffer below
the strict provider frame size could be dropped, losing the tail of a short
utterance. The padded bytes are PCM silence and preserve the documented
real-time frame contract.

**Evidence.** Native self-tests verify complete framing, one padded tail, and
an empty second flush. The Release build had zero warnings/errors and all 128
Python tests plus 8 subtests passed without microphone or cloud activity.

## 2026-10-18 — installed-helper import smoke regression

**Change.** Added an isolated Python packaging regression that copies exactly
the staged helper layout—renaming `atticus.py` to `silly.py`, with its direct
modules and integrations—then executes only `silly.py --help`. It uses a fresh
temporary Silly data directory and explicitly removes `GNANI_API_KEY` from the
child environment.

**Evidence.** The staged helper imports successfully without access to the
source tree and does not launch the desktop, call a provider, or run an action.
This is a stronger import-boundary check, not a substitute for installer or
desktop acceptance testing.

## 2026-10-18 — reproducible isolated development launcher

**Change.** `scripts/run-dev.ps1` now creates its Python 3.11+ virtual
environment inside the new temporary development directory and installs the
pinned requirements there before publishing/running the debug copy. The
launcher continues to use an isolated `SILLY_DIR`, source helper, development
mutex, and no installer or login-startup registration.

**Evidence.** Static regressions verify the temporary environment and reject
installer/startup references. The release validator also now checks the staged
Python import manifest; it passed 127 tests plus 8 subtests, both self-tests,
zero-warning build, and self-contained publish without installing or launching
Silly.

## 2026-10-18 — staged Python runtime completeness

**Audit.** `silly.py` imports the typed action registry and AI-provider router
from its installed directory. The installer had copied the entry script but
not those new modules, so an installed build could fail before its first voice
request even though a native-only publish passed.

**Change.** The installer now stages `action_engine.py` and
`ai_provider_router.py` with the existing Python helpers. Identity regression
coverage and the non-installing release validator both assert the complete
direct-import manifest without invoking the installer.

## 2026-10-18 — short-utterance cloud drain

**Change.** When a user releases the hotkey during the initial Gnani
connection, STT now waits up to two seconds for the verified sender to start,
then drains the PCM frames captured during the handshake. This prevents a
short first command from being discarded solely because the connection began
slightly later. Cancellation, the existing overlay timeout, and local fallback
remain authoritative.

**Evidence.** The change shares the native protocol self-test path; the
Release build had zero warnings/errors and the full Python suite passed 125
tests plus 8 subtests. Real network/microphone latency remains a manual smoke
test, not a simulated claim.

## 2026-10-18 — dependency health check

**Evidence.** `dotnet list win\\Atticus\\Atticus.csproj package --vulnerable
--include-transitive` reported no known vulnerable NuGet packages from the
current configured source. `py -3 -m pip check` reported no broken Python
requirements. `pip-audit` is not installed, so no claim is made about a Python
vulnerability-database scan. These were read-only checks; no dependency was
installed or updated.

## 2026-10-18 — Gnani STT handshake gate

**Change.** The persistent STT session now waits for Gnani's documented
`connected` message before releasing buffered microphone frames. It validates
the echoed 16 kHz sample rate and 512-sample chunk size against Silly's
1,024-byte PCM framer. A malformed, error, or incompatible handshake becomes a
sanitized transcription failure rather than sending audio on an uncertain
stream.

**Evidence.** Native self-tests cover accepted, incompatible-format, and
credential-error handshake messages. The Release build had zero warnings and
errors; all 125 Python tests and 8 subtests passed. No cloud connection,
microphone capture, desktop launch, or installation ran.

## 2026-10-18 — public action-path narrowing

**Audit.** The native overlay used `--fast` for partial-transcript latency,
while the completed transcript used `--wait`. Although direct actions were
already typed first, both paths could still reach the historical convenience
parser after an unmatched route.

**Change.** Added `deterministic_action()` as the sole public fast-action
policy: a schema-validated registry action, followed only by one previously
approved typed shortcut. `--fast` now exits for an unmatched phrase rather
than invoking a legacy parser, player, shell shortcut, or AI provider. The
finalized `--wait` path follows the same typed-shortcut policy before selecting
its text-only provider.

**Evidence.** Mock regressions prove an unsupported fast request starts neither
the legacy player nor a provider, and a finalized approved shortcut bypasses
the legacy parser. Focused action/brain tests passed 62 tests; the Python
self-test passed. No desktop action, microphone, cloud call, or installation
ran.

## 2026-10-18 — Gnani protocol documentation verification

**Audit.** Re-read Gnani's current official realtime STT and TTS WebSocket
documentation. The implemented STT endpoint/header, 16 kHz signed PCM framing
and 32 ms pacing match the documented contract. The implemented TTS
endpoint/header, raw 24 kHz PCM request, ordered Base64 chunk validation, and
completion frame also match the current documented contract.

**Evidence.** This was a read-only documentation check; it did not use
`GNANI_API_KEY`, create a socket, capture audio, or consume credits. Mock and
native self-tests remain the only protocol execution evidence until the
documented manual smoke test is intentionally performed.

## 2026-10-18 — Gnani error normalization

**Change.** Gnani STT and TTS server errors no longer surface arbitrary
provider text. The transport maps credential/authentication, quota/credit,
timeout, and connection failures to distinct sanitized recovery messages.
Other provider failures receive a generic settings/connection message. Local
fallback still occurs only when explicitly selected; a failed transcript never
becomes a command.

**Evidence.** Native self-tests exercise sanitized quota, credential, timeout,
and transport outcomes as well as the existing mock protocol parsers. A clean
Release build and focused Python action/brain checks passed. No Gnani request,
microphone capture, application launch, or installation occurred.

## 2026-10-18 — AI routing and direct-navigation completion pass

**Audit.** The typed `route_action` path already preceded the legacy `fast`
handler, but the finalized request path still made that route conditional on
the Instant preference and commit marker. `Search for <query> on YouTube` was
also being parsed as a Google query. The API adapters were wired for selected
non-Claude providers, but Free-only indiscriminately blocked every API route,
and an unavailable Claude Code session could not hand off to configured API
backups.

**Change.** Finalized typed actions now run before every provider, licence,
commit-marker, or Instant-command gate. A typed failure is final and reported
truthfully rather than being sent to a model. The parser recognizes trailing
site forms while preserving query casing, domains, hyphens, punctuation, and
Unicode. The text-only provider contract now returns the actual model identity,
uses a bounded timeout, validates model identifiers before provider URL
construction, supports cancellation before dispatch, and has ordered,
single-attempt failover. In Free-only mode it contacts only a provider the user
has explicitly marked as a documented no-additional-charge route; all other
routes are skipped without network contact. If Claude Code is unavailable, a
configured eligible API backup can answer an unresolved request. The same
backup path handles a Claude Code CLI that cannot be warm-started.

**Safety.** The explicit approval is intentionally not guessed from a secret
or subscription. Current official docs were rechecked: Claude Code access is
separate from Console API billing; OpenAI's ChatGPT-plan capability now uses
the documented Sign in with ChatGPT OAuth flow with explicit consent; Gemini
lists free availability by individual model/tier. No browser cookie, consumer
session token, or undocumented OAuth flow is used. Provider output remains
text only and cannot reach the action registry as a command.

**Mock evidence.** Focused direct-action/provider routing tests passed: 37
tests in 0.53 seconds. They include the requested direct corpus, no-provider
gate ordering, no-charge eligibility, credential and quota failover, timeout,
cancellation, provider/model attribution, and Claude-Code-unavailable API
backup behavior. No live provider request or desktop action was made.

**Final validation.** The full Python suite passed with 96 tests and 8
subtests in 12.76 seconds; `silly.py --selftest` passed; Release .NET build
passed with zero warnings/errors; and the native self-test passed. The existing
non-installing release validator was invoked with the fresh isolated output
directory `%TEMP%\silly-ai-routing-final-20261018`; its captured output showed
the suite, Python self-test, release build, native self-test, and publish
starting. The terminal host truncates this long script at 30 seconds, so the
published `Silly.exe --selftest` and `git diff --check` were also run directly
afterward and completed without error. No installer, startup setting,
application launch, or provider request was run.

**External blocker.** Live provider validation is still BLOCKED: no specific
provider/model has been demonstrated as an authorized no-additional-charge
route for this milestone. Do not run a live request until the user selects a
provider, configures an explicit model, and confirms its account/tier is
eligible. The remaining full release validation is due after final test and
documentation review.

## 2026-10-17 — end-to-end V1 audit

**Observed architecture.** The Windows host installs the configured hotkey and
starts `Overlay`. `Speech` captures 16 kHz mono microphone PCM and uses either
local Whisper or the opt-in Gnani STT session. On release, `Overlay` sends the
final transcript to `silly.py --wait`; that shim starts `atticus.py`. The
Python entry point selects the typed deterministic action route before it
initializes the Claude provider. The overlay turns the confirmed result into
an `AssistantResponse` and delivers it through `ResponseDelivery` to `Voice`.

**Current voice finding.** `Test selected Gnani voice` and normal replies both
call `GnaniTtsOptions.TryFromPrefs`. The difference is intentional fallback:
the diagnostic call reports the Gnani result directly, whereas a normal reply
can fall back to Windows speech when `ttsFallback` is enabled. Therefore an
audible Windows reply does not prove that Windows was selected; it can conceal
a Gnani transport or protocol failure. The next change exposes the selected
request configuration and preserves the sanitized Gnani failure alongside the
fallback result.

**Safety findings.** Direct OS actions use the Python `ActionRegistry`; unknown
identifiers, unexpected fields, unsafe URL schemes, invalid placement targets,
and ambiguous application matches are rejected. Claude is started with only
`WebSearch,WebFetch` and explicitly disallows Bash/Read. Legacy command-string
shortcut replay is unreachable. Some legacy helper command-line actions remain
in `atticus.py` for host-controlled use and require a separate audit before any
new provider can invoke them.

**Known external blockers.** This environment has no available native desktop
surface for microphone or audible playback verification. No real Gnani request
was made during this audit; doing so intentionally consumes user credits. The
manual procedure remains required for real STT/TTS acceptance.

**Validation already observed before this audit.** Python tests passed (72
tests and 8 subtests); `silly.py --selftest`, native self-test, .NET build,
self-contained publish, and `git diff --check` passed. The next iteration will
rerun these after the focused change and record fresh results.

**Next task.** Add a shared, sanitized Gnani TTS request plan and tests for the
normal response path, fallback, cancellation, duplicate delivery, and explicit
mute behavior. Then run mock and native validations before asking for the
single, intentional real-device smoke test.

## 2026-10-17 — normal Gnani reply diagnostics

**Change.** `GnaniTtsRequest` is now the common request description for Test
Voice and normal replies. Both routes call the same `SpeakGnaniAsync` transport
and streamed-PCM playback method. `Voice.LastRequest` records only model,
voice, language, and speed; Settings displays that selected request alongside
the actual provider and sanitized error. A normal Gnani configuration failure
now preserves its reason when Windows-local fallback succeeds. Duplicate
completion no longer changes the clipboard when automatic copy is enabled.

**Regression evidence.** Native self-test now verifies normal and diagnostic
requests have identical selected configuration and emit the expected model,
voice, language, and raw-PCM payload. It also retains the existing duplicate
delivery and fallback-selection checks. `py -3 -m pytest -q` passed: 72 tests,
8 subtests, 4.37 seconds. `py -3 silly.py --selftest` and the native release
self-test both passed. `dotnet build win\\Atticus -c Release` passed with zero
warnings and zero errors.

**Remaining blocker.** No live Gnani request or audible desktop run was made.
Run the documented manual test once to compare `Test Voice` and `Normal reply`
in Settings after an action; the diagnostics will identify a fallback rather
than presenting it as a selected Gnani voice.

## 2026-10-17 — AI action-boundary audit

**Observed risk.** The active Claude process already allowed only
`WebSearch,WebFetch`, but its inherited prompt still described Bash and local
helper commands. That mismatch could lead to misleading AI claims and would be
unsafe if tool configuration drifted later.

**Change.** The active provider prompt now states its read-only capability and
explicitly forbids shell commands, local actions, external side effects,
credentials, and safety-control bypass instructions. It directs common local
requests to the preceding typed deterministic engine and reports unsupported
local work as unavailable. The legacy text is retained only as inactive
technical-reference material while its remaining helper surfaces are audited.

**Regression evidence.** `tests/test_action_engine.py` passed all 18 tests.
The new assertion verifies the active prompt is read-only and does not contain
the `Bash` capability. Full-suite/build validation remains due after the next
coherent batch.

## 2026-10-17 — direct navigation hardening

**Change.** The Windows executor focuses an already-running matched
application before using the existing validated launcher. The deterministic
router now removes conversational framing without modifying captured names or
queries, and recognizes a new Chrome/Edge tab phrased either way around. These
requests resolve to `open_application` or `open_browser_url`; no provider is
started.

**Regression evidence.** Focus-before-launch, polite navigation, and both
new-tab phrasings are covered by mock tests. Focused action-engine suite:
20 passed in 0.13 seconds.

## 2026-10-17 — Gnani documentation recheck

**Verification.** Read Gnani's current official documentation bundle and the
STT/TTS reference pages. It still documents STT at
`wss://api.vachana.ai/stt/v3/stream` with `x-api-key-id`, and TTS at
`wss://api.vachana.ai/api/v1/tts` with `X-API-Key-ID`. TTS requests use JSON
audio chunks carrying ordered Base64 PCM and a final `complete` event. Both
Timbre v2.5 and v3.0 remain documented; voices are model-specific. The current
implementation's endpoint, raw 24 kHz mono PCM request, headers, and parser
match those documented fields. No live request was sent during this check.

## 2026-10-17 — provider-router foundation

**Change.** Added a text-only provider boundary for Anthropic, OpenAI, and
Gemini. It uses documented API header shapes through injected transport, takes
credentials only from process environment, requires an explicit model rather
than guessing an unstable provider default, and has bounded ordered failover
only for retryable quota/rate-limit/outage results. Free-only mode fails closed
without making a network call. Provider replies contain text only—there is no
action or shell-command field to reach the desktop boundary.

**Regression evidence.** Mock-only router tests cover Free-only, retryable and
authentication failover, missing model/key handling,
response parsing, and provider headers: 6 passed in 0.28 seconds. The module is
not yet the application’s selected AI path; Settings and an intentional live
connection test remain unfinished.

## 2026-10-17 — provider selection integration

**Change.** Added validated preference defaults and Settings controls for a
primary API provider, two ordered backups, automatic failover, Free-only, and
explicit provider models. Claude Code remains the default. For an unresolved
request, a non-Claude selection invokes the text-only router only after the
normal request-confirmation boundary; direct typed actions still precede it.
Free-only blocks the request before any network operation. API status reports
only `Environment variable` or `Not configured`, never a credential value.

**Regression evidence.** Added tests that prove a selected API request does
not start Claude or execute an action, and that provider state is sanitized.
Provider-router suite: 8 passed in 0.10 seconds. Full Python suite: 82 tests,
8 subtests, 4.23 seconds. Release .NET build had zero warnings/errors and the
native self-test passed.

**Remaining work.** API credentials are process-environment development
configuration only. A Credential Manager UI, vendor-account verification, and
an intentionally user-authorized live request/failover test remain required
before this area can be marked fully accepted.

**Publish verification.** A fresh self-contained `win-x64` publish succeeded
at `%LOCALAPPDATA%\\Temp\\silly-v1-provider-validation-20261017-1905`; its
published native self-test passed. `git diff --check` also passed. No installer,
startup registration, application launch, or cloud API call was performed.

**Follow-up repair.** Duplicate backup selections are normalized before the
router is called, rather than surfacing a configuration error. The focused
provider suite passed 9 tests in 0.11 seconds; the full suite then passed 83
tests and 8 subtests in 4.21 seconds.

## 2026-10-17 — API credential storage

**Change.** Added current-user Windows Credential Manager storage for
Anthropic, OpenAI, and Gemini API keys. Settings saves/removes an explicitly
entered key without displaying it later. On worker startup, a saved credential
is injected only into that child process environment, unless an explicit
development environment value already exists. A source marker makes Settings
truthfully distinguish Credential Manager from an environment configuration.

**Regression evidence.** Native self-test validates the fixed Silly Credential
Manager target/environment mappings. The focused provider suite passed 9 tests
in 0.11 seconds, Release .NET build had zero warnings/errors, and the native
self-test passed. No key value was read into diagnostics, printed, committed,
or sent to an external provider.

**Least-privilege follow-up.** Saved keys are now copied only to a `--wait`
unresolved-request worker. Other Python helpers, including provider-status
refreshes, receive only a non-secret Credential Manager source marker.

**Final validation for this batch.** Full Python suite: 83 tests and 8
subtests passed in 4.30 seconds. A self-contained `win-x64` publish succeeded
at `%LOCALAPPDATA%\\Temp\\silly-v1-credential-validation-20261017-1930`; the
published native self-test passed. `git diff --check` passed. No installer,
startup registration, application launch, provider API call, or credential
value exposure occurred.

## 2026-10-17 — non-installing release validation

**Change.** Added `scripts/validate-release.ps1` and release-validation
documentation. The script rejects a non-empty output directory and runs the
complete test/build/publish/self-test/diff sequence without invoking the
installer script, registering startup, launching the app, or touching an
installed copy.

**Evidence.** The script completed successfully against
`%LOCALAPPDATA%\\Temp\\silly-release-check-20261017-1950`: 83 Python tests and
8 subtests passed in 4.18 seconds; Python self-test, Release build (zero
warnings/errors), native self-test, self-contained publish, and diff check all
completed. The terminal emitted only Git line-ending notices during the final
diff check, not a validation failure.

## 2026-10-17 — provider settings polish

**Change.** Claude Code plan/model controls now hide when an API provider is
selected, and the Claude status row says it is not selected rather than showing
an irrelevant setup error. This keeps the visible Settings contract aligned
with the provider that will actually receive unresolved text requests.

**Regression evidence.** JavaScript/settings and provider-router focused tests
passed: 10 tests and 5 subtests in 0.47 seconds.

## 2026-10-17 — updater safety default

**Observed risk.** The updater defaulted to automatic checks. Its update path
can fetch, pull, build, stage, and eventually restart the app, which is too
consequential for a default background behavior.

**Change.** `autoUpdate` now defaults to false. Scheduled checks do nothing
until a user enables them; a pre-existing staged update is shown as ready but
does not restart the app unless automatic updates are enabled. The explicit
Settings **Check now** path remains user-initiated.

**Regression evidence.** Identity/update regression tests passed: 5 in 0.02
seconds. Release .NET build had zero warnings/errors and native self-test
passed. Isolated real updater swap behavior remains a manual verification item.

**Full validation.** Python suite: 84 tests and 8 subtests passed in 4.22
seconds. Fresh self-contained publish to
`%LOCALAPPDATA%\\Temp\\silly-v1-updater-validation-20261017-2015` succeeded;
its native self-test and `git diff --check` passed. No updater action was run.

## 2026-10-17 — regression and publish validation

**Automated results.** `py -3 -m pytest -q` passed: 80 tests and 8 subtests in
4.20 seconds. `py -3 silly.py --selftest` passed. Release `.NET` build passed
with zero warnings/errors; the native self-test passed from both the build
output and a self-contained publish.

**Publish result.** `dotnet publish win\\Atticus -c Release -r win-x64
--self-contained -p:DebugType=none` succeeded to the isolated temporary
directory `%LOCALAPPDATA%\\Temp\\silly-v1-validation-20261017-1845`.
The published `Silly.exe --selftest` passed. No installer, application launch,
startup registration, real cloud call, or process termination occurred.

**Quality checks.** `git diff --check` passed. The tree intentionally remains
dirty because it includes prior rebrand/action/voice work plus this incremental
V1 work; no existing change was reset or overwritten.

## 2026-10-17 — security and dependency audit

**Action boundary.** Confirmed that the live provider invocation exposes only
WebSearch/WebFetch and explicitly disallows Bash/Read. Legacy shell replay is
unreachable, watch actions are disabled before their legacy handler, and no
provider output has an action-execution path. The remaining shell/process code
is host-controlled legacy/helper functionality; it is not reachable from the
active model tool list and remains a follow-up removal/hardening candidate.

**Process and credential handling.** The installer stops only a `Silly.exe`
whose resolved path equals Silly's own installation path. Runtime process stop
uses the app-owned Python job/process object. Gnani uses process environment
or current-user Credential Manager and no credential value is written to
settings/logs. Validated HTTP(S) actions use Windows associations or an exact
known browser shortcut.

**Dependency evidence.** `dotnet list win\\Atticus\\Atticus.csproj package
--vulnerable --include-transitive` reported no vulnerable packages from the
current NuGet source. `py -3 -m pip check` reported no broken requirements.
These checks do not substitute for future advisory monitoring.

## 2026-10-18 — account-backed AI routing

**Implemented.** Added an explicit OpenAI Sign in with ChatGPT plan route:
stable host identity, dynamic client registration, loopback callback, PKCE,
state/nonce, signed-ID-token validation, granted-scope gating, credential
manager storage, refresh rotation, revoke-on-disconnect, model catalog and
streamed public Responses requests with `store:false`. The route remains
text-only and does not cross Silly's typed action boundary. Claude stays on its
supported signed-in CLI route; Gemini CLI OAuth remains deliberately unused.

**Mock evidence.** `py -3 -m pytest -q` passed 105 tests and 8 subtests;
SIWC tests cover authorization fields, callback state/decline, signed identity,
permission absence, refresh, model catalog, stream completion, and text-only
router behavior. `py -3 silly.py --selftest` passed. Native Release build and
self-contained temporary publish passed with zero build warnings/errors.

**Live evidence.** BLOCKED: no deliberately authorized ChatGPT account was
connected during this change, so no account eligibility, plan usage, callback
browser handoff, refresh, or remote revocation claim is marked end-to-end
verified. The manual procedure is in `docs/ai-providers.md`.

## 2026-10-18 — Claude subscription and account failover

**Audit.** The existing Claude route already used the official local
`claude -p` session and restricted its active tool set to WebSearch/WebFetch.
It was nevertheless outside the typed provider priority list, and its status
treated an Anthropic API-key CLI session as interchangeable with a subscription
session. The current official Anthropic guidance permits `claude -p`, Agent SDK
and third-party apps against subscription limits; Gemini CLI OAuth remains
prohibited for this product.

**Change.** Added `claude-subscription` as a separate text-only provider. It
accepts only the sanitized local Claude Code Max/Team subscription state and
never consumes or exports a Claude website session or Anthropic API key. Both
account-backed routes can now appear in ordered backup priority. Free-only
requires explicit Claude-subscription approval plus a supported authenticated
state. Failover is allowed only before a completed answer; a started Claude
request is marked non-retryable to avoid duplicate model work.

**Evidence and live status.** Mock tests cover status modes, API-key
separation, Free-only rejection, cancellation, ChatGPT→Claude and
Claude→ChatGPT pre-dispatch failover, attribution, timeout, and no replay after
a started Claude request. On this current worktree, `silly.py --check` reports
Claude Code not installed and sanitized ChatGPT status reports Not connected.
Although the user reports performing an earlier ChatGPT smoke test, no result
was recorded and it cannot be retrospectively marked PASS. Both live routes
are BLOCKED pending restored/local authorized sessions; no paid or quota
exhaustion request was made.

**Release evidence.** `py -3 -m pytest -q` passed **115 tests and 8
subtests**. `py -3 silly.py --selftest` returned `selftest ok`. The native
Release build had zero warnings/errors. The non-installing release validator
also passed native and published self-tests plus a self-contained `win-x64`
publish at
`%TEMP%\Silly-claude-failover-release-20261018-02`; `git diff --check`
passed. It did not install, launch the GUI, alter startup, or contact either
account provider.

## 2026-10-18 — updater activation policy and packaged font

**Updater policy.** A manual **Check now** can still download and stage a
candidate, but a staged result now remains pending unless the user has enabled
automatic updates. The native self-test covers both policy branches. This
prevents a support check from silently replacing or restarting the running
application.

**Font packaging.** The supplied Satoshi variable font is bundled locally at
`ui/assets/fonts/Satoshi-Variable.ttf`; its source, repository, and isolated
release copies had the same SHA-256 checksum. The UI does not download a
typeface at runtime.

**Regression evidence.** `py -3 -m pytest -q` passed **119 tests and 8
subtests**. `py -3 silly.py --selftest`, a zero-warning Release build, and the
native self-test passed. The non-installing validator published a fresh
self-contained `win-x64` build at `%TEMP%\Silly-v1-release-20261018-05` and
passed its published native self-test and diff check. No application,
installer, updater, cloud provider, or account-provider request was launched
during this validation.

**External verification still required.** The automated environment could not
retrieve Gnani's official documentation during this pass, and no real Gnani
request was made. The protocol remains mock-validated only until the documented
manual smoke test is deliberately run with an authorized account and microphone.

## 2026-10-18 — realtime transcript revision handling

**Change.** Gnani's realtime accumulator now distinguishes an identical
retransmission from a revised interim/final segment. A later event with the
same segment ID can replace its earlier text at the same segment index; an
identical event remains ignored. This preserves live corrections without
creating duplicate words or command executions.

**Evidence.** The native self-test covers first receipt, exact duplicate,
same-ID replacement, ordered next segment, provider error, and malformed JSON.
The Release build had zero warnings/errors; `py -3 -m pytest -q` passed 119
tests and 8 subtests, and both Python and native self-tests passed. A fresh
non-installing self-contained publish passed at
`%TEMP%\Silly-v1-release-20261018-06`. No cloud connection, audio capture,
GUI launch, or installation occurred.

## 2026-10-18 — direct URL dispatch hardening

**Change.** The typed URL validator now rejects raw control/whitespace
characters, backslashes, quotes, credentials, and malformed ports before a
URL can reach Windows' URL association or a browser shortcut. Deterministic
website searches still construct and encode their own HTTPS destinations.

**Evidence.** Mock action tests cover the rejected forms and successful encoded
searches. Focused action tests passed 23 tests; Python and native self-tests,
and a zero-warning Release build passed. No URL, browser, application, or GUI
was launched during the check.

## 2026-10-18 — active AI subprocess boundary

**Change.** The Claude subprocess now receives only the compact, capability-
accurate text-only system prompt. The historical helper/automation prompt and
the pre-tool command hook are no longer attached; its explicit tool list stays
`WebSearch,WebFetch` with `Bash` and `Read` disallowed.

**Evidence.** An offline regression inspects the generated command, settings,
environment, and system-prompt files and confirms no hook environment is
present. Provider/router/action regressions passed 86 tests; both self-tests
and a zero-warning Release build passed. No model process, web request,
desktop action, or installation was started.

## 2026-10-18 — installer candidate promotion

**Change.** A normal `build.ps1` run now assembles a complete
`Programs\Silly.next` candidate before it stops a process. It then filters by
the resolved installed `Silly.exe` path, moves the current product directory
to `Silly.old`, promotes the candidate, and restores the prior directory when
promotion fails. Stage builds retain the same candidate contract.

**Evidence.** The build script parsed without execution and the installation-
boundary regressions passed, including candidate, rollback, exact-path, and
reference-product checks. No installer, package download, process stop, or
application launch was performed.

## 2026-10-18 — user-facing CLI identity cleanup

**Change.** `silly.py --help` now describes only Silly's supported typed
actions, sanitized diagnostics, account-provider boundary, local storage, and
disabled legacy capabilities. It no longer presents the technical-reference or
Mac-oriented helper catalog as product functionality.

**Evidence.** The real help command printed the Silly-only contract without
starting a provider or desktop action. The full suite passed 122 tests and 8
subtests; the Python self-test, native self-test, and zero-warning Release
build passed.

## 2026-10-18 — truthful staged-update status

**Change.** Pending-update copy in Settings now uses the same centralized
activation policy as the updater. With automatic updates disabled it says the
update is ready for review; only an enabled automatic-update setting describes
an idle restart.

**Evidence.** Native self-tests exercise both status branches. The complete
Python suite passed 122 tests and 8 subtests; Python self-test, zero-warning
Release build, native self-test, and diff check passed. No updater action,
installation, or desktop launch occurred.

## 2026-10-18 — telemetry transport removed

**Change.** Removed the reference application's optional PostHog environment
switch and outbound transport from Silly's product path. Usage pings and
failure-report calls are now compatibility no-ops; local logs remain local.
Cloud speech and account providers remain explicit, user-selected requests
rather than telemetry.

**Evidence.** Regression tests force legacy telemetry flags and verify no
adapter call occurs; static checks verify no PostHog key or endpoint remains in
the runtime. Focused privacy, helper, and identity checks passed 61 tests and
3 subtests. Python/native self-tests and a zero-warning Release build passed.
No network request, audio capture, UI launch, or installation occurred.

## 2026-10-18 — named-pipe control-surface reduction

**Change.** Removed the `update` message from Silly's local named-pipe server.
The pipe now supports only second-instance Settings activation and local
notifications; the explicit Settings button invokes an update check directly.
An arbitrary local pipe client can no longer trigger a network/build update
operation through that channel.

**Evidence.** Identity regression coverage asserts the Silly-specific pipe and
the absence of the update command. Focused checks passed 10 tests; Python and
native self-tests plus a zero-warning Release build passed. No update check,
network request, application launch, or installation ran.

## 2026-10-18 — telemetry UI removal

**Change.** Removed the remaining legacy “Help improve” settings toggle and
in-overlay feedback prompt. They described sending task data despite Silly
having no telemetry transport, and their handlers are now gone with the stale
preference defaults.

**Evidence.** A UI regression check rejects those labels and the old command
hook. Validation remains local-only; no desktop, cloud, installer, or network
action is needed for this change.

## 2026-10-18 — focused onboarding polish

**Change.** Reduced first-run setup to Microphone and local Speech Model.
Claude provider status, installation, sign-in, and plan actions are no longer
part of onboarding or capable of reopening it. Provider selection remains in
Intelligence Settings. Satoshi now has explicit control inheritance for
onboarding controls, settings controls, the overlay, and Web Awesome selects.

**Evidence.** The full release validator passed 132 Python tests and 8
subtests; Python and native self-tests passed; the Release build had zero
warnings; a self-contained `win-x64` artifact was published at
`%TEMP%\Silly-onboarding-20261018` and its native self-test passed. The
artifact contains the bundled Satoshi font and attribution. A temporary,
isolated launch exposed the published **Welcome to Silly** window, then was
closed by its exact PID. Native UI automation could not enumerate that window,
so full visual walkthrough and completion are explicitly pending manual
acceptance rather than claimed as verified.
