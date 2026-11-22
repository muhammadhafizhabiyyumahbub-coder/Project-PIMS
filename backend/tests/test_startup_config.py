import logging
import pytest
import os
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

logger = logging.getLogger(__name__)

def test_run_migrations_no_alembic_ini():
    """Verify run_migrations doesn't crash when alembic.ini is missing."""
    with patch("os.path.exists", return_value=False):
        from app.main import run_migrations
        # Should not raise exception
        run_migrations()

def test_app_startup_no_crash():
    """Verify application starts even if migrations are skipped."""
    with patch("app.main.run_migrations"):
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200

def test_run_migrations_with_alembic_ini(tmp_path):
    """Verify migrations use absolute paths."""
    alembic_ini = tmp_path / "alembic.ini"
    alembic_ini.write_text("[alembic]\nscript_location = app/database/migrations")
    
    with patch("os.environ.get", return_value=str(alembic_ini)):
        from app.main import run_migrations
        with patch("alembic.command.upgrade") as mock_upgrade:
            run_migrations()
            mock_upgrade.assert_called_once()
            args, _ = mock_upgrade.call_args
            config = args[0]
            assert Path(config.get_main_option("script_location")).is_absolute()
