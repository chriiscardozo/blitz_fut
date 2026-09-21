from django.urls import path, re_path

from config.api import api
from config.views import spa_index


urlpatterns = [
    path("api/", api.urls),
    re_path(r"^(?!(?:api|assets)(?:/|$)).*$", spa_index, name="spa-index"),
]
