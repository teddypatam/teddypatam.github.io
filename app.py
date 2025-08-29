#!/usr/bin/env python3

from datetime import datetime
from flask import Flask, render_template, abort
from pathlib import Path
from typing import List, Dict, Any

import frontmatter
import markdown as md
import os

BASE_DIR = Path(__file__).parent
CONTENT_ROOT = BASE_DIR / "content"
STATIC_DIR = BASE_DIR / "static"
SUPPORTED_LANGS = ["en", "ru"]
DEFAULT_LANG = "ru"
# Base URL configuration - override with environment variable for local development
BASE_URL = os.environ.get("BASE_URL", "https://teddypatam.github.io")


# Load UI strings for specific language
def load_ui_strings(lang: str) -> Dict[str, str]:
    """Load UI strings from the language-specific ui.md file"""
    ui_path = CONTENT_ROOT / lang / "pages" / "ui.md"
    if not ui_path.exists():
        raise FileNotFoundError(f"Missing UI strings file: {ui_path}")

    post = frontmatter.load(ui_path)
    return dict(post.metadata or {})


# Load bear data from markdown files
def load_bears(lang: str) -> List[Dict[str, Any]]:
    content_dir = CONTENT_ROOT / lang / "bears"
    if not content_dir.exists():
        raise FileNotFoundError(f"Missing content directory: {content_dir}")

    strings = load_ui_strings(lang)

    bears: List[Dict[str, Any]] = []
    for path in content_dir.glob("*.md"):
        if path.name == "template.md":
            print("Skipping template file:", path)
            continue # Skip template file
        post = frontmatter.load(path)
        meta: Dict[str, Any] = post.metadata or {}
        slug = meta.get("slug") or path.stem
        name = meta.get("name") or slug.replace("-", " ").title()
        summary = meta.get("summary") or ""
        size = meta.get("size")
        materials = meta.get("materials")
        cover_image = meta.get("cover_image") or meta.get("cover")
        images = meta.get("images") or []
        group = meta.get("group")
        store_links = meta.get("store_links") or {}

        # Handle pinned attribute - convert various truthy values
        pinned = meta.get("pinned")
        if isinstance(pinned, str):
            pinned = pinned.lower() in ("true", "yes", "1")
        elif isinstance(pinned, (int, float)):
            pinned = bool(pinned)
        else:
            pinned = bool(pinned)

        description_md: str = post.content or ""
        description_html = (
            md.markdown(description_md, extensions=["extra", "sane_lists", "smarty"])
            if description_md
            else ""
        )

        # Handle creation date from metadata or file creation time
        creation_date_str = str(meta.get("creation_date", "")).strip()
        if len(creation_date_str) > 0:
            try:
                creation_date = datetime.strptime(creation_date_str, "%Y-%m-%d")
            except (ValueError, TypeError):
                print(
                    f"Warning: Invalid date format for {slug}, using file modification time."
                )
                # Fallback to file modification time if date string is invalid
                creation_date = datetime.fromtimestamp(path.stat().st_mtime)
        else:
            # Use file modification time if no date provided
            creation_date = datetime.fromtimestamp(path.stat().st_mtime)

        formatted_date = creation_date.strftime("%d.%m.%Y")
        # Generate schema.org markup for product
        schema = {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": name,
            "description": summary,
            "brand": {"@type": "Brand", "name": strings["site_title"]},
        }

        if size:
            schema["size"] = size
        if materials:
            schema["material"] = materials
        if cover_image:
            schema["image"] = f"{BASE_URL}/static/{cover_image}"

        # Generate SEO metadata
        canonical_url = f"{BASE_URL}/{lang}/bear/{slug}/"
        alternate_urls = {
            alt_lang: f"{BASE_URL}/{alt_lang}/bear/{slug}/"
            for alt_lang in SUPPORTED_LANGS
            if alt_lang != lang
        }

        bears.append(
            {
                "slug": slug,
                "name": name,
                "summary": summary,
                "size": size,
                "creation_date": creation_date.timestamp(),  # For sorting
                "formatted_date": formatted_date,  # For display
                "materials": materials,
                "cover_image": cover_image,
                "images": images,
                "group": group,
                "store_links": store_links,
                "description_html": description_html,
                "pinned": pinned,
                # SEO metadata
                "meta": {
                    "title": name,
                    "description": summary,
                    "keywords": meta.get("keywords"),
                    "og_type": "product",
                    "og_image": (
                        f"{BASE_URL}/static/{cover_image}" if cover_image else None
                    ),
                    "canonical_url": canonical_url,
                    "alternate_urls": alternate_urls,
                    "schema": schema,
                },
            }
        )

    # Sort by pinned status first, then by creation date
    bears.sort(key=lambda b: (-1 if b.get("pinned") else 0, -b.get("creation_date", 0)))
    return bears


app = Flask(__name__)
app.config["FREEZER_RELATIVE_URLS"] = True
app.config["FREEZER_DESTINATION"] = str(BASE_DIR / "_site")
app.config["FREEZER_REMOVE_EXTRA_FILES"] = True


@app.route("/sitemap.xml")
def sitemap():
    """Generate sitemap.xml for the entire site."""
    pages = []

    # Add index pages for each language
    for lang in SUPPORTED_LANGS:
        pages.append(
            {"loc": f"{BASE_URL}/{lang}/", "changefreq": "daily", "priority": "1.0"}
        )

        # Add about and contact pages
        pages.append(
            {
                "loc": f"{BASE_URL}/{lang}/about/",
                "changefreq": "monthly",
                "priority": "0.6",
            }
        )
        pages.append(
            {
                "loc": f"{BASE_URL}/{lang}/contact/",
                "changefreq": "monthly",
                "priority": "0.6",
            }
        )

        # Add all bears for this language
        bears = load_bears(lang)
        for bear in bears:
            pages.append(
                {
                    "loc": f"{BASE_URL}/{lang}/bear/{bear['slug']}/",
                    "changefreq": "weekly",
                    "priority": "0.8",
                    "lastmod": datetime.fromtimestamp(bear["creation_date"]).strftime(
                        "%Y-%m-%d"
                    ),
                }
            )

    sitemap_xml = render_template("sitemap.xml", pages=pages, base_url=BASE_URL)
    response = app.make_response(sitemap_xml)
    response.headers["Content-Type"] = "application/xml"
    return response


@app.route("/")
def root_redirect():
    return render_template("redirect.html", default_language=DEFAULT_LANG)


@app.route("/<lang>/")
def index(lang: str):
    if lang not in SUPPORTED_LANGS:
        abort(404)
    bears = load_bears(lang)
    # Unique groups preserving order, plus counts
    groups: List[str] = []
    group_counts: Dict[str, int] = {}
    for b in bears:
        g = b.get("group")
        if g:
            if g not in groups:
                groups.append(g)
            group_counts[g] = group_counts.get(g, 0) + 1
    total_count = len(bears)
    strings = load_ui_strings(lang)

    # Generate schema.org markup for collection page
    schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": strings["site_title"],
        "description": strings["intro"],
        "url": f"{BASE_URL}/{lang}/",
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": total_count,
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": idx + 1,
                    "url": f"{BASE_URL}/{lang}/bear/{bear['slug']}/",
                }
                for idx, bear in enumerate(bears[:10])  # Include first 10 items
            ],
        },
    }

    # Generate alternate URLs for other languages
    alternate_urls = {
        alt_lang: f"{BASE_URL}/{alt_lang}/"
        for alt_lang in SUPPORTED_LANGS
        if alt_lang != lang
    }

    meta = {
        "title": f"{strings['site_title']} - {strings['site_tagline']}",
        "description": strings["intro"],
        "keywords": strings.get("keywords"),
        "og_type": "website",
        "canonical_url": f"{BASE_URL}/{lang}/",
        "alternate_urls": alternate_urls,
        "schema": schema,
    }

    return render_template(
        "index.html",
        bears=bears,
        groups=groups,
        group_counts=group_counts,
        total_count=total_count,
        lang=lang,
        strings=strings,
        meta=meta,
    )


@app.route("/<lang>/bear/<slug>/")
def bear_detail(lang: str, slug: str):
    if lang not in SUPPORTED_LANGS:
        abort(404)
    bears = load_bears(lang)
    bear = next((b for b in bears if b.get("slug") == slug), None)
    if not bear:
        abort(404)
    strings = load_ui_strings(lang)
    return render_template(
        "item_detail.html", bear=bear, lang=lang, strings=strings, meta=bear["meta"]
    )


@app.route("/<lang>/about/")
def about(lang: str):
    if lang not in SUPPORTED_LANGS:
        abort(404)
    strings = load_ui_strings(lang)

    # Load the about page content
    about_path = CONTENT_ROOT / lang / "pages" / "about.md"
    if not about_path.exists():
        abort(404)

    post = frontmatter.load(about_path)
    meta = post.metadata or {}
    content = (
        md.markdown(post.content, extensions=["extra", "sane_lists", "smarty"])
        if post.content
        else ""
    )

    # Generate schema.org markup for organization
    schema = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "Teddy Patam",
        "description": post.content,
        "url": f"{BASE_URL}/{lang}/about/",
        "logo": "{BASE_URL}/static/images/logo.jpeg",
    }

    # Generate alternate URLs for other languages
    alternate_urls = {
        alt_lang: f"{BASE_URL}/{alt_lang}/about/"
        for alt_lang in SUPPORTED_LANGS
        if alt_lang != lang
    }

    about_meta = {
        "title": meta.get("title", strings["nav_about"]),
        "description": meta.get("description", content[:160] + "..."),
        "og_type": "website",
        "og_image": (
            f"{BASE_URL}/static/{meta.get('image')}" if meta.get("image") else None
        ),
        "canonical_url": f"{BASE_URL}/{lang}/about/",
        "alternate_urls": alternate_urls,
        "schema": schema,
    }

    page = {
        "title": meta.get("title", strings["nav_about"]),
        "image": meta.get("image"),
        "content": content,
    }

    return render_template(
        "about.html", lang=lang, strings=strings, page=page, meta=about_meta
    )


@app.route("/<lang>/contact/")
def contact(lang: str):
    if lang not in SUPPORTED_LANGS:
        abort(404)
    strings = load_ui_strings(lang)

    # Load the contact page content
    contact_path = CONTENT_ROOT / lang / "pages" / "contact.md"
    if not contact_path.exists():
        abort(404)

    post = frontmatter.load(contact_path)
    meta = post.metadata or {}
    content = (
        md.markdown(post.content, extensions=["extra", "sane_lists", "smarty"])
        if post.content
        else ""
    )

    # Generate schema.org markup for contact page
    schema = {
        "@context": "https://schema.org",
        "@type": "ContactPage",
        "name": meta.get("title", strings["nav_contact"]),
        "description": content,
        "url": f"{BASE_URL}/{lang}/contact/",
    }

    # Generate alternate URLs for other languages
    alternate_urls = {
        alt_lang: f"{BASE_URL}/{alt_lang}/contact/"
        for alt_lang in SUPPORTED_LANGS
        if alt_lang != lang
    }

    contact_meta = {
        "title": meta.get("title", strings["nav_contact"]),
        "description": meta.get("description", content[:160] + "..."),
        "og_type": "website",
        "canonical_url": f"{BASE_URL}/{lang}/contact/",
        "alternate_urls": alternate_urls,
        "schema": schema,
    }

    page = {
        "title": meta.get("title", strings["nav_contact"]),
        "content": content,
        "store_links": meta.get("store_links", {}),
    }

    return render_template(
        "contact.html", lang=lang, strings=strings, page=page, meta=contact_meta
    )


@app.route("/<lang>/legal/")
def legal(lang: str):
    if lang not in SUPPORTED_LANGS:
        abort(404)
    strings = load_ui_strings(lang)
    legal_path = CONTENT_ROOT / lang / "pages" / "legal.md"
    if not legal_path.exists():
        abort(404)
    post = frontmatter.load(legal_path)
    meta = post.metadata or {}
    content = md.markdown(post.content, extensions=["extra", "sane_lists", "smarty"]) if post.content else ""
    # Alternate URLs
    alternate_urls = {alt: f"{BASE_URL}/{alt}/legal/" for alt in SUPPORTED_LANGS if alt != lang}
    legal_meta = {
        "title": meta.get("title", strings.get("nav_legal", "Legal")),
        "description": meta.get("description", content[:160] + "..."),
        "og_type": "website",
        "canonical_url": f"{BASE_URL}/{lang}/legal/",
        "alternate_urls": alternate_urls,
    }
    page = {"title": meta.get("title", strings.get("nav_legal", "Legal")), "content": content}
    return render_template("legal.html", lang=lang, strings=strings, page=page, meta=legal_meta)


if __name__ == "__main__":
    app.run(debug=True)
