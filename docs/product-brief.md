# Blitz Fut — Product Brief

Status: Living document
Last updated: 2026-09-17

## 1. Product summary

Blitz Fut is a mobile-first web application for organizing an astro five-a-side football cup among friends. It gives one organizer the tools to configure and run the competition, while everyone else can follow it through a public, read-only website.

The MVP supports one constrained but configurable competition structure:

1. A single round-robin group stage.
2. A single-match knockout stage.
3. A mandatory final.
4. An optional third-place match.

## 2. Goals

- Make the competition easy for one organizer to configure and operate.
- Give participants easy access through a normal web link, especially on mobile devices.
- Calculate group standings, qualification, knockout progression, and player leaderboards consistently.
- Support different valid numbers of groups, teams per group, and qualifiers per group.
- Keep match-result and player-stat entry quick enough to use immediately after a game.
- Keep development, deployment, and operation within free service tiers where practical.

## 3. Explicit non-goals

The following are outside the scope of this project:

- Native mobile applications.
- App Store or Play Store distribution.
- Notifications.
- Payments.
- Player accounts.
- Public user registration.
- Wildcard qualification across groups.
- Knockout byes.
- Multiple group phases, group-only competitions, knockout-only competitions, double elimination, or two-legged ties.
- A ChatGPT plugin or embedded ChatGPT UI for the MVP.

Progressive Web App features may be considered later, but are not required for the MVP.

## 4. Users and access

### Administrator

There is exactly one administrator account. The administrator can:

- Create and configure competition editions.
- Create teams and players.
- Assign players to teams.
- Assign teams to groups.
- Generate group fixtures.
- Enter and correct match results and player statistics.
- Resolve a standings tie that reaches a drawing of lots.
- Finalize or reopen the group stage when permitted.
- Operate the knockout stage through completion.

There is no public signup, invitation, or password-recovery flow. Initial account creation and password reset will use a secure administrative command.

### Public visitors

All other visitors are anonymous and read-only. They can view competition information without creating an account or signing in.

### Authentication and security requirements

- Store the administrator password using an established Argon2id password-hashing implementation with a unique salt and appropriate cost parameters.
- Never store plaintext or reversibly encrypted passwords.
- Use server-managed sessions and cookies configured with `Secure`, `HttpOnly`, and an appropriate `SameSite` policy.
- Protect state-changing requests against CSRF.
- Rate-limit login attempts and use generic authentication error messages.
- Enforce administrator authorization on the server for every write operation.
- Require HTTPS in production.
- Keep credentials and secret keys outside the repository.
- Use established framework and library security features instead of custom cryptographic code.

## 5. Delivery platform

- Mobile-first responsive web application.
- Accessible through a normal URL with no installation required.
- Python will be used for application development.
- Python 3.13 is the required backend runtime for local development, testing, and PythonAnywhere deployment.
- Django 5.2 LTS is the backend web framework.
- Django Ninja provides the JSON API consumed by the frontend.
- Pydantic schemas are used for API request and response contracts and for other structured validation boundaries where they improve type safety and clarity.
- Pydantic does not replace Django ORM models, database constraints, or transactional domain services for persisted business invariants.
- The product frontend is a separate React application written in TypeScript; product pages do not use Django templates.
- Vite provides the frontend development server and produces the optimized static production build.
- Node.js 24 LTS runs the frontend toolchain locally and in CI; Node.js is not part of the PythonAnywhere runtime.
- npm manages frontend dependencies, and `package-lock.json` is committed to keep installations reproducible.
- Backend automated tests use pytest, with pytest-django providing Django integration. The MVP does not require property-based, browser, or coverage-threshold tooling.
- PythonAnywhere's free plan hosts the single live application environment. There is no separate hosted development or staging environment.
- The Django application and the React production build are delivered through the same PythonAnywhere web application and public origin.
- SQLite is the MVP database. Its live database file is stored on PythonAnywhere's persistent filesystem outside the version-controlled source tree.
- Django migrations manage the database schema.
- Backend dependencies are declared in `pyproject.toml`, resolved and locked locally with `uv`, and committed with `uv.lock`.
- A production-only `requirements.txt` is exported from the lock and installed with `pip` on PythonAnywhere; `uv` is not required on the host.
- The repository is a monorepo with separate `backend/` and `frontend/` directories.
- The Django project package is `config`, containing settings, root URL configuration, and WSGI setup.
- A single Django domain app named `competitions` owns competition editions, teams, players, rosters, groups, rounds, matches, standings, and knockout progression for the MVP.
- Within `competitions`, ORM models own persisted data and row-level constraints, Pydantic schemas own API contracts, transactional services own state changes and cross-row invariants, selectors own derived reads, and API handlers remain thin.
- Django's built-in authentication application owns the administrator identity and sessions; no custom account app or model is introduced.
- Infrastructure as Code tooling, including Terraform, is intentionally out of scope. The PythonAnywhere setup and operational procedures will be documented and performed manually.
- The deployment must remain within PythonAnywhere's free-plan constraints, including any periodic web-app renewal requirement.
- The user interface, source code, database identifiers, and technical documentation are all written in English.
- The MVP has no language selector or localization framework.
- MUI Core provides the UI components and Emotion provides its styling runtime.
- The visual theme uses an off-white background (`#f7f8f4`), near-black text (`#172019`), and football green (`#237a45`), with semantic colours reserved for feedback states.
- ChatGPT integration is deferred. If introduced later, it will complement the website rather than replace its backend or database.

## 6. Competition format

Let:

- `T` be the total number of teams entered during initial configuration.
- `G` be the number of groups.
- `M = T / G` be the derived number of teams in each group.
- `Q` be the number of qualifiers from each group.
- `K = G × Q` be the total number of knockout teams.

The MVP enforces these invariants:

- `G` is a power of two: 1, 2, 4, 8, and so on.
- `T` must divide evenly by `G`.
- Every group has the same number of teams, `M`.
- `M >= 2`, with no application-defined maximum.
- `Q` is a power of two: 1, 2, 4, 8, and so on.
- `Q <= M`.
- `K >= 2` and `K` is a power of two.
- Every competition team belongs to exactly one group.
- Every group qualifies the same number of teams.
- There are no wildcards and no knockout byes.

Examples of valid configurations:

| Groups | Teams per group | Qualifiers per group | Knockout teams | First knockout round |
| ---: | ---: | ---: | ---: | --- |
| 1 | 4 | 2 | 2 | Final |
| 1 | 5 | 4 | 4 | Semifinals |
| 2 | 4 | 1 | 2 | Final |
| 2 | 4 | 2 | 4 | Semifinals |
| 2 | 4 | 4 | 8 | Quarterfinals |

## 7. Group-stage fixtures

### Group assignment

- The administrator may assign teams to groups manually.
- The administrator may use `Randomize groups` to shuffle teams and distribute them evenly across the configured groups.
- Random assignment does not use seeded pots, rankings, or any other balancing criteria.
- Before fixtures are generated, the administrator may randomize again or adjust any assignment manually.

### Fixture generation

- Fixtures are generated automatically after teams have been assigned to groups.
- Each group uses a single round-robin: every team plays every other team in its group exactly once.
- A team plays at most once in a rodada.
- With an even `M`, each group has `M - 1` rodadas.
- With an odd `M`, each group has `M` rodadas and each team has one bye.
- Each group has `M × (M - 1) / 2` matches.
- Corresponding rodadas from different groups are presented together.
- Matches do not store or display a scheduled date or time.

### Configuration locking

- Initial competition configuration is a creation step before the persisted `DRAFT` lifecycle and before any teams or assignments exist.
- The administrator enters the competition name and year, total number of teams `T`, number of groups `G`, qualifiers per group `Q`, and whether a third-place match is enabled.
- The application validates the format, derives `M = T / G`, and atomically creates the `DRAFT` competition and its `G` empty groups. It does not persist a partially configured competition.
- The initial format values are locked after creation. An incorrect empty draft can be discarded and recreated before teams are added.
- During `DRAFT`, participating teams, rosters, and group assignments are editable, but exactly `T` teams must exist before fixtures can be generated.
- Generating fixtures temporarily locks participating teams and group assignments.
- While no match result has been completed, the administrator may use `Return to setup`. After confirmation, this removes all pending fixtures and unlocks teams and group assignments, but not the initial format.
- Completing the first group-stage result permanently locks participating teams, rosters, and group assignments.
- Reopening a finalized group stage unlocks results only; it does not unlock the structural configuration.
- Descriptive fields such as competition, team, and player names remain correctable after the structural configuration is locked.

## 8. Group standings

### Points

- Win: 3 points.
- Draw: 1 point.
- Loss: 0 points.

### Tie-breakers

Tied teams are ordered using these criteria, in order:

1. Total points.
2. Overall goal difference.
3. Overall goals scored.
4. Points in matches among the tied teams.
5. Goal difference in matches among the tied teams.
6. Goals scored in matches among the tied teams.
7. An organizer-recorded drawing of lots.

If the tie reaches the last criterion, the application must flag it and require the administrator to record the resolution explicitly before finalizing the group stage.

For a drawing-of-lots resolution:

- The application identifies every team that remains tied after all calculated criteria.
- The administrator conducts the drawing of lots outside the application.
- The administrator assigns each team in the tied cohort a positive drawing-of-lots priority; higher values rank first.
- Priorities only need to be unique within the completely tied cohort and may be reused by a separate tied cohort in the same group.
- Saving requires explicit confirmation that the entered order reflects the draw.
- A nullable `draw_lots_priority` on the team's group membership stores the result; `NULL` means no result has been recorded.
- Correcting a completed result clears every drawing-of-lots priority in the affected group before recalculating its standings.
- Group-stage finalization is blocked until every unresolved ordering has been recorded.

Standings are derived from completed group matches rather than maintained as independent source data.

## 9. Match results and player statistics

### Roster membership

- When adding a roster member, the administrator may create a new global player or select an existing player by identifier; names are not unique identifiers.
- A player may belong to only one team within a competition edition.
- Roster assignments can be added, removed, or moved freely until the first match result in the competition is completed.
- Completing the first match result locks every roster assignment for that competition.
- After the roster is locked, players cannot be added to, removed from, or moved between teams.
- Player names may still be corrected after the roster is locked.

### Result-entry interaction

For each team, the result-entry screen lists its roster and provides increment and decrement controls for every player's goals and assists. It also provides an `Own goals received` row for each team.

Conceptually:

```text
Player                  Goals        Assists
Player 1                 - 0 +         - 0 +
Player 2                 - 0 +         - 0 +
...
Own goals received       - 0 +
```

The normal match score is calculated automatically for each team:

```text
team score = sum(player goals) + own goals received
```

There is no separate manual normal-time score entry. Player goals and assists are stored as aggregate totals per player and match; the MVP does not record their time, order, or per-goal association.

### Statistical rules

- Own goals increase the beneficiary team's match score but are not credited to a player.
- Own goals cannot receive an assist.
- An individual player may have more assists than goals.
- For each team, total assists cannot exceed the sum of its player-attributed goals.
- Saving result changes recalculates the match score, standings, and leaderboards.
- Penalty-shootout kicks are not recorded as goals or assists.

### Completion workflow

- A match remains pending while the administrator adjusts its goal, assist, and own-goal counters.
- Pending form changes do not affect public scores, standings, or leaderboards.
- Selecting `Complete match` commits all player and team statistics atomically; the normal score is derived from them.
- Because the score is derived from the distributed player goals and own goals, a completed match cannot contain an undistributed goal.
- A 0–0 group-stage result is valid.
- Completing a tied knockout match additionally requires selecting its shootout winner.
- The MVP does not persist partially entered draft results.
- A completed result may be corrected subject to the group-stage and knockout dependency rules.

## 10. Knockout stage

### Rounds

The knockout rounds are derived from `K`:

- 2 teams: final.
- 4 teams: semifinals, then final.
- 8 teams: quarterfinals, semifinals, then final.
- 16 teams: round of 16, quarterfinals, semifinals, then final.
- The same pattern continues for larger valid powers of two.

The final is always created and cannot be disabled. A third-place match is optional and can only be enabled when `K >= 4`.

### Seeding

- The bracket is generated automatically from final group positions.
- Higher-positioned qualifiers face lower-positioned qualifiers.
- Teams from the same group do not meet in the first knockout round when multiple groups exist.
- Teams are not globally ranked by points or goal difference across different groups.
- The bracket is fixed once generated and is not reseeded after each round.
- Groups are processed by ordinal and paired adjacently: A with B, C with D, E with F, and so on.
- Within each group pair, qualifiers are cross-seeded by group position: the best qualifier from one group faces the lowest qualifier from the other group, continuing inward.
- Each adjacent group pair occupies one contiguous bracket block. Winners remain inside that block until one block winner emerges; adjacent block winners then meet in subsequent rounds.
- With a single group, qualifiers are seeded only by their group position using the same standard single-elimination placement.
- No random draw is used to place knockout teams.

Examples:

- One group with four qualifiers: 1st vs 4th and 2nd vs 3rd.
- Two groups with two qualifiers each: A1 vs B2 and B1 vs A2.
- Four groups with one qualifier each: A1 vs B1 and C1 vs D1.
- Two groups with four qualifiers each: A1 vs B4, B1 vs A4, A2 vs B3, and B2 vs A3; bracket-slot ordering keeps the two group winners in opposite halves of that group-pair block.

### Drawn knockout matches

- There is no extra time.
- A tied knockout match goes directly to penalties.
- The penalty score is not recorded.
- When the normal score is unequal, the winner is derived automatically and the penalty-winner selector is disabled.
- When the normal score is tied, selecting one of the two teams as the shootout winner is required.
- Only the selected team identifier is stored as the shootout winner.
- Group-stage matches never display this selector and may finish as draws.
- For the final and third-place match, the selector is labelled `Winner`; for earlier rounds, it is labelled `Qualified team`.

### Progression and corrections

- Completing a knockout match automatically places its winner into the dependent match.
- Semifinal losers automatically populate the optional third-place match.
- Completing the final records the competition champion.
- The competition becomes completed after the final and, when enabled, the third-place match have both been completed.
- A knockout result may be corrected while none of its dependent matches has a recorded result.
- Once a dependent match has been completed, changing the earlier result is blocked to prevent an inconsistent bracket.

## 11. Group-stage finalization

- Group standings update live while results are entered.
- The knockout bracket is not generated merely because the last group result is saved.
- Once all group matches are complete and any unresolved ties are settled, the administrator can select `Finalize group stage`.
- Finalization requires confirmation, creates the complete knockout bracket, and locks group results.
- The administrator may reopen the group stage only while no knockout result has been recorded.
- Reopening removes the unplayed knockout bracket and unlocks the group results.
- After corrections, finalizing again generates a fresh bracket.
- Once any knockout result exists, reopening the group stage is blocked.

## 12. MVP views

### Public competition view

- Active competitions are listed before completed competitions.
- Completed competitions remain publicly accessible under `Past competitions`.
- Group tables and current qualification positions.
- Matches and results organized by rodada.
- Knockout bracket once the group stage is finalized.
- Top scorers.
- Top assisters.
- Teams and their rosters.
- Competition champion after the final is completed.
- Third-place result when enabled.
- Historical tables, fixtures, brackets, rosters, and leaderboards remain read-only.
- Statistics are scoped to an individual competition; the MVP does not calculate cross-edition player career totals.

### Administrator views

- Login.
- Competition creation and configuration.
- Team, player, and roster management.
- Group assignment and fixture generation.
- Group match result and statistics entry.
- Group-stage tie resolution and finalization.
- Knockout result entry and bracket progression.

## 13. Preliminary domain concepts

These are working concepts, not a final database schema:

- **Competition edition:** the configured cup for a particular occurrence or year.
- **Stage:** group or knockout portion of a competition.
- **Group:** a competition group with an ordered label such as A, B, C, or D.
- **Round:** a group-stage rodada or knockout round.
- **Team:** a participant that belongs to exactly one competition edition. Team names may be reused by creating a new team record in another edition; the MVP has no long-lived club identity shared across editions.
- **Player:** a reusable person who can participate in different competition editions.
- **Roster membership:** assignment of a player to one competition team. A player may belong to only one team within a competition.
- **Group membership:** assignment of a competition team to exactly one group, including its nullable drawing-of-lots priority when required.
- **Match:** two participating teams, its stage and round, completion state, and knockout dependencies where applicable.
- **Player match statistics:** aggregate goals and assists for one player in one match.
- **Team match statistics:** own goals received by a team in a match.
- **Shootout winner:** the selected winner of a tied knockout match, without penalty-score details.

Normal match scores, standings, qualification positions, and leaderboards are derived from source match statistics.

## 14. Outstanding product decisions

No known MVP product-rule decisions are outstanding. New questions discovered during domain modeling will be added here.

## 15. Outstanding technical decisions

The following choices will be made one at a time after the relevant product behavior is settled:

- API conventions and frontend type-generation strategy.
- Continuous integration and delivery.

The SQLite backup/restore policy, session-authentication implementation, and PythonAnywhere operational runbook are now defined in [operations.md](operations.md).
