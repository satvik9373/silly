"""Paperless-ngx: find a document by what's in it, read it, open it."""
import os
from . import http, arg

TITLE = 'Paperless'
ABOUT = 'Paperless-ngx. "Find my car insurance policy" · "When does the fridge warranty end?"'
EXAMPLE = 'http://<server>:8000'
KEY_HELP = 'Your user menu (top right) → My Profile → API Auth Token'
KEY_PAGE = '/'
FIELDS = [('url', 'Address', False), ('key', 'API token', True)]
WORDS = r'\b(paperless|document|documents|docs?|receipt|receipts|invoice|invoices|bill|bills|statement|policy|warranty|contract|lease|tax|taxes|letter|scan|scanned|paperwork|insurance|manual)\b'
HELP = ('{CMD} search "<words>" (full text; newest first) | read <id> (its text) | open <id> (in the browser). '
        'Answer from read rather than guessing from titles.')
RISKY = {}


def _h(cfg):
    return {'Authorization': f'Token {cfg["key"]}', 'Accept': 'application/json'}   # the server's own API version: pinning one 406s on newer releases


def check(cfg):
    try:
        http('GET', cfg['url'] + '/api/documents/', _h(cfg), page_size=1)
        return 'Connected.'
    except Exception as e:
        return f'Could not connect: {e}'


def run(cfg, args):
    what = arg(args, 0)
    if what == 'search':
        names = {}
        try:
            names = {c['id']: c['name'] for c in http('GET', cfg['url'] + '/api/correspondents/', _h(cfg), page_size=500).get('results', [])}
        except Exception:
            pass
        r = http('GET', cfg['url'] + '/api/documents/', _h(cfg), query=' '.join(args[1:]), page_size=10)
        return '\n'.join(f"id {d['id']}: {d['title']} — {d.get('created', '')[:10]}" + (f", from {names[d['correspondent']]}" if d.get('correspondent') in names else '')
                         for d in r.get('results', [])) or 'no documents found'
    if what == 'read' and arg(args, 1).isdigit():
        d = http('GET', f"{cfg['url']}/api/documents/{args[1]}/", _h(cfg))
        return f"{d['title']} ({d.get('created', '')[:10]})\n" + (d.get('content') or '(no text)')[:5000]
    if what == 'open' and arg(args, 1).isdigit():
        os.startfile(f"{cfg['url']}/documents/{args[1]}/details")
        return 'opened it in Paperless'
    return HELP.replace('{CMD}', 'silly --int paperless')
