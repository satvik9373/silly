"""Home Assistant, through its own MCP server: lights, switches, climate, covers, media, and asking what's on."""
import json, re
from . import http

TITLE = 'Home Assistant'
ABOUT = '"Turn off the office lights" · "Set the heat to 21" · "Is the garage open?" Uses the entities you expose to Assist.'
EXAMPLE = 'http://<server>:8123'
KEY_HELP = 'Your profile (bottom left) → Security → Long-lived access tokens → Create token. Also add the "Model Context Protocol Server" integration (Settings → Devices & services).'
KEY_PAGE = '/profile/security'
FIELDS = [('url', 'Address', False), ('key', 'Long-lived access token', True)]
WORDS = (r'\b(home assistant|light|lights|lamp|lamps|switch|plug|outlet|fan|thermostat|heat|heating|temperature|ac|air conditioning|'
         r'blinds?|shades?|curtains?|garage|door|doors|lock|locks|unlock|alarm|vacuum|scene|scenes|turn on|turn off|dim|brighten|'
         r'is the \w+ (on|off|open|closed)|humidity|sensors?|speaker|motion|movement|occupied|occupancy|anyone (home|there|in)|camera|doorbell|'
         r'battery|batteries|power|energy|smart home|house|home|office|bedroom|kitchen|living room|bathroom|basement|hallway|porch|backyard)\b')
HELP = ('its tools are the mcp__homeassistant__ ones: use them to read and control the home. To see what exists or what is on, call GetLiveContext '
        'with {} (no filters: they fail) and read its list. Control things by the names it shows.')
RISKY = {}
SECURITY = re.compile(r'\b(lock|unlock|door|garage|gate|alarm|security|disarm|arm)\b', re.I)


def MCP(cfg):
    return {'type': 'http', 'url': cfg['url'] + '/api/mcp', 'headers': {'Authorization': f'Bearer {cfg["key"]}'}}


def mcp_risky(tool, args):
    """Locks, doors, garages and alarms ask first; lights and the rest just happen."""
    if tool.startswith(('Hass', 'Set')) and not tool.startswith(('HassLight', 'HassMedia', 'HassGet')) and SECURITY.search(json.dumps(args)):
        name = args.get('name') or args.get('area') or args.get('device_class') or 'that'
        return f'{tool.replace("Hass", "").replace("TurnOn", "Turn on").replace("TurnOff", "Turn off").replace("SetPosition", "Move")} {name}?'
    return ''


def check(cfg):
    try:
        http('GET', cfg['url'] + '/api/', {'Authorization': f'Bearer {cfg["key"]}'})
    except Exception as e:
        return f'Could not connect: {e}'
    try:
        http('GET', cfg['url'] + '/api/mcp', {'Authorization': f'Bearer {cfg["key"]}', 'Accept': 'text/event-stream, application/json'}, timeout=5)
    except Exception as e:
        if getattr(e, 'code', 0) == 404:
            return 'Connected, but the Model Context Protocol Server integration is not added in Home Assistant yet.'
    return 'Connected.'


def run(cfg, args):
    return 'Home Assistant is used through its MCP tools (mcp__homeassistant__…), not a command. ' + check(cfg)
