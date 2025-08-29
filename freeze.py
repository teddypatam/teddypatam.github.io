#!/usr/bin/env python3

from app import app, load_bears, SUPPORTED_LANGS
from flask_frozen import Freezer
from pathlib import Path


freezer = Freezer(app)


@freezer.register_generator
def index():
    for lang in SUPPORTED_LANGS:
        yield {"lang": lang}


@freezer.register_generator
def about():
    for lang in SUPPORTED_LANGS:
        yield {"lang": lang}


@freezer.register_generator
def contact():
    for lang in SUPPORTED_LANGS:
        yield {"lang": lang}


@freezer.register_generator
def bear_detail():
    for lang in SUPPORTED_LANGS:
        for bear in load_bears(lang):
            yield {"lang": lang, "slug": bear.get("slug")}


def main() -> None:
    # Ensure destination exists
    dest = Path(app.config.get("FREEZER_DESTINATION", "docs"))
    dest.mkdir(parents=True, exist_ok=True)
    freezer.freeze()


if __name__ == "__main__":
    main()
