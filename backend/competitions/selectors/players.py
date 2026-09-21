from django.db.models import Q

from competitions.models import Player


def search_players(*, query: str = "", limit: int = 20) -> list[Player]:
    normalized = query.strip()
    players = Player.objects.all()
    if normalized:
        criteria = Q(name__icontains=normalized)
        if normalized.isdecimal():
            criteria |= Q(id=int(normalized))
        players = players.filter(criteria)
    return list(players.order_by("name", "id")[:limit])
