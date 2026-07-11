from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def project_version() -> str:
    configure = ROOT / "configure.ac"
    if configure.exists():
        text = configure.read_text(encoding="utf-8", errors="replace")
        match = re.search(r"AC_INIT\(\[OpenOCD\],\s*\[([^\]]+)\]", text)
        if match:
            return match.group(1)
    return "development"

project = "OpenOCD Multi-Platform Build"
author = "OpenOCD contributors and xsession"
release = project_version()
version = release

extensions = [
    "myst_parser",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.extlinks",
    "sphinx.ext.intersphinx",
    "sphinx_copybutton",
]

autosectionlabel_prefix_document = True
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "fieldlist",
    "tasklist",
]

source_suffix = {".rst": "restructuredtext", ".md": "markdown"}
master_doc = "index"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "furo"
html_title = "OpenOCD Build & Deployment Guide"
html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_theme_options = {
    "navigation_with_keys": True,
    "source_repository": "https://github.com/xsession/openocd/",
    "source_branch": "master",
    "source_directory": "docs/",
}

extlinks = {
    "repo": ("https://github.com/xsession/openocd/%s", "%s"),
    "upstream": ("https://github.com/openocd-org/openocd/%s", "%s"),
}

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

nitpicky = False
