#!/usr/bin/env python3

from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from typing import Tuple, Union

import better_exchook
from pynput.mouse import Controller, Listener

import common
from vec2 import Vec2


class ScrollEvent:
    def __init__(self, pos: Vec2, delta: Vec2, generated: bool):
        self.time = time.time()
        self.pos = pos
        self.delta = delta
        self.generated = generated


class ScrollAccelerator:
    _DiscreteScrollEvents = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    _VelocityEstimateMaxDeltaTime = 1.0
    _MaxScrollDelta = 100 if sys.platform != "darwin" else 1000

    def __init__(self, multiplier: float = 1.0, exp: float = 0.0):
        if multiplier <= 1.0 and exp <= 0.0:
            logging.warning(
                f"Not using acceleration with multiplier {multiplier} and exp {exp}"
            )
        elif sys.platform == "darwin":
            logging.warning(
                "On Darwin/MacOSX, the OS already does scroll acceleration. "
                "You can use this tool in combination, but you might want to use lower values."
            )
        self.accel_factor = multiplier
        self.accel_factor_exp = exp
        self.mouse = Controller()
        self.listener = Listener(on_scroll=self._on_scroll)
        self._scroll_events = []  # type: list[ScrollEvent]
        self._outstanding_generated_scrolls = Vec2()
        self._discrete_scroll_events = sys.platform.startswith(
            "linux"
        )  # whether (sent) scroll events are always discrete

    def join(self):
        self.listener.start()
        self.listener.join()

    def _scroll(self, delta: Vec2):
        delta = delta.abs_cap(self._MaxScrollDelta)
        delta = delta.round()  # in any case, backends anyway use int
        if not delta:
            return
        if (
            self._outstanding_generated_scrolls
            and self._outstanding_generated_scrolls.sign() != delta.sign()
        ):
            # Don't generate a new scroll if there is an outstanding, which was in another direction.
            return
        self._outstanding_generated_scrolls += delta
        self.mouse.scroll(delta.x, delta.y)

    def _on_scroll(self, x: int, y: int, dx: int, dy: int):
        # We get user events and also generated events here.
        # We kept track of how much scroll events we generated,
        # which allows us to estimate the user scroll velocity.
        pos = Vec2(x, y)
        delta = Vec2(dx, dy)
        generated = False
        if delta.sign() == self._outstanding_generated_scrolls.sign():
            generated = True
        if (
            self._discrete_scroll_events
            and delta not in self._DiscreteScrollEvents
        ):
            generated = False
        if generated:
            new_outstanding = self._outstanding_generated_scrolls - delta
            if (
                new_outstanding.sign()
                != self._outstanding_generated_scrolls.sign()
            ):
                new_outstanding = Vec2()
            self._outstanding_generated_scrolls = new_outstanding
        self._scroll_events.append(
            ScrollEvent(pos, delta, generated=generated)
        )
        vel, gen_vel = self._estimate_current_scroll_velocity(
            self._scroll_events[-1].time
        )
        cur_vel = vel + gen_vel
        abs_vel = vel.l2()
        abs_vel_cur = cur_vel.l2()
        logging.debug(
            f"on scroll {(x, y)} {(dx, dy)}, gen {generated}, outstanding gen {self._outstanding_generated_scrolls},"
            f" user vel {abs_vel}, cur vel {abs_vel_cur}"
        )
        # accelerate
        m = self._acceleration_scheme_get_scroll_multiplier(abs_vel)
        if m > 1 and abs_vel * m > abs_vel_cur:
            # Amount of scrolling to add to get to target speed.
            scroll_ = vel * m - cur_vel
            (logging.debug if generated else logging.info)(
                f"scroll user vel {abs_vel:.2f}"
                f" -> accel multiplier {m:.2f}, cur vel {cur_vel}, target vel {abs_vel * m:.2f}"
                f" -> scroll {scroll_}"
            )
            if self._discrete_scroll_events:
                time.sleep(
                    0.001
                )  # enforce some minimal sleep time before the next generated scroll
            if self._discrete_scroll_events and scroll_.round():
                # Scroll only by one. Once we get the next scroll event from that, we will again trigger the next.
                self._scroll(scroll_.round().sign())
            else:
                self._scroll(scroll_)

    def _estimate_current_scroll_velocity(
        self, cur_time: float
    ) -> Tuple[Vec2, Vec2]:
        """
        We estimate the user speed, excluding generated scroll events,
        and separately only the generated scroll events.

        :return: vel_user, vel_generated
        """
        # Very simple: Just count, but max up to _VelocityEstimateMaxDeltaTime sec.
        # Once there is some sign flip, reset.
        d, gen = Vec2(), Vec2()
        start_idx = len(self._scroll_events)
        for ev in reversed(self._scroll_events):
            if cur_time - ev.time > self._VelocityEstimateMaxDeltaTime:
                break
            start_idx -= 1
        del self._scroll_events[:start_idx]
        for ev in self._scroll_events:
            d_ = ev.delta
            dt = cur_time - ev.time
            weight = 1 - dt / self._VelocityEstimateMaxDeltaTime
            if d_.sign() != (d or gen or d_).sign():  # sign change
                d, gen = Vec2(), Vec2()
                continue
            if ev.generated:
                gen += d_ * weight
            else:
                d += d_ * weight
        f = 1.0 / self._VelocityEstimateMaxDeltaTime
        if f > 1:
            f = 1  # do not increase the estimate
        return d * f, gen * f

    def _acceleration_scheme_get_scroll_multiplier(
        self, abs_vel: float
    ) -> Union[int, float]:
        if abs_vel <= 1:
            return 1

        # Exponential scheme.
        m = abs_vel**self.accel_factor_exp
        return m * self.accel_factor


def _timeout_handler(*_args):
    logging.info("Timeout")
    sys.exit(0)


def _init_logging(verbose: int = 0):
    logging.basicConfig(
        level=max(1, logging.WARNING - verbose * 10),
        format="%(asctime)s %(levelname)s: %(message)s",
    )


def main():
    arg_parser = argparse.ArgumentParser(common.app_name_human)
    arg_parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="logging level. can be given multiple times",
    )
    arg_parser.add_argument(
        "--multiplier",
        type=float,
        default=None,
        help="Linear factor, default 1.",
    )
    arg_parser.add_argument(
        "--exp",
        type=float,
        default=None,
        help="Exponential factor. Try 1 or so.",
    )
    arg_parser.add_argument(
        "--timeout",
        type=int,
        help="Will quit after this time (secs). For debugging.",
    )
    args = arg_parser.parse_args()
    if common.config_fn.exists():
        config_env = {}
        code = compile(common.config_fn.read_text(), common.config_fn, "exec")
        exec(code, config_env, config_env)
        _init_logging(args.verbose or config_env.get("verbose", 0))
        logging.info(f"Loaded config {common.config_fn}")
        for key, value in args.__dict__.items():
            if value is None and key in config_env:
                args.__dict__[key] = config_env[key]
                logging.info(f"Use config setting {key} = {config_env[key]}")
    else:
        _init_logging(args.verbose)
        logging.warning(f"Config {common.config_fn} not found")
    if args.multiplier is None and args.exp is None:
        arg_parser.print_help()
        print()
        logging.error("Specify --multiplier and/or --exp.")
        sys.exit(1)
    if args.multiplier is None:
        args.multiplier = 1.0
    if args.exp is None:
        args.exp = 0.0
    if args.timeout:
        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(args.timeout)
    app = ScrollAccelerator(multiplier=args.multiplier, exp=args.exp)
    app.join()


if __name__ == "__main__":
    better_exchook.install()
    try:
        main()
    except KeyboardInterrupt:
        print("KeyboardInterrupt")
        sys.exit(1)
