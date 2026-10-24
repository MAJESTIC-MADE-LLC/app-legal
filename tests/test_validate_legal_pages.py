from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.validate_legal_pages import validate


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class LegalPageValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name) / "site"
        shutil.copytree(
            REPOSITORY_ROOT,
            self.root,
            ignore=shutil.ignore_patterns(".git", "__pycache__"),
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def assert_has_error(self, fragment: str) -> None:
        self.assertTrue(
            any(fragment in error for error in validate(self.root)),
            msg=f"Expected an error containing {fragment!r}",
        )

    def test_repository_fixture_is_valid(self) -> None:
        self.assertEqual(validate(self.root), [])

    def test_missing_required_page_is_rejected(self) -> None:
        (self.root / "skepbook/privacy/index.html").unlink()
        self.assert_has_error("skepbook/privacy/index.html: missing page")

    def test_incorrect_canonical_url_is_rejected(self) -> None:
        path = self.root / "skepbook/privacy/index.html"
        path.write_text(
            path.read_text().replace("/skepbook/privacy/", "/wrong/privacy/"),
            encoding="utf-8",
        )
        self.assert_has_error("expected one canonical URL")

    def test_broken_local_link_is_rejected(self) -> None:
        path = self.root / "skepbook/index.html"
        path.write_text(
            path.read_text().replace('href="privacy/"', 'href="missing/"'),
            encoding="utf-8",
        )
        self.assert_has_error("broken local link 'missing/'")

    def test_active_product_placeholder_is_rejected(self) -> None:
        path = self.root / "skepbook/support/index.html"
        path.write_text(
            path.read_text().replace("<main", "<!-- Draft placeholder --><main"),
            encoding="utf-8",
        )
        self.assert_has_error("active product still contains placeholder copy")

    def test_concept_notice_must_be_visible_on_every_page(self) -> None:
        for suffix in ("index.html", "privacy/index.html", "terms/index.html", "support/index.html"):
            with self.subTest(page=suffix):
                path = self.root / "campsake" / suffix
                original = path.read_text()
                # A comment preserves the source strings but does not inform a reader.
                path.write_text(original.replace("Pre-release", "Preview").replace("not released", "unavailable").replace("</main>", "<!-- Pre-release: not released --></main>"))
                self.assert_has_error("concept needs visible Pre-release and not released notices")
                path.write_text(original)

    def test_hidden_concept_notice_is_rejected(self) -> None:
        path = self.root / "campsake/index.html"
        path.write_text(path.read_text().replace("Pre-release", "Preview").replace("not released", "unavailable").replace("</main>", '<p hidden>Pre-release: not released</p></main>'))
        self.assert_has_error("concept needs visible Pre-release and not released notices")

    def test_unfinished_copy_on_concept_page_is_rejected(self) -> None:
        path = self.root / "campsake/privacy/index.html"
        path.write_text(path.read_text().replace("</main>", "<p>Replace this paragraph.</p></main>"))
        self.assert_has_error("unfinished placeholder copy")

    def test_base_element_is_rejected(self) -> None:
        path = self.root / "skepbook/index.html"
        path.write_text(
            path.read_text().replace("</head>", '<base href="https://example.com/">\n  </head>'),
            encoding="utf-8",
        )
        self.assert_has_error("disallowed active content: <base>")

    def test_inline_event_handler_is_rejected(self) -> None:
        path = self.root / "skepbook/index.html"
        path.write_text(
            path.read_text().replace("<body>", '<body onload="alert(1)">'),
            encoding="utf-8",
        )
        self.assert_has_error("disallowed active content: body[onload]")

    def test_unsafe_link_scheme_is_rejected(self) -> None:
        path = self.root / "skepbook/index.html"
        path.write_text(
            path.read_text().replace('href="privacy/"', 'href="javascript:alert(1)"'),
            encoding="utf-8",
        )
        self.assert_has_error("unsafe link scheme is not allowed")

    def test_remote_stylesheet_is_rejected(self) -> None:
        path = self.root / "skepbook/index.html"
        path.write_text(
            path.read_text().replace(
                "</head>",
                '<link rel="stylesheet" href="https://example.com/site.css">\n  </head>',
            ),
            encoding="utf-8",
        )
        self.assert_has_error("stylesheet must be local")

    def test_uninventoried_app_folder_is_rejected(self) -> None:
        shutil.copytree(self.root / "campsake", self.root / "untracked-app")
        self.assert_has_error("site folders missing from inventory: untracked-app")

    def test_index_omission_is_rejected(self) -> None:
        path = self.root / "index.html"
        path.write_text(
            path.read_text().replace('href="skepbook/"', 'href="campsake/"', 1),
            encoding="utf-8",
        )
        self.assert_has_error("index.html: missing app link 'skepbook'")

    def test_inventory_name_mismatch_is_rejected(self) -> None:
        inventory_path = self.root / "legal-pages.json"
        inventory_path.write_text(
            inventory_path.read_text().replace('"name": "Skepbook"', '"name": "Wrong"'),
            encoding="utf-8",
        )
        self.assert_has_error("h1 does not identify 'Wrong'")

    def test_device_local_disclosures_match_release_boundaries(self) -> None:
        expected_privacy_copy = {
            "fine-notes": ("device-bound", "automatic operating-system backup"),
            "skepbook": ("device-bound", "automatic iOS backups"),
            "paws": ("device-bound", "automatic operating-system backup"),
            "namefold": ("device-bound", "automatic iOS backups"),
            "pantry-clock": ("device-bound", "automatic operating-system backup"),
        }

        for slug, fragments in expected_privacy_copy.items():
            source = (self.root / slug / "privacy/index.html").read_text(
                encoding="utf-8"
            )
            for fragment in fragments:
                self.assertIn(fragment, source, msg=f"{slug} is missing {fragment!r}")

    def test_hub_disclosures_match_the_submission_boundary(self) -> None:
        privacy = (self.root / "majestic-made-hub/privacy/index.html").read_text()
        support = (self.root / "majestic-made-hub/support/index.html").read_text()
        for fragment in (
            "Cloudflare Pages", "Cloudflare D1", "Cloudflare Turnstile", "Cloudflare Access",
            "authentication cookies", "six-hour sessions", "twelve months",
            "bounded batches as new submissions are processed", "inactivity can delay deletion",
            "does not send an automatic confirmation", "do not expose stored records",
        ):
            self.assertIn(fragment, privacy)
        self.assertIn("no automatic confirmation email", support)
        self.assertNotIn("Supabase", privacy)
        self.assertNotIn("does not intentionally set cookies", privacy)
        self.assertNotIn("Stripe", privacy)

    def test_missing_legacy_alias_is_rejected(self) -> None:
        (self.root / "almanac/privacy/index.html").unlink()
        self.assert_has_error("almanac/privacy/index.html: missing page")

    def test_unknown_legacy_target_is_rejected(self) -> None:
        path = self.root / "legacy-urls.json"
        mapping = json.loads(path.read_text())
        mapping["almanac"] = "unknown-product"
        path.write_text(json.dumps(mapping))
        self.assert_has_error("unknown canonical target")

    def test_unsafe_legacy_slug_is_rejected(self) -> None:
        path = self.root / "legacy-urls.json"
        mapping = json.loads(path.read_text())
        mapping["../escape"] = mapping.pop("almanac")
        path.write_text(json.dumps(mapping))
        self.assert_has_error("unsafe legacy slug")

    def test_canonical_slug_cannot_be_a_legacy_alias(self) -> None:
        path = self.root / "legacy-urls.json"
        mapping = json.loads(path.read_text())
        mapping["fine-notes"] = "skepbook"
        path.write_text(json.dumps(mapping))
        self.assert_has_error("legacy slug is already canonical")

    def test_duplicate_legacy_slug_is_rejected(self) -> None:
        (self.root / "legacy-urls.json").write_text('{"almanac":"fine-notes","almanac":"skepbook"}')
        self.assert_has_error("duplicate legacy slug")

    def test_alias_refresh_must_match_fixed_canonical_target(self) -> None:
        path = self.root / "almanac/privacy/index.html"
        original = path.read_text()
        for replacement in (
            "0;url=https://example.com/",
            "0;url=javascript:alert(1)",
            "1;url=https://legal.majesticmade.dev/fine-notes/privacy/",
            "0;url=https://legal.majesticmade.dev/fine-notes/support/",
        ):
            with self.subTest(refresh=replacement):
                path.write_text(original.replace("0;url=https://legal.majesticmade.dev/fine-notes/privacy/", replacement))
                self.assert_has_error("unexpected meta refresh")
        path.write_text(original)

    def test_second_alias_refresh_is_rejected(self) -> None:
        path = self.root / "almanac/privacy/index.html"
        path.write_text(path.read_text().replace("</head>", '<meta http-equiv="refresh" content="0;url=https://legal.majesticmade.dev/fine-notes/privacy/"></head>'))
        self.assert_has_error("unexpected meta refresh")

    def test_duplicate_refresh_attributes_are_rejected(self) -> None:
        path = self.root / "almanac/privacy/index.html"
        path.write_text(path.read_text().replace(
            'http-equiv="refresh"',
            'content="0;url=https://example.com/" http-equiv="refresh"',
        ))
        self.assert_has_error("meta[duplicate attributes]")

    def test_canonical_page_cannot_refresh(self) -> None:
        path = self.root / "fine-notes/privacy/index.html"
        path.write_text(path.read_text().replace("</head>", '<meta http-equiv=" Refresh " content="0;url=https://legal.majesticmade.dev/fine-notes/privacy/"></head>'))
        self.assert_has_error("unexpected meta refresh")

    def test_alias_keeps_active_content_restrictions(self) -> None:
        path = self.root / "almanac/index.html"
        path.write_text(path.read_text().replace("</main>", "<script>alert(1)</script></main>"))
        self.assert_has_error("disallowed active content: <script>")

    def test_alias_needs_visible_current_link(self) -> None:
        path = self.root / "almanac/privacy/index.html"
        original = path.read_text()
        path.write_text(original.replace('class="continue-link"', 'hidden class="continue-link"'))
        self.assert_has_error("alias needs a visible link")


if __name__ == "__main__":
    unittest.main()
