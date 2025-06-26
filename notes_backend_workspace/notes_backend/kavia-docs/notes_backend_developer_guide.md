# Notes Backend Developer Guide

## Table of Contents

- [Overview](#overview)
- [Architecture Overview](#architecture-overview)
- [Setup and Requirements](#setup-and-requirements)
- [Models](#models)
- [Authentication Mechanism](#authentication-mechanism)
- [REST API Endpoints](#rest-api-endpoints)
    - [Authentication Endpoints](#authentication-endpoints)
    - [Notes Endpoints](#notes-endpoints)
    - [Health and Info Endpoints](#health-and-info-endpoints)
- [OpenAPI/Swagger Documentation](#openapiswapper-documentation)
- [Implementation Details](#implementation-details)
- [Mermaid: High-Level Architecture](#mermaid-high-level-architecture)

---

## Overview

The `notes_backend` service provides a RESTful API for creating, editing, and managing text notes, along with user registration and authentication. It's built with FastAPI and uses Pydantic models. All user and notes data are stored in in-memory Python dictionaries for demonstration; production systems should use persistent storage.

## Architecture Overview

- **Framework:** FastAPI
- **Storage:** In-memory dictionaries (`fake_users_db`, `fake_notes_db`) for users and notes. (Replaceable with a real database.)
- **Authentication:** OAuth2 "password" flow, JWT tokens, hashed passwords
- **API Style:** RESTful, organized into `/auth` and `/notes` endpoints
- **OpenAPI:** Auto-generated docs via FastAPI

### Main Components

- **main.py**: Defines all routes, models, authentication helpers, and configures FastAPI.
- **requirements.txt**: All required dependencies for the backend.

## Setup and Requirements

1. **Python version:** 3.8+
2. **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3. **Run the server:**
    ```bash
    uvicorn src.api.main:app --reload
    ```
4. By default, API documentation will be available at `/docs`.

#### Key dependencies:
- fastapi
- uvicorn
- pydantic
- python-jose[cryptography]
- passlib[bcrypt]
- python-multipart

See `requirements.txt` for the full list.

## Models

### User Models

- **UserCreate**
    - `username: str` — Unique, min 3, max 32 chars
    - `password: str` — Min 6 chars

- **UserOut**
    - `username: str`

- **Token**
    - `access_token: str`
    - `token_type: str`

### Note Models

- **NoteBase**
    - `title: str` — Required, max 100 chars
    - `content: str` — Required

- **NoteCreate**
    - Inherits from `NoteBase`

- **NoteUpdate**
    - `title: Optional[str]`
    - `content: Optional[str]`

- **Note**
    - Inherits from `NoteBase`
    - `id: str`
    - `created_at: datetime`
    - `updated_at: datetime`

## Authentication Mechanism

- **Registration:** `POST /auth/register`
    - Stores hashed passwords (bcrypt via passlib)
    - Unique usernames

- **Login:** `POST /auth/token`
    - Password verified and JWT "access_token" issued

- **JWT Details:**
    - **Algorithm:** HS256
    - **Claims:** `"sub": username`, `"exp": expiration time`
    - **Config:** `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES` (change in production!)
    - Users must include `Authorization: Bearer <token>` for endpoints requiring authentication.

- **Password Hashing:** Uses passlib/bcrypt for secure password storage/verification.

## REST API Endpoints

### Authentication Endpoints

- **POST `/auth/register`**
    - Request: `{ "username": str, "password": str }`
    - Response: `{ "username": str }`
    - Errors: Username already registered

- **POST `/auth/token`**
    - OAuth2 password flow ("username" & "password" form fields)
    - Response: `{ "access_token": str, "token_type": "bearer" }`
    - Errors: Incorrect username/password

### Notes Endpoints

All `/notes` endpoints require JWT Bearer authentication.

- **POST `/notes`**  
    Create a new note  
    - Request: `{ "title": str, "content": str }`
    - Response: Note object (with id, created_at, updated_at)

- **GET `/notes`**  
    List all user's notes (desc: most recent first)  
    - Response: Array of Note objects

- **GET `/notes/{note_id}`**  
    Fetch a note by id  
    - Response: Note object  
    - 404 if not found

- **PUT `/notes/{note_id}`**  
    Update note fields  
    - Request: `{ "title": Optional[str], "content": Optional[str] }`
    - Response: Updated Note object  
    - 404 if not found

- **DELETE `/notes/{note_id}`**  
    Delete a note  
    - Response: (204 No Content)
    - 404 if not found

### Health and Info Endpoints

- **GET `/`**
    - Health check: `{ "message": "Healthy" }`

- **GET `/docs/websocket`**
    - Returns a message clarifying that no WebSocket API is available (RESTful only).

## OpenAPI/Swagger Documentation

FastAPI automatically generates OpenAPI docs.
- **Swagger UI:**  
  Visit `/docs` for the interactive API explorer and testing.
- **OpenAPI JSON spec:**  
  Visit `/openapi.json` for the machine-readable API spec.
- Tag structure in OpenAPI is:
    - *Authentication* — all registration and login endpoints
    - *Notes* — all CRUD endpoints on notes

## Implementation Details

- **CORS:** Configured to allow all origins (`*`) for demo purposes. Change this setting for production!
- **Persistence:** Currently, in-memory only (`fake_users_db`, `fake_notes_db`). Replace with a database in real deployments.
- **Security:** JWT secret, access token expiry, and CORS settings must be set using environment variables, not hardcoded.
- **Password Security:** Always hashes passwords with bcrypt.

## Mermaid: High-Level Architecture

```mermaid
flowchart TD
    subgraph Client
        A[User] 
    end
    subgraph Backend
        B[FastAPI App<br/>main.py]
        C[In-memory DB<br/>(fake_users_db, fake_notes_db)]
        D[Authentication<br/>(JWT/OAuth2)]
    end

    A -- HTTP(S) requests --> B
    B -- stores/reads --> C
    B -- verifies auth --> D
    D -- user context --> B
    B -- serves OpenAPI docs --> E[/Swagger UI/]
```

---

## Further Recommendations

- Replace in-memory storage with a persistent database.
- Store `SECRET_KEY` and sensitive config as environment variables.
- Restrict CORS allowed origins.
- Add rate-limiting and account lockout as security enhancements.

---

*This documentation was auto-generated to help developers quickly understand the notes_backend structure, API, and best practices for customizing or deploying the service.*
