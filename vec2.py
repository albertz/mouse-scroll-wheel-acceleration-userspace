
from __future__ import annotations
import math
from typing import Union
import operator


class Vec2:
  def __init__(self, x=0, y=0):
    self.x, self.y = x, y

  def __repr__(self):
    if isinstance(self.x, float) or isinstance(self.y, float):
      return f"Vec2({self.x:.2f}, {self.y:.2f})"
    return f"Vec2({self.x}, {self.y})"

  def __bool__(self) -> bool:
    return bool(self.x or self.y)

  def all(self) -> bool:
    return bool(self.x and self.y)

  def __eq__(self, other) -> bool:
    return self.binary_map(other, func=operator.eq).all()

  def __ne__(self, other) -> bool:
    return not self.__eq__(other)

  def __add__(self, other):
    return self.binary_map(other, func=operator.add)

  def __sub__(self, other):
    return self.binary_map(other, func=operator.sub)

  def __mul__(self, other):
    return self.binary_map(other, func=operator.mul)

  def l1(self):
    return abs(self.x) + abs(self.y)

  def l2(self):
    if not self:
      return 0.0
    if self.x and not self.y:
      return abs(self.x)
    if self.y and not self.x:
      return abs(self.y)
    return math.sqrt(self.x * self.x + self.y * self.y)

  def map(self, func):
    return Vec2(func(self.x), func(self.y))

  def binary_map(self, other, *, func):
    if isinstance(other, (tuple, list)):
      other = Vec2(*other)
    if not isinstance(other, Vec2):
      if int(other) == other:
        other = int(other)
      other = Vec2(other, other)
    return Vec2(func(self.x, other.x), func(self.y, other.y))

  def int(self) -> Vec2:
    return self.map(int)

  def round(self) -> Vec2:
    return self.map(round)

  def sign(self) -> Vec2:
    return self.map(sign)

  def abs_cap(self, v) -> Vec2:
    return self.map(lambda x: sign(x) * min(abs(x), v))


def sign(v: Union[float, int]) -> int:
  if v < 0:
    return -1
  if v > 0:
    return 1
  return 0
