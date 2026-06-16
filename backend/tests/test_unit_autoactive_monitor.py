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
    @patch("app.services.autoactive_monitor.AutoactiveMonitorService._find_sim_pid")
    def test_healthy_sim_no_remediation(self, mock_pid, mock_vram, mock_ollama):
        """Healthy sim: Ollama alive, VRAM ok, sim running — remediation should be no-op."""
        mock_ollama.return_value = True
        mock_vram.return_value = 5000
        mock_pid.return_value = 99999
        result = AutoactiveMonitorService._execute_remediation("sim_healthy", object())
        actions = result.get("actions", [])
        assert "ollama_restart" not in actions, "Should not restart Ollama when it's alive"

    @patch("app.services.autoactive_monitor.AutoactiveMonitorService._re_trigger_start")
    @patch("app.services.autoactive_monitor.AutoactiveMonitorService._find_sim_pid")
    @patch("app.services.autoactive_monitor.AutoactiveMonitorService._vram_used_mib")
    @patch("app.services.autoactive_monitor.AutoactiveMonitorService._restart_ollama")
    @patch("app.services.autoactive_monitor.AutoactiveMonitorService._ollama_is_alive")
    def test_intervention_triggers_when_ollama_dead(self, mock_alive, mock_restart, mock_vram, mock_pid, mock_trigger):
        """Dead Ollama triggers restart intervention."""
        mock_alive.return_value = False
        mock_restart.return_value = True
        mock_vram.return_value = 5000
        mock_pid.return_value = 99999
        mock_trigger.return_value = None
        intervention = AutoactiveMonitorService._execute_remediation("sim_test", {})
        assert "ollama_restart" in intervention.get("actions", [])
