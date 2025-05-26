import logging
import sys
import time
from typing import Tuple, Union

from pynput.mouse import Controller, Listener

from scroll_accelerator.vec2 import Vec2

logger = logging.getLogger(__name__)


def check_config(multiplier: float, exp: float, threshold: float):
    if multiplier <= 0:
        raise ValueError("Multiplier must be greater than 0.")
    if exp < 0:
        raise ValueError("Exp must be greater than or equal to 0.")
    if threshold < 0:
        raise ValueError("Threshold must be greater than or equal to 0.")


class ScrollEvent:
    def __init__(self, pos: Vec2, delta: Vec2, generated: bool):
        self.time = time.time()
        self.pos = pos
        self.delta = delta
        self.generated = generated


class ScrollAccelerator:
    """Scroll accelerator.

    This class uses the pynput library to listen for scroll events and
    accelerate them. It does this by estimating the user's scroll velocity
    and then sending additional scroll events to reach the target velocity,
    as calculated by the acceleration parameters.
    """

    _DiscreteScrollEvents = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    _VelocityEstimateMaxDeltaTime = 1.0
    _MaxScrollDelta = 100 if sys.platform != "darwin" else 1000

    def __init__(
        self,
        multiplier: float = 1.0,
        exp: float = 0.0,
        threshold: float = 0.0,
    ):
        """Initialize the scroll accelerator.

        Args:
            multiplier: The linear acceleration factor.
            exp: The exponential acceleration factor.
            threshold: The minimum scroll speed at which the acceleration starts.

        For more details, try `scroll-accelerator --help` or see the README.md
        on GitHub (https://github.com/albertz/mouse-scroll-wheel-acceleration-userspace).
        """
        check_config(multiplier, exp, threshold)

        self.multiplier = multiplier
        self.exp = exp
        self.threshold = threshold
        self._mouse = Controller()
        self._listener = Listener(on_scroll=self._on_scroll)
        self._scroll_events: list[ScrollEvent] = []
        self._outstanding_generated_scrolls = Vec2()
        self._discrete_scroll_events = "linux" in sys.platform

        logger.info(
            f"ScrollAccelerator initialized with config: "
            f"multiplier={multiplier}, exp={exp}, threshold={threshold}"
        )

    def join(self):
        """Join the listener thread.

        This will block the current thread until the listener thread is stopped.
        """
        self._listener.start()
        self._listener.join()

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

    def _get_scroll_multiplier(self, speed: float) -> Union[int, float]:
        """Exponential acceleration scheme."""
        speed_thresh = speed - self.threshold
        if speed_thresh <= 1:
            return 1
        return (speed_thresh**self.exp) * self.multiplier

    def _scroll(self, delta: Vec2):
        """Scroll by the given delta.

        Args:
            delta: The delta to scroll by.
        """
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
        self._mouse.scroll(delta.x, delta.y)

    def _on_scroll(self, x: int, y: int, dx: int, dy: int):
        """Called when a scroll event is detected.

        We get user events and also generated events here.
        We keep track of how much scroll events we generated,
        which allows us to estimate the user scroll velocity.
        """
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
        user_vel, gen_vel = self._estimate_current_scroll_velocity(
            self._scroll_events[-1].time
        )
        cur_vel = user_vel + gen_vel
        user_speed = user_vel.l2()
        cur_speed = cur_vel.l2()
        logger.debug(
            f"On scroll {(x, y)} {(dx, dy)}, gen {generated}, "
            f"outstanding gen {self._outstanding_generated_scrolls}, "
            f"user speed {user_speed}, cur speed {cur_speed}"
        )

        # Accelerate
        m = self._get_scroll_multiplier(user_speed)
        if m > 1 and user_speed * m > cur_speed:
            # Amount of scrolling to add to get to target velocity.
            scroll_delta = user_vel * m - cur_vel
            (logger.debug if generated else logger.info)(
                f"scroll user speed {user_speed:.2f}"
                f" -> accel factor {m:.2f}, cur speed {cur_speed}, target speed {user_speed * m:.2f}"
                f" -> scroll {scroll_delta}"
            )

            if self._discrete_scroll_events:
                # Enforce some minimal sleep time before the next generated scroll
                time.sleep(1e-4)

                # Scroll only by one.
                # Once we get the next scroll event from that, we will again trigger the next.
                if scroll_delta.round():
                    self._scroll(scroll_delta.round().sign())
                    return

            # Scroll by the amount of the delta.
            self._scroll(scroll_delta)
