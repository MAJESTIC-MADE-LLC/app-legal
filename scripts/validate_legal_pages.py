#!/usr/bin/env python3
"""Validate the static legal-site inventory, structure, and local links."""

from __future__ import annotations

import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

BASE_URL = "https://legal.majesticmade.dev"
PAGE_KINDS = ("privacy", "terms", "support")
VALID_STATUSES = {"active", "placeholder"}
ALLOWED_LINK_SCHEMES = {"https", "mailto"}
DISALLOWED_ACTIVE_TAGS = {"base", "embed", "form", "iframe", "object", "script"}
SUPPORT_MAILTO = "mailto:support@majesticmade.dev"
PLACEHOLDER_MARKERS = (
    "draft placeholder",
    "replace this paragraph",
    "replace or expand this support page",
    "reserved for the",
)


class ParsedPage(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: set[str] = set()
        self.links: list[str] = []
        self.canonicals: list[str] = []
        self.stylesheets: list[str] = []
        self.text: list[str] = []
        self.headings: dict[str, list[str]] = {"h1": [], "h2": []}
        self.active_content: list[str] = []
        self._heading: str | None = None
        self._heading_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.add(tag)
        attributes = dict(attrs)
        if tag in DISALLOWED_ACTIVE_TAGS:
            self.active_content.append(f"<{tag}>")
        if tag == "meta" and (attributes.get("http-equiv") or "").lower() == "refresh":
            self.active_content.append("meta refresh")
        for name, _ in attrs:
            lowered_name = name.lower()
            if lowered_name.startswith("on") or lowered_name == "srcdoc":
                self.active_content.append(f"{tag}[{name}]")
        if tag == "a" and attributes.get("href") is not None:
            self.links.append(attributes["href"] or "")
        if tag == "link":
            relationships = set((attributes.get("rel") or "").split())
            href = attributes.get("href")
            if href is not None and "canonical" in relationships:
                self.canonicals.append(href)
            if href is not None and "stylesheet" in relationships:
                self.stylesheets.append(href)
        if tag in self.headings:
            self._heading = tag
            self._heading_text = []

    def handle_endtag(self, tag: str) -> None:
        if self._heading == tag:
            heading = " ".join(self._heading_text).strip()
            if heading:
                self.headings[tag].append(heading)
            self._heading = None
            self._heading_text = []

    def handle_data(self, data: str) -> None:
        value = data.strip()
        if value:
            self.text.append(value)
            if self._heading is not None:
                self._heading_text.append(value)


def _parse(path: Path) -> tuple[str, ParsedPage]:
    source = path.read_text(encoding="utf-8")
    parsed = ParsedPage()
    parsed.feed(source)
    return source, parsed


def _expected_file(root: Path, source: Path, href: str) -> Path | None:
    target = urlsplit(href)
    if target.scheme or target.netloc or href.startswith(("mailto:", "tel:", "#")):
        return None
    if not target.path:
        return None
    relative = unquote(target.path)
    candidate = (source.parent / relative).resolve()
    if relative.endswith("/") or candidate.is_dir():
        return candidate / "index.html"
    return candidate


def _validate_page(
    root: Path,
    path: Path,
    expected_canonical: str,
    expected_stylesheet: str,
    *,
    active: bool | None,
    kind: str | None,
    expected_name: str | None = None,
) -> list[str]:
    display = path.relative_to(root).as_posix()
    if not path.is_file():
        return [f"{display}: missing page"]
    if path.stat().st_size == 0:
        return [f"{display}: page is empty"]

    source, parsed = _parse(path)
    text = " ".join(parsed.text)
    lowered = source.lower()
    errors: list[str] = []
    for required in ("html", "head", "body", "title", "main", "h1"):
        if required not in parsed.tags:
            errors.append(f"{display}: missing <{required}>")
    if "<!doctype html>" not in lowered:
        errors.append(f"{display}: missing HTML doctype")
    if 'lang="en"' not in lowered:
        errors.append(f"{display}: missing lang=\"en\"")
    if 'name="viewport"' not in lowered:
        errors.append(f"{display}: missing viewport metadata")
    if parsed.canonicals != [expected_canonical]:
        errors.append(
            f"{display}: expected one canonical URL {expected_canonical!r}, "
            f"found {parsed.canonicals!r}"
        )
    if expected_stylesheet not in parsed.stylesheets:
        errors.append(f"{display}: missing stylesheet {expected_stylesheet!r}")
    if parsed.active_content:
        errors.append(
            f"{display}: disallowed active content: "
            f"{', '.join(sorted(set(parsed.active_content)))}"
        )
    if not parsed.headings["h1"]:
        errors.append(f"{display}: missing non-empty h1")
    elif expected_name is not None and not any(
        expected_name.lower() in heading.lower() for heading in parsed.headings["h1"]
    ):
        errors.append(f"{display}: h1 does not identify {expected_name!r}")

    for href in parsed.links:
        parsed_href = urlsplit(href)
        scheme = parsed_href.scheme.lower()
        if parsed_href.netloc and not scheme:
            errors.append(f"{display}: scheme-relative link is not allowed: {href!r}")
            continue
        if scheme not in ALLOWED_LINK_SCHEMES and scheme:
            errors.append(f"{display}: unsafe link scheme is not allowed: {href!r}")
            continue
        if scheme == "mailto" and href.lower() != SUPPORT_MAILTO:
            errors.append(f"{display}: unexpected support address: {href!r}")
            continue
        target = _expected_file(root, path, href)
        if target is None:
            continue
        try:
            target.relative_to(root.resolve())
        except ValueError:
            errors.append(f"{display}: local link escapes the site root: {href!r}")
            continue
        if not target.is_file():
            errors.append(f"{display}: broken local link {href!r}")

    for href in parsed.stylesheets:
        parsed_href = urlsplit(href)
        if parsed_href.scheme or parsed_href.netloc:
            errors.append(f"{display}: stylesheet must be local: {href!r}")
            continue
        target = _expected_file(root, path, href)
        if target is None:
            continue
        try:
            target.relative_to(root.resolve())
        except ValueError:
            errors.append(f"{display}: local link escapes the site root: {href!r}")
            continue
        if not target.is_file():
            errors.append(f"{display}: broken local link {href!r}")

    has_placeholder = any(marker in lowered for marker in PLACEHOLDER_MARKERS)
    if active is True and has_placeholder:
        errors.append(f"{display}: active product still contains placeholder copy")
    if active is False and not has_placeholder:
        errors.append(f"{display}: placeholder status is missing a placeholder warning")
    if active is True and kind in PAGE_KINDS:
        if "support@majesticmade.dev" not in lowered:
            errors.append(f"{display}: active legal page is missing the support address")
        minimum_sections = 3 if kind == "support" else 4
        if len(parsed.headings["h2"]) < minimum_sections:
            errors.append(
                f"{display}: active {kind} page needs at least {minimum_sections} sections"
            )
        if kind in {"privacy", "terms"} and "last updated" not in text.lower():
            errors.append(f"{display}: active {kind} page is missing an updated date")
    return errors


def validate(root: Path) -> list[str]:
    root = root.resolve()
    inventory_path = root / "legal-pages.json"
    if not inventory_path.is_file():
        return ["legal-pages.json: missing canonical inventory"]
    try:
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        return [f"legal-pages.json: invalid JSON: {error}"]
    if not isinstance(inventory, list):
        return ["legal-pages.json: top-level value must be a list"]

    errors: list[str] = []
    cname_path = root / "CNAME"
    if not cname_path.is_file() or cname_path.read_text(encoding="utf-8").strip() != "legal.majesticmade.dev":
        errors.append("CNAME: expected legal.majesticmade.dev")
    entries: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, raw in enumerate(inventory):
        if not isinstance(raw, dict):
            errors.append(f"legal-pages.json: entry {index} must be an object")
            continue
        slug = raw.get("slug")
        name = raw.get("name")
        status = raw.get("status")
        if not isinstance(slug, str) or not slug or slug in {"assets", "scripts", "tests"}:
            errors.append(f"legal-pages.json: entry {index} has an invalid slug")
            continue
        if slug in seen:
            errors.append(f"legal-pages.json: duplicate slug {slug!r}")
            continue
        seen.add(slug)
        if not isinstance(name, str) or not name.strip():
            errors.append(f"legal-pages.json: {slug!r} has an invalid name")
            continue
        if status not in VALID_STATUSES:
            errors.append(f"legal-pages.json: {slug!r} has invalid status {status!r}")
            continue
        entries.append({"slug": slug, "name": name, "status": status})

    discovered = {
        child.name
        for child in root.iterdir()
        if child.is_dir()
        and not child.name.startswith(".")
        and child.name not in {"assets", "scripts", "tests"}
        and (child / "index.html").is_file()
    }
    if seen != discovered:
        missing = sorted(seen - discovered)
        extra = sorted(discovered - seen)
        if missing:
            errors.append(f"inventory folders missing from site: {', '.join(missing)}")
        if extra:
            errors.append(f"site folders missing from inventory: {', '.join(extra)}")

    root_page = root / "index.html"
    errors.extend(
        _validate_page(
            root,
            root_page,
            f"{BASE_URL}/",
            "assets/site.css",
            active=None,
            kind=None,
        )
    )
    _, site_index = _parse(root_page)
    index_links = set(site_index.links)
    readme = (root / "README.md").read_text(encoding="utf-8")

    for entry in entries:
        slug = entry["slug"]
        active = entry["status"] == "active"
        if f"{slug}/" not in index_links:
            errors.append(f"index.html: missing app link {slug!r}")
        if f"`{slug}/`" not in readme:
            errors.append(f"README.md: missing app folder {slug!r}")
        errors.extend(
            _validate_page(
                root,
                root / slug / "index.html",
                f"{BASE_URL}/{slug}/",
                "../assets/site.css",
                active=active,
                kind=None,
                expected_name=entry["name"],
            )
        )
        for kind in PAGE_KINDS:
            errors.extend(
                _validate_page(
                    root,
                    root / slug / kind / "index.html",
                    f"{BASE_URL}/{slug}/{kind}/",
                    "../../assets/site.css",
                    active=active,
                    kind=kind,
                    expected_name=entry["name"],
                )
            )
    return errors


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    errors = validate(root)
    if errors:
        print("Legal-page validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Legal-page inventory, structure, status, and links are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
