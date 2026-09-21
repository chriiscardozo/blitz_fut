import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = "Restore a verified SQLite backup while the web application is stopped."

    def add_arguments(self, parser):
        parser.add_argument("source", type=Path, help="SQLite backup to restore.")
        parser.add_argument(
            "--confirmed",
            action="store_true",
            help="Confirm that the web application is stopped and restoration is intended.",
        )

    def handle(self, *args, **options):
        if connection.vendor != "sqlite":
            raise CommandError("restore_sqlite supports only SQLite databases.")
        if not options["confirmed"]:
            raise CommandError(
                "Stop the web application, then repeat with --confirmed."
            )

        source_path: Path = options["source"].expanduser().resolve()
        if not source_path.is_file():
            raise CommandError(f"Backup does not exist: {source_path}")
        database_name = settings.DATABASES["default"]["NAME"]
        database_path = Path(database_name).expanduser().resolve()
        if source_path == database_path:
            raise CommandError("The backup and live database paths must differ.")

        try:
            with sqlite3.connect(f"file:{source_path}?mode=ro", uri=True) as source:
                result = source.execute("PRAGMA quick_check").fetchone()
                if result != ("ok",):
                    raise CommandError("The source backup failed SQLite quick_check.")
                migration_table = source.execute(
                    "SELECT 1 FROM sqlite_master "
                    "WHERE type = 'table' AND name = 'django_migrations'"
                ).fetchone()
                if migration_table is None:
                    raise CommandError("The source is not a migrated Blitz Fut database.")

                connection.close()
                database_path.parent.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
                safety_backup = database_path.with_name(
                    f"{database_path.name}.pre-restore-{timestamp}"
                )
                if database_path.exists():
                    with sqlite3.connect(database_path) as live, sqlite3.connect(
                        safety_backup
                    ) as safety:
                        live.backup(safety)
                    os.chmod(safety_backup, 0o600)

                temporary = database_path.with_name(f".{database_path.name}.restore.tmp")
                try:
                    with sqlite3.connect(temporary) as target:
                        source.backup(target)
                    os.chmod(temporary, 0o600)
                    temporary.replace(database_path)
                finally:
                    temporary.unlink(missing_ok=True)
        except sqlite3.DatabaseError as exc:
            raise CommandError(f"SQLite restoration failed: {exc}") from exc

        self.stdout.write(self.style.SUCCESS(f"Restored {database_path}"))
