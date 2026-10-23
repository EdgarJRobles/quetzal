# SPDX-License-Identifier: LGPL-3.0-or-later
"""Convert a FreeCAD Flange document object into a pure FlangeSpec."""

from __future__ import annotations

from typing import Any

from ...domain.flange import FlangeSpec


def spec_from_object(fp: Any) -> FlangeSpec:
    return FlangeSpec(
        flange_type=str(fp.FlangeType),
        D=float(fp.D),
        d=float(fp.d),
        df=float(fp.df),
        f=float(fp.f),
        t=float(fp.t),
        n=int(fp.n),
        trf=float(fp.trf),
        drf=float(fp.drf),
        twn=float(fp.twn),
        dwn=float(fp.dwn),
        ODp=float(fp.ODp),
        R=float(fp.R),
        T1=float(fp.T1),
        B2=float(fp.B2),
        Y=float(fp.Y),
    )
