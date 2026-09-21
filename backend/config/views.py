from django.conf import settings
from django.http import FileResponse, HttpRequest, HttpResponse


def spa_index(request: HttpRequest) -> HttpResponse:
    index_path = settings.FRONTEND_DIST / "index.html"
    if not index_path.is_file():
        return HttpResponse(
            "The Blitz Fut frontend has not been built yet.",
            status=503,
            content_type="text/plain; charset=utf-8",
        )
    return FileResponse(index_path.open("rb"), content_type="text/html")
