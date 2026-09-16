from isaac.vgu_sim.cmd_vel_watchdog import (
    SafetyHoldState,
    parse_holds,
    watchdog_velocity,
)

TIMEOUT = 0.5


def test_no_command_yet_is_zero():
    assert watchdog_velocity(None, (0.2, 0.1), TIMEOUT) == (0.0, 0.0)


def test_fresh_command_passes_through():
    assert watchdog_velocity(0.1, (0.2, 0.1), TIMEOUT) == (0.2, 0.1)


def test_stale_command_is_zeroed():
    assert watchdog_velocity(0.6, (0.2, 0.1), TIMEOUT) == (0.0, 0.0)


def test_exactly_at_timeout_still_passes():
    # stale only when strictly older than the timeout
    assert watchdog_velocity(0.5, (0.2, 0.1), TIMEOUT) == (0.2, 0.1)


def test_held_robot_relays_zero_twist_despite_nonzero_command():
    holds = SafetyHoldState()
    holds.set_held({"robot_1"})
    assert watchdog_velocity(0.0, (0.2, 0.1), TIMEOUT, holds.is_held("robot_1")) == (0.0, 0.0)


def test_release_restores_relay():
    holds = SafetyHoldState()
    holds.set_held({"robot_1"})
    holds.set_held(set())
    assert watchdog_velocity(0.1, (0.2, 0.1), TIMEOUT, holds.is_held("robot_1")) == (0.2, 0.1)


def test_hold_only_affects_listed_robot():
    holds = SafetyHoldState()
    holds.set_held({"robot_1"})
    assert holds.is_held("robot_1") is True
    assert holds.is_held("robot_2") is False
    assert watchdog_velocity(0.1, (0.2, 0.1), TIMEOUT, holds.is_held("robot_2")) == (0.2, 0.1)


def test_set_held_reports_transitions_once():
    holds = SafetyHoldState()
    assert holds.set_held({"robot_1"}) == ({"robot_1"}, set())
    # A repeated message is not a transition, so the node logs nothing again.
    assert holds.set_held({"robot_1"}) == (set(), set())
    assert holds.set_held({"robot_2"}) == ({"robot_2"}, {"robot_1"})


def test_parse_holds_accepts_valid_payload():
    assert parse_holds('{"held": ["robot_1", "robot_2"]}') == ({"robot_1", "robot_2"}, True)


def test_parse_holds_accepts_empty_payload():
    assert parse_holds('{"held": []}') == (set(), True)


def test_parse_holds_rejects_malformed_payload_without_raising():
    # ok=False means the caller must keep its previous hold set, never apply
    # this empty one: a corrupt message must not release a safety stop.
    for payload in ('{"held": ', "null", "[]", '{"held": "robot_1"}', '{"held": [1]}',
                    '{"held": [""]}'):
        assert parse_holds(payload) == (set(), False)


def test_hold_does_not_reset_silence_timeout_semantics():
    holds = SafetyHoldState()
    holds.set_held({"robot_1"})
    # Released with a fresh command: relays it immediately.
    holds.set_held(set())
    assert watchdog_velocity(0.2, (0.15, 0.0), TIMEOUT, holds.is_held("robot_1")) == (0.15, 0.0)
    # Released with a stale last command: still zeroed by the timeout rule.
    holds.set_held({"robot_1"})
    holds.set_held(set())
    assert watchdog_velocity(1.0, (0.15, 0.0), TIMEOUT, holds.is_held("robot_1")) == (0.0, 0.0)
