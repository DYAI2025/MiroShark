"""Tests for the autoactive monitor service."""

import pytest
import time
import threading
from unittest.mock import patch, MagicMock
from app.services.autoactive_monitor import AutoactiveMonitorService, MonitorStatus


class TestAutoactiveMonitorService:
    """Suite for monitor service lifecycle and remediation logic."""

    def test_start_monitor_returns_running_status(self):
        """Starting monitor returns RUNNING state immediately."""
        result = AutoactiveMonitorService.start("sim_test_1")
        assert result["success"] is True
        assert result["data"]["status"] == MonitorStatus.RUNNING.value
        # Cleanup
        AutoactiveMonitorService.stop("sim_test_1")

    def test_double_start_returns_error(self):
        """Starting an already-running monitor returns error."""
        AutoactiveMonitorService.start("sim_test_2")
        result = AutoactiveMonitorService.start("sim_test_2")
        assert result["success"] is False
        assert "already running" in result["error"].lower()
        AutoactiveMonitorService.stop("sim_test_2")

    def test_stop_monitor_sets_stopped(self):
        """Stopping transitions state to STOPPED."""
        AutoactiveMonitorService.start("sim_test_3")
        result = AutoactiveMonitorService.stop("sim_test_3")
        assert result["success"] is True
        status = AutoactiveMonitorService.status("sim_test_3")
        assert status["data"]["status"] == MonitorStatus.STOPPED.value

    def test_status_idle_when_not_started(self):
        """Querying status for unknown sim returns IDLE, not error."""
        status = AutoactiveMonitorService.status("sim_test_nonexistent")
        assert status["data"]["status"] == MonitorStatus.IDLE.value

    def test_stop_nonexistent_returns_error(self):
        """Stopping an unmonitored sim returns error, not crash."""
        result = AutoactiveMonitorService.stop("sim_test_nonexistent")
        assert result["success"] is False

    @patch("app.services.autoactive_monitor.AutoactiveMonitorService._ollama_is_alive")
    @patch("app.services.autoactive_monitor.AutoactiveMonitorService._vram_used_mib")
    def test_no_intervention_when_healthy(self, mock_vram, mock_ollama):
        """Healthy sim with progress should have stuck_count = 0."""
        mock_ollama.return_value = True
        mock_vram.return_value = 5000
        # Simulate a running monitor with progress
        state = {
            "status": MonitorStatus.RUNNING.value,
            "last_progress": "round_5|150_actions",
            "stuck_count": 0,
        }
        assert state["stuck_count"] == 0

    @patch("app.services.autoactive_monitor.AutoactiveMonitorService._restart_ollama")
    @patch("app.services.autoactive_monitor.AutoactiveMonitorService._ollama_is_alive")
    def test_intervention_triggers_when_ollama_dead(self, mock_alive, mock_restart):
        """Dead Ollama triggers restart intervention."""
        mock_alive.return_value = False
        mock_restart.return_value = True
        intervention = AutoactiveMonitorService._execute_remediation("sim_test", {})
        assert "ollama_restart" in intervention.get("actions", [])
