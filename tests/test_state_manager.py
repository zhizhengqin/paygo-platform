import json
import os
import tempfile
from datetime import date, timedelta

import pytest

import controller.state_manager as sm


@pytest.fixture
def temp_state_dir(monkeypatch):
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
        saved = {"secret_key": "a" * 32, "count": 2, "used_counts": [0, 1],
                 "remaining_days": 27, "last_update": "2026-05-17", "status": "active"}
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
    def test_add_time_from_unbound(self, temp_state_dir):
        state = dict(sm.DEFAULT_STATE)
        today = date.today().isoformat()
        sm.apply_token(state, days=30, token_type=1, new_count=2, used_counts=[0, 1])
        assert state["status"] == "active"
        assert state["remaining_days"] == 30
        assert state["count"] == 2
        assert state["used_counts"] == [0, 1]
        assert state["last_update"] == today

    def test_add_time_stacks_days(self, temp_state_dir):
        state = {"secret_key": "a" * 32, "count": 2, "used_counts": [0, 1],
                 "remaining_days": 10, "last_update": "2026-05-17", "status": "active"}
        sm.apply_token(state, days=30, token_type=1, new_count=4, used_counts=[0, 1, 2, 3])
        assert state["remaining_days"] == 40
        assert state["count"] == 4
        assert state["status"] == "active"

    def test_locked_to_active(self, temp_state_dir):
        state = {"secret_key": "a" * 32, "count": 0, "used_counts": [],
                 "remaining_days": 0, "last_update": "2026-05-10", "status": "locked"}
        sm.apply_token(state, days=15, token_type=1, new_count=2, used_counts=[0, 1])
        assert state["status"] == "active"
        assert state["remaining_days"] == 15

    def test_disable_payg_permanent(self, temp_state_dir):
        state = dict(sm.DEFAULT_STATE)
        sm.apply_token(state, days=0, token_type=3, new_count=1, used_counts=[0])
        assert state["status"] == "permanent"
        assert state["remaining_days"] == -1
        assert state["count"] == 1

    def test_disable_payg_from_active(self, temp_state_dir):
        state = {"secret_key": "a" * 32, "count": 2, "used_counts": [0, 1],
                 "remaining_days": 5, "last_update": "2026-05-18", "status": "active"}
        sm.apply_token(state, days=0, token_type=3, new_count=3, used_counts=[0, 1, 2])
        assert state["status"] == "permanent"
        assert state["remaining_days"] == -1


class TestTick:
    def test_reduces_days_by_date_difference(self, temp_state_dir):
        yesterday = (date.today() - timedelta(days=5)).isoformat()
        state = {"secret_key": "a" * 32, "count": 0, "used_counts": [],
                 "remaining_days": 30, "last_update": yesterday, "status": "active"}
        sm.tick(state)
        assert state["remaining_days"] == 25
        assert state["last_update"] == date.today().isoformat()
        assert state["status"] == "active"

    def test_goes_locked_when_days_run_out(self, temp_state_dir):
        yesterday = (date.today() - timedelta(days=35)).isoformat()
        state = {"secret_key": "a" * 32, "count": 0, "used_counts": [],
                 "remaining_days": 30, "last_update": yesterday, "status": "active"}
        sm.tick(state)
        assert state["remaining_days"] == 0
        assert state["status"] == "locked"

    def test_no_change_same_day(self, temp_state_dir):
        today = date.today().isoformat()
        state = {"secret_key": "a" * 32, "count": 0, "used_counts": [],
                 "remaining_days": 10, "last_update": today, "status": "active"}
        sm.tick(state)
        assert state["remaining_days"] == 10
        assert state["status"] == "active"

    def test_does_not_change_unbound(self, temp_state_dir):
        state = dict(sm.DEFAULT_STATE)
        sm.tick(state)
        assert state["status"] == "unbound"
        assert state["remaining_days"] == 0

    def test_does_not_change_locked(self, temp_state_dir):
        state = {"secret_key": "a" * 32, "count": 0, "used_counts": [],
                 "remaining_days": 0, "last_update": "2026-05-10", "status": "locked"}
        sm.tick(state)
        assert state["status"] == "locked"

    def test_does_not_reduce_permanent(self, temp_state_dir):
        yesterday = (date.today() - timedelta(days=100)).isoformat()
        state = {"secret_key": "a" * 32, "count": 1, "used_counts": [0],
                 "remaining_days": -1, "last_update": yesterday, "status": "permanent"}
        sm.tick(state)
        assert state["remaining_days"] == -1
        assert state["status"] == "permanent"

    def test_permanent_stays_permanent_forever(self, temp_state_dir):
        state = {"secret_key": "a" * 32, "count": 1, "used_counts": [0],
                 "remaining_days": -1, "last_update": "2020-01-01", "status": "permanent"}
        sm.tick(state)
        assert state["status"] == "permanent"


class TestFastForward:
    def test_reduces_days(self, temp_state_dir):
        state = {"secret_key": "a" * 32, "count": 0, "used_counts": [],
                 "remaining_days": 30, "last_update": "2026-05-18", "status": "active"}
        sm.fast_forward(state, 10)
        assert state["remaining_days"] == 20
        assert state["status"] == "active"

    def test_to_lock(self, temp_state_dir):
        state = {"secret_key": "a" * 32, "count": 0, "used_counts": [],
                 "remaining_days": 5, "last_update": "2026-05-18", "status": "active"}
        sm.fast_forward(state, 10)
        assert state["remaining_days"] == 0
        assert state["status"] == "locked"

    def test_permanent_does_nothing(self, temp_state_dir):
        state = {"secret_key": "a" * 32, "count": 1, "used_counts": [0],
                 "remaining_days": -1, "last_update": "2026-05-18", "status": "permanent"}
        sm.fast_forward(state, 999)
        assert state["remaining_days"] == -1
        assert state["status"] == "permanent"


class TestReset:
    def test_reset_to_default(self, temp_state_dir):
        state = {"secret_key": "a" * 32, "count": 5, "used_counts": [0, 1, 2, 3, 4],
                 "remaining_days": 30, "last_update": "2026-05-18", "status": "active"}
        sm.save(state)
        new_state = sm.reset()
        assert new_state == sm.DEFAULT_STATE
        assert new_state["secret_key"] is None
        assert new_state["count"] == 0
