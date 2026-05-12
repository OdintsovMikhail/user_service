"""
Tests for user_service.py

Strategy: mock `get_connection` in both `user_service` and `resolvers` so no
real SQL Server is needed. We also stub `pyodbc` and `dotenv` in sys.modules
before the app imports them so native drivers are not required on the test machine.

Run with (from the project root):
    pip install fastapi httpx pytest email-validator strawberry-graphql[fastapi]
    pytest test_user_service.py -v
"""

import sys
import types
from unittest.mock import MagicMock, patch
import pytest

# ---------------------------------------------------------------------------
# Stub pyodbc so the native ODBC driver is not required on the test machine
# ---------------------------------------------------------------------------
_pyodbc_stub = types.ModuleType("pyodbc")
_pyodbc_stub.connect = MagicMock()
_pyodbc_stub.Connection = MagicMock
sys.modules.setdefault("pyodbc", _pyodbc_stub)

# Stub python-dotenv so no .env file is required
_dotenv_stub = types.ModuleType("dotenv")
_dotenv_stub.load_dotenv = lambda *a, **kw: None
sys.modules.setdefault("dotenv", _dotenv_stub)

from fastapi.testclient import TestClient  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cursor(fetchone_return=None):
    cursor = MagicMock()
    cursor.fetchone.return_value = fetchone_return
    return cursor


def _make_conn(cursor):
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cursor
    return conn


GQL_USER_BY_ID = """
    query GetUserById($id: Int!) {
        userById(id: $id) {
            id
            username
            email
        }
    }
"""

GQL_USER_BY_USERNAME = """
    query GetUserByUsername($username: String!) {
        userByUsername(username: $username) {
            id
            username
            email
        }
    }
"""


# ---------------------------------------------------------------------------
# Fixture: a fresh TestClient with get_connection patched in both modules
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    with patch("user_service.get_connection") as mock_rest, \
         patch("resolvers.get_connection") as mock_gql:
        import user_service as us
        tc = TestClient(us.app, raise_server_exceptions=False)
        tc._mock_rest_conn = mock_rest
        tc._mock_gql_conn = mock_gql
        yield tc


# ---------------------------------------------------------------------------
# POST /user/register
# ---------------------------------------------------------------------------

class TestRegister:

    def test_register_success(self, client):
        cursor = _make_cursor()
        cursor.fetchone.side_effect = [
            None,                                       # no duplicate found
            (42, "alice", "alice@example.com"),         # INSERT OUTPUT row
        ]
        client._mock_rest_conn.return_value = _make_conn(cursor)

        resp = client.post("/user/register", json={
            "username": "alice",
            "email": "alice@example.com",
            "password": "secret123",
        })

        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == 42
        assert data["username"] == "alice"
        assert data["email"] == "alice@example.com"

    def test_register_duplicate_returns_409(self, client):
        cursor = _make_cursor(fetchone_return=(1,))     # existing user found
        client._mock_rest_conn.return_value = _make_conn(cursor)

        resp = client.post("/user/register", json={
            "username": "alice",
            "email": "alice@example.com",
            "password": "secret123",
        })

        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"]

    def test_register_invalid_email_returns_422(self, client):
        resp = client.post("/user/register", json={
            "username": "bob",
            "email": "not-an-email",
            "password": "pass",
        })
        assert resp.status_code == 422

    def test_register_missing_required_field_returns_422(self, client):
        resp = client.post("/user/register", json={"username": "bob"})
        assert resp.status_code == 422

    def test_register_commits_transaction(self, client):
        cursor = _make_cursor()
        cursor.fetchone.side_effect = [
            None,
            (1, "charlie", "c@example.com"),
        ]
        conn = _make_conn(cursor)
        client._mock_rest_conn.return_value = conn

        client.post("/user/register", json={
            "username": "charlie",
            "email": "c@example.com",
            "password": "pw",
        })

        conn.commit.assert_called_once()

    def test_register_checks_both_username_and_email_for_duplicates(self, client):
        cursor = _make_cursor()
        cursor.fetchone.side_effect = [
            None,
            (99, "dave", "dave@example.com"),
        ]
        client._mock_rest_conn.return_value = _make_conn(cursor)

        client.post("/user/register", json={
            "username": "dave",
            "email": "dave@example.com",
            "password": "pw",
        })

        sql = cursor.execute.call_args_list[0][0][0]
        assert "Username" in sql
        assert "Email" in sql


# ---------------------------------------------------------------------------
# POST /user/login
# ---------------------------------------------------------------------------

class TestLogin:

    def test_login_success(self, client):
        cursor = _make_cursor(fetchone_return=(7, "bob", "bob@example.com"))
        client._mock_rest_conn.return_value = _make_conn(cursor)

        resp = client.post("/user/login", json={
            "username": "bob",
            "password": "correctpass",
        })

        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Login successful"
        assert data["user"]["id"] == 7
        assert data["user"]["username"] == "bob"
        assert data["user"]["email"] == "bob@example.com"

    def test_login_wrong_credentials_returns_401(self, client):
        cursor = _make_cursor(fetchone_return=None)
        client._mock_rest_conn.return_value = _make_conn(cursor)

        resp = client.post("/user/login", json={
            "username": "bob",
            "password": "wrongpass",
        })

        assert resp.status_code == 401
        assert "Invalid credentials" in resp.json()["detail"]

    def test_login_missing_password_returns_422(self, client):
        resp = client.post("/user/login", json={"username": "bob"})
        assert resp.status_code == 422

    def test_login_missing_username_returns_422(self, client):
        resp = client.post("/user/login", json={"password": "pw"})
        assert resp.status_code == 422

    def test_login_queries_username_and_password(self, client):
        cursor = _make_cursor(fetchone_return=(1, "u", "u@e.com"))
        client._mock_rest_conn.return_value = _make_conn(cursor)

        client.post("/user/login", json={"username": "u", "password": "p"})

        sql = cursor.execute.call_args[0][0]
        assert "Username" in sql
        assert "Password" in sql