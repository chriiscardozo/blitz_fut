from django.core.exceptions import ValidationError as DjangoValidationError
from ninja import NinjaAPI, Schema

from competitions.api_admin import router as admin_router
from competitions.api_public import router as public_router
from config.auth_api import router as auth_router


class HealthResponse(Schema):
    status: str


api = NinjaAPI(title="Blitz Fut API", version="1.0.0")


@api.exception_handler(DjangoValidationError)
def validation_error(request, exc: DjangoValidationError):
    errors = exc.message_dict if hasattr(exc, "message_dict") else {"__all__": exc.messages}
    return api.create_response(
        request,
        {"detail": "Validation failed.", "errors": errors},
        status=422,
    )


@api.get("/health", response=HealthResponse, auth=None)
def health(request) -> HealthResponse:
    return HealthResponse(status="ok")


api.add_router("", auth_router)
api.add_router("", public_router)
api.add_router("", admin_router)
