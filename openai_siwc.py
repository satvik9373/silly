"""OpenAI Sign in with ChatGPT (SIWC) support for Silly.

This module implements the documented local/OSS public-client flow.  It keeps
each account's tokens in Windows Credential Manager, not in Settings, logs, or
the command line.  The module deliberately has no desktop-action capability:
its only output is text from the public Responses endpoint.
"""
from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes as W
from dataclasses import dataclass
import hashlib
import json
import os
import secrets
import threading
import time
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

AUTHORIZE = "https://auth.openai.com/api/accounts/authorize"
TOKEN = "https://auth.openai.com/api/accounts/oauth/token"
DISCOVERY = "https://auth.openai.com/.well-known/openid-configuration"
RESOURCE = "https://api.openai.com/v1"
REQUIRED_SCOPES = frozenset({"openid", "profile", "email", "offline_access", "resource.invoke", "chatgpt.tokens.use.direct"})
PLAN_SCOPE = "chatgpt.tokens.use.direct"


class SiwcError(RuntimeError):
    """A user-safe OAuth or plan-routing error (never contains a token)."""


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


@dataclass(frozen=True)
class PendingAuthorization:
    state: str
    nonce: str
    verifier: str
    redirect_uri: str
    client_id: str
    host_id: str
    registration: bool


class CredentialStore:
    """Small storage boundary; unit tests use an in-memory implementation."""
    def get(self, name: str) -> str: raise NotImplementedError
    def set(self, name: str, value: str) -> bool: raise NotImplementedError
    def delete(self, name: str) -> bool: raise NotImplementedError


class MemoryCredentialStore(CredentialStore):
    def __init__(self): self.values: dict[str, str] = {}
    def get(self, name): return self.values.get(name, "")
    def set(self, name, value): self.values[name] = value; return True
    def delete(self, name): self.values.pop(name, None); return True


class WindowsCredentialStore(CredentialStore):
    """Current-user Windows Credential Manager generic records, under Silly/."""
    def __init__(self):
        self.available = os.name == "nt"
        if not self.available: return
        class CRED(ctypes.Structure):
            _fields_ = [("Flags", W.DWORD), ("Type", W.DWORD), ("TargetName", W.LPWSTR), ("Comment", W.LPWSTR), ("LastWritten", W.FILETIME),
                        ("CredentialBlobSize", W.DWORD), ("CredentialBlob", ctypes.POINTER(ctypes.c_byte)), ("Persist", W.DWORD),
                        ("AttributeCount", W.DWORD), ("Attributes", ctypes.c_void_p), ("TargetAlias", W.LPWSTR), ("UserName", W.LPWSTR)]
        self.CRED, self.api = CRED, ctypes.WinDLL("advapi32", use_last_error=True)
        self.api.CredReadW.argtypes = [W.LPCWSTR, W.DWORD, W.DWORD, ctypes.POINTER(ctypes.POINTER(CRED))]
        self.api.CredWriteW.argtypes = [ctypes.POINTER(CRED), W.DWORD]
        self.api.CredDeleteW.argtypes = [W.LPCWSTR, W.DWORD, W.DWORD]
        self.api.CredFree.argtypes = [ctypes.c_void_p]
    def _name(self, name): return "Silly/OpenAIChatGPT/" + name
    def get(self, name):
        if not self.available: return ""
        p = ctypes.POINTER(self.CRED)()
        if not self.api.CredReadW(self._name(name), 1, 0, ctypes.byref(p)): return ""
        try: return ctypes.string_at(p.contents.CredentialBlob, p.contents.CredentialBlobSize).decode("utf-16-le")
        finally: self.api.CredFree(p)
    def set(self, name, value):
        if not self.available: return False
        raw = value.encode("utf-16-le"); buffer = (ctypes.c_byte * len(raw)).from_buffer_copy(raw)
        credential = self.CRED(Type=1, TargetName=self._name(name), CredentialBlobSize=len(raw), CredentialBlob=buffer, Persist=2, UserName="Silly")
        return bool(self.api.CredWriteW(ctypes.byref(credential), 0))
    def delete(self, name):
        return bool(self.available and self.api.CredDeleteW(self._name(name), 1, 0))


def _json(value: str, default):
    try: return json.loads(value) if value else default
    except (TypeError, ValueError): return default


class AccountStore:
    """Index is non-secret metadata; every token set stays in its own record."""
    def __init__(self, credentials: CredentialStore | None = None): self.credentials = credentials or WindowsCredentialStore()
    def host_id(self) -> str:
        current = self.credentials.get("host-id")
        if current.startswith("urn:uuid:"): return current
        current = "urn:uuid:" + str(uuid.uuid4())
        if not self.credentials.set("host-id", current): raise SiwcError("Windows Credential Manager is unavailable; ChatGPT cannot be connected.")
        return current
    def _index(self): return _json(self.credentials.get("accounts"), {"active": "", "accounts": []})
    def _save_index(self, index):
        if not self.credentials.set("accounts", json.dumps(index, separators=(",", ":"))): raise SiwcError("Windows Credential Manager could not save the ChatGPT connection.")
    def active(self) -> dict[str, Any] | None:
        index = self._index(); client = index.get("active", "")
        return self.load(client) if client else None
    def load(self, client_id: str) -> dict[str, Any] | None:
        record = _json(self.credentials.get("account-" + client_id), None)
        return record if isinstance(record, dict) else None
    def save(self, record: Mapping[str, Any], active=True):
        client = str(record.get("client_id", ""))
        if not client or client == "dynamic_agent_client": raise SiwcError("OpenAI did not return an issued client ID.")
        if not self.credentials.set("account-" + client, json.dumps(dict(record), separators=(",", ":"))):
            raise SiwcError("Windows Credential Manager could not save the ChatGPT connection.")
        index = self._index(); rows = [x for x in index.get("accounts", []) if x.get("client_id") != client]
        rows.append({"client_id": client, "email": str(record.get("email", "")), "subject": str(record.get("subject", ""))})
        index["accounts"] = rows
        if active: index["active"] = client
        self._save_index(index)
    def clear_tokens(self, client_id: str):
        record = self.load(client_id)
        if record:
            for key in ("access_token", "refresh_token", "id_token", "expires_at", "scopes"): record.pop(key, None)
            self.credentials.set("account-" + client_id, json.dumps(record, separators=(",", ":")))


def begin_authorization(store: AccountStore, port: int, selected: Mapping[str, Any] | None = None) -> tuple[PendingAuthorization, str]:
    """Create a fresh state/nonce/PKCE authorization request; does not open it."""
    if not 1 <= port <= 65535: raise SiwcError("Could not start the local ChatGPT callback listener.")
    selected = dict(selected or {})
    issued = str(selected.get("client_id", ""))
    registration = not issued
    client = "dynamic_agent_client" if registration else issued
    verifier = _b64(secrets.token_bytes(48)); state = _b64(secrets.token_bytes(32)); nonce = _b64(secrets.token_bytes(32))
    pending = PendingAuthorization(state, nonce, verifier, f"http://127.0.0.1:{port}/auth/callback", client, store.host_id(), registration)
    query = {"client_id": client, "ext_agent_host_id": pending.host_id, "response_type": "code", "redirect_uri": pending.redirect_uri,
             "scope": " ".join(sorted(REQUIRED_SCOPES)), "resource": RESOURCE, "state": state, "nonce": nonce,
             "code_challenge_method": "S256", "code_challenge": _b64(hashlib.sha256(verifier.encode()).digest())}
    if registration: query["agent_name_hint"] = "Silly"
    else:
        if selected.get("id_token"): query["id_token_hint"] = selected["id_token"]
        if selected.get("email"): query["login_hint"] = selected["email"]
    return pending, AUTHORIZE + "?" + urlencode(query)


def validate_callback(pending: PendingAuthorization, callback: Mapping[str, str]) -> tuple[str, str]:
    if not secrets.compare_digest(str(callback.get("state", "")), pending.state): raise SiwcError("ChatGPT sign-in was rejected because the callback state did not match.")
    if callback.get("error"):
        if callback.get("error") == "access_denied": raise SiwcError("ChatGPT plan permission was declined. No request was sent.")
        raise SiwcError("ChatGPT sign-in did not complete.")
    code = str(callback.get("code", "")); callback_client = str(callback.get("client_id", ""))
    if not code: raise SiwcError("ChatGPT did not return an authorization code.")
    if pending.registration:
        if not callback_client or callback_client == "dynamic_agent_client": raise SiwcError("ChatGPT registration did not return an issued client ID.")
        return code, callback_client
    if callback_client and callback_client != pending.client_id: raise SiwcError("ChatGPT returned a different client registration; the connection was not changed.")
    return code, pending.client_id


class Http:
    def form(self, url: str, form: Mapping[str, str], timeout: float) -> tuple[int, dict[str, Any]]:
        request = Request(url, data=urlencode(form).encode(), headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
        try:
            with urlopen(request, timeout=timeout) as response: return response.status, _json(response.read().decode("utf-8", "replace"), {})
        except HTTPError as error: return error.code, _json(error.read().decode("utf-8", "replace"), {})
        except (URLError, TimeoutError, OSError): return 0, {}
    def json(self, url: str, headers: Mapping[str, str], timeout: float) -> tuple[int, dict[str, Any]]:
        request = Request(url, headers=dict(headers))
        try:
            with urlopen(request, timeout=timeout) as response: return response.status, _json(response.read().decode("utf-8", "replace"), {})
        except (HTTPError, URLError, TimeoutError, OSError): return 0, {}
    def stream(self, url: str, headers: Mapping[str, str], payload: Mapping[str, Any], timeout: float) -> tuple[int, list[str], dict[str, Any]]:
        request = Request(url, data=json.dumps(payload).encode(), headers={**headers, "Content-Type": "application/json", "Accept": "text/event-stream"}, method="POST")
        try:
            with urlopen(request, timeout=timeout) as response: return response.status, [line.decode("utf-8", "replace").strip() for line in response], {}
        except HTTPError as error: return error.code, [], _json(error.read().decode("utf-8", "replace"), {})
        except (URLError, TimeoutError, OSError): return 0, [], {}


def _claims_unverified(token: str) -> tuple[dict[str, Any], dict[str, Any], bytes]:
    try:
        head, body, sig = token.split(".")
        return _json(_unb64(head).decode(), {}), _json(_unb64(body).decode(), {}), _unb64(sig)
    except (ValueError, UnicodeDecodeError): raise SiwcError("ChatGPT returned an invalid identity token.")


def validate_id_token(token: str, client_id: str, nonce: str, jwks: Mapping[str, Any], now: float | None = None) -> dict[str, Any]:
    """Verify a RS256 ID token against discovery JWKS before trusting identity."""
    header, claims, signature = _claims_unverified(token)
    if header.get("alg") != "RS256" or not header.get("kid"): raise SiwcError("ChatGPT identity token used an unsupported signature.")
    key = next((k for k in jwks.get("keys", []) if k.get("kid") == header["kid"] and k.get("kty") == "RSA"), None)
    if not key: raise SiwcError("ChatGPT identity signing key was unavailable.")
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding, rsa
        public = rsa.RSAPublicNumbers(int.from_bytes(_unb64(key["e"]), "big"), int.from_bytes(_unb64(key["n"]), "big")).public_key()
        signed = ".".join(token.split(".")[:2]).encode(); public.verify(signature, signed, padding.PKCS1v15(), hashes.SHA256())
    except ImportError: raise SiwcError("Silly's secure token validator is unavailable; ChatGPT was not connected.")
    except Exception: raise SiwcError("ChatGPT identity token signature could not be verified.")
    current = time.time() if now is None else now
    audience = claims.get("aud"); allowed = audience == client_id or isinstance(audience, list) and client_id in audience
    if claims.get("iss") != "https://auth.openai.com" or not allowed or claims.get("nonce") != nonce or not isinstance(claims.get("sub"), str) or float(claims.get("exp", 0)) <= current:
        raise SiwcError("ChatGPT identity validation failed; the connection was not changed.")
    return claims


class ChatGPTPlan:
    """Refreshes one selected account and consumes only the documented stream."""
    def __init__(self, store: AccountStore | None = None, http: Http | None = None): self.store, self.http, self.lock = store or AccountStore(), http or Http(), threading.Lock()
    def status(self):
        record = self.store.active()
        if not record:
            return {"mode": "ChatGPT plan", "state": "not_connected", "connected": False, "planEnabled": False,
                    "modelsLoaded": False, "models": [], "reasoningVerified": False,
                    "message": "ChatGPT is not connected.", "account": "Not connected"}
        connected = bool(record.get("id_token") and record.get("access_token"))
        scopes = set(record.get("scopes", []))
        plan_enabled = connected and PLAN_SCOPE in scopes and bool(record.get("refresh_token"))
        state = "authenticated" if connected else "unavailable"
        message = "Authenticated; retrieving available ChatGPT models." if connected else "ChatGPT authorization is incomplete."
        if connected and not plan_enabled:
            message = "ChatGPT authorization is missing plan-use permission."
        return {"mode": "ChatGPT plan", "state": state, "connected": connected, "planEnabled": plan_enabled,
                "modelsLoaded": False, "models": [], "reasoningVerified": False,
                "message": message, "account": (record.get("email") or "Connected account") if connected else "Not connected",
                "client": bool(record.get("client_id"))}
    def _discovery(self):
        status, body = self.http.json(DISCOVERY, {}, 15)
        if status != 200 or not body.get("jwks_uri"): raise SiwcError("ChatGPT identity service is temporarily unavailable.")
        return body
    def exchange(self, pending: PendingAuthorization, callback: Mapping[str, str], selected: Mapping[str, Any] | None = None):
        code, client_id = validate_callback(pending, callback)
        status, tokens = self.http.form(TOKEN, {"grant_type": "authorization_code", "client_id": client_id, "code": code, "code_verifier": pending.verifier, "redirect_uri": pending.redirect_uri, "resource": RESOURCE}, 30)
        if status != 200: raise SiwcError("ChatGPT authorization could not be completed.")
        discovery = self._discovery(); jwks_status, jwks = self.http.json(discovery["jwks_uri"], {}, 15)
        if jwks_status != 200: raise SiwcError("ChatGPT identity signing keys are unavailable.")
        claims = validate_id_token(str(tokens.get("id_token", "")), client_id, pending.nonce, jwks)
        if selected and selected.get("subject") and selected["subject"] != claims["sub"]: raise SiwcError("The selected ChatGPT account did not match the returned identity.")
        scopes = str(tokens.get("scope", "")).split(); required = {"access_token", "id_token"}
        if not required.issubset(tokens): raise SiwcError("ChatGPT did not return a renewable session.")
        record = {"client_id": client_id, "ext_agent_host_id": pending.host_id, "subject": claims["sub"], "email": claims.get("email", ""), "issuer": claims["iss"], "id_token": tokens["id_token"], "access_token": tokens["access_token"], "refresh_token": tokens.get("refresh_token", ""), "scopes": scopes, "expires_at": time.time() + max(0, int(tokens.get("expires_in", 0))), "saved_at": int(time.time())}
        self.store.save(record)
        state = self.availability()
        if state.get("state") != "ready":
            state["message"] = "ChatGPT authorization succeeded, but model retrieval failed: " + str(state.get("message", "unknown error"))
        return state
    def _refresh(self, record):
        status, token = self.http.form(TOKEN, {"grant_type": "refresh_token", "client_id": record["client_id"], "refresh_token": record.get("refresh_token", ""), "resource": RESOURCE}, 30)
        if status != 200:
            if token.get("error") in {"invalid_grant", "invalid_refresh_token", "token_expired", "refresh_token_expired", "refresh_token_invalidated", "refresh_token_reused"}: self.store.clear_tokens(record["client_id"])
            raise SiwcError("ChatGPT plan access expired or was revoked. Continue with ChatGPT again.")
        if not token.get("access_token") or not token.get("refresh_token"): raise SiwcError("ChatGPT did not return a renewed session.")
        record.update({"access_token": token["access_token"], "refresh_token": token["refresh_token"], "expires_at": time.time() + max(0, int(token.get("expires_in", 0))), "scopes": str(token.get("scope", " ".join(record.get("scopes", [])))).split(), "saved_at": int(time.time())})
        self.store.save(record); return record
    def _record(self):
        with self.lock:
            record = self.store.active()
            if not record: raise SiwcError("Continue with ChatGPT in Settings before using ChatGPT plan usage.")
            if PLAN_SCOPE not in set(record.get("scopes", [])): raise SiwcError("This ChatGPT account did not grant plan usage permission. Choose an API key or authorize plan usage explicitly.")
            if float(record.get("expires_at", 0)) <= time.time() + 60: record = self._refresh(record)
            return record
    def models(self) -> list[dict[str, str]]:
        """Return only server-listed models; Settings never guesses a slug."""
        record = self._record()
        status, body = self.http.json(RESOURCE + "/models", {"Authorization": "Bearer " + record["access_token"]}, 20)
        if status != 200:
            raise SiwcError("ChatGPT models could not be retrieved.")
        rows = body.get("models")
        if not isinstance(rows, list):
            rows = body.get("data", [])
        models = []
        for row in rows:
            if not isinstance(row, dict) or row.get("visibility", "list") != "list":
                continue
            slug = row.get("slug", row.get("id"))
            if isinstance(slug, str) and slug:
                models.append({"slug": slug, "display_name": str(row.get("display_name") or slug)})
        if not models:
            raise SiwcError("ChatGPT returned no usable models for this account.")
        return models

    def availability(self) -> dict[str, Any]:
        state = self.status()
        if state["state"] == "not_connected":
            return state
        try:
            models = self.models()
        except SiwcError as error:
            state.update({"state": "unavailable", "modelsLoaded": False, "models": [], "message": str(error)})
            return state
        state.update({"state": "ready", "modelsLoaded": True, "models": models,
                      "message": "ChatGPT is ready to reason. A real request has not been tested yet."})
        return state
    def complete(self, prompt: str, model: str, timeout: float = 20) -> tuple[str, str]:
        record = self._record()
        status, lines, error = self.http.stream(RESOURCE + "/responses", {"Authorization": "Bearer " + record["access_token"]}, {"model": model, "input": prompt, "store": False, "stream": True}, timeout)
        if status != 200:
            code = error.get("error", {}).get("code", "") if isinstance(error.get("error"), dict) else ""
            if code == "subscription_sharing_user_not_eligible": raise SiwcError("This ChatGPT account is not eligible for plan usage.")
            if code == "subscription_sharing_usage_limit_exceeded": raise SiwcError("ChatGPT plan usage is currently limited. Review ChatGPT Settings → Usage.")
            if code == "subscription_sharing_usage_unavailable": raise SiwcError("ChatGPT plan usage is temporarily unavailable.")
            raise SiwcError("ChatGPT plan request could not be completed.")
        text, completed = [], False
        for line in lines:
            if not line.startswith("data:"): continue
            event = _json(line[5:].strip(), {})
            if event.get("type") == "response.output_text.delta": text.append(str(event.get("delta", "")))
            if event.get("type") == "response.completed": completed = True
            if event.get("type") == "response.failed": raise SiwcError("ChatGPT did not complete the response.")
        if not completed or not "".join(text).strip(): raise SiwcError("ChatGPT returned an incomplete response.")
        return "".join(text).strip(), model


def _callback_server(port: int, timeout: int):
    result: dict[str, str] = {}
    class Callback(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path != "/auth/callback": self.send_error(404); return
            for key, values in parse_qs(parsed.query, keep_blank_values=True).items(): result[key] = values[0] if values else ""
            body = b"Silly received the ChatGPT sign-in result. You can close this tab."
            self.send_response(200); self.send_header("Content-Type", "text/plain; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        def log_message(self, *args): pass
    server = HTTPServer(("127.0.0.1", port), Callback); server.timeout = timeout
    return server, result


def connect_interactively(timeout=300, opener: Callable[[str], bool] = webbrowser.open) -> dict[str, Any]:
    """Called only from the user-initiated Settings button; never automatically."""
    plan = ChatGPTPlan(); selected = plan.store.active()
    # Bind before opening the browser so another process cannot take the port.
    server, result = _callback_server(0, timeout)
    pending, url = begin_authorization(plan.store, server.server_address[1], selected)
    try:
        if not opener(url): raise SiwcError("Silly could not open the browser for ChatGPT sign-in.")
        server.handle_request()
        if not result: raise SiwcError("ChatGPT sign-in timed out. No connection was changed.")
        return plan.exchange(pending, result, selected)
    finally: server.server_close()


def disconnect() -> dict[str, Any]:
    plan = ChatGPTPlan(); record = plan.store.active()
    if not record: return plan.status()
    # Always clear local secrets. Remote revocation is best effort; it uses
    # discovery rather than a hard-coded endpoint and is never retried in a loop.
    remote = "remote revocation confirmed"
    try:
        if not record.get("refresh_token"):
            remote = "no renewable session was present"
        else:
            discovery = plan._discovery()
            status, _ = plan.http.form(str(discovery.get("revocation_endpoint", "")), {"token": record["refresh_token"], "token_type_hint": "refresh_token", "client_id": record["client_id"]}, 15)
            if status != 200: remote = "remote revocation was not confirmed"
    except Exception:
        remote = "remote revocation was not confirmed"
    plan.store.clear_tokens(record["client_id"])
    return {"mode": "ChatGPT plan", "connected": False, "planEnabled": False, "account": "Disconnected (local tokens cleared; " + remote + ")"}
