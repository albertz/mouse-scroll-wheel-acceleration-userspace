from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Optional, Sequence

import yaml

from scroll_accelerator.constants import (
    APP_DESCRIPTION,
    APP_NAME,
    CONFIG_DIR,
    CONFIG_FILE,
    DEFAULT_CONFIG,
    DEFAULT_MACOS_CONFIG,
    SYSTEMD_UNIT_NAME,
)
from scroll_accelerator.daemon import (
    daemon_log,
    daemon_status,
    install_daemon,
    restart_daemon,
    stop_daemon,
    uninstall_daemon,
)
from scroll_accelerator.scroll_accelerator import (
    ScrollAccelerator,
    check_config,
)

# Logging

logger = logging.getLogger(__name__)


def init_logging(verbose: int = 0):
    """Initialize logging.

    Args:
        verbose: Verbosity level.
    """
    if verbose <= 0:
        format = "%(levelname)s: %(message)s"
    else:
        format = "%(asctime)s %(levelname)s: %(message)s"

    logging.basicConfig(
        format=format,
        level=max(1, logging.WARNING - verbose * 10),
    )


# Config


def get_default_config() -> dict:
    """Default config for the application.

    This is probably very subjective. But just to have some reasonable defaults,
    which might be used.

    Returns:
        Default config for the application.
    """
    if sys.platform == "darwin":
        # Darwin (MacOSX) already has builtin mouse scroll wheel acceleration,
        # so we should apply much less extra acceleration.
        config = DEFAULT_MACOS_CONFIG.copy()
    else:
        # All other common desktop platforms do not (Linux, Windows).
        # (Android does, but we don't expect that here...)
        config = DEFAULT_CONFIG.copy()

    try:
        check_config(**config)
    except Exception as e:
        assert False, f"Default config is invalid: {e}."

    return config


def get_command_line_config(args: argparse.Namespace) -> dict:
    """Get config from command line arguments.

    Args:
        args: Command line arguments.

    Returns:
        Config from command line arguments.
    """
    default_config = get_default_config()
    config = {}
    for key in default_config.keys():
        value = getattr(args, key)
        if value is not None:
            config[key] = value
    return config


def load_config() -> dict:
    """Load config from yaml file.

    Returns:
        Config from file.

    Raises:
        RuntimeError: If the config file does not exist, is empty, or is invalid.
    """
    if not os.path.exists(CONFIG_FILE):
        logger.warning(f"Config file {CONFIG_FILE} does not exist.")
        return {}

    with open(CONFIG_FILE, "r") as f:
        config = yaml.safe_load(f)

    # If the config file is empty, return an empty dict
    if config is None:
        logger.warning(f"Config file {CONFIG_FILE} is empty.")
        return {}

    # If the config file is not a dict, raise an error
    if not isinstance(config, dict):
        raise RuntimeError(f"Config file {CONFIG_FILE} is invalid.")

    # Check that the config file contains only valid keys
    default_config = get_default_config()
    for key in config.keys():
        if key not in default_config:
            raise RuntimeError(f"Unknown config key in {CONFIG_FILE}: {key}")

    return config


def validate_saved_config(expected_config: dict):
    """Validate saved config.

    Args:
        expected_config: Config that should have been saved to the config file.

    Raises:
        RuntimeError: If the config file does not exist, is empty, or is invalid.
    """
    try:
        loaded_config = load_config()
    except Exception as e:
        raise RuntimeError(
            "Error loading config file. Please check the config file or "
            "use `--save-config`/`--reset-config` to modify/reset the config "
            "file before installing or restarting the daemon."
        ) from e
    assert loaded_config == expected_config, (
        f"Loaded config {loaded_config} does not match expected config "
        f"{expected_config} that was (supposedly) saved to {CONFIG_FILE}. "
        f"You can try manually deleting the config file (`rm {CONFIG_FILE}`) "
        f"and reinstalling the daemon using `--install-daemon`."
    )


def save_config(config: dict):
    """Save config to yaml file.

    Args:
        config: Config to save.
    """
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(config, f)


# CLI


def parse_args(arg_list: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse command line arguments.

    Args:
        arg_list: Unparsed argument sequence. If None, the arguments are read from
        sys.argv.

    Returns:
        Command line arguments.
    """
    arg_parser = argparse.ArgumentParser(
        prog=APP_NAME, description=APP_DESCRIPTION
    )
    arg_parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Logging level. Can be given multiple times to increase "
        "verbosity.",
    )

    # Acceleration parameter arguments
    param_group = arg_parser.add_argument_group("Acceleration Parameters")
    param_group.add_argument(
        "--multiplier",
        type=float,
        help=f"Acceleration coefficient. Determines the linear scaling of the "
        f"acceleration. Default: {get_default_config()['multiplier']}",
    )
    param_group.add_argument(
        "--exp",
        type=float,
        help=f"Acceleration exponent. Determines the exponential scaling of the "
        f"acceleration. Default: {get_default_config()['exp']}",
    )
    param_group.add_argument(
        "--threshold",
        type=float,
        help=f"Velocity threshold. Determines the minimum velocity at which "
        f"acceleration will be applied. Default: "
        f"{get_default_config()['threshold']}",
    )

    # Config arguments
    config_group = arg_parser.add_argument_group("Config File Options")
    config_mutex_group = config_group.add_mutually_exclusive_group()
    config_mutex_group.add_argument(
        "--save-config",
        action="store_true",
        help=f"Save the provided parameters to {CONFIG_FILE}. Exits without "
        "running the application.",
    )
    config_mutex_group.add_argument(
        "--reset-config",
        action="store_true",
        help=f"Save the default config to {CONFIG_FILE}. Exits without running "
        "the application.",
    )

    # Daemon arguments
    daemon_group = arg_parser.add_argument_group("Daemon Options")
    daemon_group.add_argument(
        "--daemon-verbosity",
        type=int,
        help="Set the verbosity of the daemon. A verbosity greater than 0 will "
        "cause the daemon to log more information. This information is useful "
        "for debugging and can be read using the command `journalctl --user -u "
        f"{SYSTEMD_UNIT_NAME}`. This can only be used when installing/restarting "
        "the daemon with `--install-daemon`/`--restart-daemon`.",
    )
    daemon_mutex_group = daemon_group.add_mutually_exclusive_group()
    daemon_mutex_group.add_argument(
        "--install-daemon",
        action="store_true",
        help="Install and start the daemon. The daemon will start the "
        f"application with the saved config ({CONFIG_FILE}). Any provided "
        "acceleration parameters will automatically be saved to the config "
        "file before starting the daemon.",
    )
    daemon_mutex_group.add_argument(
        "--restart-daemon",
        action="store_true",
        help="Start/restart the daemon. The daemon will be (re)started with the "
        f"saved config ({CONFIG_FILE}). Any provided acceleration parameters "
        "will automatically be saved to the config file before (re)starting "
        "the daemon.",
    )
    daemon_mutex_group.add_argument(
        "--stop-daemon",
        action="store_true",
        help="Stop the daemon. Note that this does not uninstall/disable the "
        "daemon and it will be restarted after a system restart/reboot.",
    )
    daemon_mutex_group.add_argument(
        "--uninstall-daemon",
        action="store_true",
        help="Stop and uninstall the daemon. The daemon will be removed from "
        "the system and will not be restarted after a system restart/reboot.",
    )
    daemon_mutex_group.add_argument(
        "--daemon-status",
        action="store_true",
        help="Get the status of the daemon. If the output indicates that the "
        "daemon/unit is inactive but still installed, you can use the "
        "`--restart-daemon` option to start it. If instead it shows that the "
        "daemon/unit does not exist, you can use the `--install-daemon` option "
        "to install it.",
    )
    daemon_mutex_group.add_argument(
        "--daemon-log",
        action="store_true",
        help="Print the log of the daemon. Essentially calls `journalctl --user "
        f"-u {SYSTEMD_UNIT_NAME}`. This can only be used when the daemon is "
        "installed or restarted.",
    )
    args = arg_parser.parse_args(arg_list)

    return args


class ArgumentError(Exception):
    """Exception raised for invalid command line arguments."""

    pass


def validate_args(args: argparse.Namespace) -> argparse.Namespace:
    """Validate arguments.

    Args:
        args: Command line arguments.

    Returns:
        Validated command line arguments.

    Raises:
        ArgumentError: If the arguments are invalid.
    """
    command_line_config = get_command_line_config(args)

    if (
        args.stop_daemon
        or args.uninstall_daemon
        or args.daemon_status
        or args.daemon_log
    ):
        if len(command_line_config) > 0:
            raise ArgumentError(
                "Acceleration parameters cannot be provided when "
                "stopping, uninstalling, or getting the status/log of the "
                "daemon."
            )
        if args.save_config or args.reset_config:
            raise ArgumentError(
                "Config cannot be saved or reset when "
                "stopping, uninstalling, or getting the status/log of the "
                "daemon."
            )

    if args.daemon_verbosity is not None:
        if not args.install_daemon and not args.restart_daemon:
            raise ArgumentError(
                "Daemon verbosity can only be used when installing/restarting the "
                "daemon with `--install-daemon`/`--restart-daemon`."
            )
        if args.daemon_verbosity < 0:
            raise ArgumentError("Daemon verbosity cannot be negative.")

    if args.install_daemon or args.restart_daemon:
        if len(command_line_config) > 0:
            logger.debug(
                "Saving config to file because new acceleration parameters were "
                "provided."
            )
            args.save_config = True
        elif not os.path.exists(CONFIG_FILE):
            logger.debug(
                "Saving default config to file because a config file does not "
                "already exist and no new acceleration parameters were provided."
            )
            args.reset_config = True

    if args.save_config and len(command_line_config) == 0:
        raise ArgumentError(
            "No acceleration parameters provided to save. If you want to "
            "reset the config file to the default acceleration parameters, "
            "use `--reset-config`."
        )
    if args.reset_config and len(command_line_config) > 0:
        raise ArgumentError(
            "Acceleration parameters cannot be provided when resetting the "
            "config file to default. Instead, use `--save-config` to save the "
            "provided acceleration parameters to the config file."
        )

    return args


def cli(args: argparse.Namespace):
    """CLI logic.

    Args:
        args: Command line arguments.
    """

    # Uninstall, stop, or get status of daemon
    if args.uninstall_daemon:
        uninstall_daemon()
        print("\nDaemon successfully uninstalled.")
        return
    elif args.stop_daemon:
        stop_daemon()
        print("\nDaemon successfully stopped.")
        return
    elif args.daemon_status:
        daemon_status()
        return
    elif args.daemon_log:
        daemon_log()
        return

    # Load default config
    config = get_default_config()
    logger.info(f"Default config: {config}")

    if not args.reset_config:
        # Override default config with config from file
        if len(file_config := load_config()) > 0:
            logger.info(f"Config file {CONFIG_FILE} overrides: {file_config}")
            config.update(file_config)

        # Override default and file config with command line arguments, where
        # provided
        if len(command_line_config := get_command_line_config(args)) > 0:
            logger.info(
                f"Command line config overrides: {command_line_config}"
            )
            config.update(command_line_config)

    # Validate config
    try:
        check_config(**config)
    except Exception as e:
        raise RuntimeError(
            f"Invalid config after loading from file and command line "
            f"arguments: {config}"
        ) from e

    # Save config if requested or daemon is being installed/restarted
    if args.save_config or args.reset_config:
        save_config(config)
        if args.save_config:
            print(f"Config saved to {CONFIG_FILE}: {config}")
        else:
            print(f"Default config saved to {CONFIG_FILE}: {config}")
        if not args.install_daemon and not args.restart_daemon:
            print(
                "\nNote: If the daemon is already running, you will need to "
                "restart it with `--restart-daemon` for the changes to take "
                "effect."
            )
            return

    # Only run the application if the daemon is not being installed/restarted
    if args.install_daemon:
        validate_saved_config(config)
        install_daemon(args.daemon_verbosity)
        print(
            f"\nDaemon successfully installed and started with config: {config}"
        )
    elif args.restart_daemon:
        validate_saved_config(config)
        restart_daemon(args.daemon_verbosity)
        print(f"\nDaemon successfully restarted with config: {config}")
    else:
        print(f"Running {APP_NAME} with config: {config}")
        app = ScrollAccelerator(**config)
        app.join()


def main(arg_list: Optional[Sequence[str]] = None):
    """Entry point for the CLI.

    Args:
        arg_list: Unparsed argument sequence. If None, the arguments are read from
        sys.argv. Useful for testing.
    """
    # Print warning if on Darwin/MacOSX
    if sys.platform == "darwin":
        print(
            "Warning: On Darwin/MacOSX, the OS already does scroll acceleration. "
            "You can use this tool in combination, but you might want to lower "
            "your acceleration parameters. The default acceleration parameters "
            "are already adjusted for this."
        )

    # Parse and validate arguments
    args = parse_args(arg_list)
    try:
        args = validate_args(args)
    except ArgumentError as e:
        sys.stderr.write(f"{APP_NAME}: error: {e}\n")
        sys.exit(1)

    # Initialize logging
    init_logging(args.verbose)

    # Run CLI logic
    try:
        cli(args)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt, exiting.")
    except Exception as e:
        sys.stderr.write(f"\n{e}\n")
        if args.verbose > 0:
            raise
        else:
            sys.stderr.write(
                "Use `-v` or `--verbose` to see the full error traceback.\n"
            )
            sys.exit(1)


if __name__ == "__main__":
    main()
