# AI reasoning providers

Silly's product UI supports two account-backed routes for unresolved text:
**ChatGPT plan** and a supported local **Claude subscription** session. Direct
typed commands do not depend on either route. Silly does not expose or use
Anthropic, OpenAI, or Gemini API-key configuration in the product UI.

## ChatGPT plan usage (Sign in with ChatGPT)

Silly supports the documented **Sign in with ChatGPT** public-client flow. It
is opt-in: in Settings → Reasoning, choose **ChatGPT plan** and click
**Connect**. That
user-initiated button opens the system browser and asks for the account's
actual permission. Silly does not send a request to OpenAI until the connection
is complete and its returned grant includes `chatgpt.tokens.use.direct`.

The connection uses a stable per-host opaque identifier, a `127.0.0.1`
loopback callback at `/auth/callback`, fresh state, nonce and PKCE verifier for
each attempt, dynamic registration, and the issued client ID rather than
`dynamic_agent_client`. It verifies the signed ID token against the discovery
JWKS before trusting its issuer, audience, expiry, nonce, subject or email.
Each account's token set and registration are protected separately in
current-user Windows Credential Manager below `Silly/OpenAIChatGPT/`; no token
is put in Settings, command lines, logs, browser storage, source control or
diagnostics.

Silly calls only the public Responses endpoint with the authorized account
token, `store: false`, and `stream: true`. It never uses browser cookies or
ChatGPT `backend-api` endpoints. A reply is accepted only after
`response.completed`; streamed provider text never becomes an action or
command. Access and rotating refresh tokens are renewed through the documented
token endpoint. Disconnect looks up the documented revocation endpoint,
attempts refresh-token revocation, then clears local tokens even if remote
revocation cannot be confirmed.

Settings displays the connection mode, account label and plan-permission state,
never a token. A valid identity without direct-plan permission is connected but
unavailable for plan requests. Ineligibility, permission decline, usage limits,
revocation and temporary route failures are not converted into an API-key or
paid fallback. Users can review usage or revoke app access in
[ChatGPT Settings → Usage](https://chatgpt.com/#settings/usage).

Eligibility is decided by OpenAI, account/workspace policy and the granted
scope. Silly does not claim that any specific ChatGPT plan is eligible before
an authorized live result. In Free-only mode, the plan route is approved only
when the direct-plan permission is present.

## Claude and Gemini account routes

Claude Code is Silly's separate account-backed Claude route. Select **Claude
subscription** as a primary provider or an explicit backup, then use the
existing **Set Up** control to install/sign in through the official local
Claude Code CLI. Silly calls only `claude auth status` for sanitized state and
the existing `claude -p` route for a request; it never reads, copies, exports,
or scrapes browser cookies or Claude session tokens.

The current supported subscription route is deliberately narrow: Silly accepts
only a locally reported `claude.ai` **Max** or **Team** subscription. A missing
CLI, signed-out session, free plan, unknown account type, timeout, or
incomplete response is surfaced as unavailable. Anthropic's current guidance
says that `claude -p`, Agent SDK, and third-party apps draw from
subscription limits; Max and Team may also include monthly API credits. The
user must explicitly approve the Claude subscription's no-additional-charge
setting before Free-only will dispatch to it.

A backup is attempted only if a provider is unavailable before a completed
answer. Once a Claude request starts, an incomplete/error result is final and
is not replayed through ChatGPT or another provider. Direct actions remain
independent and never enter this routing path.

Gemini CLI OAuth is not used: the Gemini CLI terms prohibit third-party
software from directly accessing the services behind it. Gemini is absent from
the product until Google documents a supported account-backed route.

## Safety and billing

The router is text-only. Its output is never interpreted as a command or action;
operating-system actions must be proposed and validated separately through
Silly's typed action registry.

**Free-only** defaults to fail closed. It sends a request only when the
account-backed route has the required plan permission or the user has reviewed
and checked the Claude subscription's no-additional-charge setting. An
unchecked, unknown, or paid route is skipped without contact. A configured
backup can be used if an earlier provider is ineligible or returns an
authentication, quota/rate-limit, or temporary failure.

Before checking that setting, review the provider's current official policy:

- [Claude Code authentication](https://code.claude.com/docs/en/getting-started)
  requires an eligible Claude Code account.
- [OpenAI Sign in with ChatGPT plan usage](https://developers.openai.com/siwc/token-sharing-open-source)
  is an OAuth capability for eligible open-source/local apps. Silly implements
  its documented, explicit-consent route and never reads website cookies or
  private session tokens.

The router does not use browser cookies, consumer sign-in sessions, scraped
tokens, or unofficial OAuth flows. It neither promises unlimited free usage
nor silently changes to a chargeable route.

## Current integration status

Settings selects a Claude subscription or ChatGPT plan for an unresolved
question; direct typed commands always run first, even if Instant commands is
off or an account provider is unavailable. Requests receive only text and
return text plus the actual provider/model identity. Model output is never
executed as a desktop command. Settings displays authorized account state and
never exposes a credential value.

No live provider request is made automatically. A user must explicitly select
an account provider, choose an account-supported model, and keep Free-only on
unless they have deliberately reviewed billing. Live connection and failover
behavior remain manual acceptance tests; unit tests use mock transports only.

## Manual Claude subscription smoke test (not run automatically)

Use this only when Claude Code is already installed and signed in by the user;
Silly does not install it or initiate sign-in on its own. In Settings →
Reasoning, select **Claude subscription** as the primary provider, retain
Free-only, and check the Claude no-additional-charge approval only after
reviewing the account's current subscription limits. Ask one harmless factual
question and verify that the reply identifies Claude and that no desktop action
is attempted. If Claude Code reports a limit, sign-in, or account error before
dispatch, a separately-approved configured backup may answer once. If the
Claude request has started, Silly reports its final error rather than replaying
the request. Record only the outcome and provider/model, never credentials,
tokens, account identifiers, or prompt content.

## Manual ChatGPT plan smoke test (not run automatically)

1. Build and start a development copy with `scripts/run-dev.ps1`; do not use
   the installer or enable startup.
2. In Settings → Reasoning, choose OpenAI as primary, choose **ChatGPT plan**,
   click **Continue with ChatGPT**, and explicitly approve the displayed Silly
   permission request in the system browser.
3. Confirm Settings shows the expected account label and enabled plan
   permission. If it says unavailable or ineligible, record that result and do
   record the unavailable result; Silly does not offer a paid fallback.
4. Choose an account-supported model, keep Free-only enabled, and ask one
   harmless unresolved text question. Verify the reply names OpenAI and no
   desktop action is attempted.
5. Click **Disconnect**. Confirm local tokens are removed, then use ChatGPT
   Settings → Usage to verify or revoke remote access if revocation was not
   confirmed.

Claude Code remains a separate supported CLI session rather than an API-key
adapter. If it is not licensed, authenticated, or installed, Silly can use a
configured API backup before a Claude request starts. If an already-started
Claude CLI request later fails, Silly reports that result rather than starting a
second provider request whose external read-only work could be duplicated.
