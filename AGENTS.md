# Blitz Fut agent guidance

## Project context

- Read `README.md` for the application and local setup, `docs/product-brief.md` and
  `docs/data-model.md` for product decisions, and `docs/operations.md` for live
  operations.
- The backend is Django, Django Ninja, Pydantic, and SQLite. The frontend is
  React, TypeScript, Vite, and MUI. Production is one PythonAnywhere web app;
  there is no hosted staging environment.
- Keep changes within the agreed MVP scope. Notifications, payments, player
  accounts, and native mobile apps are out of scope.

## Git and review workflow

- Make repository changes on a feature branch. Never commit or push directly to
  `main`.
- Push the feature branch and open a pull request for Christian to review and
  merge. Do not merge the pull request yourself unless explicitly asked.
- Keep pull requests focused and report the checks run and any checks skipped.
- Do not deploy an unmerged branch. Deploy to PythonAnywhere only after an
  explicit request from Christian, following `docs/operations.md`.

## Verification

- For backend changes, run `cd backend && .venv/bin/pytest` when the local
  environment is prepared.
- For frontend changes, run `cd frontend && npm run typecheck && npm run build`.
- For documentation-only changes, review the changed text and links; application
  test suites are not required unless the documentation changes behavior or
  executable examples.

## Secrets and live data

- Never commit or disclose credentials, API tokens, passwords, `.env` files,
  SQLite databases, or backups. `.env.example` may contain placeholders only.
- Do not modify production data or perform a deployment without an explicit
  request. Before an authorized deployment or destructive production-data
  operation, create a consistent SQLite backup as described in
  `docs/operations.md`.
