# Copyright (c) 2026 Manuel Hilgert <hilman2@gmail.com>
"""Smoke tests, with an upload of an AMBWeatherV4.0.2 console."""

import urllib.request

import weewx

from user import ambient_http_push

UPLOAD = ('stationtype=AMBWeatherV4.0.2&PASSKEY=DUMMYDATADUMMYDATADUMMYDATADATAD'
          '&dateutc=2018-06-20+13:39:00&winddir=169&windspeedmph=1.8&windgustmph=2.2'
          '&maxdailygust=3.4&tempf=69.1&hourlyrainin=0.00&eventrainin=0.00&dailyrainin=0.10'
          '&weeklyrainin=0.87&monthlyrainin=0.87&totalrainin=0.87&baromrelin=29.89'
          '&baromabsin=29.48&humidity=61&tempinf=73.4&humidityin=51&uv=3&solarradiation=299.23')


def test_an_upload_becomes_a_packet():
    packet = ambient_http_push.Converter().packet(ambient_http_push.parse_upload('/data?' + UPLOAD))
    assert packet['usUnits'] == weewx.US
    assert (packet['outTemp'], packet['outHumidity']) == (69.1, 61)
    assert (packet['inTemp'], packet['inHumidity']) == (73.4, 51)
    assert (packet['barometer'], packet['pressure']) == (29.89, 29.48)
    assert (packet['windSpeed'], packet['windGust'], packet['windDir']) == (1.8, 2.2, 169)
    assert (packet['radiation'], packet['UV'], packet['rainRate']) == (299.23, 3, 0)


def test_the_pairs_are_found_wherever_the_console_puts_them():
    for target, body in (('/data?' + UPLOAD, ''), ('/data/' + UPLOAD, ''), ('/' + UPLOAD, ''),
                         ('/?' + UPLOAD, ''), ('/data', UPLOAD), ('/data?', UPLOAD)):
        assert ambient_http_push.parse_upload(target, body)['tempf'] == '69.1'


def test_rain_is_what_the_daily_counter_gained():
    converter = ambient_http_push.Converter()
    amounts = [converter.packet({'dailyrainin': text})['rain']
               for text in ('0.10', '0.10', '0.25', '0.00', '0.05')]
    assert amounts[0] is None
    assert amounts[1:] == [0, 0.15, 0, 0.05]


def test_a_rain_counter_reset_keeps_the_rain_after_it():
    converter = ambient_http_push.Converter()
    converter.packet({'dailyrainin': '0.50'})
    assert converter.packet({'dailyrainin': '0.02'})['rain'] == 0.02


def test_a_low_battery_is_1_as_in_weewx():
    packet = ambient_http_push.Converter().packet({'battout': '0', 'batt1': '1'})
    assert (packet['outTempBatteryStatus'], packet['batteryStatus1']) == (1, 0)


def test_a_request_without_readings_gives_no_packet():
    converter = ambient_http_push.Converter()
    assert converter.packet(ambient_http_push.parse_upload('/favicon.ico')) is None
    assert converter.packet({'PASSKEY': 'x', 'tempf': 'nan'}) is None


def test_an_upload_arrives_through_the_server():
    driver = ambient_http_push.AmbientHTTPPushDriver(port=0, address='127.0.0.1')
    try:
        url = 'http://127.0.0.1:%d/data?%s' % (driver.server.server_address[1], UPLOAD)
        with urllib.request.urlopen(url, timeout=5) as reply:
            assert reply.read() == b'success'
        assert next(driver.genLoopPackets())['outTemp'] == 69.1
    finally:
        driver.closePort()
