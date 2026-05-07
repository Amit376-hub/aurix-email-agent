import hashlib
import json
import os
from datetime import datetime
import streamlit as st

_USER_DB = "users.json"

def _load_users() -> dict:
    if os.path.exists(_USER_DB):
        try:
            with open(_USER_DB, "r") as f:
                data = json.load(f)
            # Must be a dict mapping email -> {name, password, ...}
            # If it's a list, string, or any other type, reset it.
            if not isinstance(data, dict):
                raise ValueError("Bad format")
            return data
        except (json.JSONDecodeError, ValueError):
            # Corrupted or wrong-format file — reset it
            _save_users({})
    return {}

def _save_users(users: dict):
    with open(_USER_DB, "w") as f:
        json.dump(users, f, indent=2)

def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def signup(name: str, email: str, password: str) -> tuple:
    """Register a new user. Returns (True, success_msg) or (False, error_msg)."""
    name     = (name or "").strip()
    email    = (email or "").strip().lower()
    password = password or ""

    if not name or not email or not password:
        return False, "All fields are required."
    if len(password) < 8:
        return False, "Password must be at least 8 characters."

    users = _load_users()
    if email in users:
        return False, "An account with this email already exists."

    users[email] = {
        "name": name,
        "password": _hash(password),
        "created_at": datetime.now().isoformat(),
    }
    _save_users(users)
    return True, "Account created successfully!"


def login(email: str, password: str) -> tuple:
    """Authenticate a user. Returns (True, full_name) or (False, error_msg)."""
    email    = (email or "").strip().lower()
    password = password or ""

    if not email or not password:
        return False, "Email and password are required."

    users = _load_users()
    if email not in users:
        return False, "No account found for that email."
    if users[email]["password"] != _hash(password):
        return False, "Incorrect password."

    return True, users[email]["name"]


def logout():
    """Clear authentication from Streamlit session state."""
    for key in ("authenticated", "user_name", "user_email"):
        st.session_state.pop(key, None)


def is_authenticated() -> bool:
    """Return True if the current session is logged in."""
    return bool(st.session_state.get("authenticated", False))