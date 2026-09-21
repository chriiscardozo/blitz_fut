import sqlite3

import pytest
from django.core.management import call_command


@pytest.mark.django_db(transaction=True)
def test_backup_command_creates_valid_sqlite_copy_and_prunes(tmp_path):
    for index in range(3):
        call_command("backup_sqlite", directory=tmp_path, retain=2, verbosity=0)

    backups = sorted(tmp_path.glob("blitz-fut-*.sqlite3"))
    assert len(backups) == 2
    with sqlite3.connect(backups[-1]) as backup:
        assert backup.execute("PRAGMA quick_check").fetchone() == ("ok",)
        assert backup.execute(
            "SELECT 1 FROM sqlite_master "
            "WHERE type = 'table' AND name = 'django_migrations'"
        ).fetchone() == (1,)
    assert backups[-1].stat().st_mode & 0o077 == 0
