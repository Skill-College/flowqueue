# Publishing the `flowqueue` SDK to PyPI

The SDK is published from `./sdk` via **Trusted Publishing** (GitHub Actions + OIDC) —
no API tokens are stored anywhere.

## One-time setup (PyPI Trusted Publisher)

1. Sign in at https://pypi.org.
2. The project `flowqueue` doesn't exist yet, so add a **pending publisher**:
   - Account → **Publishing** → *Add a pending publisher*.
   - PyPI Project Name: `flowqueue`
   - Owner: your GitHub org/user
   - Repository name: this repo
   - Workflow name: `publish.yml`
   - Environment name: `pypi`
3. (Optional, recommended) In GitHub → repo **Settings → Environments**, create an
   environment named `pypi` and add required reviewers for release protection.

## Release flow (each version)

1. Bump the version in `sdk/pyproject.toml` and `sdk/flowqueue/__init__.py`.
2. Commit + push to the default branch.
3. Create a **GitHub Release** with a tag like `sdk-v0.1.0` (tag must start with
   `sdk-v` — that's what triggers the workflow).
4. The `publish.yml` workflow builds the wheel + sdist, runs `twine check`, and
   uploads to PyPI via OIDC. Within a minute: `pip install flowqueue`.

## Manual fallback (local, with an API token)

If you ever need to publish without CI:

```bash
cd sdk
python -m pip install --upgrade build twine
python -m build                      # creates dist/*.whl and dist/*.tar.gz
python -m twine check dist/*
python -m twine upload dist/*        # prompts for token; use __token__ + a PyPI API token
```

Create the API token at PyPI → Account → API tokens (scope it to the `flowqueue`
project after the first upload). Store it in `~/.pypirc` or paste when prompted.

## Notes

- The **server** distribution is named `flowqueue-server` (see root `pyproject.toml`)
  so the PyPI name `flowqueue` belongs solely to this client SDK.
- TestPyPI dry-run: add `repository-url: https://test.pypi.org/legacy/` to the publish
  step and register a matching pending publisher on https://test.pypi.org first.
