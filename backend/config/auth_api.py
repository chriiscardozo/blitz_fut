from django.contrib.auth import authenticate
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.middleware.csrf import get_token
from ninja import Router, Schema
from ninja.errors import HttpError
from pydantic import Field

from config.security import admin_auth, csrf_only_auth, login_rate_throttle


class CsrfOut(Schema):
    csrf_token: str


class LoginIn(Schema):
    username: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=1, max_length=256)


class SessionOut(Schema):
    authenticated: bool
    is_admin: bool
    username: str | None
    csrf_token: str


router = Router(tags=["Authentication"])


def _session_data(request) -> dict[str, object]:
    user = request.user
    is_admin = bool(
        user.is_authenticated and (getattr(user, "is_staff", False) or user.is_superuser)
    )
    return {
        "authenticated": bool(user.is_authenticated),
        "is_admin": is_admin,
        "username": user.get_username() if user.is_authenticated else None,
        "csrf_token": get_token(request),
    }


@router.get("/auth/csrf", response=CsrfOut, auth=None)
def csrf_token(request):
    return {"csrf_token": get_token(request)}


@router.get("/auth/session", response=SessionOut, auth=None)
def session(request):
    return _session_data(request)


@router.post(
    "/auth/login",
    response=SessionOut,
    auth=csrf_only_auth,
    throttle=login_rate_throttle,
)
def login(request, payload: LoginIn):
    user = authenticate(
        request,
        username=payload.username,
        password=payload.password,
    )
    if user is None or not (user.is_staff or user.is_superuser):
        raise HttpError(401, "Invalid credentials.")
    django_login(request, user)
    return _session_data(request)


@router.post("/auth/logout", response=SessionOut, auth=admin_auth)
def logout(request):
    django_logout(request)
    return _session_data(request)
