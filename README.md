# Mouse scroll wheel acceleration, implemented in user space

## Background

### Mouse scroll wheel acceleration

What is that?

It's the same as mouse cursor movement acceleration,
but for the mouse scroll wheel.

This makes esp sense for devices where scrolling is continuous,
such as the trackpad
(but even if the scrolling is discrete, like other mouse, it makes sense).
In any case you want to be able to scroll slowly
(e.g. pixel by pixel, or maybe max only a couple of lines).
If you are in a very long document / webpage,
you also want to be able to scroll very fastly.
It is not possible to have both slow and fast scrolling
without acceleration.
With acceleration, this becomes very natural.

If you have used MacOSX, you have that enabled.
You might not even have noticed,
as this feels very natural.


### Non-MacOSX support

Unfortunately, this is not supported yet in other desktop operating systems
(Linux or Windows)
(it is supported on iOS and Android though).
When you switch from MacOSX to Linux or Windows,
you will probably greatly miss this.
(If you have never used MacOSX much,
you might not have gotten used to it,
and might not even know what you miss.)

As this is not implemented in the OS,
some applications and frameworks slowly
start to add their own support for it.
This is really a bad solution,
as it means that the behavior will be inconsistent from app to app.
E.g. GTK has some support ([here](https://gitlab.gnome.org/GNOME/gtk/blob/c734c7e9188b56f56c3a504abee05fa40c5475ac/gtk/gtkrange.c#L3065-3073)),
Firefox has some support (I think only trackpad, [here](https://searchfox.org/mozilla-central/rev/029d9d2477ef0232bb08db94696badddec4d5bda/gfx/layers/apz/src/AsyncPanZoomController.cpp#2572)).

If you want to do it right,
it's still not so clear where exactly this should be implemented.
Long time ago (2010),
I implemented a patch for xf86-input-mouse ([here](https://bugs.freedesktop.org/show_bug.cgi?id=29905)).
This code used a similar acceleration logic
as the mouse cursor movement acceleration.
In Xorg/X11, you get discrete button press events for scroll events,
which made it a bit ugly.
The discussion was mostly about whether this is useful at all,
and also where to actually implement it,
where the conclusion was mostly either in libinput,
or in xf86-input-libinput.
A new proposal for libinput mouse wheel acceleration
was opened [here](https://gitlab.freedesktop.org/libinput/libinput/-/issues/7).
As continuous scrolling and high resolution scrolling
becomes more widely used,
corresponding support in libinput for
[high-resolution scroll wheel support](https://gitlab.freedesktop.org/libinput/libinput/-/merge_requests/139)
was merged now (2021).
This was blocking any further development on the scroll acceleration.
Which probably makes sense, as a clean high resolution API
makes any implementation of scroll acceleration much cleaner.
However, it is also slightly problematic,
as applications which do not support the new high-res scroll API
will use the old API.

For reference, in MacOSX, this is deeply implemented in the kernel
(see [here](https://stackoverflow.com/questions/44196338/where-is-mouse-cursor-movement-acceleration-and-scroll-wheel-acceleration-implem)),
specifically in IOHIDFamily (e.g. see [here](https://github.com/apple-oss-distributions/IOHIDFamily/blob/c56e1c1b2469d9956a585cc2518c8f0c51b5809d/IOHIDSystem/IOHIPointing.cpp#L25)).


### User space implementation

I just want to have that support now, on my desktop.

How?

We can just send extra scroll events,
and basically replicate the logic of my original xf86-input-mouse patch.

This uses [pynput](https://pypi.org/project/pynput/)
both to listen to scroll events,
and also to send out further scroll events.

Pynput supports all the major desktop platforms
like X11, Wayland, MacOSX and Windows.
It even works on MacOSX in addition to the OS scroll acceleration,
such that you can further increase the acceleration.


## Prerequisites

### `pipx`

`pipx` is recommended to install the application so that it does not interfere
with other packages or environments.
It works by creating a virtual environment for the application,
installing the application into it, and then making any executables available
in the system path.

To install `pipx`, see [here](https://pipx.pypa.io/stable/installation/).


## Installation

There are a few ways to install the application.

### Using pipx (recommended)

To install the application, run:
```bash
pipx install git+https://github.com/albertz/mouse-scroll-wheel-acceleration-userspace.git
```
This will create a virtual environment for the application and install the
application into it.
You can then run the application from the command line using
`scroll-accelerator` without
having to activate the virtual environment.

### Using a virtual environment

You can also manually create a virtual environment (using any environment
manager you prefer)
and install the application into it.
For example, using `venv`:
```bash
python -m venv .venv
source .venv/bin/activate
pip install git+https://github.com/albertz/mouse-scroll-wheel-acceleration-userspace.git
```
Note that you will need to activate the virtual environment before running
the application
from the command line.

### Using your system Python/pip (not recommended)

If you want to install the application to your system, run:
```bash
pip install [--user] git+https://github.com/albertz/mouse-scroll-wheel-acceleration-userspace.git
```
where `--user` is optional if you want to install the application to your
user directory.

Note that this is NOT recommended, as some systems may not allow you to
install the application directly to the system,
and forcing the installation to the system will likely break other packages.

## Usage

### Running the application

If you installed the application manually to a virtual environment,
activate the virtual environment first.

To run the application, run:
```bash
scroll-accelerator [-v]
```
where `-v` is optional and can be used to increase the verbosity of the
application.
Providing it multiple times (e.g. `-vvv`) will increase the verbosity
even further.

You can customize the scroll behavior with the `--exp`, `--multiplier` and
`--threshold` acceleration parameter options:
```bash
scroll-accelerator --exp 0.4 --multiplier 1.2 --threshold 1.0
```
See the [Acceleration parameters](#acceleration-parameters) section for more
details about the acceleration parameters.


### Installing the daemon as a systemd user unit (Linux only)

If you found values that work for you, you can install the application as a
user-space, systemd daemon:
```bash
scroll-accelerator --install-daemon --exp 0.4 --multiplier 1.2 --threshold 1.0
```
This will create and start a systemd user unit for the application.
It will run the application in the background, automatically start it on
boot,
and also restart it if it crashes.
This command also automatically saves the configuration to the file
`~/.config/scroll-accelerator/config.yaml`.

### Modifying the configuration

To modify the configuration, you can use the `--save-config` option with at
least one of the acceleration parameter options.

For example, to change the multiplier 0.8, you can run:
```bash
scroll-accelerator --save-config --multiplier 0.8
```
which will modify the configuration file to have a multiplier of 0.8.

Note that if the daemon is already running, you will need to restart it for
the changes to take effect:
```bash
scroll-accelerator --restart-daemon
```

You can do both of these steps at once in one command by running:
```bash
scroll-accelerator --restart-daemon --multiplier 0.8
```
Note that the new config is automatically saved when using `--restart-daemon`
or `--install-daemon`
and therefore the `--save-config` option is not needed.

You can also modify the configuration by editing the file
`~/.config/scroll-accelerator/config.yaml` directly.

### Stopping/uninstalling the daemon

To stop the daemon, you can use the `--stop-daemon` option.
```bash
scroll-accelerator --stop-daemon
```
This will stop the daemon temporarily, but it will still be restarted on
boot.

To uninstall the daemon, you can use the `--uninstall-daemon` option.
```bash
scroll-accelerator --uninstall-daemon
```
This will stop the daemon and uninstall it. Note that this will not remove
the configuration file.

### Getting the status/log of the daemon

To get the status of the daemon, you can use the `--daemon-status` option.
```bash
scroll-accelerator --daemon-status
```
This will print the status of the systemd unit associated with the daemon.

To get the log of the daemon, you can use the `--daemon-log` option.
```bash
scroll-accelerator --daemon-log
```
This will print the log of the daemon.

Note that this will be fairly empty by default.
To get more verbose output, you can use the `--daemon-verbosity` option
when installing or restarting the daemon:
```bash
scroll-accelerator --restart-daemon --daemon-verbosity 1
```
Then, after scrolling a few times, you can use `--daemon-log` again to see
the log.
It should now show a more verbose log, including the scroll events and the
acceleration.

## Acceleration parameters

The following acceleration parameters determine the behavior of the scroll
accelerator
and can be set using the command line options or the configuration file.

* `exp`: the exponential factor. This controls how fast the scroll speed
  increases.
* `multiplier`: the scalar multiplier. This is multiplied by the scroll
  speed.
* `threshold`: the threshold. This controls the minimum scroll speed.

The exact formula for computing the target scroll speed is:
```python
m = (user_scroll_speed - threshold) ** exp
target_scroll_speed = user_scroll_speed + m * multiplier
```

## Uninstallation

To uninstall `scroll-accelerator`, first uninstall the daemon:
```bash
scroll-accelerator --uninstall-daemon
```

Then you can uninstall the application using whichever package manager was
used to install it.
For pipx:
```bash
pipx uninstall scroll-accelerator
```

For `pip`:
```bash
pip uninstall scroll-accelerator
```

Note that this will not remove the configuration file.
To remove the configuration file, you can run:
```bash
rm -rf ~/.config/scroll-accelerator
```

## Development/Contributing

We welcome any and all contributions!

We ask that you follow the guidelines below in order to make it easier to
review and merge your changes.

### Prerequisites

#### Uninstall the package (if applicable)

If you already installed the package using `pipx` or some other method,
it is highly recommended to uninstall it first.
This will ensure that you are not using a version of the package that is not
under development.
See the [Uninstallation](#uninstallation) section for instructions.

#### Install `uv`

We ask that you use `uv` to manage the project and its dependencies.
`uv` is a modern, fast, and cross-platform Python package and project
management tool.
To install `uv`, see [here](https://docs.astral.sh/uv/getting-started/installation/).

#### Fork the repository

If you want to contribute and you do not have write access to the
repository,
you will need to fork the repository (create a copy of the repository in
your own GitHub account).
To fork, go to our [GitHub repository page](https://github.com/albertz/mouse-scroll-wheel-acceleration-userspace)
and click the "Fork" button in the top right corner.
Follow the instructions to finish creating the fork.

### Setup

Now that you have forked the repository, you can clone it using:
```bash
git clone <your-fork-url> scroll-accelerator
cd scroll-accelerator
```

We've included a `uv.lock` file to lock the dependencies for development
purposes.
To install the package and its dependencies with uv, simply run:
```bash
uv sync
```
This will create a virtual environment and install the package and its
dependencies
into it.

To run the application, you can use the `uv run` command:
```bash
uv run scroll-accelerator
```

Alternatively, you can first manually activate the virtual environment.
```bash
source .venv/bin/activate
```

You can then run the application as normal:
```bash
scroll-accelerator
```

### Pre-commit hooks

We use `pre-commit` to run automated checks and formatting on the code
before it is committed.
To install the pre-commit hooks, run:
```bash
uv run pre-commit install
```
Now whenever you commit, the pre-commit hooks will run and check the code.
If the code does not pass the checks, the commit will be rejected.
Pre-commit may automatically fix some of the issues,
but if any of the files have been modified, you will need to stage them again
using `git add` and commit again.

You can also run the checks manually without committing:
```bash
uv run pre-commit run --all-files
```

### Committing and pushing

When you are satisfied with your changes, you can stage and commit them:
```bash
git add -A
git commit -m "Your commit message"
```
or in one command:
```bash
git commit -am "Your commit message"
```

You can then push your changes to your fork:
```bash
git push
```

### Submitting a pull request

Now that you have pushed your changes to your fork,
you can submit a pull request to the main branch of the repository.
To do this, go to the the [pull requests page](https://github.com/albertz/mouse-scroll-wheel-acceleration-userspace/pulls)
and click the "New pull request" button.
Follow the instructions to submit the pull request.
