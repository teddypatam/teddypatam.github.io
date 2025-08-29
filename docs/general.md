# Teddy Bears Portfolio (Flask + Frozen-Flask)

Static portfolio website for hand-crafted teddy bears. Content is stored as Markdown files with YAML front matter (like Jekyll), and the site is frozen to static HTML for GitHub Pages.

Supports multiple languages (currently `en` and `ru`) with locale-prefixed URLs.

## Quick start

1. Create and activate a virtual environment
```bash
python3 -m venv .venv && source .venv/bin/activate
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Run locally (dynamic Flask)
```bash
BASE_URL=http://localhost:5000 FLASK_APP=app.py FLASK_ENV=development flask run --debug
```
Visit `http://localhost:5000/`.

4. Freeze to static site (outputs to `_site/`)
```bash
python freeze.py
```

## Content (Markdown with front matter)

- Add/edit bears (or other crafted items) in `content/<lang>/bears/*.md`.
- Front matter fields:
  - `slug` (required), `name`, `group` (optional), `creation_date` (optional), `summary`, `size`, `materials`, `cover_image`, `images` (list), `store_links` (optional dictionary), `pinned` (optional, possible value: `yes`, `true`, `1`)
- The Markdown body becomes the detailed description.

## Languages

- Supported: `en`, `ru`. Default: `en`.
- URLs:
  - Home: `/<lang>/`
  - Item: `/<lang>/bear/<slug>/`
  - About: `/<lang>/about/`
  - Contact: `/<lang>/contact/`
- UI strings are located at `content/<lang>/pages/ui.md`
- <Base URL> without language id in path is redirected to <Base URL>/en

## Media

- Place images under `static/images/` and reference them by relative path in markdown (*.md) files.

## Structure
```
app.py
freeze.py
requirements.txt
/ content
    /en
        /bears
            honey-biscuit.md
            rose-cream.md
            sage-meadow.md
        /pages
            about.md
            contact.md
            ui.md
    /ru
        /bears
            honey-biscuit.md
            rose-cream.md
            sage-meadow.md
        /pages
            about.md
            contact.md
            ui.md
/ templates
    base.html
    index.html
    item_detail.html
    about.html
    contact.html
    redirect.html
    sitemap.xml
/ static
    /css/styles.css
    /images/*
/ _site (generated)
```
