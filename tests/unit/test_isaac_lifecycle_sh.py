"""Offline tests for scripts/vm/isaac_lifecycle.sh (fc_launch's Option B tail
and stop-flag wait), driven with stand-in processes instead of Isaac."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "scripts" / "vm" / "isaac_lifecycle.sh"


def run_bash(body: str, timeout: float = 30.0) -> str:
    """Source the helper library, run `body`, and return its stdout."""
    completed = subprocess.run(
        ["bash", "-c", f'. "{LIB}"\n{body}'],
        capture_output=True, text=True, check=False, timeout=timeout,
    )
    assert completed.returncode == 0, completed.stderr
    return completed.stdout.strip()


def test_pid_alive_true_for_a_running_process():
    out = run_bash("sleep 5 & p=$!; isaac_pid_alive $p && echo alive; kill $p")
    assert out == "alive"


def test_pid_alive_false_once_the_process_exited_even_unreaped():
    # The child is never `wait`ed for, so it may still be a zombie here.
    out = run_bash("sleep 0.2 & p=$!; sleep 1; isaac_pid_alive $p && echo alive || echo gone")
    assert out == "gone"


def test_pid_alive_false_for_an_empty_or_unknown_pid():
    out = run_bash(
        'isaac_pid_alive "" && echo a || echo b; isaac_pid_alive 999999 && echo a || echo b'
    )
    assert out.split() == ["b", "b"]


def test_wait_returns_0_after_the_grace_when_isaac_exits():
    out = run_bash(
        "sleep 30 & tail_pid=$!; sleep 1 & isaac=$!\n"
        "isaac_wait_exit_or_cap $isaac $tail_pid 20 0.2 1; rc=$?\n"
        'echo "$rc $ISAAC_WAIT_ELAPSED_SEC ${ISAAC_EXITED_AT:+set}"; kill $tail_pid'
    )
    rc, elapsed, exited_at = out.split()
    assert rc == "0"
    assert 1 <= int(elapsed) <= 4
    assert exited_at == "set"


def test_wait_returns_1_at_the_cap_while_isaac_runs():
    out = run_bash(
        "sleep 30 & tail_pid=$!; sleep 30 & isaac=$!\n"
        "isaac_wait_exit_or_cap $isaac $tail_pid 2 0.2 1; rc=$?\n"
        'echo "$rc $ISAAC_WAIT_ELAPSED_SEC"; kill $tail_pid $isaac'
    )
    rc, elapsed = out.split()
    assert rc == "1"
    assert 2 <= int(elapsed) <= 4


def test_wait_returns_2_when_the_tail_ends_first():
    out = run_bash(
        "sleep 1 & tail_pid=$!; sleep 30 & isaac=$!\n"
        "isaac_wait_exit_or_cap $isaac $tail_pid 20 0.2 1; rc=$?\n"
        'echo "$rc"; kill $isaac'
    )
    assert out == "2"


def test_wait_without_an_isaac_pid_falls_back_to_the_cap():
    out = run_bash(
        "sleep 30 & tail_pid=$!\n"
        'isaac_wait_exit_or_cap "" $tail_pid 1 0.2 1; rc=$?\n'
        'echo "$rc"; kill $tail_pid'
    )
    assert out == "1"


def test_stop_flag_stops_a_sigterm_ignoring_stand_in(tmp_path):
    # Stand-in for Kit: swallows SIGTERM, leaves its loop only on the flag.
    flag = tmp_path / "isaac.stop"
    out = run_bash(
        f"bash -c 'trap \"\" TERM; while [ ! -e \"{flag}\" ]; do sleep 0.1; done' & p=$!\n"
        "sleep 0.5; kill -TERM $p; sleep 0.5\n"
        "isaac_pid_alive $p && echo survived_term || echo died_on_term\n"
        f'touch "{flag}"\n'
        "isaac_wait_pid_exit $p 10 0.2; rc=$?\n"
        'echo "$rc $ISAAC_WAIT_ELAPSED_SEC"'
    )
    first, last = out.splitlines()
    rc, elapsed = last.split()
    assert first == "survived_term"
    assert rc == "0"
    assert int(elapsed) <= 2


def test_wait_pid_exit_returns_1_when_the_process_outlives_the_wait():
    out = run_bash("sleep 30 & p=$!; isaac_wait_pid_exit $p 1 0.2; echo $?; kill $p")
    assert out == "1"
