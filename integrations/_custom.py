"""Integrations people add themselves in Settings, no code: an MCP server, or any web API.

Each is a definition saved in integrations.json under "_custom" ({kind, title, about, words, auth, auth_name, docs, ask});
Custom(name, d) turns one into the same shape as a module in this folder, so Settings, hints, the gate and removal
treat it like the built-in ones.
"""
import base64, json, re, urllib.error, urllib.parse, urllib.request

AUTHS = ('bearer', 'header', 'query', 'basic', 'none')
READ_VERBS = re.compile(r'^(get|list|search|read|find|query|describe|fetch|show|lookup|count|check|status)', re.I)


def slug(title):
    return 'my_' + (re.sub(r'[^a-z0-9]+', '_', title.lower()).strip('_')[:24] or 'service')


def words_regex(title, words):
    ws = [w.strip() for w in re.split(r'[,\n]', words or '') if w.strip()] + [title]
    return r'\b(' + '|'.join(re.escape(w) for w in sorted(set(ws), key=len, reverse=True)) + r')\b'


def _auth(d, cfg, headers, url):
    key, how, name = cfg.get('key', ''), d.get('auth', 'bearer'), d.get('auth_name', '')
    if not key or how == 'none':
        return headers, url
    if how == 'bearer':
        headers['Authorization'] = f'Bearer {key}'
    elif how == 'header':
        headers[name or 'X-Api-Key'] = key
    elif how == 'basic':
        headers['Authorization'] = 'Basic ' + base64.b64encode(key.encode()).decode()   # key is "user:password"
    elif how == 'query':
        url += ('&' if '?' in url else '?') + urllib.parse.urlencode({name or 'apikey': key})
    return headers, url



class Custom:
    def __init__(self, name, d):
        self.name, self.d = name, d
        self.TITLE = d.get('title') or name
        self.ABOUT = d.get('about', '') + ('' if d.get('about') else f'Your own {"MCP server" if d.get("kind") == "mcp" else "web API"}.')
        self.EXAMPLE = 'http://<server>:<port>/mcp' if d.get('kind') == 'mcp' else 'http://<server>:<port>'
        self.KEY_HELP = 'Added by you. ' + ('Silly connects to it only for requests that use its words.' if d.get('kind') == 'mcp'
                                          else 'Reading runs freely; anything that changes it asks you first.')
        self.KEY_PAGE = ''
        self.FIELDS = [('url', 'Address', False), ('key', 'Key or token (blank if none)', True)]
        self.KEY_OPTIONAL = True   # plenty of home services have no key
        self.WORDS = words_regex(self.TITLE, d.get('words', ''))
        self.CUSTOM = d.get('kind', 'api')
        docs = f' API docs: {d["docs"]}.' if d.get('docs') else ''
        if d.get('kind') == 'mcp':
            self.HELP = f'{d.get("about", "")} Its tools are the mcp__{name}__ ones.'.strip()
            self.RISKY = {}
            self.MCP = self._mcp
        else:
            self.HELP = (f'{d.get("about", "")} Its REST API: {{CMD}} get "/path?query" | post|put|patch|delete "/path" \'<json body>\'.{docs} '
                         'Use the endpoints you know for this app; if unsure, get its API root or docs first.').strip()
            self.RISKY = {m: f'Change something in {self.TITLE}?' for m in ('post', 'put', 'patch', 'delete')}

    # --- MCP ---
    def _mcp(self, cfg):
        headers, url = _auth(self.d, cfg, {}, cfg['url'])
        return {'type': 'sse' if url.rstrip('/').endswith('/sse') else 'http', 'url': url, **({'headers': headers} if headers else {})}

    def mcp_risky(self, tool, args):
        if self.CUSTOM != 'mcp' or not self.d.get('ask', True) or READ_VERBS.match(tool):
            return ''
        what = re.sub(r'(?<=[a-z])(?=[A-Z])|_', ' ', re.sub(r'^Hass', '', tool)).strip().lower()
        target = next((str(args[k]) for k in ('name', 'entity', 'entity_id', 'target', 'title', 'id', 'path') if args.get(k)), '')
        return f'{self.TITLE}: {what}{" " + target if target else ""}?'

    # --- web API ---
    def _call(self, cfg, method, path, body=None):
        url = cfg['url'].rstrip('/') + '/' + path.lstrip('/')
        headers, url = _auth(self.d, cfg, {'Accept': 'application/json, text/plain, */*'}, url)
        data = None
        if body:
            data = (body if isinstance(body, str) else json.dumps(body)).encode()
            headers['Content-Type'] = 'application/json'
        r = urllib.request.urlopen(urllib.request.Request(url, data=data, method=method.upper(), headers=headers), timeout=15)
        raw = r.read().decode('utf-8', 'replace')
        try:
            return json.dumps(json.loads(raw), separators=(',', ':'))[:4000] if raw.strip() else f'{r.status} OK (no content)'
        except ValueError:
            return ' '.join(re.sub(r'(?is)<(script|style)\b.*?</\1>|<[^>]+>', ' ', raw).split())[:3000]

    def check(self, cfg):
        try:
            if self.CUSTOM == 'mcp':
                headers, url = _auth(self.d, cfg, {'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream'}, cfg['url'])
                if url.rstrip('/').endswith('/sse'):
                    urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=5).close()
                else:
                    body = {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
                            'params': {'protocolVersion': '2025-03-26', 'capabilities': {}, 'clientInfo': {'name': 'silly', 'version': '1'}}}
                    urllib.request.urlopen(urllib.request.Request(url, json.dumps(body).encode(), headers, method='POST'), timeout=8).close()
            else:
                self._call(cfg, 'GET', '/')
            return 'Connected.'
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                return f'It answered {e.code}: check the key and how it is sent.'
            return 'Connected.' if self.CUSTOM == 'api' and e.code < 500 else f'It answered {e.code} {e.reason}.'
        except Exception as e:
            return f'Could not connect: {getattr(e, "reason", e)}'

    def run(self, cfg, args):
        if self.CUSTOM == 'mcp':
            return f'{self.TITLE} is used through its MCP tools (mcp__{self.name}__…). ' + self.check(cfg)
        method = (args[0] if args else '').lower()
        if method not in ('get', 'post', 'put', 'patch', 'delete') or len(args) < 2:
            return self.HELP.replace('{CMD}', f'silly --int {self.name}')
        path = re.sub(r'^[A-Za-z]:/.*?/Git(?=/)', '', args[1].replace('\\', '/'))   # a path Git Bash rewrote anyway
        return self._call(cfg, method, path, ' '.join(args[2:]) or None)
