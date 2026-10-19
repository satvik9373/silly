"""Immich: find photos by what's in them, who's in them, and when; open them or a whole search in the browser."""
import json, os, urllib.parse
from . import http, arg, opt

TITLE = 'Immich'
ABOUT = '"Show me photos from the cottage last summer" · "Pictures of Sam at the beach" · "Open the Japan album"'
EXAMPLE = 'http://<server>:2283'
KEY_HELP = 'Your avatar (top right) → Account Settings → API Keys → New API Key'
KEY_PAGE = '/user-settings?isOpen=api-keys'
FIELDS = [('url', 'Address', False), ('key', 'API key', True)]
WORDS = r'\b(immich|photo|photos|picture|pictures|pics?|album|albums|selfie|selfies|screenshot of me|video of|videos of|memories|camera roll)\b'
HELP = ('{CMD} show "<what>" [--after YYYY-MM-DD] [--before YYYY-MM-DD] [--person "<name>"] (opens the search in the browser: use this to "show me") | '
        'search "<what>" [same options] (lists them) | open <id> | albums ["<words>"] | album "<name>" (opens it). Work out dates for "last summer" etc. from Now.')
RISKY = {}


def _h(cfg):
    return {'x-api-key': cfg['key']}


def check(cfg):
    try:
        http('GET', cfg['url'] + '/api/users/me', _h(cfg))
        return 'Connected.'
    except Exception as e:
        return f'Could not connect: {e}'


def _query(cfg, args):
    args = list(args)
    after, before, person = opt(args, '--after'), opt(args, '--before'), opt(args, '--person')
    q = {'query': ' '.join(args[1:])}
    if after:
        q['takenAfter'] = after + 'T00:00:00.000Z'
    if before:
        q['takenBefore'] = before + 'T23:59:59.999Z'
    if person:
        people = http('GET', cfg['url'] + '/api/people', _h(cfg), withHidden='false').get('people', [])
        hit = next((p for p in people if p.get('name', '').lower() == person.lower()), None) or next((p for p in people if person.lower() in p.get('name', '').lower()), None)
        if not hit:
            return None, f'no person called "{person}" in Immich. Named people: ' + ', '.join(p['name'] for p in people if p.get('name'))[:400]
        q['personIds'] = [hit['id']]
    if not q['query']:
        q.pop('query')
    return q, ''


def run(cfg, args):
    what = arg(args, 0)
    if what in ('search', 'show'):
        q, err = _query(cfg, args)
        if err:
            return err
        if what == 'show':
            os.startfile(cfg['url'] + '/search?query=' + urllib.parse.quote(json.dumps(q)))
            return 'opened the search in Immich'
        path = '/api/search/smart' if 'query' in q else '/api/search/metadata'
        r = http('POST', cfg['url'] + path, _h(cfg), {**q, 'size': 12})
        items = (r.get('assets') or {}).get('items', [])
        return '\n'.join(f"id {a['id']}: {a.get('originalFileName', '')} — {(a.get('fileCreatedAt') or '')[:10]}"
                         + (f", {(a.get('exifInfo') or {}).get('city')}" if (a.get('exifInfo') or {}).get('city') else '') for a in items) or 'no photos found'
    if what == 'open' and arg(args, 1):
        os.startfile(f"{cfg['url']}/photos/{args[1]}")
        return 'opened it in Immich'
    if what in ('albums', 'album'):
        words = ' '.join(args[1:]).lower()
        albums = http('GET', cfg['url'] + '/api/albums', _h(cfg))
        hits = [a for a in albums if not words or words in a.get('albumName', '').lower()]
        if what == 'album':
            exact = next((a for a in hits if a.get('albumName', '').lower() == words), None) or (hits[0] if hits else None)
            if not exact:
                return f'no album called "{words}". Albums: ' + ', '.join(a['albumName'] for a in albums)[:400]
            os.startfile(f"{cfg['url']}/albums/{exact['id']}")
            return f"opened the album {exact['albumName']}"
        return '\n'.join(f"{a['albumName']} ({a.get('assetCount', 0)} items)" for a in hits) or 'no albums'
    return HELP.replace('{CMD}', 'silly --int immich')
