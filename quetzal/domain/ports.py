# SPDX-License-Identifier: LGPL-3.0-or-later
"""Small, FreeCAD-free vector and port helpers.

Feature proxies deal with FreeCAD vectors, but the *rules* (which port is
closest to a point, how to normalise a direction) are plain geometry.  This
module keeps those rules testable without loading FreeCAD.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Iterator, Sequence, Tuple


@dataclass(frozen=True)
class Vec3:
    """Immutable 3D vector with just the operations the domain needs."""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __iter__(self) -> Iterator[float]:
        yield self.x
        yield self.y
        yield self.z

    def __add__(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> "Vec3":
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    __rmul__ = __mul__

    def dot(self, other: "Vec3") -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    @property
    def length(self) -> float:
        return sqrt(self.dot(self))

    def normalized(self) -> "Vec3":
        length = self.length
        if length == 0.0:
            return Vec3()
        return self * (1.0 / length)

    def distance_to(self, other: "Vec3") -> float:
        return (self - other).length

    def as_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)


@dataclass(frozen=True)
class Port:
    """A connection point: local position plus outward direction."""

    position: Vec3
    direction: Vec3 = Vec3(0.0, 0.0, -1.0)

    def normalized(self) -> "Port":
        return Port(self.position, self.direction.normalized())


def nearest_port_index(ports: Sequence[Port], point: Vec3) -> int:
    """Index of the port closest to ``point`` (``-1`` for an empty sequence)."""

    if not ports:
        return -1
    best_index = 0
    best_distance = ports[0].position.distance_to(point)
    for index, port in enumerate(ports[1:], start=1):
        distance = port.position.distance_to(point)
        if distance < best_distance:
            best_index = index
            best_distance = distance
    return best_index
