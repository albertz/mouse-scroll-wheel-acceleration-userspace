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
  def __init__(self, x: int, y: int, dx: int, dy: int, generated: bool):
    self.time = time.time()
    self.pos = (x, y)
    self.delta = (dx, dy)
    self.generated = generated


def sign(v: Union[float, int]) -> int:
  if v < 0:
    return -1
  if v > 0:
    return 1
  return 0


class ScrollAccelerator:
  _DiscreteScrollEvents = [(0, 1), (0, -1), (1, 0), (-1, 0)]
  _MaxKeepScrollEvents = 1000
  _VelocityEstimateMaxDeltaTime = 1.
  _MaxScrollDelta = 100

  def __init__(self, multiplier: float = 1., exp: float = 0.):
    if multiplier <= 1. and exp <= 0.:
      logging.warning(f"Not using acceleration with multiplier {multiplier} and exp {exp}")
    self.accel_factor = multiplier
    self.accel_factor_exp = exp
    self.mouse = Controller()
    self.listener = Listener(on_scroll=self._on_scroll)
    self._scroll_events = []  # type: List[ScrollEvent]
    self._discrete_scroll_events = True  # whether (sent) scroll events are always discrete

  def join(self):
    self.listener.start()
    self.listener.join()

  def _scroll(self, dx: Union[int, float], dy: Union[int, float]):
    if dx == dy == 0:
      return
    if self._discrete_scroll_events and abs(dx) < 1 and abs(dy) < 1:
      return
    dx = sign(dx) * min(abs(dx), self._MaxScrollDelta)
    dy = sign(dy) * min(abs(dy), self._MaxScrollDelta)
    if self._discrete_scroll_events:
      dx, dy = int(dx), int(dy)
    self._scroll_events.append(ScrollEvent(0, 0, dx, dy, generated=True))
    self.mouse.scroll(dx, dy)

  def _on_scroll(self, x: int, y: int, dx: int, dy: int):
    # We get user events and also generated events here,
    # but we do not distinguish them anymore.
    # However, we also kept track of how much scroll events we generated,
    # which allows us to estimate the user scroll velocity.
    self._scroll_events.append(ScrollEvent(x, y, dx, dy, generated=False))
    while len(self._scroll_events) > self._MaxKeepScrollEvents:
      del self._scroll_events[:1]
    (vel_x, vel_y), (gen_vel_x, gen_vel_y) = self._estimate_current_scroll_velocity()
    if vel_x == vel_y == 0:
      return
    cur_vel_x, cur_vel_y = vel_x + gen_vel_x, vel_y + gen_vel_y
    abs_vel = math.sqrt(vel_x * vel_x + vel_y * vel_y)
    abs_vel_cur = math.sqrt(cur_vel_x * cur_vel_x + cur_vel_y * cur_vel_y)
    logging.debug(f"on scroll {(x, y)} {(dx, dy)}, user velocity {abs_vel}, current velocity {abs_vel_cur}")
    # accelerate
    m = self._acceleration_scheme_get_scroll_multiplier(abs_vel)
    if m > 1 and abs_vel * m > abs_vel_cur:
      logging.info(
        f"user velocity {abs_vel} -> scroll acceleration multiplier {m:.2f} -> scroll ({dx * m:.2f}, {dy * m:.2f})")
      m -= 1  # already one scroll event was processed
      self._scroll(dx * m, dy * m)

  def _estimate_current_scroll_velocity(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    """
    We estimate the user speed, excluding generated scroll events,
    and separately only the generated scroll events.

    :return: vel_user, vel_generated
    """
    # Very simple: Just count, but max up to _VelocityEstimateMaxDeltaTime sec.
    # Once there is some sign flip, reset.
    cur_time = time.time()
    dx, dy = 0, 0
    gen_x, gen_y = 0, 0
    start_idx = len(self._scroll_events)
    for ev in reversed(self._scroll_events):
      if cur_time - ev.time > self._VelocityEstimateMaxDeltaTime:
        break
      start_idx -= 1
    for ev in self._scroll_events[start_idx:]:
      dx_, dy_ = ev.delta
      if sign(dx_) != sign(dx or gen_x or dx_) or sign(dy_) != sign(dy or gen_y or dy_):  # sign change
        dx, dy = 0, 0
        gen_x, gen_y = 0, 0
        dx_, dy_ = 0, 0
      if ev.generated:
        gen_x += dx_
        gen_y += dy_
      else:
        dx += dx_
        dy += dy_
    if abs(gen_x) >= abs(dx):  # not all generated events processed yet
      dx = 0
    else:
      dx -= gen_x
    if abs(gen_y) >= abs(dy):  # not all generated events processed yet
      dy = 0
    else:
      dy -= gen_y
    d = 1. / self._VelocityEstimateMaxDeltaTime
    if d > 1:
      d = 1  # do not increase the estimate
    return (float(dx) * d, float(dy) * d), (float(gen_x) * d, float(gen_y) * d)

  def _acceleration_scheme_get_scroll_multiplier(self, abs_vel: float) -> Union[int, float]:
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
