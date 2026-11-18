"""Checks for the free GitHub Actions self-dispatch heartbeat.

All cases use fake time and no network, keys, trades or live ledger.
"""
from datetime import datetime, timezone
import schedule_relay as relay


T0 = 1794873831.4168396


def state(*, latest=T0 + 3600, finished=False, start=T0, deadline=T0+604800):
    return {
        "status": "FINISHED" if finished else "LIVE",
        "meta": {
            "started_at": start,
            "deadline": deadline,
            "finished": finished,
            "last_completed_tick": datetime.fromtimestamp(
                latest, timezone.utc).isoformat()
        },
    }


def test_chain_dispatch_waits_until_fifteen_minutes_after_paper_tick():
    now = T0 + 3700
    trigger, wait, why = relay.relay_plan(state(), "workflow_dispatch", now)
    assert trigger is True
    assert abs(wait - 800) < 0.1
    assert why == "dispatch-next-paper-tick"


def test_missed_tick_is_immediately_recovered_without_resetting_clock():
    s = state()
    now = T0 + 4*3600
    trigger, wait, _ = relay.relay_plan(s, "schedule", now)
    assert trigger is True
    assert wait == 0
    assert s["meta"]["deadline"] == T0 + 604800


def test_cron_does_not_start_a_duplicate_chain_if_dispatch_recent():
    now = T0 + 7200
    trigger, wait, why = relay.relay_plan(
        state(latest=now-100), "schedule", now, latest_dispatch_at=now-300)
    assert trigger is False
    assert wait == 0
    assert "active" in why


def test_cron_rescues_when_chain_is_missing_for_half_an_hour():
    now = T0 + 7200
    trigger, wait, why = relay.relay_plan(
        state(latest=now-2400), "schedule", now, latest_dispatch_at=now-2500)
    assert trigger is True
    assert wait == 0
    assert why == "dispatch-next-paper-tick"


def test_original_seven_day_deadline_is_immutable():
    trigger, _, why = relay.relay_plan(state(deadline=T0+2*604800), "workflow_dispatch", T0+5000)
    assert trigger is False
    assert why == "unexpected-deadline-immutable-clock"


def test_finished_contest_never_dispatches():
    trigger, wait, why = relay.relay_plan(
        state(finished=True), "workflow_dispatch", T0+7000)
    assert trigger is False
    assert wait == 0
    assert why == "tournament-finished"


def test_uninitialized_or_invalid_state_fails_closed():
    for bad in (
        {"status": "NOT_STARTED", "meta": {}},
        {"status": "LIVE", "meta": None},
        {"status": "LIVE", "meta": {"started_at": T0}},
    ):
        trigger, _, _ = relay.relay_plan(bad, "workflow_dispatch", T0)
        assert trigger is False


def test_relay_does_not_run_for_unrecognized_event_types():
    trigger, _, _ = relay.relay_plan(state(), "workflow_run", T0 + 3700)
    assert trigger is False


def test_date_parsing_supports_github_utc_format():
    assert abs(relay.as_epoch("2026-11-17T00:03:51+00:00") - 1794873831) < 0.1
    assert relay.as_epoch("not-a-date") is None
