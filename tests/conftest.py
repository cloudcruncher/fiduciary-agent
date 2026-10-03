import pytest

import fiduciary.config as config
import fiduciary.storage.db as db


@pytest.fixture(autouse=True, scope="session")
def isolate_test_database(tmp_path_factory):
    temp_dir = tmp_path_factory.mktemp("test_db")
    test_db_path = temp_dir / "test_financial.db"

    # Switch active DB path for tests to temporary isolated database
    orig_path = config.DB_PATH
    config.DB_PATH = test_db_path
    db.init_db()

    yield test_db_path

    config.DB_PATH = orig_path
