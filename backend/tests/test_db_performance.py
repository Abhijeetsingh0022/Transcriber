"""
Self-check for SQLite performance, pragmas, WAL checkpointing, and vacuuming.
Run directly with python tests/test_db_performance.py.
"""

import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db.database import (
    get_db_connection,
    get_db,
    get_db_stats,
    wal_checkpoint,
    vacuum_db,
    optimize_db,
)


def run_checks():
    print("Testing SQLite connection and pragmas...")
    conn = get_db_connection()
    try:
        # Check foreign keys
        fk = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
        assert fk == 1, f"Expected PRAGMA foreign_keys = 1, got {fk}"

        # Check synchronous
        sync = conn.execute("PRAGMA synchronous;").fetchone()[0]
        assert sync == 1, f"Expected PRAGMA synchronous = 1 (NORMAL), got {sync}"

        # Check busy timeout
        timeout = conn.execute("PRAGMA busy_timeout;").fetchone()[0]
        assert timeout >= 10000, f"Expected PRAGMA busy_timeout >= 10000, got {timeout}"

        # Check journal mode
        jm = conn.execute("PRAGMA journal_mode;").fetchone()[0]
        assert jm.lower() == "wal", f"Expected PRAGMA journal_mode = wal, got {jm}"

        print("  ✓ Pragmas verified (foreign_keys=ON, synchronous=NORMAL, timeout=10s, journal=WAL)")
    finally:
        conn.close()

    print("Testing get_db_stats()...")
    stats = get_db_stats()
    assert stats["status"] == "healthy", f"Expected healthy DB, got {stats['status']}"
    assert stats["db_size_bytes"] > 0, "DB size should be > 0"
    assert "tables" in stats, "Stats should contain table counts"
    assert "jobs" in stats["tables"], "Tables should include jobs"
    print(f"  ✓ Database stats: {stats['db_size_mb']} MB, {len(stats['tables'])} tables, status={stats['status']}")

    print("Testing wal_checkpoint()...")
    ckpt_passive = wal_checkpoint("PASSIVE")
    assert ckpt_passive["status"] in ("ok", "busy"), f"Unexpected checkpoint status: {ckpt_passive}"
    ckpt_truncate = wal_checkpoint("TRUNCATE")
    assert ckpt_truncate["status"] in ("ok", "busy"), f"Unexpected truncate checkpoint status: {ckpt_truncate}"
    print(f"  ✓ WAL Checkpoint succeeded (mode=TRUNCATE, log_frames={ckpt_truncate['log_frames']})")

    print("Testing optimize_db()...")
    opt = optimize_db()
    assert opt["status"] == "ok", f"Expected ok optimize status, got {opt}"
    print("  ✓ PRAGMA optimize executed successfully")

    print("Testing vacuum_db()...")
    vac = vacuum_db(incremental=False)
    assert vac["status"] == "ok", f"Expected ok vacuum status, got {vac}"
    print(f"  ✓ Full VACUUM succeeded, current size: {vac['db_size_mb']} MB")

    print("\nAll SQLite performance and reliability checks PASSED!")


if __name__ == "__main__":
    run_checks()
