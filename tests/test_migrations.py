import subprocess


def test_migration_upgrades_cleanly():
    # Runs against the dev DB; should apply without error and be idempotent on re-run.
    r1 = subprocess.run(["uv", "run", "alembic", "upgrade", "head"], capture_output=True, text=True)
    assert r1.returncode == 0, r1.stderr
    r2 = subprocess.run(["uv", "run", "alembic", "upgrade", "head"], capture_output=True, text=True)
    assert r2.returncode == 0, r2.stderr
