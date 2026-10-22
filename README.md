# OmniCrit

An AI testing agent that learns any application (web, mobile, API, desktop, any tech stack) from its docs and its live screens, plans its own tests, runs them like a human tester, and replays passing tests later without spending LLM tokens.

> Status: early development. Module 1 (Foundation) of step 2. See the architecture spec and build plan for the roadmap.

## Install (development)

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/VijayR2297/OmniCrit.git
cd OmniCrit
uv sync
uv run omnicrit --help     # or the short alias: uv run crit --help
```

## Try it

```bash
omnicrit init "Shop app" --link          # create a project; --link ties this folder to it
omnicrit target add web --kind web --env staging=https://staging.example.com
omnicrit target add android --kind android --env dev=./build/app.apk
omnicrit secret set ANTHROPIC_API_KEY    # stored in the OS keychain, never on disk
omnicrit init "Bank portal"
omnicrit list                            # * marks the active project
omnicrit use shop-app
omnicrit current
```

## Where data lives

```
~/.omnicrit/                 (override with OMNICRIT_HOME)
  config.yaml                active project, default LLM settings
  logs/omnicrit.log
  projects/<slug>-<id>/
    project.yaml             targets, environments, access level, LLM choice
    stack.json               detected tech stack per target (module 6)
    memory.db                App Model, tests, replay scripts (SQLite)
    anchors/  runs/  cache/
```

A `.omnicrit.yaml` file in a folder (or any parent) selects that project, the same way git finds a repo. Otherwise the project chosen with `omnicrit use` is active.

## Develop

```bash
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run mypy
```
