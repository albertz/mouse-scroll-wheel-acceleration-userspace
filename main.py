#!/usr/bin/env python3

import better_exchook
import sys
import argparse
import time
import math
import logging
from typing import List, Tuple, Union
from pynput.mouse import Controller, Listener


class ScrollEvent:
  def __init__(self, x: int, y: int, dx: int, dy: int):
    self.time = time.time()
    self.pos = (x, y)
    self.delta = (dx, dy)


class Main:
  _DiscreteScrollEvents = [(0, 1), (0, -1), (1, 0), (-1, 0)]
  _MaxKeepScrollEvents = 10
  _VelocityEstimateMaxDeltaTime = .5
  _MaxMultiplier = 100

  def __init__(self, accel_factor: float = 1., accel_factor_exp: float = 1.):
    self.accel_factor = accel_factor
    self.accel_factor_exp = accel_factor_exp
    self.mouse = Controller()
    self.listener = Listener(on_scroll=self._on_scroll)
    self._ignore_next_scroll_event = 0
    self._scroll_events = []  # type: List[ScrollEvent]
    self._discrete_scroll_events = True  # whether scroll events are always discrete

  def join(self):
    self.listener.start()
    self.listener.join()

  def _scroll(self, dx: Union[int, float], dy: Union[int, float]):
    if dx == dy == 0:
      return
    if self._discrete_scroll_events and abs(dx) < 1 and abs(dy) < 1:
      return
    self._ignore_next_scroll_event += (abs(dx) + abs(dy)) if self._discrete_scroll_events else 1
    self.mouse.scroll(dx, dy)

  def _on_scroll(self, x: int, y: int, dx: int, dy: int):
    if self._ignore_next_scroll_event > 0:
      self._ignore_next_scroll_event -= 1
      return
    logging.debug(f"on scroll {(x, y)} {(dx, dy)}")
    if (dx, dy) not in self._DiscreteScrollEvents:
      self._discrete_scroll_events = False
    self._scroll_events.append(ScrollEvent(x, y, dx, dy))
    while len(self._scroll_events) > self._MaxKeepScrollEvents:
      del self._scroll_events[:1]
    # accelerate
    m = self._acceleration_scheme_get_scroll_multiplier()
    if m > 1:
      logging.info(f"scroll acceleration multiplier: {m}")
      if m > self._MaxMultiplier:
        m = self._MaxMultiplier
      m -= 1  # already one scroll event was processed
      self._scroll(dx * m, dy * m)

  def _estimate_current_scroll_velocity(self) -> Tuple[float, float]:
    # Very simple: Just count, but max up to _VelocityEstimateMaxDeltaTime sec.
    cur_time = time.time()
    dx, dy = 0, 0
    count = 0
    for ev in reversed(self._scroll_events):
      if cur_time - ev.time > self._VelocityEstimateMaxDeltaTime:
        break
      dx += ev.delta[0]
      dy += ev.delta[1]
      count += 1
    if count == 0:
      return 0., 0.
    d = 1. / self._VelocityEstimateMaxDeltaTime
    if d > 1:
      d = 1  # do not increase the estimate
    return float(dx) * d, float(dy) * d

  def _acceleration_scheme_get_scroll_multiplier(self) -> Union[int, float]:
    vel_x, vel_y = self._estimate_current_scroll_velocity()
    abs_vel = math.sqrt(vel_x * vel_x + vel_y * vel_y)
    logging.debug(f"Estimated scroll velocity: {abs_vel}")
    if vel_x == vel_y == 0:
      return 1
    if abs_vel <= 1:
      return 1

    # Exponential scheme.
    m = abs_vel ** self.accel_factor_exp
    return m * self.accel_factor


def main():
  arg_parser = argparse.ArgumentParser()
  arg_parser.add_argument(
    '-v', '--verbose', action='count', default=0, help="logging level. can be given multiple times")
  arg_parser.add_argument("--multiplier", type=float, default=1.)
  arg_parser.add_argument("--exp", type=float, default=2.)
  args = arg_parser.parse_args()
  logging.basicConfig(
    level=max(1, logging.WARNING - args.verbose * 10),
    format='%(asctime)s %(levelname)s: %(message)s')
  app = Main(accel_factor=args.multiplier, accel_factor_exp=args.exp)
  app.join()


if __name__ == '__main__':
  better_exchook.install()
  try:
    main()
  except KeyboardInterrupt:
    print("KeyboardInterrupt")
    sys.exit(1)
