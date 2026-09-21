import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = "Create a consistent SQLite backup and prune older managed backups."

    def add_arguments(self, parser):
        parser.add_argument(
            "--directory",
            type=Path,
            default=settings.SQLITE_BACKUP_DIR,
            help="Backup directory (defaults to BLITZ_FUT_BACKUP_DIR).",
        )
        parser.add_argument(
            "--retain",
            type=int,
            default=7,
            help="Number of managed backups to retain (default: 7).",
        )

    def handle(self, *args, **options):
        if connection.vendor != "sqlite":
            raise CommandError("backup_sqlite supports only SQLite databases.")
        retain = options["retain"]
        if retain < 1:
            raise CommandError("--retain must be at least 1.")

        directory: Path = options["directory"].expanduser().resolve()
        directory.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        destination = directory / f"blitz-fut-{timestamp}.sqlite3"
        temporary = directory / f".{destination.name}.tmp"

        connection.ensure_connection()
        source = connection.connection
        if not isinstance(source, sqlite3.Connection):
            raise CommandError("The active database connection is not SQLite.")
        try:
            with sqlite3.connect(temporary) as target:
                source.backup(target)
                result = target.execute("PRAGMA quick_check").fetchone()
                if result != ("ok",):
                    raise CommandError("SQLite integrity check failed for the new backup.")
            os.chmod(temporary, 0o600)
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)

        backups = sorted(
            directory.glob("blitz-fut-*.sqlite3"),
            key=lambda path: path.name,
            reverse=True,
        )
        for old_backup in backups[retain:]:
            old_backup.unlink()

        self.stdout.write(self.style.SUCCESS(str(destination)))
