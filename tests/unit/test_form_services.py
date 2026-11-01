# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unit tests for the UI service container and workbench state."""

from __future__ import annotations

from quetzal.application.form_services import FormServices
from quetzal.application.reporting import NullReporter, RecordingReporter
from quetzal.application.workbench_state import WorkbenchState


def test_workbench_state_is_explicit_and_clearable():
    state = WorkbenchState()
    assert state.active_pype_line is None
    state.set_active_pype_line("PL1")
    state.set_active_frame_line("FL1")
    assert (state.active_pype_line, state.active_frame_line) == ("PL1", "FL1")
    state.clear()
    assert (state.active_pype_line, state.active_frame_line) == (None, None)


def test_recording_reporter():
    reporter = RecordingReporter()
    reporter.info("a")
    reporter.warning("b")
    reporter.error("c")
    assert reporter.messages == [("info", "a"), ("warning", "b"), ("error", "c")]


def test_null_reporter_is_silent():
    NullReporter().info("x")
    NullReporter().warning("x")
    NullReporter().error("x")


def test_form_services_is_a_dependency_container():
    services = FormServices(
        catalog=object(),
        catalog_presenter=object(),
        section_presenter=object(),
        standard_filters=object(),
        preview=object(),
        state=WorkbenchState(active_pype_line="PL"),
        reporter=NullReporter(),
    )
    assert services.state.active_pype_line == "PL"
    assert isinstance(services.standard_filters, object)
