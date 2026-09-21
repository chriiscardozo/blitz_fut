from django.conf import settings
from django.http import HttpRequest
from ninja.security import SessionAuthIsStaff
from ninja.security.apikey import APIKeyCookie
from ninja.throttling import SimpleRateThrottle


class CsrfOnlyAuth(APIKeyCookie):
    """Apply cookie-based CSRF validation without requiring a logged-in user."""

    param_name = settings.CSRF_COOKIE_NAME

    def authenticate(self, request: HttpRequest, key: str | None) -> bool:
        return True


class LoginRateThrottle(SimpleRateThrottle):
    def get_cache_key(self, request: HttpRequest) -> str:
        return self.cache_format % {
            "scope": "admin_login",
            "ident": self.get_ident(request) or "unknown",
        }


admin_auth = SessionAuthIsStaff()
csrf_only_auth = CsrfOnlyAuth()
login_rate_throttle = LoginRateThrottle(rate="10/5min")
