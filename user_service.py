from fastapi import FastAPI, HTTPException
from utility import get_connection, DB_SCHEMA
from schemas import UserRegister, UserLogin, UserOut
import logging

app = FastAPI(
    title="UserService API",
    description="",
    version="1.0.0",
)

logger = logging.getLogger("user_service")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

S = DB_SCHEMA


@app.get("/health")
def health():
    return {"status": "ok"}


# ── POST /user/register ───────────────────────────────────────────────────────

@app.post("/user/register", response_model=UserOut, status_code=201)
def register(payload: UserRegister):
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            f"SELECT Id FROM [{S}].[User] WHERE Username = ? OR Email = ?",
            payload.username, payload.email
        )
        if cursor.fetchone():
            exc = HTTPException(status_code=409, detail="Username or email already exists")
            logger.error("Failed: %s", exc)
            raise exc

        cursor.execute(
            f"""
            INSERT INTO [{S}].[User] (Username, Email, Password)
            OUTPUT INSERTED.Id, INSERTED.Username, INSERTED.Email
            VALUES (?, ?, ?)
            """,
            payload.username, payload.email, payload.password
        )
        row = cursor.fetchone()
        conn.commit()

    logger.info("User registered id=%s", row[0])
    return UserOut(id=row[0], username=row[1], email=row[2])


# ── POST /user/login ──────────────────────────────────────────────────────────

@app.post("/user/login")
def login(payload: UserLogin):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT Id, Username, Email FROM [{S}].[User] WHERE Username = ? AND Password = ?",
            payload.username, payload.password
        )
        row = cursor.fetchone()

    if not row:
        exc = HTTPException(status_code=401, detail="Invalid credentials")
        logger.error("Failed: %s", exc)
        raise exc

    logger.info("User authorised id=%s", row[0])
    return {"message": "Login successful", "user": UserOut(id=row[0], username=row[1], email=row[2])}


# ── GET /user/{username} ──────────────────────────────────────────────────────

@app.get("/user/{username}", response_model=UserOut)
def get_user_by_username(username: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT Id, Username, Email FROM [{S}].[User] WHERE Username = ?",
            username
        )
        row = cursor.fetchone()

    if not row:
        exc = HTTPException(status_code=404, detail="User not found")
        logger.error("Failed: %s", exc)
        raise exc

    logger.info("User with username %s found id=%s", username, row[0])
    return UserOut(id=row[0], username=row[1], email=row[2])


# ── GET /user/id/{id} ─────────────────────────────────────────────────────────

@app.get("/user/id/{id}", response_model=UserOut)
def get_user_by_id(id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT Id, Username, Email FROM [{S}].[User] WHERE Id = ?",
            id
        )
        row = cursor.fetchone()

    if not row:
        exc = HTTPException(status_code=404, detail="User not found")
        logger.error("Failed: %s", exc)
        raise exc

    logger.info("User with id %s found", id)
    return UserOut(id=row[0], username=row[1], email=row[2])