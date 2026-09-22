# Continuous integration

The repository contains release workflows under `.github/workflows`.

Recommended jobs:

- Linux x86-64 package on `ubuntu-latest`.
- Linux ARM64 package through Buildx/QEMU or a native ARM64 runner.
- Windows x86-64 cross-package on `ubuntu-latest`.
- macOS x86-64 on an Intel macOS runner when available.
- macOS ARM64 on an Apple Silicon runner.
- MkDocs Material HTML documentation with strict build validation.

Use immutable dependency versions and pin action major versions. Upload package archives as workflow artifacts for pull requests, then attach them to GitHub Releases for tags.

For reproducibility, include these metadata values in the release notes:

```text
OpenOCD commit
Jim Tcl commit
libjaylink commit
Dockerfile dependency versions
Build runner architecture
```

## GitHub Pages deployment

The public documentation site is deployed by
`.github/workflows/pages.yml`. It is deliberately separate from
`.github/workflows/docs.yml`: the latter retains the downloadable HTML build
artifact used for CI inspection, while the Pages workflow owns publication.

The Pages workflow runs when documentation inputs change on `master` or `main`,
and it can also be started manually from the **Actions** tab. It performs the
same checks as the local documentation build:

1. Checks out the repository and its required submodules.
2. Installs the pinned documentation dependencies from
   `docs/requirements.txt`.
3. Verifies that the generated support matrix is current.
4. Builds MkDocs with `--strict` into `site/`.
5. Uploads `site/` as the official Pages artifact.
6. Deploys that artifact through the protected `github-pages` environment.

The expected site URL is
<https://xsession.github.io/openocd/>. The project-site base path is already
encoded in `mkdocs.yml` as `site_url`; do not publish the repository root or a
local `docs/_build` directory as the Pages artifact.

### First-time repository setup

In the repository settings, open **Pages** and set **Build and deployment →
Source** to **GitHub Actions**. The workflow supplies the required
`pages:write` and `id-token:write` permissions only to its deployment job. If
the repository uses environment protection rules, approve the `github-pages`
deployment when prompted.

### Troubleshooting a deployment

- If the workflow does not start, check that the change matches the path filter
  and that it was pushed to `master` or `main`; use **Run workflow** for a
  manual deployment.
- If the build job fails, reproduce it locally with the commands in
  [Documentation workflow](../development/documentation.md).
- If the artifact uploads but deployment fails, check the repository Pages
  source, the `github-pages` environment, and the workflow permissions.
- If links work locally but not on Pages, verify `site_url` includes the
  repository path `/openocd/` and that the artifact path remains `site/`.
