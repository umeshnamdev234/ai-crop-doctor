# Contributing to Smarter Crops AI

Thanks for helping farmers! This guide explains how to propose changes and what we expect in a pull request.

## Ground rules

- **`main` is protected.** Every change arrives as a **pull request from a separate branch** and is merged after a maintainer approves it.
- **No personal data.** Don't commit real farmers' names, phone numbers, locations or photos that identify people.
- **No real expert or centre contact details** without permission. Sample data must stay clearly fictional.
- **Agronomic accuracy matters.** Wrong doses or wrong products can destroy a crop or harm people. See [Changes that affect advice](#changes-that-affect-advice).
- **No secrets.** Never commit `.env` files, passwords or API keys. Only `.env.example` files with placeholders belong in git.

## Workflow

1. **Open an issue** for bugs (steps to reproduce, expected vs actual behaviour, `curl http://localhost:8100/api/health` output) or to discuss a feature first. Small fixes can go straight to a PR.
2. **Fork and branch:**
   ```bash
   git clone https://github.com/<your-username>/ai-crop-doctor.git
   cd ai-crop-doctor
   git remote add upstream https://github.com/umeshnamdev234/ai-crop-doctor.git
   git checkout -b feat/short-description
   ```
   Branch prefixes: `feat/`, `fix/`, `docs/`, `refactor/`, `test/`, `chore/`, and `data/` for directory or sample-data changes.
3. **Set up the project** by following the [README](README.md) quick start.
4. **Keep PRs small:** one feature or fix per PR.
5. **Check before opening the PR:**
   ```bash
   cd backend && .venv/bin/python -m pytest -q
   cd frontend && npx tsc --noEmit && npm run lint && npm run build
   ```
   Also try the change in the app, **in both English and Hindi**, and at phone width.
6. **Commit messages:** `fix: ...`, `feat: ...`, `docs: ...`
7. **Open the PR** against `main`. Include what changed and why, how you tested it, and screenshots for UI changes.

## Coding guidelines

### Backend
- Python 3.11 with type hints.
- Model calls go in `llm_client.py`, queries in `db.py`, prompts in `prompts.py`, and ranking in `directory.py`.
- **Ranking stays deterministic.** The AI only classifies the problem (`triage.py`). Don't move ranking decisions into the model.
- Never log message content or photos.
- Add tests in `backend/tests/` for logic changes. Tests must not need the model or the database.

### Database (Alembic)
- Edit `app/models.py`, then run `alembic revision --autogenerate -m "..."`.
- Review the generated file. Triggers and expression indexes must be written by hand.
- Never edit a migration that is already on `main`, and always include a working `downgrade()`.

### Frontend
- Next.js 16: check `frontend/node_modules/next/dist/docs/` when unsure.
- **Every user-facing string goes in `src/lib/i18n.ts` with both `en` and `hi` versions.** Hindi should be simple and farmer-friendly.
- Make sure changes work in light and dark themes and on small phones.

## Changes that affect advice

PRs that touch prompts (`prompts.py`), safety (`safety.py`), triage (`triage.py`), ranking (`directory.py`) or **product data** get extra review:

- **Products and doses:** cite a source for each dose, such as the product label, an ICAR or state agricultural university package of practices, or CIB&RC registration. Use generic active-ingredient names, never brands. Don't add products that are **banned or restricted** in India.
- **Prompts and ranking:** explain the reason, and show before/after examples with made-up scenarios.
- **Safety:** never weaken the pesticide-poisoning warnings, the "follow the label" reminders, or the rule that **no product is suggested without a specific diagnosis**. New emergency phrases in English or Hindi are very welcome, with tests.

## Reporting security issues

Don't open a public issue. Contact the maintainer privately through GitHub (@umeshnamdev234).

## License

By contributing, you agree that your contributions are provided under the same terms as this repository. Gemma is subject to the [Gemma Terms of Use](https://ai.google.dev/gemma/terms).
