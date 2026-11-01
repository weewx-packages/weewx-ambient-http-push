# Copyright (c) 2026 Manuel Hilgert <hilman2@gmail.com>
# Distributed under the terms of the GNU General Public License (GPLv3)
"""WeeWX driver for Ambient Weather consoles, using their custom server upload.

The awnet app can make a console upload to a server of your own. A console does not
answer requests, so the driver runs a small HTTP server and turns each upload into a
LOOP packet. Uploads arrive in the Ambient Weather protocol: name=value pairs in US
units, in the query string of a GET or in the body of a POST.

The field names are those of the ambient_station integration in Home Assistant,
https://github.com/home-assistant/core, which is Apache-2.0.
"""

import http.server
import logging
import math
import queue
import threading
import time
import urllib.parse

import weewx
import weewx.drivers

log = logging.getLogger(__name__)

DRIVER_NAME = 'AmbientHTTPPush'
DRIVER_VERSION = '0.1.0a1'

DEFAULT_PORT = 8080
MAX_BODY = 16384
# Consoles upload about once a minute, so the queue only has to outlast a slow report.
MAX_QUEUED = 100

# Upload field -> WeeWX field, for readings that need no calculation. Despite its name,
# 'hourlyrainin' is the current rate in in/hr, which is what rainRate holds.
FIELDS = {
    'tempf': 'outTemp', 'humidity': 'outHumidity', 'tempinf': 'inTemp', 'humidityin': 'inHumidity',
    'baromrelin': 'barometer', 'baromabsin': 'pressure', 'winddir': 'windDir',
    'windspeedmph': 'windSpeed', 'windgustmph': 'windGust', 'windgustdir': 'windGustDir',
    'hourlyrainin': 'rainRate', 'solarradiation': 'radiation', 'uv': 'UV', 'pm25': 'pm2_5',
    'co2': 'co2',
}
FIELDS.update({'temp%df' % n: 'extraTemp%d' % n for n in range(1, 9)})
FIELDS.update({'humidity%d' % n: 'extraHumid%d' % n for n in range(1, 9)})
FIELDS.update({'soiltemp%df' % n: 'soilTemp%d' % n for n in range(1, 5)})
FIELDS.update({'soilhum%d' % n: 'soilMoist%d' % n for n in range(1, 5)})

# A console sends 1 for a good battery and 0 for a low one. WeeWX means the opposite:
# the skins show 1 as low.
BATTERIES = {'battout': 'outTempBatteryStatus', 'battin': 'inTempBatteryStatus'}
BATTERIES.update({'batt%d' % n: 'batteryStatus%d' % n for n in range(1, 9)})


def loader(config_dict, engine):
    return AmbientHTTPPushDriver(**config_dict[DRIVER_NAME])


def parse_upload(target, body=''):
    """Return the name=value pairs of an upload.

    Args:
        target (str): The request target, with the path and any query string.
        body (str): The body of a POST. Default is none.

    Returns:
        dict: The value of each name, as text.
    """
    # The path typed into awnet has to end in '?' for the pairs to become a query
    # string. Without it they follow the path directly, which spoils only the name of
    # the first pair. The console sends its identity first, so no reading is lost.
    return dict(urllib.parse.parse_qsl((body or target).rpartition('?')[2]))


def _number(text):
    """Return an upload value as a number, or None if it is not one."""
    try:
        value = float(text)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _increase(new, old):
    """Return what a daily counter gained, or None if there is nothing to compare."""
    if new is None or old is None:
        return None
    # A smaller value means that the console reset the counter at midnight. Everything
    # it holds now was added after the reset.
    return new - old if new >= old else new


class Converter:
    """Turn uploads into LOOP packets, remembering the daily counters between them."""

    def __init__(self):
        self.last_rain = None
        self.last_lightning = None

    def packet(self, fields):
        """Convert one upload.

        Args:
            fields (dict): The pairs of the upload, from parse_upload.

        Returns:
            dict|None: The LOOP packet, or None if the upload holds no readings.
        """
        packet = {}
        for name, target in FIELDS.items():
            value = _number(fields.get(name))
            if value is not None:
                packet[target] = value
        for name, target in BATTERIES.items():
            value = _number(fields.get(name))
            if value is not None:
                packet[target] = 1.0 if value == 0 else 0.0
        rain = _number(fields.get('dailyrainin'))
        if rain is not None:
            packet['rain'] = _increase(rain, self.last_rain)
            self.last_rain = rain
        lightning = _number(fields.get('lightning_day'))
        if lightning is not None:
            packet['lightning_strike_count'] = _increase(lightning, self.last_lightning)
            self.last_lightning = lightning
        if not packet:
            return None
        packet['dateTime'] = int(time.time() + 0.5)
        packet['usUnits'] = weewx.US
        return packet


class _Handler(http.server.BaseHTTPRequestHandler):
    """Accept any path, because the path is whatever was typed into awnet."""

    timeout = 10

    def do_GET(self):
        self._accept('')

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
        except ValueError:
            length = 0
        self._accept(self.rfile.read(max(0, min(length, MAX_BODY))).decode('utf-8', 'replace'))

    def _accept(self, body):
        try:
            self.server.uploads.put_nowait(parse_upload(self.path, body))
        except queue.Full:
            log.error('Dropped an upload, because WeeWX is not keeping up')
        answer = b'success'
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Content-Length', str(len(answer)))
        self.end_headers()
        self.wfile.write(answer)

    def log_message(self, format, *args):
        log.debug(format, *args)


class AmbientHTTPPushDriver(weewx.drivers.AbstractDevice):
    """Receive the uploads of an Ambient Weather console."""

    def __init__(self, **stn_dict):
        """Start the HTTP server.

        Args:
            stn_dict (dict): The driver's section of weewx.conf, with the options
                address and port.

        Raises:
            weewx.WeeWxIOError: The port cannot be opened.
        """
        self.converter = Converter()
        port = int(stn_dict.get('port', DEFAULT_PORT))
        try:
            self.server = http.server.ThreadingHTTPServer((stn_dict.get('address', ''), port),
                                                          _Handler)
        except OSError as error:
            raise weewx.WeeWxIOError('Cannot listen on port %d: %s' % (port, error))
        self.server.uploads = queue.Queue(MAX_QUEUED)
        threading.Thread(target=self.server.serve_forever, name='ambient-http-push',
                         daemon=True).start()
        log.info('Waiting for uploads from an Ambient Weather console on port %d',
                 self.server.server_address[1])

    @property
    def hardware_name(self):
        return 'Ambient Weather'

    def genLoopPackets(self):
        """Yield a packet for every upload that holds readings.

        Yields:
            dict: A LOOP packet.
        """
        while True:
            packet = self.converter.packet(self.server.uploads.get())
            if packet:
                yield packet

    def closePort(self):
        self.server.shutdown()
        self.server.server_close()
