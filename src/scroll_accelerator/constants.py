import os

import appdirs

APP_NAME = "scroll-accelerator"
APP_DESCRIPTION = "Mouse scroll wheel accelerator"

SYSTEMD_USER_DIR = os.path.expanduser("~/.config/systemd/user")
SYSTEMD_UNIT_NAME = f"{APP_NAME}.service"
SYSTEMD_CONFIG_FILE = os.path.join(SYSTEMD_USER_DIR, SYSTEMD_UNIT_NAME)

CONFIG_DIR = appdirs.user_config_dir(appname=APP_NAME)
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.yaml")

DEFAULT_CONFIG = {
    "multiplier": 0.5,
    "exp": 1.5,
    "threshold": 2.0,
}

DEFAULT_MACOS_CONFIG = {
    "multiplier": 1.0,
    "exp": 0.5,
    "threshold": 2.0,
}

SYSTEMD_CONFIG_TEMPLATE = """
[Unit]
Description={service_description}
PartOf=graphical-session.target
After=graphical-session.target

[Install]
WantedBy=graphical-session.target

[Service]
ExecStart={executable_command}
Type=exec
Restart=on-failure
RestartSec=1
"""
