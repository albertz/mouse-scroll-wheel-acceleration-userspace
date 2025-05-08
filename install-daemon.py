#!/usr/bin/env python3

"""
Install as a systemd daemon service.
(Later maybe also OSX launchd, and others...)
(https://github.com/karlicoss/grasp/issues/32, https://github.com/karlicoss/promnesia/issues/15)

Code based on this:
https://github.com/karlicoss/promnesia/blob/197af911eb/setup_server
Systemd refs:
https://man.archlinux.org/man/systemd.special.7#Special_Passive_User_Units
https://wiki.archlinux.org/title/Systemd/User

Copyright 2019 Dmitrii Gerasimov, 2021 Albert Zeyer
"""

import argparse
from pathlib import Path
from subprocess import check_call, run

try:
    from mswaa import common
except ModuleNotFoundError:
    print("[!] ERROR: `mswaa` module not found.")
    print("[?] HELP: Install the package as instructed in the README`")
    print()
    raise

_SystemdConfigTemplate = """
[Unit]
Description={service_name}
PartOf=graphical-session.target

[Install]
WantedBy=default.target

[Service]
ExecStart={server}
Type=simple
Restart=always
"""


def systemd(*args, ignore_errors=False):
    if ignore_errors:
        method = run
    else:
        method = check_call
    method(["systemctl", "--no-pager", "--user", *args])


def get_mswaa_path():
    import shutil

    mswaa = shutil.which("mswaa")

    return mswaa


def setup(args):
    if not common.config_fn.exists():
        # We need some config, otherwise the service wont start.
        common.install_default_config()

    unit_name = args.unit_name
    systemd_user_dir = Path("~/.config/systemd/user").expanduser()
    systemd_user_dir.mkdir(parents=True, exist_ok=True)
    out = systemd_user_dir / unit_name
    print(f"Writing systemd config to {out}:")

    server_bin = get_mswaa_path()
    if not server_bin:
        print(
            "ERROR: `mswaa` not found in path. (hint: Have you installed it yet? Read the README.)"
        )
        exit(1)

    out.write_text(
        _SystemdConfigTemplate.format(
            service_name=common.app_name_human, server=server_bin
        )
    )

    # https://github.com/albertz/mouse-scroll-wheel-acceleration-userspace/issues/7
    (systemd_user_dir / "default.target.wants").mkdir(parents=True, exist_ok=True)

    try:
        systemd(
            "stop", unit_name, ignore_errors=True
        )  # ignore errors here if it wasn't running in the first place
        systemd("daemon-reload")
        systemd("enable", unit_name)
        systemd("start", unit_name)
        systemd("status", unit_name)
    except Exception as e:
        print(
            f"Something has gone wrong... you might want to use 'journalctl --user -u {unit_name}' to debug"
        )
        raise e


def main():
    p = argparse.ArgumentParser(
        f"{common.app_name_human} service setup",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--unit-name",
        type=str,
        default=f"{common.app_name}.service",
        help="Systemd unit name",
    )
    args = p.parse_args()
    setup(args)


if __name__ == "__main__":
    main()
