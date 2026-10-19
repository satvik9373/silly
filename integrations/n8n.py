"""n8n: run any of your workflows by voice. Every active workflow with a Webhook trigger is a command."""
import json
from . import http, arg

TITLE = 'n8n'
ABOUT = 'Any workflow with a Webhook trigger becomes something you can say: "run the morning report", "log my run: 5k".'
EXAMPLE = 'http://<server>:5678'
KEY_HELP = 'Settings → n8n API → Create an API key. Then give your workflows a Webhook trigger.'
KEY_PAGE = '/settings/api'
FIELDS = [('url', 'Address', False), ('key', 'API key', True)]
WORDS = r'\b(n8n|workflow|workflows|automation|automations|run the|trigger|kick off|start the)\b'
HELP = '{CMD} list (workflows you can run) | run "<workflow name>" ["<text to send it>"] (prints what the workflow answers)'
RISKY = {'run': 'Run this workflow?'}


def _h(cfg):
    return {'X-N8N-API-KEY': cfg['key']}


def check(cfg):
    try:
        n = len(_hooks(cfg))
        return f'Connected. {n} workflow(s) with a Webhook trigger.'
    except Exception as e:
        return f'Could not connect: {e}'


def _hooks(cfg):
    """[(workflow name, method, webhook path)] for active workflows."""
    out, cursor = [], None
    for _ in range(10):
        r = http('GET', cfg['url'] + '/api/v1/workflows', _h(cfg), active='true', limit=100, cursor=cursor)
        for w in r.get('data', []):
            for n in w.get('nodes', []):
                if n.get('type') == 'n8n-nodes-base.webhook' and not n.get('disabled'):
                    p = n.get('parameters', {})
                    out.append((w['name'], p.get('httpMethod', 'GET'), p.get('path') or n.get('webhookId')))
        cursor = r.get('nextCursor')
        if not cursor:
            break
    return out


def run(cfg, args):
    what = arg(args, 0)
    if what == 'list':
        return '\n'.join(f'{n} ({m})' for n, m, _ in _hooks(cfg)) or 'no active workflows with a Webhook trigger'
    if what == 'run' and arg(args, 1):
        name, text = args[1].lower(), ' '.join(args[2:])
        hooks = _hooks(cfg)
        hit = next((h for h in hooks if h[0].lower() == name), None) or next((h for h in hooks if name in h[0].lower()), None)
        if not hit:
            return f'no workflow called "{args[1]}". Runnable: ' + ', '.join(h[0] for h in hooks)
        wname, method, path = hit
        if method.upper() == 'GET':
            r = http('GET', f"{cfg['url']}/webhook/{path}", {}, text=text or None, source='silly', timeout=60)
        else:
            r = http(method.upper(), f"{cfg['url']}/webhook/{path}", {}, {'text': text, 'source': 'silly'}, timeout=60)
        answer = r if isinstance(r, str) else json.dumps(r)[:1500]
        return f'ran {wname}' + (f': {answer}' if answer and answer not in ('null', '""') else '')
    return HELP.replace('{CMD}', 'silly --int n8n')
