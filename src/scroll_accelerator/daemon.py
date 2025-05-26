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

import logging
import os
import shutil
import subprocess
from typing import Optional

from scroll_accelerator.constants import (
    APP_NAME,
    CONFIG_FILE,
    SYSTEMD_CONFIG_FILE,
    SYSTEMD_CONFIG_TEMPLATE,
    SYSTEMD_UNIT_NAME,
    SYSTEMD_USER_DIR,
)

logger = logging.getLogger(__name__)


# Systemd


def systemd(*args: str, ignore_errors: bool = False, silent: bool = False):
    """Run systemctl command.

    Args:
        args: Arguments to pass to systemctl.
        ignore_errors: Whether to ignore errors.
        silent: Whether to suppress output.
    """
    cmd = ["systemctl", "--no-pager", "--user", *args]
    subprocess.run(cmd, capture_output=silent, check=not ignore_errors)


def get_executable_path() -> str:
    """Get the path to the application executable.

    Returns:
        str: Path to the application executable.

    Raises:
        RuntimeError: If the application executable is not found.
    """
    executable_path = shutil.which(APP_NAME)
    if executable_path is None:
        raise RuntimeError(
            f"ERROR: `{APP_NAME}` not found in path. (hint: Have you installed it yet? Read the README.)"
        )
    return executable_path


def save_systemd_config(daemon_verbosity: Optional[int] = None):
    """Save systemd config to file."""
    # Create systemd user directory
    os.makedirs(SYSTEMD_USER_DIR, exist_ok=True)

    # Fill in systemd config template with executable command (including verbosity)
    executable_path = get_executable_path()
    if daemon_verbosity is not None and daemon_verbosity > 0:
        executable_command = f"{executable_path} -{'v' * daemon_verbosity}"
    else:
        executable_command = executable_path
    systemd_config = SYSTEMD_CONFIG_TEMPLATE.format(
        service_description=f"{APP_NAME} daemon",
        executable_command=executable_command,
    )
    logger.debug(f"Systemd unit config: {systemd_config}")

    # Write systemd config
    logger.info(f"Writing systemd unit config to {SYSTEMD_CONFIG_FILE}")
    with open(SYSTEMD_CONFIG_FILE, "w") as f:
        f.write(systemd_config)

    # Create default.target.wants directory, fix for:
    # https://github.com/albertz/mouse-scroll-wheel-acceleration-userspace/issues/7
    os.makedirs(
        os.path.join(SYSTEMD_USER_DIR, "default.target.wants"), exist_ok=True
    )


def delete_systemd_config():
    """Delete systemd config

    Does not raise an exception if the config file does not exist.
    """
    try:
        os.remove(SYSTEMD_CONFIG_FILE)
    except FileNotFoundError:
        logger.warning(
            f"Could not delete systemd unit config {SYSTEMD_CONFIG_FILE} because "
            "it does not exist."
        )
    except Exception as e:
        logger.warning(
            f"Failed to delete systemd unit config {SYSTEMD_CONFIG_FILE}: {e}"
        )


# Scroll Accelerator Daemon


def daemon_status():
    """Get the status of the daemon."""
    logger.info("Printing daemon status")
    systemd("status", SYSTEMD_UNIT_NAME, ignore_errors=True)


def daemon_log():
    """Print the log of the daemon."""
    logger.info("Printing daemon log")
    cmd = ["journalctl", "--user", "-u", SYSTEMD_UNIT_NAME]
    subprocess.run(cmd)


def install_daemon(verbosity: Optional[int] = None):
    """Install as a systemd daemon service."""
    assert os.path.exists(CONFIG_FILE), (
        f"Config file {CONFIG_FILE} does not exist"
    )

    # Save systemd config
    save_systemd_config(verbosity)

    logger.info("Stopping daemon")
    systemd("stop", SYSTEMD_UNIT_NAME, ignore_errors=True, silent=True)

    try:
        logger.info("Reloading systemd")
        systemd("daemon-reload")
        logger.info("Enabling daemon")
        systemd("enable", SYSTEMD_UNIT_NAME)
        logger.info("Starting daemon")
        systemd("start", SYSTEMD_UNIT_NAME)
    except Exception as e:
        raise RuntimeError(
            f"Failed to install/start {SYSTEMD_UNIT_NAME}. You might want to use "
            f"'journalctl --user -u {SYSTEMD_UNIT_NAME}' to debug"
        ) from e

    if logger.isEnabledFor(logging.INFO):
        daemon_status()


def restart_daemon(verbosity: Optional[int] = None):
    """Restart the daemon."""
    assert os.path.exists(CONFIG_FILE), (
        f"Config file {CONFIG_FILE} does not exist"
    )

    # Save systemd config
    save_systemd_config(verbosity)

    try:
        logger.info("Reloading systemd")
        systemd("daemon-reload")
        logger.info("Restarting daemon")
        systemd("restart", SYSTEMD_UNIT_NAME)
    except Exception as e:
        raise RuntimeError(
            f"Failed to restart {SYSTEMD_UNIT_NAME}. Make sure the daemon is "
            "installed (try `scroll-accelerator --install-daemon`)."
        ) from e

    if logger.isEnabledFor(logging.INFO):
        daemon_status()


def stop_daemon():
    """Stop the daemon."""
    try:
        logger.info("Stopping daemon")
        systemd("stop", SYSTEMD_UNIT_NAME)
    except Exception as e:
        raise RuntimeError(
            f"Failed to stop {SYSTEMD_UNIT_NAME}. Make sure the daemon is "
            "installed (try `scroll-accelerator --install-daemon`)."
        ) from e

    if logger.isEnabledFor(logging.INFO):
        daemon_status()


def uninstall_daemon():
    """Uninstall the daemon."""
    logger.info("Stopping daemon")
    systemd("stop", SYSTEMD_UNIT_NAME, ignore_errors=True)

    if logger.isEnabledFor(logging.INFO):
        daemon_status()

    try:
        logger.info("Disabling daemon")
        systemd("disable", SYSTEMD_UNIT_NAME)
    except Exception as e:
        raise RuntimeError(
            f"Failed to disable {SYSTEMD_UNIT_NAME}. The daemon might already "
            "have been uninstalled."
        ) from e
    finally:
        try:
            logger.info("Deleting systemd unit config")
            os.remove(SYSTEMD_CONFIG_FILE)
        except FileNotFoundError:
            logger.warning(
                f"Systemd unit config {SYSTEMD_CONFIG_FILE} not found. "
                "It might already have been deleted."
            )
        except Exception as e2:
            logger.warning(
                f"Failed to delete systemd unit config {SYSTEMD_CONFIG_FILE}: "
                f"{e2}"
            )

        logger.info("Reloading systemd")
        systemd("daemon-reload")
