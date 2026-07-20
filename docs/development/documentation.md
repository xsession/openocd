# Documentation development

## Why Sphinx

Sphinx is used for the deployment site because it provides searchable, cross-linked HTML; PDF and man-page builders; validation; and future Doxygen integration through Breathe. MyST keeps authoring in Markdown. Furo provides a readable responsive theme.

Typst remains a good optional downstream format for brochures or polished release handbooks, but it is not the primary documentation engine because it does not replace a searchable versioned website and API cross-references as effectively.

## Local build with Python

```console
$ python -m venv .venv-docs
$ . .venv-docs/bin/activate
$ pip install -r docs/requirements.txt
$ sphinx-build -W --keep-going -b html docs docs/_build/html
```

Windows PowerShell:

```powershell
py -m venv .venv-docs
.\.venv-docs\Scripts\Activate.ps1
pip install -r docs\requirements.txt
sphinx-build -W --keep-going -b html docs docs\_build\html
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
