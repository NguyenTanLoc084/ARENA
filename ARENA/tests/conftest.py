import shutil
import pytest
from app import create_app
from app.seed import seed_demo


@pytest.fixture(scope="session")
def template_db(tmp_path_factory):
    path = tmp_path_factory.mktemp("seed") / "seed.sqlite3"
    app = create_app(
        {"TESTING": True, "DATABASE": str(path), "SECRET_KEY": "test-only"}
    )
    with app.app_context():
        seed_demo()
    return path


@pytest.fixture
def app(template_db, tmp_path):
    path = tmp_path / "test.sqlite3"
    shutil.copy2(template_db, path)
    return create_app(
        {"TESTING": True, "DATABASE": str(path), "SECRET_KEY": "test-only"}
    )


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def login(client):
    def do(uid=2):
        with client.session_transaction() as s:
            s["uid"] = uid
            s["csrf"] = "test-token"
        return {"csrf": "test-token"}

    return do
