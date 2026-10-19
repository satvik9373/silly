"""Typed, deterministic Windows actions for Silly.

This module deliberately accepts action data, never shell command strings.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import os
import re
from typing import Any, Callable
from urllib.parse import quote_plus, urlparse


class Permission(str, Enum):
    NONE = "none"
    CONFIRM = "confirm"


class Status(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"
    PARTIAL = "partial"


@dataclass(frozen=True)
class ActionResult:
    status: Status
    message: str
    data: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == Status.SUCCESS


@dataclass(frozen=True)
class ActionSpec:
    action_id: str
    fields: dict[str, type]
    permission: Permission
    executor: Callable[[dict[str, Any], Any], ActionResult]


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


ALIASES = {
    "chrome": "Google Chrome", "edge": "Microsoft Edge", "vscode": "Visual Studio Code",
    "vs code": "Visual Studio Code", "code": "Visual Studio Code", "terminal": "Terminal",
    "explorer": "File Explorer", "file explorer": "File Explorer", "files": "File Explorer",
    "word": "Word", "excel": "Excel", "powerpoint": "PowerPoint", "outlook": "Outlook",
    "teams": "Microsoft Teams", "paint": "Paint", "task manager": "Task Manager",
    "control panel": "Control Panel",
}


def valid_http_url(value: str) -> bool:
    try:
        if not isinstance(value, str) or not value or any(ch.isspace() or ord(ch) < 32 for ch in value):
            return False
        # A backslash is not valid in an HTTP URI and could be interpreted as a
        # Windows path separator by an association handler. Raw quotes are also
        # rejected before a browser shortcut receives an argument.
        if "\\" in value or '"' in value or "'" in value:
            return False
        p = urlparse(value)
        # Accessing .port forces urllib to reject malformed `host:port` forms.
        _ = p.port
        return p.scheme.lower() in {"http", "https"} and bool(p.hostname) and not p.username and not p.password
    except (TypeError, ValueError):
        return False


def amazon_locale(value: str | None = None) -> str:
    host = (value or os.environ.get("SILLY_AMAZON_LOCALE") or "www.amazon.com").lower().strip()
    if not re.fullmatch(r"[a-z0-9][a-z0-9.-]*amazon\.[a-z.]{2,12}", host):
        return "www.amazon.com"
    return host


SEARCH_ROOTS = {
    "google": "https://www.google.com/search?q=",
    "youtube": "https://www.youtube.com/results?search_query=",
}


def valid_search_query(value: str) -> bool:
    """Accept human search text, but never control characters or oversized input."""
    return (isinstance(value, str) and 0 < len(value.strip()) <= 400
            and not any(ord(char) < 32 for char in value))


def search_url(site: str, query: str, amazon_host: str | None = None) -> str | None:
    """Build the sole browser destination for a registered search site."""
    site = normalize(site)
    if not valid_search_query(query):
        return None
    roots = {**SEARCH_ROOTS, "amazon": f"https://{amazon_locale(amazon_host)}/s?k="}
    root = roots.get(site)
    return root + quote_plus(query.strip()) if root else None


class WindowsExecutor:
    """Small adapter around the existing Windows helpers; replaceable in tests."""
    def __init__(self, winctl):
        self.winctl = winctl

    def applications(self) -> list[dict[str, str]]:
        return self.winctl.apps()

    def launch(self, name: str) -> bool:
        # Prefer an existing window so “switch to Chrome” does not create an
        # avoidable second instance. Older helpers and mocks may not expose
        # focus_app, in which case the existing safe launcher remains used.
        focus = getattr(self.winctl, "focus_app", None)
        if callable(focus) and focus(name):
            return True
        return bool(self.winctl.launch(name))

    def open_url(self, url: str) -> bool:
        os.startfile(url)  # Windows registered HTTP(S) handler; validated by the registry.
        return True

    def open_in_browser(self, browser: str, url: str) -> bool:
        return bool(self.winctl.launch_url(browser, url))

    def arrange(self, name: str, position: str, screen: str) -> str:
        return self.winctl.place(name, position, screen)


class ActionRegistry:
    def __init__(self, executor: Any, amazon_host: str | None = None):
        self.executor = executor
        self.amazon_host = amazon_locale(amazon_host)
        self._specs = {
            "open_application": ActionSpec("open_application", {"name": str}, Permission.NONE, self._open_application),
            "open_url": ActionSpec("open_url", {"url": str}, Permission.NONE, self._open_url),
            "open_browser_url": ActionSpec("open_browser_url", {"browser": str, "url": str}, Permission.NONE, self._open_browser_url),
            "search_website": ActionSpec("search_website", {"site": str, "query": str}, Permission.NONE, self._search_website),
            "search_website_in_browser": ActionSpec("search_website_in_browser", {"site": str, "query": str, "browser": str}, Permission.NONE, self._search_website_in_browser),
            "arrange_window": ActionSpec("arrange_window", {"application": str, "position": str, "screen": str}, Permission.NONE, self._arrange_window),
        }

    @property
    def action_ids(self) -> set[str]:
        return set(self._specs)

    def execute(self, action_id: str, params: dict[str, Any], confirmed: bool = False) -> ActionResult:
        spec = self._specs.get(action_id)
        if not spec:
            return ActionResult(Status.FAILURE, f"Unsupported action: {action_id}")
        if not isinstance(params, dict) or set(params) != set(spec.fields):
            return ActionResult(Status.FAILURE, "Malformed action parameters")
        if any(not isinstance(params[k], kind) or not params[k].strip() for k, kind in spec.fields.items()):
            return ActionResult(Status.FAILURE, "Malformed action parameters")
        if spec.permission == Permission.CONFIRM and not confirmed:
            return ActionResult(Status.CANCELLED, "Confirmation is required")
        try:
            return spec.executor(params, self.executor)
        except (OSError, ValueError) as exc:
            return ActionResult(Status.FAILURE, str(exc) or "The action could not be completed")

    def _resolve_application(self, value: str, executor: Any) -> tuple[str | None, list[str]]:
        requested = ALIASES.get(normalize(value), value)
        apps = [a.get("name", "") for a in executor.applications() if isinstance(a, dict) and isinstance(a.get("name"), str)]
        exact = [name for name in apps if _key(name) == _key(requested)]
        if len(exact) == 1:
            return exact[0], []
        partial = [name for name in apps if _key(name).startswith(_key(requested))]
        if len(partial) == 1:
            return partial[0], []
        return None, partial[:5]

    def _open_application(self, params: dict[str, Any], executor: Any) -> ActionResult:
        name, choices = self._resolve_application(params["name"], executor)
        if not name:
            return ActionResult(Status.FAILURE, "No matching application was found" if not choices else "Application name is ambiguous", {"choices": choices})
        if not executor.launch(name):
            return ActionResult(Status.FAILURE, f"Could not open {name}")
        return ActionResult(Status.SUCCESS, f"Opened {name}.", {"application": name})

    def _open_url(self, params: dict[str, Any], executor: Any) -> ActionResult:
        url = params["url"].strip()
        if not valid_http_url(url):
            return ActionResult(Status.FAILURE, "Only valid HTTP or HTTPS URLs can be opened")
        if not executor.open_url(url):
            return ActionResult(Status.FAILURE, "Could not open the URL")
        return ActionResult(Status.SUCCESS, "Opened URL.", {"url": url})

    def _open_browser_url(self, params: dict[str, Any], executor: Any) -> ActionResult:
        url = params["url"].strip()
        if not valid_http_url(url):
            return ActionResult(Status.FAILURE, "Only valid HTTP or HTTPS URLs can be opened")
        browser, choices = self._resolve_application(params["browser"], executor)
        if not browser:
            return ActionResult(Status.FAILURE, "No matching browser was found" if not choices else "Browser name is ambiguous", {"choices": choices})
        if not executor.open_in_browser(browser, url):
            return ActionResult(Status.FAILURE, f"Could not open the URL in {browser}")
        return ActionResult(Status.SUCCESS, f"Opened URL in {browser}.", {"url": url, "browser": browser})

    def _search_website(self, params: dict[str, Any], executor: Any) -> ActionResult:
        site, query = normalize(params["site"]), params["query"].strip()
        url = search_url(site, query, self.amazon_host)
        if not url:
            return ActionResult(Status.FAILURE, "Unsupported search website")
        if not executor.open_url(url):
            return ActionResult(Status.FAILURE, "Could not open the search")
        return ActionResult(Status.SUCCESS, f"Searched {query} on {site.title()}.", {"url": url, "site": site})

    def _search_website_in_browser(self, params: dict[str, Any], executor: Any) -> ActionResult:
        site, query = normalize(params["site"]), params["query"].strip()
        url = search_url(site, query, self.amazon_host)
        if not url:
            return ActionResult(Status.FAILURE, "Unsupported search website")
        browser, choices = self._resolve_application(params["browser"], executor)
        if not browser:
            return ActionResult(Status.FAILURE, "No matching browser was found" if not choices else "Browser name is ambiguous", {"choices": choices})
        if not executor.open_in_browser(browser, url):
            return ActionResult(Status.FAILURE, f"Could not open the search in {browser}")
        return ActionResult(Status.SUCCESS, f"Searched {query} on {site.title()} in {browser}.", {"url": url, "site": site, "browser": browser})

    def _arrange_window(self, params: dict[str, Any], executor: Any) -> ActionResult:
        name, choices = self._resolve_application(params["application"], executor)
        if not name:
            return ActionResult(Status.FAILURE, "No matching application was found" if not choices else "Application name is ambiguous", {"choices": choices})
        position = normalize(params["position"])
        if position == "maximized":
            position = "full"
        if position not in {"left", "right", "center", "full"}:
            return ActionResult(Status.FAILURE, "Unsupported window position")
        screen = normalize(params["screen"])
        if screen not in {"current", "laptop", "monitor"}:
            return ActionResult(Status.FAILURE, "Unsupported screen target")
        result = executor.arrange(name, position, screen)
        if not isinstance(result, str) or result.lower().startswith(("no window", "where must", "could not", "failed")):
            return ActionResult(Status.FAILURE, result or "Could not arrange the window")
        return ActionResult(Status.SUCCESS, f"{name}: {position}" + (f" on {screen}" if screen != "current" else "."), {"application": name, "position": position, "screen": screen})


@dataclass(frozen=True)
class Route:
    matched: bool
    action_id: str = ""
    params: dict[str, str] = field(default_factory=dict)


def route_transcript(transcript: str) -> Route:
    raw = transcript.strip()
    text = normalize(raw)
    # Remove conversational framing once, before intent parsing. The untouched
    # raw text is still used for a captured search query, so names and Hindi
    # script are never reconstructed from normalized command words.
    text = re.sub(r"^(?:(?:hey|hi|okay|ok)\s+)?(?:silly\s*[,:]?\s*)?(?:(?:please|can you|could you|would you)\s+)?", "", text).strip()
    intent_raw = re.sub(r"^(?:(?:hey|hi|okay|ok)\s+)?(?:silly\s*[,:]?\s*)?(?:(?:please|can you|could you|would you)\s+)?", "", raw, flags=re.I).strip()
    def youtube_search(query: str, requested_browser: str = "") -> Route:
        query = query.strip()
        if requested_browser:
            return Route(True, "open_browser_url", {"browser": requested_browser.lower(), "url": "https://www.youtube.com/results?search_query=" + quote_plus(query)})
        return Route(True, "search_website", {"site": "youtube", "query": query})

    def website_search(site: str, query: str, requested_browser: str = "") -> Route:
        """Route variable search slots through registered actions, never a command line."""
        query = query.strip()
        if not valid_search_query(query):
            return Route(False)
        if requested_browser:
            return Route(True, "search_website_in_browser", {"site": site, "query": query, "browser": requested_browser.lower()})
        return Route(True, "search_website", {"site": site, "query": query})

    # Preserve the raw query (including Hindi script and artist names); normalize
    # only command and website keywords.
    hindi_open_app = re.fullmatch(r"(क्रोम|नोटपैड) (?:खोलो|खोलिए)", raw)
    if hindi_open_app:
        return Route(True, "open_application", {"name": {"क्रोम": "Chrome", "नोटपैड": "Notepad"}[hindi_open_app[1]]})
    if re.fullmatch(r"यूट्यूब (?:खोलो|खोलिए)", raw):
        return Route(True, "open_url", {"url": "https://www.youtube.com/"})
    hindi_song = re.fullmatch(r"यूट्यूब (?:पर|पे) (.+?) के गाने (?:चलाओ|चलाइए)", raw)
    if hindi_song and hindi_song[1].strip():
        return youtube_search(hindi_song[1])
    hindi_search = re.fullmatch(r"यूट्यूब (?:पर|पे) (.+?) (?:खोजो|खोजिए|सर्च करो)", raw)
    if hindi_search and hindi_search[1].strip():
        return youtube_search(hindi_search[1])
    # Keep the content query separate from Hindi action words.  In particular,
    # "Raftaar ke songs chalao" should search Raftaar, not those suffix words.
    hinglish_song = re.fullmatch(r"(?:youtube )?(?:pe|par) (.+?) ke songs? (?:chala do|chalao)(?: (?:in|on|using) (chrome|edge))?", raw, flags=re.I)
    if hinglish_song and hinglish_song[1].strip():
        return youtube_search(hinglish_song[1], hinglish_song[2] or "")
    hinglish_search = re.fullmatch(r"(?:youtube )?(?:pe|par) (.+?) search karo(?: (?:in|on|using) (chrome|edge))?", raw, flags=re.I)
    if hinglish_search and hinglish_search[1].strip():
        return youtube_search(hinglish_search[1], hinglish_search[2] or "")
    open_site_search = re.fullmatch(r"(?:open|go to|launch) (youtube|amazon|google) (?:and )?(?:search(?: for)?|look up) (.+?)(?: (?:in|on|using) (chrome|edge))?", raw, flags=re.I)
    if open_site_search:
        return website_search(open_site_search[1].lower(), open_site_search[2], open_site_search[3] or "")
    go_search = re.fullmatch(r"(?:go to )?youtube (?:and )?(?:search(?: for)?|search karo|pe|par) (.+?)(?: (?:in|on|using) (chrome|edge))?", raw, flags=re.I)
    if go_search and go_search[1].strip():
        return youtube_search(go_search[1], go_search[2] or "")
    play = re.fullmatch(r"(?:play|play some|play music by) (.+?)(?: (?:music|songs?))? on youtube(?: (?:in|on|using) (chrome|edge))?", raw, flags=re.I)
    if play and play[1].strip():
        return youtube_search(play[1], play[2] or "")
    # "Search for X on YouTube" means a YouTube search, not a Google search
    # whose literal query happens to end in "on YouTube".  Keep this ahead of
    # the general search grammar so the source site is unambiguous while the
    # captured query keeps its dots, hyphens, Unicode, and original casing.
    search_on_site = re.fullmatch(r"(?:search|look up|google)(?: for)? (.+?) (?:on|in) (youtube|amazon|google|the web|web|online)(?: (?:in|on|using) (chrome|edge))?", raw, flags=re.I)
    if search_on_site and search_on_site[1].strip():
        site = search_on_site[2].lower()
        site = "google" if site in {"the web", "web", "online"} else site
        query, requested_browser = search_on_site[1].strip(), search_on_site[3] or ""
        return website_search(site, query, requested_browser)
    search = re.fullmatch(r"(?:search|google|look up)(?: (?:on |in )?(google|youtube|amazon|the web|web|online))?(?: for)? (.+?)(?: (?:in|on|using) (chrome|edge))?", raw, flags=re.I)
    if search and search[2].strip():
        site = (search[1] or "google").lower()
        site = "google" if site in {"the web", "web", "online"} else site
        return website_search(site, search[2], search[3] or "")
    arrange = re.fullmatch(r"(?:move|snap|arrange|put) (.+?) (?:to )?(left|right|center|centred|maximize|maximized|full screen)(?: on (current|laptop|monitor))?", text)
    if arrange:
        pos = {"centred": "center", "maximize": "maximized", "full screen": "maximized"}.get(arrange[2], arrange[2])
        return Route(True, "arrange_window", {"application": arrange[1], "position": pos, "screen": arrange[3] or "current"})
    opened = re.fullmatch(r"(?:open|launch|start|focus|switch to|go to) (.+)", text)
    opened_raw = re.fullmatch(r"(?:open|launch|start|focus|switch to|go to) (.+)", intent_raw, flags=re.I)
    if opened:
        target = (opened_raw[1] if opened_raw else opened[1]).strip().rstrip('.,!')
        sites = {"youtube": "https://www.youtube.com/", "github": "https://github.com/", "google": "https://www.google.com/"}
        target_browser = re.fullmatch(r"(.+?) (?:in|on|using) (chrome|edge)", target, flags=re.I)
        if target_browser:
            site_target, browser_name = target_browser[1].strip(), target_browser[2].lower()
            if normalize(site_target) in sites:
                return Route(True, "open_browser_url", {"browser": browser_name, "url": sites[normalize(site_target)]})
            candidate = site_target if re.match(r"https?://", site_target, flags=re.I) else "https://" + site_target
            if "." in site_target and valid_http_url(candidate):
                return Route(True, "open_browser_url", {"browser": browser_name, "url": candidate})
        if normalize(target) in sites:
            return Route(True, "open_url", {"url": sites[normalize(target)]})
        tab = re.fullmatch(r"(?:a )?new (chrome|edge) tab", normalize(target)) or re.fullmatch(r"(?:a )?new tab (?:in|on|using) (chrome|edge)", normalize(target))
        if tab:
            # A safe, known HTTPS destination creates a new browser surface; no
            # user text is ever passed as a command-line browser argument.
            return Route(True, "open_browser_url", {"browser": tab[1], "url": "https://www.google.com/"})
        candidate = target if re.match(r"https?://", target) else "https://" + target
        if "." in target and valid_http_url(candidate):
            return Route(True, "open_url", {"url": candidate})
        return Route(True, "open_application", {"name": target})
    return Route(False)
