from fastapi import FastAPI, HTTPException
from utility import get_connection
from schemas import UserRegister, UserLogin, UserOut

app = FastAPI(
    title="BookService API",
    description="",
    version="1.0.0",
)

# ── POST /api/user/register ───────────────────────────────────────────────────

@app.post("/user/register", response_model=UserOut, status_code=201)
def register(payload: UserRegister):
    with get_connection() as conn:
        cursor = conn.cursor()

        # Check duplicate username / email
        cursor.execute(
            "SELECT Id FROM dbo.[User] WHERE Username = ? OR Email = ?",
            payload.username, payload.email
        )
        if cursor.fetchone():
            raise HTTPException(status_code=409, detail="Username or email already exists")

        cursor.execute(
            """
            INSERT INTO dbo.[User] (Username, Email, Password)
            OUTPUT INSERTED.Id, INSERTED.Username, INSERTED.Email
            VALUES (?, ?, ?)
            """,
            payload.username, payload.email, payload.password   # hash in production!
        )
        row = cursor.fetchone()
        conn.commit()

    return UserOut(id=row[0], username=row[1], email=row[2])


# ── POST /api/user/login ──────────────────────────────────────────────────────

@app.post("/user/login")
def login(payload: UserLogin):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT Id, Username, Email FROM dbo.[User] WHERE Username = ? AND Password = ?",
            payload.username, payload.password   # compare hashes in production!
        )
        row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {"message": "Login successful", "user": UserOut(id=row[0], username=row[1], email=row[2])}


# ── GET /api/user/{username} ──────────────────────────────────────────────────

@app.get("/user/{username}", response_model=UserOut)
def get_user(username: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT Id, Username, Email FROM dbo.[User] WHERE Username = ?",
            username
        )
        row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    return UserOut(id=row[0], username=row[1], email=row[2])


# ── GET /api/user/id/{id} ──────────────────────────────────────────────────

@app.get("/user/id/{id}", response_model=UserOut)
def get_user(id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT Id, Username, Email FROM dbo.[User] WHERE Id = ?",
            id
        )
        row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    return UserOut(id=row[0], username=row[1], email=row[2])