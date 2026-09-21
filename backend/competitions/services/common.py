from django.core.exceptions import ValidationError


MAX_NAME_LENGTH = 120
MAX_POSITIVE_SMALL_INTEGER = 32_767


def normalize_required_name(value: str, *, label: str) -> str:
    if not isinstance(value, str):
        raise ValidationError({"name": [f"{label} name must be text."]})
    normalized = value.strip()
    if not normalized:
        raise ValidationError({"name": [f"{label} name is required."]})
    if len(normalized) > MAX_NAME_LENGTH:
        raise ValidationError(
            {"name": [f"{label} name cannot exceed {MAX_NAME_LENGTH} characters."]}
        )
    return normalized
