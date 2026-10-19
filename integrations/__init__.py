"""Integrations: the user's own services (Jellyfin, Seerr, Paperless…), one module each.

A module defines:
  TITLE    shown in Settings and in the AI's hints
  ABOUT    one line for Settings: what it lets you say
  EXAMPLE  an example address for the Address field (http://<server>:8096)
  KEY_HELP where the key is, in words;  KEY_PAGE: that page's path on the server, for the "Where's my key?" button
  FIELDS   [(key, label, secret?)] it needs; secrets go to Windows Credential Manager, the rest to integrations.json
  WORDS    a regex: the AI only hears about the integration when the request matches it, so unused ones cost nothing
  HELP     one line for the AI; {CMD} becomes the command to run it
  RISKY    {subcommand: question}: those need the user's Allow in safe mode
  run(cfg, args) -> str      cfg holds every field, secrets included; never print them
  MCP(cfg) -> dict           optional: an HTTP MCP server Claude Code connects to for matching requests (Home Assistant)
  mcp_risky(tool, args) -> str   optional: a question for MCP tool calls that need an Allow

The AI runs them as:  silly --int <name> <subcommand> [args…]
Setup (Settings, or by hand):  silly --int <name> setup  then one "key=value" per line on stdin.

Three more places integrations come from, so people can add their own:
  - <config folder>/integrations/*.py: personal modules, same shape as these; they survive updates
  - Settings → Integrations → Add your own: an MCP server or any web API, no code (see _custom.py)
"""
import importlib, importlib.util, json, os, pkgutil, re, sys, urllib.error, urllib.parse, urllib.request

CONFIG = None   # set by atticus.py: <DIR>/integrations.json
_mods = {}


def user_dir():
    return os.path.join(os.path.dirname(CONFIG), 'integrations') if CONFIG else ''


def modules():
    if not _mods:
        for m in pkgutil.iter_modules(__path__):
            if not m.name.startswith('_'):
                try:
                    _mods[m.name] = importlib.import_module(f'{__name__}.{m.name}')
                except Exception as e:   # one broken integration must not take the others down
                    print(f'integration {m.name} failed to load: {e}', file=sys.stderr)
        d = user_dir()
        for f in sorted(os.listdir(d)) if d and os.path.isdir(d) else []:   # personal modules; a built-in of the same name wins
            stem = f[:-3]
            if f.endswith('.py') and not f.startswith('_') and stem not in _mods:
                try:
                    spec = importlib.util.spec_from_file_location(f'{__name__}.{stem}', os.path.join(d, f))
                    mod = importlib.util.module_from_spec(spec)
                    sys.modules[spec.name] = mod   # so its "from . import http" works
                    spec.loader.exec_module(mod)
                    mod.PERSONAL = True
                    _mods[stem] = mod
                except Exception as e:
                    print(f'your integration {f} failed to load: {e}', file=sys.stderr)
        from ._custom import Custom
        for n, d in (_saved().get('_custom') or {}).items():
            if n not in _mods:
                _mods[n] = Custom(n, d)
    return _mods


def add_custom(values):
    """Settings → Add your own. values: kind (mcp|api), title, url, key, auth, auth_name, about, words, docs, ask."""
    from ._custom import AUTHS, slug
    title = ' '.join(values.get('title', '').split())[:40]
    if not title or not values.get('url', '').strip():
        return 'Give it a name and an address.'
    name = slug(title)
    if name in modules() and name not in (_saved().get('_custom') or {}):   # a personal module took the name; same name again = an update
        return f'{title} is already an integration: set it up in its own card.'
    d = {'kind': 'mcp' if values.get('kind') == 'mcp' else 'api', 'title': title,
         'auth': values.get('auth') if values.get('auth') in AUTHS else 'bearer', 'auth_name': values.get('auth_name', '').strip()[:60],
         'about': ' '.join(values.get('about', '').split())[:200], 'words': values.get('words', '')[:300],
         'docs': values.get('docs', '').strip()[:200], 'ask': values.get('ask', 'true') != 'false'}
    allc = _saved()
    allc.setdefault('_custom', {})[name] = d
    os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
    json.dump(allc, open(CONFIG, 'w', encoding='utf-8'), indent=1)
    _mods.clear()   # load it like the rest
    return setup(name, {'url': values.get('url', ''), 'key': values.get('key', '')})


def _saved():
    try:
        return json.load(open(CONFIG, encoding='utf-8'))
    except (OSError, ValueError, TypeError):
        return {}


def config(name, secrets=True):
    """Every field of one integration ({} if it was never set up)."""
    import winctl
    mod, saved = modules().get(name), _saved().get(name)
    if not mod or not saved:
        return {}
    cfg = dict(saved)
    if secrets:
        for k, _, secret in mod.FIELDS:
            if secret:
                cfg[k] = winctl.secret_get(f'{name}/{k}')
    return cfg


def configured():
    """Set up and usable: saved, not turned off, and holding at least one of its keys (an address alone is not enough)."""
    import winctl
    saved, out = _saved(), []
    for n, mod in modules().items():
        if not saved.get(n) or not saved[n].get('enabled', True):
            continue
        secrets = [k for k, _, sec in mod.FIELDS if sec]
        if not secrets or getattr(mod, 'KEY_OPTIONAL', False) or any(winctl.secret_get(f'{n}/{k}') for k in secrets):
            out.append(n)
    return out


def setup(name, values):
    """values: {field: value}. Empty secret = keep the saved one."""
    import winctl
    mod = modules().get(name)
    if not mod:
        return f'no integration called {name}. There are: ' + ', '.join(modules())
    allc = _saved()
    cur = allc.get(name, {})
    for k, _, secret in mod.FIELDS:
        v = values.get(k, '').strip()
        if secret:
            if v:
                winctl.secret_set(f'{name}/{k}', v)
        elif v or k not in cur:
            cur[k] = v.rstrip('/') if k.endswith('url') else v
    cur.setdefault('enabled', True)
    allc[name] = cur
    os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
    json.dump(allc, open(CONFIG, 'w', encoding='utf-8'), indent=1)
    test = getattr(mod, 'check', None)
    return f'{mod.TITLE} saved.' + (' ' + test(config(name)) if test else '')


def remove(name):
    import winctl
    mod, allc = modules().get(name), _saved()
    if mod:
        for k, _, secret in mod.FIELDS:
            if secret:
                winctl.secret_set(f'{name}/{k}', '')
    allc.pop(name, None)
    (allc.get('_custom') or {}).pop(name, None)   # one you added: gone from the list too
    json.dump(allc, open(CONFIG, 'w', encoding='utf-8'), indent=1)
    _mods.clear()
    return f'{mod.TITLE if mod else name} removed.'


def catalog():
    """Every integration, for Settings → Integrations (never a secret's value)."""
    out = []
    for n, mod in sorted(modules().items(), key=lambda x: x[1].TITLE.lower()):
        cfg = config(n)
        out.append({'name': n, 'title': mod.TITLE, 'about': getattr(mod, 'ABOUT', ''), 'on': n in configured(),
                    'keyHelp': getattr(mod, 'KEY_HELP', ''), 'keyPage': getattr(mod, 'KEY_PAGE', ''), 'mcp': hasattr(mod, 'MCP'),
                    'custom': getattr(mod, 'CUSTOM', '') or ('personal' if getattr(mod, 'PERSONAL', False) else ''),
                    'fields': [{'k': k, 'label': lab, 'secret': sec, 'value': '' if sec else cfg.get(k, ''), 'has': bool(cfg.get(k)),
                                'example': getattr(mod, 'EXAMPLE', '') if k.endswith('url') else ''} for k, lab, sec in mod.FIELDS]})
    return out


def mcp_for(task):
    """{server name: Claude Code MCP config} for the MCP integrations this request is about."""
    out = {}
    for n in configured():
        mod = modules()[n]
        if hasattr(mod, 'MCP') and re.search(mod.WORDS, task, re.I):
            out[n] = mod.MCP(config(n))
    return out


def mcp_risky(tool, args):
    """tool: 'mcp__<server>__<tool>' -> a question, or ''."""
    parts = tool.split('__')
    mod = modules().get(parts[1]) if len(parts) > 2 else None
    f = getattr(mod, 'mcp_risky', None)
    return f(parts[2], args or {}) if f else ''


def hints(task, cmd):
    """Lines for the request: only the integrations the words are about."""
    out = []
    for n in configured():
        mod = modules()[n]
        if re.search(mod.WORDS, task, re.I):
            out.append(f'- {mod.TITLE}: ' + mod.HELP.replace('{CMD}', f'{cmd} {n}'))
    return '\n'.join(out)


def risky(cmd_tail):
    """cmd_tail: '<name> <subcommand> …' -> a question, or ''."""
    parts = cmd_tail.split()
    mod = modules().get(parts[0]) if parts else None
    return (getattr(mod, 'RISKY', {}) or {}).get(parts[1].strip('"\''), '') if mod and len(parts) > 1 else ''


def run(name, args):
    mod = modules().get(name)
    if not mod:
        return f'no integration called {name}'
    cfg = config(name)
    if not cfg:
        return f'{mod.TITLE} is not set up: Silly Settings → Integrations'
    try:
        return mod.run(cfg, args)
    except urllib.error.HTTPError as e:
        return f'{mod.TITLE} said {e.code} {e.reason}' + (' (check the API key in Settings → Integrations)' if e.code in (401, 403) else '')
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        return f"can't reach {mod.TITLE} at {cfg.get('url', '?')}: {getattr(e, 'reason', e)}. Away from home? It may need Tailscale."


# ---- small helpers for the modules ----

def http(method, url, headers=None, body=None, timeout=10, **query):
    q = {k: v for k, v in query.items() if v is not None}
    full = url + ('?' + urllib.parse.urlencode(q, doseq=True) if q else '')
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(full, data=data, method=method,
                                 headers={'Accept': 'application/json', **({'Content-Type': 'application/json'} if data else {}), **(headers or {})})
    raw = urllib.request.urlopen(req, timeout=timeout).read()
    try:
        return json.loads(raw or b'null')
    except ValueError:
        return raw.decode('utf-8', 'replace')


def year(s):
    return f' ({str(s)[:4]})' if s else ''


def arg(args, i, default=''):
    return args[i] if len(args) > i else default


def opt(args, flag, default=''):
    """--flag value from args (removed from them)."""
    if flag in args:
        i = args.index(flag)
        v = args[i + 1] if i + 1 < len(args) else default
        del args[i:i + 2]
        return v
    return default
