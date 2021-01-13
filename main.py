#!/usr/bin/env python3

import better_exchook
import sys
import argparse
import time
import math
import logging
from typing import List, Tuple, Union
from pynput.mouse import Controller, Listener
import signal


class ScrollEvent:
  def __init__(self, x: int, y: int, dx: int, dy: int):
    self.time = time.time()
    self.pos = (x, y)
    self.delta = (dx, dy)


def sign(v: Union[float, int]) -> int:
  if v < 0:
    return -1
  if v > 0:
    return 1
  return 0


class ScrollAccelerator:
  _DiscreteScrollEvents = [(0, 1), (0, -1), (1, 0), (-1, 0)]
  _MaxKeepScrollEvents = 1000
  _VelocityEstimateMaxDeltaTime = .5
  _MaxMultiplier = 500

  def __init__(self, multiplier: float = 1., exp: float = 0.):
    if multiplier <= 1. and exp <= 0.:
      logging.warning(f"Not using acceleration with multiplier {multiplier} and exp {exp}")
    self.accel_factor = multiplier
    self.accel_factor_exp = exp
    self.mouse = Controller()
    self.listener = Listener(on_scroll=self._on_scroll)
    self._ignore_next_scroll_event = 0
    self._ignore_next_scroll_event_delta = (0, 0)
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
    self._scroll_events.append(ScrollEvent(*self.mouse.position, dx, dy))
    if self._discrete_scroll_events:
      assert (dx or dy) and (not (dx and dy))
      self._ignore_next_scroll_event_delta = (sign(dx), sign(dy))
    else:
      self._ignore_next_scroll_event_delta = (dx, dy)
    self.mouse.scroll(dx, dy)

  def _on_scroll(self, x: int, y: int, dx: int, dy: int):
    if self._ignore_next_scroll_event > 0:
      if (dx, dy) != self._ignore_next_scroll_event_delta:
        pass  # let this pass
      else:
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
      logging.info(f"scroll acceleration multiplier {m:.2f} -> scroll ({dx * m:.2f}, {dy * m:.2f})")
      if m > self._MaxMultiplier:
        m = self._MaxMultiplier
      m -= 1  # already one scroll event was processed
      self._scroll(dx * m, dy * m)

  def _estimate_current_scroll_velocity(self) -> Tuple[float, float]:
    # Very simple: Just count, but max up to _VelocityEstimateMaxDeltaTime sec.
    cur_time = time.time()
    dx, dy = 0, 0
    dx_sign_change = False
    dy_sign_change = False
    count = 0
    for ev in reversed(self._scroll_events):
      if cur_time - ev.time > self._VelocityEstimateMaxDeltaTime:
        break
      dx_, dy_ = ev.delta
      if dx_sign_change or (dx and dx_ and sign(dx) != sign(dx_)):
        dx_sign_change = True
        dx = dx_ = 0
      if dy_sign_change or (dy and dy_ and sign(dy) != sign(dy_)):
        dy_sign_change = True
        dy = dy_ = 0
      if dx_sign_change and dy_sign_change:
        break
      dx += dx_
      dy += dy_
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


def _timeout_handler(*_args):
  logging.info("Timeout")
  sys.exit(0)


def main():
  arg_parser = argparse.ArgumentParser()
  arg_parser.add_argument(
    '-v', '--verbose', action='count', default=0, help="logging level. can be given multiple times")
  arg_parser.add_argument("--multiplier", type=float, default=None, help="Linear factor, default 1.")
  arg_parser.add_argument("--exp", type=float, default=None, help="Exponential factor. Try 0.8 or so.")
  arg_parser.add_argument("--timeout", type=int, help="Will quite after this time (secs). For debugging.")
  args = arg_parser.parse_args()
  logging.basicConfig(
    level=max(1, logging.WARNING - args.verbose * 10),
    format='%(asctime)s %(levelname)s: %(message)s')
  if args.multiplier is None and args.exp is None:
    arg_parser.print_help()
    print()
    logging.error("Specify --multiplier and/or --exp.")
    sys.exit(1)
  if args.multiplier is None:
    args.multiplier = 1.
  if args.exp is None:
    args.exp = 0.
  if args.timeout:
    signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(args.timeout)
  app = ScrollAccelerator(multiplier=args.multiplier, exp=args.exp)
  app.join()


if __name__ == '__main__':
  better_exchook.install()
  try:
    main()
  except KeyboardInterrupt:
    print("KeyboardInterrupt")
    sys.exit(1)
