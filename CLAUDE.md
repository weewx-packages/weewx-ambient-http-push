# weewx-ambient-http-push

WeeWX driver for Ambient Weather consoles. It receives their custom server uploads.

## Status

Alpha (before 1.0): smoke tests only, no backward compatibility.

## Checks

`just fast`, or `PYTHONPATH=bin python -m pytest -q tests`. Under 1 s. Needs WeeWX and
pytest.

## Conventions

One module, `bin/user/ambient_http_push.py`, with no dependencies beyond WeeWX. It
stays an ordinary WeeWX driver: a fixed field table, no field inference, no reports and
no shared listener module. Python follows the WeeWX style: no annotations, Google
docstrings with types. The version stands in `install.py` and as `DRIVER_VERSION`. The
README follows the schema in the workspace `CLAUDE.md` and names no versions.
