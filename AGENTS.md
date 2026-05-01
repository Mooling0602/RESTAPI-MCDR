# AGENTS
This file is for AI agents. Read, write as you want.

## Refers to
- **doc/RELEASE.md**: Release/tag workflow. Use bare git tags like `1.0.0` (no `v`), release commits use `release: v<version>`, and CI builds the plugin with `mcdreforged pack` after the uv environment is ready.
- **doc/CHANGELOG.md**: CI changelog parsing. Keep `**#full_changelog**` for release replacement.
- **mcdreforged.plugin.json**: Plugin metadata source of truth, including the version and plugin id `rest_api`.
- **pyproject.toml**: Hatch reads the version from `mcdreforged.plugin.json`; target Python is `>=3.12`, with runtime deps `fastapi` and `mcdreforged`, optional `moolings-rcon-api`, and dev tools `ruff`/`ty`.
- **rest_api/__init__.py**: FastAPI app entrypoint. The app is mounted by `fastapi_mcdr` under the plugin id, docs are exposed at `/rest_api/docs`, protected routes use the `Authorization` header via `verify_token`, webhooks are added with `@webhook` / `register_webhook_listener`, and the console-only token command is `!!rest_api token`.
- **rest_api/config.py**: Plugin config is loaded from `config.yml` in the MCDR data folder. The default `api_token` is `token_changethis`; change it before using protected endpoints.
- **rest_api/data.py**: Use `TextResult` and `JSONResult` for API responses when a structured success payload is needed.
- **README.md**: Project summary only; prefer the code and docs above for workflow and implementation details.
