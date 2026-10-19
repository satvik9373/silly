"""Nextcloud: find files, open them, share a link, and what's on the calendar."""
import base64, datetime, os, re, urllib.parse, urllib.request
from . import arg

TITLE = 'Nextcloud'
ABOUT = '"Find my lease PDF" · "Share the trip photos folder" · "What is on my calendar this week?"'
EXAMPLE = 'https://cloud.example.com'
KEY_HELP = 'Settings (your avatar) → Security → Devices & sessions → Create new app password (name it Silly)'
KEY_PAGE = '/settings/user/security'
FIELDS = [('url', 'Address', False), ('user', 'Your Nextcloud user name', False), ('key', 'App password', True)]
WORDS = r'\b(nextcloud|cloud|file|files|folder|folders|pdf|spreadsheet|share|shared|link|calendar|schedule|appointments?|events?|meeting|meetings|agenda|this week|tomorrow)\b'
HELP = ('{CMD} find "<name words>" (files and folders) | open "<path>" | share "<path>" (makes a public link) | calendar [days] (events, default 7)')
RISKY = {'share': 'Make a public link?'}


def _dav(cfg, method, path, body='', depth=None, ctype='text/xml'):
    auth = base64.b64encode(f"{cfg['user']}:{cfg['key']}".encode()).decode()
    h = {'Authorization': 'Basic ' + auth, 'Content-Type': ctype, 'OCS-APIRequest': 'true', 'Accept': 'application/json'}
    if depth is not None:
        h['Depth'] = str(depth)
    req = urllib.request.Request(cfg['url'] + path, data=body.encode() if body else None, method=method, headers=h)
    return urllib.request.urlopen(req, timeout=15).read().decode('utf-8', 'replace')


def check(cfg):
    try:
        _dav(cfg, 'PROPFIND', f"/remote.php/dav/files/{urllib.parse.quote(cfg['user'])}/", '', 0)
        return 'Connected.'
    except Exception as e:
        return f'Could not connect: {e}'


def _files_root(cfg):
    return f"/remote.php/dav/files/{urllib.parse.quote(cfg['user'])}"


def find(cfg, words):
    like = ''.join(f'<d:like><d:prop><d:displayname/></d:prop><d:literal>%{w}%</d:literal></d:like>' for w in words.split())
    where = f'<d:and>{like}</d:and>' if len(words.split()) > 1 else like
    body = (f'<?xml version="1.0"?><d:searchrequest xmlns:d="DAV:" xmlns:oc="http://owncloud.org/ns"><d:basicsearch>'
            f'<d:select><d:prop><d:displayname/><d:getlastmodified/><d:resourcetype/></d:prop></d:select>'
            f'<d:from><d:scope><d:href>/files/{cfg["user"]}</d:href><d:depth>infinity</d:depth></d:scope></d:from>'
            f'<d:where>{where}</d:where><d:orderby/><d:limit><d:nresults>15</d:nresults></d:limit></d:basicsearch></d:searchrequest>')
    xml = _dav(cfg, 'SEARCH', '/remote.php/dav/', body)
    out = []
    for resp in re.findall(r'<d:response>(.*?)</d:response>', xml, re.S):
        href = urllib.parse.unquote(re.search(r'<d:href>(.*?)</d:href>', resp).group(1)).split(f'/files/{cfg["user"]}', 1)[-1]
        when = (re.search(r'<d:getlastmodified>(.*?)</d:getlastmodified>', resp) or [None, ''])[1][5:16]
        out.append(f"{href}{' (folder)' if '<d:collection' in resp else ''} — {when}")
    return out


def run(cfg, args):
    what = arg(args, 0)
    if what == 'find':
        return '\n'.join(find(cfg, ' '.join(args[1:]))) or 'nothing by that name'
    if what == 'open' and arg(args, 1):
        path = '/' + args[1].strip('/')
        folder, name = path.rsplit('/', 1)
        os.startfile(f"{cfg['url']}/apps/files/files?dir={urllib.parse.quote(folder or '/')}&scrollto={urllib.parse.quote(name)}")
        return f'opened {path} in Nextcloud'
    if what == 'share' and arg(args, 1):
        body = urllib.parse.urlencode({'path': '/' + args[1].strip('/'), 'shareType': 3, 'permissions': 1})
        r = _dav(cfg, 'POST', '/ocs/v2.php/apps/files_sharing/api/v1/shares?format=json', body, ctype='application/x-www-form-urlencoded')
        m = re.search(r'"url"\s*:\s*"([^"]+)"', r)
        return ('public link: ' + m.group(1).replace('\\/', '/')) if m else 'could not share it: ' + r[:200]
    if what == 'calendar':
        days = int(arg(args, 1, '7')) if arg(args, 1, '7').isdigit() else 7
        start = datetime.datetime.now(datetime.timezone.utc)
        end = start + datetime.timedelta(days=days)
        root = f"/remote.php/dav/calendars/{urllib.parse.quote(cfg['user'])}/"
        cals = re.findall(r'<d:href>([^<]+)</d:href>', _dav(cfg, 'PROPFIND', root, '<?xml version="1.0"?><d:propfind xmlns:d="DAV:"><d:prop><d:resourcetype/></d:prop></d:propfind>', 1))
        f = lambda t: t.strftime('%Y%m%dT%H%M%SZ')
        q = (f'<?xml version="1.0"?><c:calendar-query xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav"><d:prop><c:calendar-data/></d:prop>'
             f'<c:filter><c:comp-filter name="VCALENDAR"><c:comp-filter name="VEVENT"><c:time-range start="{f(start)}" end="{f(end)}"/></c:comp-filter></c:comp-filter></c:filter></c:calendar-query>')
        events = []
        for cal in cals:
            if cal.rstrip('/').endswith((cfg['user'], 'inbox', 'outbox', 'trashbin')):
                continue
            try:
                xml = _dav(cfg, 'REPORT', cal, q, 1)
            except Exception:
                continue
            for ev in re.findall(r'BEGIN:VEVENT(.*?)END:VEVENT', xml, re.S):
                summ = (re.search(r'\nSUMMARY[^:]*:(.*)', ev) or [None, '(no title)'])[1].strip()
                dt = (re.search(r'\nDTSTART[^:]*:(\d{8}(T\d{4})?)', ev) or [None, ''])[1]
                when = f'{dt[:4]}-{dt[4:6]}-{dt[6:8]}' + (f' {dt[9:11]}:{dt[11:13]}' if 'T' in dt else ' (all day)')
                events.append((dt, f'{when}: {summ}'))
        return '\n'.join(e for _, e in sorted(events)) or f'nothing in the next {days} days'
    return HELP.replace('{CMD}', 'silly --int nextcloud')
