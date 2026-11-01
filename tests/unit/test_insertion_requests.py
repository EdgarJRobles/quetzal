# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unit tests for form-facing insertion requests."""

from __future__ import annotations

from quetzal.application.insertion_requests import PipeInsertRequest


def test_pipe_request_is_immutable_and_defaults_pypeline():
    request = PipeInsertRequest("SCH-STD", "DN50", 60.32, 3.0, 250.0)
    assert request.pypeline is None
    assert request.height == 250.0
    try:
        request.height = 1.0  # type: ignore[misc]
    except Exception:
        pass
    else:
        raise AssertionError("request should be immutable")
