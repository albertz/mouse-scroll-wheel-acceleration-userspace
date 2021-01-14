# Mouse scroll wheel acceleration, implemented in user space

## Background: Mouse scroll wheel acceleration

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


## Non-MacOSX support

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
is being implemented right now (2021) but not merged yet.
This is currently blocking any further development on the scroll acceleration.
Which probably makes sense, as a clean high resolution API
makes any implementation of scroll acceleration much cleaner.
However, it is also slightly problematic,
as applications which do not support the new high-res scroll API
will use the old API.

For reference, in MacOSX, this is deeply implemented in the kernel
(see [here](https://stackoverflow.com/questions/44196338/where-is-mouse-cursor-movement-acceleration-and-scroll-wheel-acceleration-implem)),
specifically in IOHIDFamily (e.g. see [here](https://github.com/aosm/IOHIDFamily/blob/d36f126e5b8d3183a037c453df7feedaba874553/IOHIDSystem/IOHIPointing.cpp)).


## User space implementation

I just want to have that support now, on my desktop.

How?

We can just send X events,
and basically replicate the logic of my original xf86-input-mouse patch.

This uses [pynput](https://pypi.org/project/pynput/)
both to listen to scroll events,
and also to send out further scroll events.

It is written in a way that it is cross platform.
It even works on MacOSX in addition to the OS scroll acceleration,
such that you can further increase the acceleration.
(For the best experience on MacOSX, you probably want
[this pynput PR](https://github.com/moses-palmer/pynput/pull/341).)


## Installation

    pip install -r requirements.txt

## Usage

Example:

    ./main.py -v --exp 1
