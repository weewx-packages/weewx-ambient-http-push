# Ambient HTTP Push

A WeeWX driver for Ambient Weather consoles. It receives the uploads a console sends to
a custom server, with no ambientweather.net account. It does not read ambientweather.net
and does not accept the Wunderground protocol.

This is an own project of the weewx-packages organization.

## Requirements

- An Ambient Weather console with **Customized** upload in the awnet app, for example a
  WS-2902 or WS-5000.
- A network path from the console to the WeeWX computer on the listening port.

## Installation

Install `ambient-http-push` from the [WeeWX packages catalog](https://github.com/weewx-packages/catalog/blob/main/packages/ambient-http-push.md).
The catalog page lists the current release, its WeeWX and Python
requirements, and the install, update and removal commands.

Then select the driver and restart WeeWX:

```sh
weectl station reconfigure --driver=user.ambient_http_push --config=/path/to/weewx.conf
```

In the awnet app, open your device, then Device Settings, then Customized Upload, and
set:

| Field | Value |
|---|---|
| Protocol | Ambient Weather |
| Server IP / Hostname | the address of the WeeWX computer |
| Path | `/data?` |
| Port | the `port` of the driver |
| Upload Interval | 60 |

## Configuration

```ini
[Station]
    station_type = AmbientHTTPPush

[AmbientHTTPPush]
    driver = user.ambient_http_push
    port = 8080
```

Options in `[AmbientHTTPPush]`:

| Option | Default | Meaning |
|---|---|---|
| `port` | `8080` | TCP port to listen on. |
| `address` | all addresses | Address to listen on. |

The driver accepts uploads on any path.

| Upload field | WeeWX field |
|---|---|
| `tempf`, `humidity` | `outTemp`, `outHumidity` |
| `tempinf`, `humidityin` | `inTemp`, `inHumidity` |
| `baromrelin`, `baromabsin` | `barometer`, `pressure` |
| `windspeedmph`, `windgustmph`, `winddir`, `windgustdir` | `windSpeed`, `windGust`, `windDir`, `windGustDir` |
| `dailyrainin` | `rain`, the amount since the previous upload |
| `hourlyrainin` | `rainRate` |
| `solarradiation`, `uv` | `radiation`, `UV` |
| `pm25`, `co2` | `pm2_5`, `co2` |
| `lightning_day` | `lightning_strike_count`, the strikes since the previous upload |
| `temp1f` to `temp8f`, `humidity1` to `humidity8` | `extraTemp1` to `extraTemp8`, `extraHumid1` to `extraHumid8` |
| `soiltemp1f` to `soiltemp4f`, `soilhum1` to `soilhum4` | `soilTemp1` to `soilTemp4`, `soilMoist1` to `soilMoist4` |
| `battout`, `battin`, `batt1` to `batt8` | `outTempBatteryStatus`, `inTempBatteryStatus`, `batteryStatus1` to `batteryStatus8`, with 1 for a low battery |

Other fields are ignored.

## Limitations

- Tested with a recorded upload of an `AMBWeatherV4.0.2` console, not with a real
  console.
- `soilMoist1` to `soilMoist4` hold the percentage the console sends. WeeWX labels this
  field in centibars.
- The upload has no password. Keep the port on the local network.
- Rain and lightning that fall while WeeWX is not running are lost, and so is the first
  upload's amount after a start.

## Development

```sh
PYTHONPATH=bin python -m pytest -q tests
```

## License

Copyright (c) 2026 Manuel Hilgert. GPL-3.0-only, see [LICENSE](LICENSE).

The upload field names are those of the `ambient_station` integration in
[Home Assistant](https://github.com/home-assistant/core), which is Apache-2.0.
