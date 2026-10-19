"""Jellyfin: what's on, what to resume, and playing it on a TV or in the browser."""
import os
from . import http, year, arg, opt

TITLE = 'Jellyfin'
ABOUT = '"What should I keep watching?" · "Play Breaking Bad on the living room TV" · "What\'s new?"'
EXAMPLE = 'http://<server>:8096'
KEY_HELP = 'Dashboard → API Keys → + (name it Silly)'
KEY_PAGE = '/web/#/dashboard/keys'
FIELDS = [('url', 'Address', False), ('user', 'Your Jellyfin user name', False), ('key', 'API key', True)]
WORDS = r'\b(jellyfin|watch|watching|play|resume|continue|episode|season|movie|movies|show|shows|series|tv|film|next up|latest)\b'
HELP = ('{CMD} search "<title>" | resume | nextup | latest | devices | play "<title>" [--on "<device>"] (no --on: opens it in the browser here). '
        'For "what should I watch", use resume and nextup.')
RISKY = {}


def _h(cfg):
    return {'Authorization': f'MediaBrowser Token="{cfg["key"]}", Client="Silly", Device="Silly", DeviceId="silly", Version="1"'}


def _user(cfg):
    users = http('GET', cfg['url'] + '/Users', _h(cfg))
    want = (cfg.get('user') or '').lower()
    u = next((u for u in users if u['Name'].lower() == want), None) or next((u for u in users if u['Policy'].get('IsAdministrator')), users[0])
    return u['Id']


def _line(i):
    kind = i.get('Type', '')
    if kind == 'Episode':
        name = f"{i.get('SeriesName', '')} S{i.get('ParentIndexNumber', 0):02}E{i.get('IndexNumber', 0):02} {i.get('Name', '')}"
    else:
        name = i.get('Name', '') + year(i.get('ProductionYear'))
    left = ''
    ud = i.get('UserData') or {}
    if ud.get('PlayedPercentage'):
        left = f" — {round(ud['PlayedPercentage'])}% watched"
    return f'{name} [{kind}]{left}'


def _items(cfg, path, **q):
    r = http('GET', cfg['url'] + path, _h(cfg), **q)
    return r.get('Items', r) if isinstance(r, dict) else r


def _find(cfg, uid, title):
    hits = _items(cfg, '/Items', userId=uid, searchTerm=title, IncludeItemTypes='Movie,Series,Episode,MusicAlbum,Audio', Recursive='true', Limit=8)
    exact = [i for i in hits if i.get('Name', '').lower() == title.lower()]
    return (exact or hits or [None])[0], hits


def check(cfg):
    try:
        _user(cfg)
        return 'Connected.'
    except Exception as e:
        return f'Could not connect: {e}'


def run(cfg, args):
    args = list(args)
    what = arg(args, 0)
    uid = _user(cfg)
    if what == 'search':
        _, hits = _find(cfg, uid, ' '.join(args[1:]))
        return '\n'.join(_line(i) for i in hits) or 'nothing by that name'
    if what == 'resume':
        return '\n'.join(_line(i) for i in _items(cfg, '/UserItems/Resume', userId=uid, Limit=8)) or 'nothing in progress'
    if what == 'nextup':
        return '\n'.join(_line(i) for i in _items(cfg, '/Shows/NextUp', userId=uid, Limit=8)) or 'no next episodes'
    if what == 'latest':
        items = http('GET', cfg['url'] + '/Items/Latest', _h(cfg), userId=uid, Limit=12)
        return '\n'.join(_line(i) for i in items) or 'nothing new'
    if what == 'devices':
        s = http('GET', cfg['url'] + '/Sessions', _h(cfg), controllableByUserId=uid)
        return '\n'.join(f"{x.get('DeviceName')} ({x.get('Client')})" + (f" — playing {x['NowPlayingItem']['Name']}" if x.get('NowPlayingItem') else '')
                         for x in s if x.get('SupportsRemoteControl')) or 'no devices to play on (open Jellyfin on the TV first)'
    if what == 'play':
        on = opt(args, '--on')
        item, _ = _find(cfg, uid, ' '.join(args[1:]))
        if not item:
            return 'nothing by that name'
        if item['Type'] == 'Series':   # a show: its next episode, else the first
            nxt = _items(cfg, '/Shows/NextUp', userId=uid, seriesId=item['Id'], Limit=1)
            item = nxt[0] if nxt else (_items(cfg, f"/Shows/{item['Id']}/Episodes", userId=uid, Limit=1) or [item])[0]
        if not on:
            os.startfile(f"{cfg['url']}/web/#/details?id={item['Id']}")
            return f'opened {_line(item)} in Jellyfin (press play)'
        sessions = [x for x in http('GET', cfg['url'] + '/Sessions', _h(cfg), controllableByUserId=uid) if x.get('SupportsRemoteControl')]
        s = next((x for x in sessions if on.lower() in (x.get('DeviceName', '') + ' ' + x.get('Client', '')).lower()), None)
        if not s:
            return f'no device called "{on}". Devices: ' + (', '.join(x.get('DeviceName', '') for x in sessions) or 'none open')
        http('POST', f"{cfg['url']}/Sessions/{s['Id']}/Playing", _h(cfg), playCommand='PlayNow', itemIds=item['Id'],
             startPositionTicks=(item.get('UserData') or {}).get('PlaybackPositionTicks', 0))
        return f"playing {_line(item)} on {s.get('DeviceName')}"
    return HELP.replace('{CMD}', 'silly --int jellyfin')
