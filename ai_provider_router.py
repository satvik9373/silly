"""Safe, text-only reasoning-provider routing for Silly.

This module deliberately has no dependency on the action engine. A provider
can return text and structured provider status, never shell commands or actions.
The host must turn any requested local operation into a separately validated
typed action before it is executed.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
import os
from typing import Any, Callable, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ProviderId(str, Enum):
    CLAUDE_SUBSCRIPTION = "claude-subscription"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GEMINI = "gemini"


class FailureKind(str, Enum):
    AUTH = "authentication"
    RATE_LIMIT = "rate_limit"
    QUOTA = "quota"
    TEMPORARY = "temporary"
    UNSUPPORTED = "unsupported"
    POLICY = "policy"
    CANCELLED = "cancelled"
    INVALID_RESPONSE = "invalid_response"


@dataclass(frozen=True)
class ProviderFailure:
    kind: FailureKind
    message: str
    retryable: bool = False


@dataclass(frozen=True)
class ProviderReply:
    provider: ProviderId
    model: str = ""
    text: str = ""
    failure: ProviderFailure | None = None
    attempts: tuple[ProviderId, ...] = ()

    @property
    def ok(self) -> bool:
        return self.failure is None and bool(self.text.strip())


@dataclass(frozen=True)
class ProviderPolicy:
    order: tuple[ProviderId, ...]
    failover: bool = True
    free_only: bool = True
    # This is an explicit user policy assertion, never an inference from the
    # key itself.  Empty by default means fail closed.  A host may place only a
    # provider/model route that the user has reviewed as no-additional-charge
    # into this set (for example, a documented Gemini free tier).
    no_charge_providers: frozenset[ProviderId] = frozenset()
    timeout_seconds: float = 20.0

    def validate(self) -> ProviderFailure | None:
        if not self.order or len(set(self.order)) != len(self.order):
            return ProviderFailure(FailureKind.UNSUPPORTED, "Choose one or more distinct AI providers.")
        if not self.no_charge_providers.issubset(set(self.order)):
            return ProviderFailure(FailureKind.UNSUPPORTED, "No-charge provider settings must be in the selected priority order.")
        if not 1 <= self.timeout_seconds <= 60:
            return ProviderFailure(FailureKind.UNSUPPORTED, "Provider timeout must be between 1 and 60 seconds.")
        return None


@dataclass(frozen=True)
class HttpResponse:
    status: int
    body: str


class Transport(Protocol):
    def post(self, url: str, headers: Mapping[str, str], payload: Mapping[str, Any], timeout: float) -> HttpResponse: ...


class UrlLibTransport:
    """The production transport; tests supply a mock instead of network I/O."""
    def post(self, url: str, headers: Mapping[str, str], payload: Mapping[str, Any], timeout: float) -> HttpResponse:
        request = Request(url, data=json.dumps(payload).encode("utf-8"), headers={**headers, "Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=timeout) as response:
                return HttpResponse(response.status, response.read().decode("utf-8", "replace"))
        except HTTPError as error:
            return HttpResponse(error.code, error.read().decode("utf-8", "replace"))
        except URLError:
            return HttpResponse(0, "")


def _failure(status: int, body: str) -> ProviderFailure:
    text = body.lower()
    if status in {401, 403}:
        return ProviderFailure(FailureKind.AUTH, "The provider rejected its credentials.")
    if status == 429 and ("quota" in text or "credit" in text or "billing" in text):
        return ProviderFailure(FailureKind.QUOTA, "The provider quota is unavailable.", True)
    if status == 429:
        return ProviderFailure(FailureKind.RATE_LIMIT, "The provider is rate-limited.", True)
    if status in {408, 500, 502, 503, 504} or status == 0:
        return ProviderFailure(FailureKind.TEMPORARY, "The provider is temporarily unavailable.", True)
    return ProviderFailure(FailureKind.INVALID_RESPONSE, "The provider returned an invalid response.")


class TextProvider:
    provider_id: ProviderId
    credential_environment: str
    model_environment: str

    def __init__(self, transport: Transport | None = None, model: str | None = None):
        self.transport = transport or UrlLibTransport()
        self.model = (model or "").strip()

    def credential(self, environment: Mapping[str, str]) -> str:
        return (environment.get(self.credential_environment) or "").strip()

    def request(self, prompt: str, credential: str, model: str) -> tuple[str, dict[str, str], dict[str, Any]]:
        raise NotImplementedError

    def text(self, response: Mapping[str, Any]) -> str:
        raise NotImplementedError

    def complete(self, prompt: str, environment: Mapping[str, str], timeout: float = 20) -> ProviderReply:
        credential = self.credential(environment)
        if not credential:
            return ProviderReply(self.provider_id, failure=ProviderFailure(FailureKind.AUTH, f"{self.provider_id.value.title()} is not connected."))
        model = self.model or (environment.get(self.model_environment) or "").strip()
        if not model:
            return ProviderReply(self.provider_id, failure=ProviderFailure(FailureKind.UNSUPPORTED, f"Choose a currently supported {self.provider_id.value.title()} model before connecting."))
        if not _valid_model(model):
            return ProviderReply(self.provider_id, failure=ProviderFailure(FailureKind.UNSUPPORTED, "The selected model identifier is invalid."))
        try:
            url, headers, payload = self.request(prompt, credential, model)
            response = self.transport.post(url, headers, payload, timeout)
        except (OSError, TimeoutError):
            return ProviderReply(self.provider_id, model=model, failure=ProviderFailure(FailureKind.TEMPORARY, "The provider connection timed out.", True))
        if response.status < 200 or response.status >= 300:
            return ProviderReply(self.provider_id, model=model, failure=_failure(response.status, response.body))
        try:
            text = self.text(json.loads(response.body)).strip()
        except (TypeError, ValueError, KeyError, IndexError):
            text = ""
        return ProviderReply(self.provider_id, model=model, text=text) if text else ProviderReply(self.provider_id, model=model, failure=ProviderFailure(FailureKind.INVALID_RESPONSE, "The provider returned no usable text."))


def _valid_model(model: str) -> bool:
    # Models form part of Gemini's URL path, so do not allow a configuration
    # value to alter a provider endpoint.  This matches the native settings
    # validation and accepts current documented model naming characters.
    import re
    return bool(re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", model))


class AnthropicProvider(TextProvider):
    provider_id, credential_environment, model_environment = ProviderId.ANTHROPIC, "ANTHROPIC_API_KEY", "SILLY_ANTHROPIC_MODEL"

    def request(self, prompt: str, credential: str, model: str):
        return "https://api.anthropic.com/v1/messages", {"x-api-key": credential, "anthropic-version": "2023-06-01"}, {"model": model, "max_tokens": 500, "messages": [{"role": "user", "content": prompt}]}

    def text(self, response: Mapping[str, Any]) -> str:
        return "".join(item.get("text", "") for item in response["content"] if item.get("type") == "text")


class OpenAIProvider(TextProvider):
    provider_id, credential_environment, model_environment = ProviderId.OPENAI, "OPENAI_API_KEY", "SILLY_OPENAI_MODEL"

    def request(self, prompt: str, credential: str, model: str):
        return "https://api.openai.com/v1/responses", {"Authorization": "Bearer " + credential}, {"model": model, "input": prompt}

    def text(self, response: Mapping[str, Any]) -> str:
        return response.get("output_text", "")


class OpenAIChatGPTProvider(TextProvider):
    """The SIWC route: OAuth plan tokens, streamed public Responses only.

    It is intentionally a distinct adapter from OpenAIProvider.  A user can
    switch back to their own API key, but a failed plan request never morphs
    into an API-key request or a desktop action.
    """
    provider_id, credential_environment, model_environment = ProviderId.OPENAI, "", "SILLY_OPENAI_MODEL"

    def __init__(self, plan_client=None, model: str | None = None):
        super().__init__(None, model)
        if plan_client is None:
            from openai_siwc import ChatGPTPlan
            plan_client = ChatGPTPlan()
        self.plan_client = plan_client

    def complete(self, prompt: str, environment: Mapping[str, str], timeout: float = 20) -> ProviderReply:
        model = self.model or (environment.get(self.model_environment) or "").strip()
        if not model or not _valid_model(model):
            return ProviderReply(self.provider_id, model=model, failure=ProviderFailure(FailureKind.UNSUPPORTED, "Choose a supported ChatGPT account model before connecting."))
        try:
            text, used_model = self.plan_client.complete(prompt, model, timeout)
            return ProviderReply(self.provider_id, model=used_model, text=text)
        except Exception as error:
            message = str(error) or "ChatGPT plan usage is unavailable."
            lowered = message.lower()
            kind = FailureKind.QUOTA if "limit" in lowered else FailureKind.TEMPORARY if "temporar" in lowered else FailureKind.AUTH
            return ProviderReply(self.provider_id, model=model, failure=ProviderFailure(kind, message, kind in {FailureKind.QUOTA, FailureKind.TEMPORARY}))


class ClaudeSubscriptionProvider:
    """Official local Claude Code/Agent-SDK session, not an Anthropic API key.

    The injected client owns the supported `claude -p` invocation.  It may
    report an unavailable session before dispatch (which is safe to fail over)
    but never marks a started request retryable: even read-only model work must
    not be duplicated by an automatic backup.
    """
    provider_id = ProviderId.CLAUDE_SUBSCRIPTION

    def __init__(self, status: Callable[[], Mapping[str, Any]], complete: Callable[[str, str, float], tuple[str, bool]], model: str = ""):
        self.status, self.client, self.model = status, complete, (model or "").strip()

    def complete(self, prompt: str, environment: Mapping[str, str], timeout: float = 20) -> ProviderReply:
        state = self.status()
        if not state.get("ok") or state.get("authMode") != "claude-subscription":
            need = str(state.get("need", "login"))
            if need in {"install", "unsupported"}:
                kind = FailureKind.UNSUPPORTED
            elif need in {"quota", "rate_limit"}:
                # Status has rejected the request before any model work.  A
                # separately-approved backup may be tried once in this case.
                kind = FailureKind.QUOTA if need == "quota" else FailureKind.RATE_LIMIT
            elif need in {"timeout", "temporary"}:
                kind = FailureKind.TEMPORARY
            else:
                kind = FailureKind.AUTH
            return ProviderReply(self.provider_id, failure=ProviderFailure(
                kind,
                str(state.get("text") or "Claude subscription is unavailable."),
                kind in {FailureKind.QUOTA, FailureKind.RATE_LIMIT, FailureKind.TEMPORARY},
            ))
        model = self.model or str(state.get("model") or "")
        if not model or not _valid_model(model):
            return ProviderReply(self.provider_id, model=model, failure=ProviderFailure(FailureKind.UNSUPPORTED, "Choose a supported Claude subscription model."))
        try:
            text, completed = self.client(prompt, model, timeout)
        except TimeoutError:
            return ProviderReply(self.provider_id, model=model, failure=ProviderFailure(FailureKind.TEMPORARY, "Claude subscription request timed out.", True))
        except OSError:
            return ProviderReply(self.provider_id, model=model, failure=ProviderFailure(FailureKind.TEMPORARY, "Claude Code is temporarily unavailable.", True))
        except Exception as error:
            return ProviderReply(self.provider_id, model=model, failure=ProviderFailure(FailureKind.INVALID_RESPONSE, str(error) or "Claude did not complete the request."))
        if not completed or not str(text).strip():
            # Do not fail over: this provider may already have performed its
            # bounded read-only work, and a second model request would duplicate it.
            message = str(text).strip() or "Claude did not complete the request."
            lowered = message.lower()
            if "cancel" in lowered:
                kind = FailureKind.CANCELLED
            elif "quota" in lowered or "rate limit" in lowered or "usage limit" in lowered:
                kind = FailureKind.QUOTA
            elif "sign in" in lowered or "auth" in lowered:
                kind = FailureKind.AUTH
            else:
                kind = FailureKind.INVALID_RESPONSE
            return ProviderReply(self.provider_id, model=model, failure=ProviderFailure(kind, message))
        return ProviderReply(self.provider_id, model=model, text=str(text).strip())


class GeminiProvider(TextProvider):
    provider_id, credential_environment, model_environment = ProviderId.GEMINI, "GEMINI_API_KEY", "SILLY_GEMINI_MODEL"

    def request(self, prompt: str, credential: str, model: str):
        return "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent", {"x-goog-api-key": credential}, {"contents": [{"parts": [{"text": prompt}]}]}

    def text(self, response: Mapping[str, Any]) -> str:
        return response["candidates"][0]["content"]["parts"][0]["text"]


class ProviderRouter:
    def __init__(self, providers: Mapping[ProviderId, TextProvider] | None = None, environment: Mapping[str, str] | None = None):
        self.providers = dict(providers or {
            ProviderId.ANTHROPIC: AnthropicProvider(), ProviderId.OPENAI: OpenAIProvider(), ProviderId.GEMINI: GeminiProvider(),
        })
        self.environment = environment if environment is not None else os.environ

    def complete(self, prompt: str, policy: ProviderPolicy, cancelled: Callable[[], bool] | None = None) -> ProviderReply:
        invalid = policy.validate()
        if invalid:
            return ProviderReply(policy.order[0] if policy.order else ProviderId.ANTHROPIC, failure=invalid)
        attempts: list[ProviderId] = []
        last: ProviderReply | None = None
        for provider_id in policy.order:
            if cancelled and cancelled():
                return ProviderReply(provider_id, failure=ProviderFailure(FailureKind.CANCELLED, "The request was cancelled."), attempts=tuple(attempts))
            if policy.free_only and provider_id not in policy.no_charge_providers:
                last = ProviderReply(provider_id, failure=ProviderFailure(FailureKind.POLICY, f"{provider_id.value.title()} is not approved for no-additional-charge use."))
                if not policy.failover:
                    return ProviderReply(provider_id, failure=last.failure, attempts=tuple(attempts))
                continue
            provider = self.providers.get(provider_id)
            attempts.append(provider_id)
            if provider is None:
                result = ProviderReply(provider_id, failure=ProviderFailure(FailureKind.UNSUPPORTED, "That provider is not available in this build."))
            else:
                result = provider.complete(prompt, self.environment, policy.timeout_seconds)
            last = result
            if result.ok:
                return ProviderReply(provider_id, model=result.model, text=result.text, attempts=tuple(attempts))
            # A stale/missing credential is scoped to one provider. A configured
            # backup may still be usable, but each provider is attempted once.
            # A missing build adapter or model is specific to this provider;
            # a configured backup can still answer the same text request.  We
            # never fail over after a completed answer or a cancellation.
            may_fail_over = result.failure.retryable or result.failure.kind in {FailureKind.AUTH, FailureKind.UNSUPPORTED}
            if not policy.failover or not may_fail_over:
                return ProviderReply(provider_id, failure=result.failure, attempts=tuple(attempts))
        return ProviderReply(last.provider, model=last.model, failure=last.failure, attempts=tuple(attempts))
