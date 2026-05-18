# GeoAI Docs — Publisher Guide

> **This file is excluded from the published site** (via `exclude_patterns` in `_config.yml`).

## Published URL

<https://azure.github.io/microsoft-planetary-computer-pro/geoai>

## Technology

This site is built with [Jupyter Book](https://jupyterbook.org/) (a Sphinx-based documentation system) and deployed via GitHub Pages using GitHub Actions.

---

## Folder Structure

```
docs/geoai/
├── _config.yml          # Book configuration (title, logo, repo links, excludes)
├── _toc.yml             # Table of contents — defines site navigation
├── requirements.txt     # Python dependencies for building the book
├── intro.md             # Landing page (root of the book)
├── overview.md          # Getting Started > Overview
├── logo.png             # Site logo (displayed in left sidebar)
├── models/
│   └── placeholder.md   # Models section placeholder
├── examples/
│   └── placeholder.md   # Examples section placeholder
└── README.md            # THIS FILE (excluded from build)
```

---

## Adding Content

### Add a Markdown Page

1. Create a `.md` file in the appropriate folder (e.g., `docs/geoai/models/aurora.md`).
2. Use [MyST Markdown](https://myst-parser.readthedocs.io/) syntax (superset of CommonMark with directives).
3. Add the file to `_toc.yml` under the relevant `chapters` section:

   ```yaml
   - caption: Models
     chapters:
       - file: models/aurora
       - file: models/placeholder
   ```

4. Commit and push to `main`. The site rebuilds automatically.

### Add a Jupyter Notebook

1. Place the `.ipynb` file in the relevant folder (e.g., `docs/geoai/examples/my_notebook.ipynb`).
2. Reference it in `_toc.yml` without the extension:

   ```yaml
   - caption: Examples
     chapters:
       - file: examples/my_notebook
   ```

3. Notebooks are **not re-executed** during build (`execute_notebooks: "off"` in `_config.yml`). Commit them with outputs already rendered, or change this setting if you want CI to run them.

### Add a New Section

1. Create a subfolder under `docs/geoai/` (e.g., `docs/geoai/tutorials/`).
2. Add content files inside it.
3. Add a new `- caption:` block to `_toc.yml`:

   ```yaml
   - caption: Tutorials
     chapters:
       - file: tutorials/getting_started
       - file: tutorials/advanced
   ```

---

## Editing Content

- Edit any `.md` or `.ipynb` file directly.
- Changes pushed to `main` on paths matching `docs/geoai/**` trigger an automatic rebuild.
- Use standard MyST Markdown features:
  - `{note}`, `{warning}`, `{tip}` admonitions
  - `{code-block}` for syntax-highlighted code
  - Cross-references with `{ref}` or file-based links

---

## Removing Content

1. Delete the `.md` or `.ipynb` file.
2. Remove the corresponding `- file:` entry from `_toc.yml`.
3. Commit and push.

> **Warning:** If you delete a file but forget to remove it from `_toc.yml`, the build will fail.

---

## Publishing (Deployment)

Deployment is fully automated:

- **Trigger:** Any push to `main` that modifies files in `docs/geoai/`.
- **Manual trigger:** Use the "Run workflow" button on the `Build and Deploy GeoAI Docs` action in the Actions tab.
- **What happens:**
  1. GitHub Actions checks out the repo.
  2. Installs Python dependencies from `docs/geoai/requirements.txt`.
  3. Runs `jupyter-book build docs/geoai`.
  4. Deploys the built HTML to the `gh-pages` branch under the `geoai/` directory.

### First-Time Setup (Repo Admin)

1. **Enable GitHub Pages** in the repo settings:
   - Go to **Settings → Pages**
   - Source: **Deploy from a branch**
   - Branch: `gh-pages` / `/ (root)`
2. Ensure the `GITHUB_TOKEN` has write permissions:
   - **Settings → Actions → General → Workflow permissions → Read and write permissions**
3. Push any change to `docs/geoai/` on `main` to trigger the first build.

---

## Local Development

Preview the site locally before pushing:

```bash
# Install dependencies
pip install -r docs/geoai/requirements.txt

# Build
jupyter-book build docs/geoai

# Open in browser
open docs/geoai/_build/html/index.html    # macOS
start docs/geoai/_build/html/index.html   # Windows
```

---

## Configuration Reference

| File | Purpose |
|------|---------|
| `_config.yml` | Book metadata, Sphinx extensions, repo links, theme, exclusions |
| `_toc.yml` | Navigation structure — sections, chapters, ordering |
| `requirements.txt` | Python packages needed to build the book |
| `.github/workflows/build_geoai_docs.yml` | CI/CD workflow for automated deployment |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Build fails with "file not found" | Ensure every file in `_toc.yml` exists on disk |
| Page not appearing in nav | Add it to `_toc.yml` and rebuild |
| Notebook renders without outputs | Commit the notebook with cell outputs, or enable `execute_notebooks` |
| CSS/styling issues | Clear `docs/geoai/_build/` and rebuild: `jupyter-book clean docs/geoai` |
| Site not updating after push | Check the Actions tab for build errors; ensure paths filter matches |
