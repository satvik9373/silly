"""Seerr (Jellyseerr / Overseerr): find movies and shows, request them, and see what's on the way."""
from . import http, year, arg

TITLE = 'Seerr'
ABOUT = 'Jellyseerr / Overseerr. "Add Severance season 2" · "What have I requested?"'
EXAMPLE = 'http://<server>:5055'
KEY_HELP = 'Settings → General → API Key'
KEY_PAGE = '/settings'
FIELDS = [('url', 'Address', False), ('key', 'API key', True)]
WORDS = r'\b(seerr|overseerr|jellyseerr|request|add|download|get me|grab|movie|movies|show|shows|series|season|tv|film|requests?)\b'
HELP = ('{CMD} search "<title>" (status of each: available, requested…) | request <movie|tv> <tmdb id> [season numbers…] '
        '(search first and use its id; tv with no seasons = all) | requests (the latest and their status)')
RISKY = {}
STATUS = {1: 'unknown', 2: 'requested', 3: 'downloading', 4: 'partly available', 5: 'available', 6: 'blocklisted', 7: 'deleted'}


def _h(cfg):
    return {'X-Api-Key': cfg['key']}


def check(cfg):
    try:
        http('GET', cfg['url'] + '/api/v1/auth/me', _h(cfg))
        return 'Connected.'
    except Exception as e:
        return f'Could not connect: {e}'


def _status(m):
    st = (m.get('mediaInfo') or {}).get('status')
    return STATUS.get(st, 'not requested') if st else 'not requested'


def run(cfg, args):
    what = arg(args, 0)
    if what == 'search':
        r = http('GET', cfg['url'] + '/api/v1/search', _h(cfg), query=' '.join(args[1:]), page=1)
        out = [f"{m.get('title') or m.get('name')}{year(m.get('releaseDate') or m.get('firstAirDate'))} [{m['mediaType']} id {m['id']}] — {_status(m)}"
               for m in r.get('results', []) if m.get('mediaType') in ('movie', 'tv')][:8]
        return '\n'.join(out) or 'nothing found'
    if what == 'request' and len(args) >= 3:
        kind, tmdb = args[1], int(args[2])
        body = {'mediaType': kind, 'mediaId': tmdb}
        if kind == 'tv':
            seasons = [int(s) for s in args[3:] if s.isdigit()]
            if not seasons:   # "all" seasons, spelled out: every Seerr version accepts a list
                info = http('GET', f"{cfg['url']}/api/v1/tv/{tmdb}", _h(cfg))
                seasons = [s['seasonNumber'] for s in info.get('seasons', []) if s.get('seasonNumber', 0) > 0]
            body['seasons'] = seasons
        r = http('POST', cfg['url'] + '/api/v1/request', _h(cfg), body)
        media = r.get('media') or {}
        return f"requested ({STATUS.get(media.get('status'), 'pending')})" + ('; it needs approval in Seerr' if r.get('status') == 1 else '')
    if what == 'requests':
        r = http('GET', cfg['url'] + '/api/v1/request', _h(cfg), take=10, sort='added', filter='all')
        out = []
        for q in r.get('results', []):
            m = q.get('media') or {}
            kind = m.get('mediaType', '')
            try:
                d = http('GET', f"{cfg['url']}/api/v1/{kind}/{m.get('tmdbId')}", _h(cfg))
                name = (d.get('title') or d.get('name') or '') + year(d.get('releaseDate') or d.get('firstAirDate'))
            except Exception:
                name = f"{kind} {m.get('tmdbId')}"
            out.append(f"{name} — {STATUS.get(m.get('status'), '?')}")
        return '\n'.join(out) or 'no requests'
    return HELP.replace('{CMD}', 'silly --int seerr')
