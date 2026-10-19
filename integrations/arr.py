"""Sonarr and Radarr: what's downloading right now, and what's coming out."""
import datetime
from . import http, arg

TITLE = 'Sonarr/Radarr'
ABOUT = '"What\'s downloading?" · "When\'s the next Abbott Elementary?" · "What movies come out this week?"'
EXAMPLE = 'http://<server>:8989  (Radarr: :7878)'
KEY_HELP = 'In each app: Settings → General → Security → API Key. Fill in one or both.'
KEY_PAGE = '/settings/general'
FIELDS = [('sonarr_url', 'Sonarr address', False), ('sonarr_key', 'Sonarr API key', True),
          ('radarr_url', 'Radarr address', False), ('radarr_key', 'Radarr API key', True)]
WORDS = r'\b(sonarr|radarr|download|downloading|downloads|queue|coming out|airing|calendar|this week|new episodes?|release|released)\b'
HELP = '{CMD} downloads (what is downloading, with progress) | calendar [days] (episodes and movies coming out, default 7)'
RISKY = {}


def _apps(cfg):
    return [(n, cfg.get(f'{n}_url'), cfg.get(f'{n}_key')) for n in ('sonarr', 'radarr') if cfg.get(f'{n}_url') and cfg.get(f'{n}_key')]


def check(cfg):
    out = []
    for n, url, key in _apps(cfg):
        try:
            http('GET', url + '/api/v3/system/status', {'X-Api-Key': key})
            out.append(f'{n.title()} connected.')
        except Exception as e:
            out.append(f'{n.title()}: {e}')
    return ' '.join(out) or 'Add at least one address and key.'


def run(cfg, args):
    what = arg(args, 0)
    if what == 'downloads':
        out = []
        for n, url, key in _apps(cfg):
            q = http('GET', url + '/api/v3/queue', {'X-Api-Key': key}, pageSize=20, includeSeries='true', includeMovie='true', includeEpisode='true')
            for r in q.get('records', []):
                size, left = r.get('size') or 0, r.get('sizeleft') or 0
                pct = f'{round(100 * (size - left) / size)}%' if size else ''
                if r.get('series'):
                    ep = r.get('episode') or {}
                    name = f"{r['series']['title']} S{ep.get('seasonNumber', 0):02}E{ep.get('episodeNumber', 0):02}"
                else:
                    name = (r.get('movie') or {}).get('title') or r.get('title', '?')
                eta = f", {r['timeleft']} left" if r.get('timeleft') else ''
                state = r.get('trackedDownloadState') or r.get('status', '')
                out.append(f'{name} — {pct} {state}{eta}'.replace('  ', ' '))
        return '\n'.join(out) or 'nothing downloading'
    if what == 'calendar':
        days = int(arg(args, 1, '7')) if arg(args, 1, '7').isdigit() else 7
        start = datetime.date.today()
        end = start + datetime.timedelta(days=days)
        out = []
        for n, url, key in _apps(cfg):
            for e in http('GET', url + '/api/v3/calendar', {'X-Api-Key': key}, start=start.isoformat(), end=end.isoformat(), includeSeries='true'):
                if n == 'sonarr':
                    when = (e.get('airDateUtc') or e.get('airDate') or '')[:10]
                    out.append((when, f"{(e.get('series') or {}).get('title', '?')} S{e.get('seasonNumber', 0):02}E{e.get('episodeNumber', 0):02} {e.get('title', '')}"
                                      + (' (downloaded)' if e.get('hasFile') else '')))
                else:
                    when = (e.get('digitalRelease') or e.get('physicalRelease') or e.get('inCinemas') or '')[:10]
                    out.append((when, f"{e.get('title', '?')} (movie)" + (' (downloaded)' if e.get('hasFile') else '')))
        return '\n'.join(f'{w}: {t}' for w, t in sorted(out)) or f'nothing in the next {days} days'
    return HELP.replace('{CMD}', 'silly --int arr')
