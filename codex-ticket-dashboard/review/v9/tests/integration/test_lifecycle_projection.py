from pathlib import Path

from codex_ticket_dashboard.ingest.collector import Collector
from codex_ticket_dashboard.storage.database import Database
from codex_ticket_dashboard.storage.models import DatabaseConfig
from codex_ticket_dashboard.storage.path_security import initialize_data_root
from codex_ticket_dashboard.storage.spool import SpoolWriter


def fixture(root: Path) -> tuple[Database, Collector, SpoolWriter]:
    paths = initialize_data_root(root)
    database = Database(DatabaseConfig(paths.data / "dashboard.sqlite3"))
    database.migrate()
    return database, Collector(database, paths), SpoolWriter(paths)
