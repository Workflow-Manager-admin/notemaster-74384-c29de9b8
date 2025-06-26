from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import uuid

# For brevity, in-memory "database". Production should use persistent storage!
fake_users_db = {}
fake_notes_db = {}  # {username: [notes]}

# JWT settings (these should be in environment variables)
SECRET_KEY = "NOT_REALLY_SECRET_CHANGE_ME"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Password context for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 (password flow)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

app = FastAPI(
    title="Notes Backend API",
    description="A FastAPI backend for managing notes and user authentication.",
    version="1.0.0",
    openapi_tags=[
        {"name": "Authentication", "description": "Endpoints for user registration and login."},
        {"name": "Notes", "description": "Endpoints for CRUD operations on notes."}
    ]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- Models -----------------


class UserCreate(BaseModel):
    username: str = Field(
        ...,
        min_length=3,
        max_length=32,
        description="Unique username for the user"
    )
    password: str = Field(
        ...,
        min_length=6,
        description="Password for the user (min 6 chars)"
    )


class UserOut(BaseModel):
    username: str


class Token(BaseModel):
    access_token: str
    token_type: str


class NoteBase(BaseModel):
    title: str = Field(
        ...,
        max_length=100,
        description="Title of the note"
    )
    content: str = Field(
        ...,
        description="Content of the note"
    )


class NoteCreate(NoteBase):
    pass


class NoteUpdate(BaseModel):
    title: Optional[str] = Field(
        None,
        max_length=100,
        description="Updated title of the note"
    )
    content: Optional[str] = Field(
        None,
        description="Updated content of the note"
    )


class Note(NoteBase):
    id: str
    created_at: datetime
    updated_at: datetime


# --------- Password and Token Helpers ---------


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_user(username: str):
    user = fake_users_db.get(username)
    if user:
        return {"username": username, "hashed_password": user["hashed_password"]}
    return None


def authenticate_user(username: str, password: str):
    user = get_user(username)
    if not user:
        return False
    if not verify_password(password, user["hashed_password"]):
        return False
    return user


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(username)
    if user is None:
        raise credentials_exception
    return user


# ----------------- Authentication Routes -----------------

# PUBLIC_INTERFACE
@app.post(
    "/auth/register",
    response_model=UserOut,
    tags=["Authentication"],
    summary="Register a new user"
)
def register(user: UserCreate):
    """
    Register a new user with username and password.
    - **username**: unique string identifier (min 3, max 32 chars)
    - **password**: password (min 6 chars)
    """
    if user.username in fake_users_db:
        raise HTTPException(
            status_code=400,
            detail="Username already registered."
        )
    hashed_password = get_password_hash(user.password)
    fake_users_db[user.username] = {
        "hashed_password": hashed_password,
    }
    # Each user gets an empty notes list
    fake_notes_db[user.username] = []
    return {"username": user.username}


# PUBLIC_INTERFACE
@app.post(
    "/auth/token",
    response_model=Token,
    tags=["Authentication"],
    summary="Login and get access token"
)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Log in as an existing user and receive an access token.
    - Uses OAuth2 password flow (`username` and `password` form fields).
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password."
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]},
        expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


# ----------------- Notes CRUD Endpoints -----------------
# All notes are bound to a user and require authentication

# PUBLIC_INTERFACE
@app.post(
    "/notes",
    response_model=Note,
    status_code=201,
    tags=["Notes"],
    summary="Create a new note"
)
def create_note(note: NoteCreate, current_user: dict = Depends(get_current_user)):
    """
    Create a new note for the authenticated user.
    """
    note_id = str(uuid.uuid4())
    now = datetime.utcnow()
    note_obj = {
        "id": note_id,
        "title": note.title,
        "content": note.content,
        "created_at": now,
        "updated_at": now,
    }
    fake_notes_db[current_user["username"]].append(note_obj)
    return note_obj


# PUBLIC_INTERFACE
@app.get(
    "/notes",
    response_model=List[Note],
    tags=["Notes"],
    summary="List all user notes"
)
def list_notes(current_user: dict = Depends(get_current_user)):
    """
    List all notes for the authenticated user, ordered by created_at descending.
    """
    notes = fake_notes_db.get(current_user["username"], [])
    return sorted(notes, key=lambda n: n["created_at"], reverse=True)


# PUBLIC_INTERFACE
@app.get(
    "/notes/{note_id}",
    response_model=Note,
    tags=["Notes"],
    summary="Get a note by ID"
)
def get_note(note_id: str, current_user: dict = Depends(get_current_user)):
    """
    Retrieve a note by its ID for the authenticated user.
    """
    notes = fake_notes_db.get(current_user["username"], [])
    for n in notes:
        if n["id"] == note_id:
            return n
    raise HTTPException(
        status_code=404,
        detail="Note not found."
    )


# PUBLIC_INTERFACE
@app.put(
    "/notes/{note_id}",
    response_model=Note,
    tags=["Notes"],
    summary="Update a note by ID"
)
def update_note(
    note_id: str,
    note_update: NoteUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update an existing note's title or content.
    """
    notes = fake_notes_db.get(current_user["username"], [])
    for n in notes:
        if n["id"] == note_id:
            if note_update.title is not None:
                n["title"] = note_update.title
            if note_update.content is not None:
                n["content"] = note_update.content
            n["updated_at"] = datetime.utcnow()
            return n
    raise HTTPException(
        status_code=404,
        detail="Note not found."
    )


# PUBLIC_INTERFACE
@app.delete(
    "/notes/{note_id}",
    status_code=204,
    tags=["Notes"],
    summary="Delete a note by ID"
)
def delete_note(note_id: str, current_user: dict = Depends(get_current_user)):
    """
    Delete a note by its ID.
    """
    notes = fake_notes_db.get(current_user["username"], [])
    for i, n in enumerate(notes):
        if n["id"] == note_id:
            del notes[i]
            return
    raise HTTPException(
        status_code=404,
        detail="Note not found."
    )


# Health check endpoint - unchanged
@app.get("/", summary="Health check")
def health_check():
    """Check service health."""
    return {"message": "Healthy"}


# Info/help endpoint for WebSocket (no WebSocket endpoint in this basic impl)
@app.get(
    "/docs/websocket",
    tags=["Authentication", "Notes"],
    summary="WebSocket API usage note"
)
def websocket_info():
    """
    **No WebSocket API in this backend.**
    All endpoints use RESTful HTTP via FastAPI.
    """
    return {
        "message": (
            "This backend uses only RESTful HTTP endpoints. No WebSocket API provided."
        )
    }

