# Copyright (c) 2026 Manuel Hilgert <hilman2@gmail.com>
# Distributed under the terms of the GNU General Public License (GPLv3)
"""Installer of the Ambient HTTP push driver."""

from weecfg.extension import ExtensionInstaller

VERSION = '0.1.0a1'


def loader():
    return AmbientHTTPPushInstaller()


class AmbientHTTPPushInstaller(ExtensionInstaller):
    def __init__(self):
        super(AmbientHTTPPushInstaller, self).__init__(
            version=VERSION,
            name='ambient-http-push',
            description='Receive the custom server uploads of Ambient Weather consoles.',
            author='Manuel Hilgert',
            author_email='hilman2@gmail.com',
            config={'AmbientHTTPPush': {'driver': 'user.ambient_http_push', 'port': '8080'}},
            files=[('bin/user', ['bin/user/ambient_http_push.py'])])
