# Documentation development

## MkDocs site

MkDocs Material is the primary site generator. It provides searchable,
cross-linked HTML, responsive navigation, code-copy controls, Mermaid diagrams,
and strict validation while keeping the source authoring format as Markdown.

The C4 architecture section is intentionally source-grounded: every major
container and component points to the C source, registry, build file, Tcl
directory, or deployment file that implements it. Update the relevant C4 page
when a runtime or ownership boundary changes.

The upstream Texinfo manual, generated Info/man pages, and Doxygen API inputs
remain specialist build outputs and are not replaced by this site.

## Local build with Python

```console
$ python -m venv .venv-docs
$ . .venv-docs/bin/activate
$ pip install -r docs/requirements.txt
$ python3 tools/docs/generate_support_tables.py --check
$ python3 -m mkdocs build --strict --site-dir docs/_build/html
```

The GitHub Pages workflow uses the same strict build with `site/` as its
artifact directory. To reproduce that build exactly, use:

```console
$ python3 -m mkdocs build --strict --site-dir site
```

The generated `site/` and `docs/_build/` directories are disposable outputs;
do not commit them. A successful local build is necessary but does not deploy
the site. Push documentation changes to `master` or `main`, or start
`.github/workflows/pages.yml` manually from GitHub Actions.

Windows PowerShell:

```powershell
py -m venv .venv-docs
.\.venv-docs\Scripts\Activate.ps1
pip install -r docs\requirements.txt
python tools/docs/generate_support_tables.py --check
python -m mkdocs build --strict --site-dir docs\_build\html
```

## Docker build

```console
$ docker build -f docker/Dockerfile.docs --target export \
  --output type=local,dest=docs/_build/export .
```

## Writing rules

- Begin pages with the user goal, not implementation history.
- Show one recommended command before alternatives.
- Separate build, export, install, and runtime steps.
- Include expected artifact paths.
- Put failure messages in the troubleshooting page.
- Link to the legacy command manual instead of copying it.
- Keep navigation entries in `mkdocs.yml` when adding a new user-facing page.
- Regenerate `docs/reference/support-matrix.md` after changing board,
  interface, FPGA/CPLD, SVD, or support metadata files.
- Keep the Pages workflow build command aligned with the strict local command;
  deployment should publish only the generated `site/` directory.
