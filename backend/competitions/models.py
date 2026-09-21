from django.db import models
from django.db.models import F, Q


class Competition(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        GROUP_STAGE = "GROUP_STAGE", "Group stage"
        KNOCKOUT = "KNOCKOUT", "Knockout"
        COMPLETED = "COMPLETED", "Completed"

    name = models.CharField(max_length=120)
    year = models.PositiveSmallIntegerField()
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    group_count = models.PositiveSmallIntegerField()
    teams_per_group = models.PositiveSmallIntegerField()
    qualifiers_per_group = models.PositiveSmallIntegerField()
    third_place_enabled = models.BooleanField(default=False)

    class Meta:
        ordering = ["-year", "name", "id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(group_count__gte=1),
                name="competition_group_count_gte_1",
            ),
            models.CheckConstraint(
                condition=Q(teams_per_group__gte=2),
                name="competition_teams_per_group_gte_2",
            ),
            models.CheckConstraint(
                condition=Q(qualifiers_per_group__gte=1),
                name="competition_qualifiers_gte_1",
            ),
            models.CheckConstraint(
                condition=Q(qualifiers_per_group__lte=F("teams_per_group")),
                name="competition_qualifiers_lte_teams",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.year})"

    @property
    def total_team_count(self) -> int:
        return self.group_count * self.teams_per_group


class Group(models.Model):
    competition = models.ForeignKey(
        Competition,
        on_delete=models.CASCADE,
        related_name="groups",
    )
    ordinal = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["competition_id", "ordinal"]
        constraints = [
            models.UniqueConstraint(
                fields=["competition", "ordinal"],
                name="unique_group_ordinal_per_competition",
            ),
            models.CheckConstraint(
                condition=Q(ordinal__gte=1),
                name="group_ordinal_gte_1",
            ),
        ]

    @property
    def label(self) -> str:
        value = self.ordinal
        result = ""
        while value:
            value, remainder = divmod(value - 1, 26)
            result = chr(65 + remainder) + result
        return result

    def __str__(self) -> str:
        return f"{self.competition}: Group {self.label}"


class Team(models.Model):
    competition = models.ForeignKey(
        Competition,
        on_delete=models.CASCADE,
        related_name="teams",
    )
    name = models.CharField(max_length=120)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["competition", "name"],
                name="unique_team_name_per_competition",
            )
        ]

    def __str__(self) -> str:
        return self.name


class Player(models.Model):
    name = models.CharField(max_length=120)

    class Meta:
        ordering = ["name", "id"]

    def __str__(self) -> str:
        return self.name


class RosterMembership(models.Model):
    competition = models.ForeignKey(
        Competition,
        on_delete=models.CASCADE,
        related_name="roster_memberships",
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="roster_memberships",
    )
    player = models.ForeignKey(
        Player,
        on_delete=models.PROTECT,
        related_name="roster_memberships",
    )

    class Meta:
        ordering = ["team_id", "player__name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["competition", "player"],
                name="unique_player_roster_per_competition",
            )
        ]

    def __str__(self) -> str:
        return f"{self.player} — {self.team}"


class GroupMembership(models.Model):
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    team = models.OneToOneField(
        Team,
        on_delete=models.CASCADE,
        related_name="group_membership",
    )
    draw_lots_priority = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["group_id", "team__name", "id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(draw_lots_priority__isnull=True)
                | Q(draw_lots_priority__gte=1),
                name="group_membership_draw_priority_positive",
            )
        ]

    def __str__(self) -> str:
        return f"{self.team} in Group {self.group.label}"


class Round(models.Model):
    class Stage(models.TextChoices):
        GROUP = "GROUP", "Group"
        KNOCKOUT = "KNOCKOUT", "Knockout"

    competition = models.ForeignKey(
        Competition,
        on_delete=models.CASCADE,
        related_name="rounds",
    )
    stage = models.CharField(max_length=8, choices=Stage.choices)
    number = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["competition_id", "stage", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["competition", "stage", "number"],
                name="unique_round_number_per_stage",
            ),
            models.CheckConstraint(
                condition=Q(number__gte=1),
                name="round_number_gte_1",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.competition}: {self.get_stage_display()} round {self.number}"


class Match(models.Model):
    class Kind(models.TextChoices):
        REGULAR = "REGULAR", "Regular"
        FINAL = "FINAL", "Final"
        THIRD_PLACE = "THIRD_PLACE", "Third place"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        COMPLETED = "COMPLETED", "Completed"

    class SourceOutcome(models.TextChoices):
        WINNER = "WINNER", "Winner"
        LOSER = "LOSER", "Loser"

    round = models.ForeignKey(
        Round,
        on_delete=models.CASCADE,
        related_name="matches",
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="matches",
        null=True,
        blank=True,
    )
    position = models.PositiveSmallIntegerField()
    kind = models.CharField(
        max_length=12,
        choices=Kind.choices,
        default=Kind.REGULAR,
    )
    team_a = models.ForeignKey(
        Team,
        on_delete=models.PROTECT,
        related_name="matches_as_team_a",
        null=True,
        blank=True,
    )
    team_b = models.ForeignKey(
        Team,
        on_delete=models.PROTECT,
        related_name="matches_as_team_b",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    source_match_a = models.ForeignKey(
        "self",
        on_delete=models.RESTRICT,
        related_name="dependents_as_team_a",
        null=True,
        blank=True,
    )
    source_outcome_a = models.CharField(
        max_length=6,
        choices=SourceOutcome.choices,
        null=True,
        blank=True,
    )
    source_match_b = models.ForeignKey(
        "self",
        on_delete=models.RESTRICT,
        related_name="dependents_as_team_b",
        null=True,
        blank=True,
    )
    source_outcome_b = models.CharField(
        max_length=6,
        choices=SourceOutcome.choices,
        null=True,
        blank=True,
    )
    shootout_winner = models.ForeignKey(
        Team,
        on_delete=models.PROTECT,
        related_name="shootout_wins",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["round_id", "position"]
        constraints = [
            models.UniqueConstraint(
                fields=["round", "position"],
                name="unique_match_position_per_round",
            ),
            models.CheckConstraint(
                condition=Q(position__gte=1),
                name="match_position_gte_1",
            ),
            models.CheckConstraint(
                condition=Q(team_a__isnull=True)
                | Q(team_b__isnull=True)
                | ~Q(team_a=F("team_b")),
                name="match_teams_must_differ",
            ),
            models.CheckConstraint(
                condition=Q(status="PENDING")
                | (Q(team_a__isnull=False) & Q(team_b__isnull=False)),
                name="completed_match_has_teams",
            ),
            models.CheckConstraint(
                condition=(
                    Q(source_match_a__isnull=True, source_outcome_a__isnull=True)
                    | Q(source_match_a__isnull=False, source_outcome_a__isnull=False)
                ),
                name="match_source_a_fields_together",
            ),
            models.CheckConstraint(
                condition=(
                    Q(source_match_b__isnull=True, source_outcome_b__isnull=True)
                    | Q(source_match_b__isnull=False, source_outcome_b__isnull=False)
                ),
                name="match_source_b_fields_together",
            ),
            models.CheckConstraint(
                condition=Q(shootout_winner__isnull=True)
                | (
                    Q(team_a__isnull=False)
                    & Q(shootout_winner=F("team_a"))
                )
                | (
                    Q(team_b__isnull=False)
                    & Q(shootout_winner=F("team_b"))
                ),
                name="shootout_winner_is_participant",
            ),
        ]
        indexes = [
            models.Index(
                fields=["group", "status"],
                name="match_group_status_idx",
            )
        ]

    def __str__(self) -> str:
        return f"{self.round}, match {self.position}"


class PlayerMatchStat(models.Model):
    match = models.ForeignKey(
        Match,
        on_delete=models.CASCADE,
        related_name="player_stats",
    )
    roster_membership = models.ForeignKey(
        RosterMembership,
        on_delete=models.PROTECT,
        related_name="match_stats",
    )
    goals = models.PositiveSmallIntegerField(default=0)
    assists = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["match_id", "roster_membership_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["match", "roster_membership"],
                name="unique_player_stat_per_match",
            )
        ]

    def __str__(self) -> str:
        return f"{self.roster_membership} in {self.match}"


class TeamMatchStat(models.Model):
    match = models.ForeignKey(
        Match,
        on_delete=models.CASCADE,
        related_name="team_stats",
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.PROTECT,
        related_name="match_stats",
    )
    own_goals_received = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["match_id", "team_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["match", "team"],
                name="unique_team_stat_per_match",
            )
        ]

    def __str__(self) -> str:
        return f"{self.team} in {self.match}"
