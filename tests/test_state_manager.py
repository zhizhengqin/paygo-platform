import json
import os
import tempfile
from datetime import date, timedelta

import pytest

import controller.state_manager as sm


@pytest.fixture
def temp_state_dir(monkeypatch):
    """使用临时目录替代 ~/.paygo"""
    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = os.path.join(tmpdir, ".paygo")
        monkeypatch.setattr(sm, "STATE_DIR", state_dir)
        monkeypatch.setattr(sm, "STATE_FILE", os.path.join(state_dir, "state.json"))
        yield state_dir


class TestLoad:
    def test_no_file_returns_default(self, temp_state_dir):
        state = sm.load()
        assert state == sm.DEFAULT_STATE

    def test_existing_file_returns_saved_state(self, temp_state_dir):
        saved = {"device_id_hash": 703, "remaining_days": 27,
                 "last_update": "2026-05-17", "status": "active"}
        sm.save(saved)
        loaded = sm.load()
        assert loaded == saved


class TestSave:
    def test_create_directory_if_missing(self, temp_state_dir):
        state = dict(sm.DEFAULT_STATE)
        state["status"] = "active"
        sm.save(state)
        assert os.path.exists(sm.STATE_FILE)
        with open(sm.STATE_FILE) as f:
            assert json.load(f)["status"] == "active"


class TestApplyToken:
    def test_unbound_to_active(self, temp_state_dir):
        state = dict(sm.DEFAULT_STATE)
        today = date.today().isoformat()
        sm.apply_token(state, device_id_hash=703, days=30)
        assert state["status"] == "active"
        assert state["remaining_days"] == 30
        assert state["device_id_hash"] == 703
        assert state["last_update"] == today

    def test_active_stack_days_same_device(self, temp_state_dir):
        state = {"device_id_hash": 703, "remaining_days": 10,
                 "last_update": "2026-05-17", "status": "active"}
        sm.apply_token(state, device_id_hash=703, days=30)
        assert state["remaining_days"] == 40
        assert state["status"] == "active"

    def test_locked_to_active(self, temp_state_dir):
        state = {"device_id_hash": 703, "remaining_days": 0,
                 "last_update": "2026-05-10", "status": "locked"}
        sm.apply_token(state, device_id_hash=703, days=15)
        assert state["status"] == "active"
        assert state["remaining_days"] == 15


class TestTick:
    def test_reduces_days_by_date_difference(self, temp_state_dir):
        yesterday = (date.today() - timedelta(days=5)).isoformat()
        state = {"device_id_hash": 703, "remaining_days": 30,
                 "last_update": yesterday, "status": "active"}
        sm.tick(state)
        assert state["remaining_days"] == 25
        assert state["last_update"] == date.today().isoformat()
        assert state["status"] == "active"

    def test_goes_locked_when_days_run_out(self, temp_state_dir):
        yesterday = (date.today() - timedelta(days=35)).isoformat()
        state = {"device_id_hash": 703, "remaining_days": 30,
                 "last_update": yesterday, "status": "active"}
        sm.tick(state)
        assert state["remaining_days"] == 0
        assert state["status"] == "locked"

    def test_no_change_same_day(self, temp_state_dir):
        today = date.today().isoformat()
        state = {"device_id_hash": 703, "remaining_days": 10,
                 "last_update": today, "status": "active"}
        sm.tick(state)
        assert state["remaining_days"] == 10
        assert state["status"] == "active"

    def test_does_not_change_unbound(self, temp_state_dir):
        state = dict(sm.DEFAULT_STATE)
        sm.tick(state)
        assert state["status"] == "unbound"
        assert state["remaining_days"] == 0

    def test_does_not_change_locked(self, temp_state_dir):
        state = {"device_id_hash": 703, "remaining_days": 0,
                 "last_update": "2026-05-10", "status": "locked"}
        sm.tick(state)
        assert state["status"] == "locked"
