import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app import app as flask_app
import db_internal


@pytest.fixture
def app():
    """App instance with test database."""
    # Use a temp DB for tests
    original_path = os.environ.get("DB_PATH", ".colectivo_fg.db")
    test_db = os.path.join(os.path.dirname(__file__), "test_fg.db")
    os.environ["DB_PATH"] = test_db
    
    if os.path.exists(test_db):
        os.remove(test_db)
    
    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test-secret"
    
    yield flask_app
    
    os.environ["DB_PATH"] = original_path
    if os.path.exists(test_db):
        os.remove(test_db)


@pytest.fixture
def client(app):
    """Test client with session."""
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess["user"] = "admin"
        yield c


@pytest.fixture
def anon_client(app):
    """Test client without auth."""
    with app.test_client() as c:
        yield c


@pytest.fixture
def data(app):
    """Clean test data."""
    return db_internal.load_data()
