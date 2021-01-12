#!/usr/bin/env python3

import better_exchook
import sys
from pynput.mouse import Button, Controller, Listener


class Main:
  _DiscreteScrollEvents = [(0, 1), (0, -1), (1, 0), (-1, 0)]

  def __init__(self):
    self.mouse = Controller()
    self.listener = Listener(on_scroll=self.on_scroll)
    self._ignore_next_scroll_event = 0
    self._discrete_scroll_events = True  # whether scroll events are always discrete

  def join(self):
    self.listener.start()
    self.listener.join()

  def _scroll(self, dx, dy):
    self._ignore_next_scroll_event += (abs(dx) + abs(dy)) if self._discrete_scroll_events else 1
    self.mouse.scroll(dx, dy)

  def on_scroll(self, x, y, dx, dy):
    if self._ignore_next_scroll_event > 0:
      self._ignore_next_scroll_event -= 1
      return
    print("on scroll", (x, y), (dx, dy))
    if (dx, dy) not in self._DiscreteScrollEvents:
      self._discrete_scroll_events = False
    self._scroll(dx * 2, dy * 2)  # accelerate


def main():
  Main().join()


if __name__ == '__main__':
  better_exchook.install()
  try:
    main()
  except KeyboardInterrupt:
    print("KeyboardInterrupt")
    sys.exit(1)



