import sys

import better_exchook

from . import main

if __name__ == "__main__":
    better_exchook.install()
    try:
        main()
    except KeyboardInterrupt:
        print("KeyboardInterrupt")
        sys.exit(1)
