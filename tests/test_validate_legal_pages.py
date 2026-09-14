from __future__ import annotations

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
        (self.root / "apiary/privacy/index.html").unlink()
        self.assert_has_error("apiary/privacy/index.html: missing page")

    def test_incorrect_canonical_url_is_rejected(self) -> None:
        path = self.root / "apiary/privacy/index.html"
        path.write_text(
            path.read_text().replace("/apiary/privacy/", "/wrong/privacy/"),
            encoding="utf-8",
        )
        self.assert_has_error("expected one canonical URL")

    def test_broken_local_link_is_rejected(self) -> None:
        path = self.root / "apiary/index.html"
        path.write_text(
            path.read_text().replace('href="privacy/"', 'href="missing/"'),
            encoding="utf-8",
        )
        self.assert_has_error("broken local link 'missing/'")

    def test_active_product_placeholder_is_rejected(self) -> None:
        path = self.root / "apiary/support/index.html"
        path.write_text(
            path.read_text().replace("<main", "<!-- Draft placeholder --><main"),
            encoding="utf-8",
        )
        self.assert_has_error("active product still contains placeholder copy")

    def test_uninventoried_app_folder_is_rejected(self) -> None:
        shutil.copytree(self.root / "bivy", self.root / "untracked-app")
        self.assert_has_error("site folders missing from inventory: untracked-app")

    def test_index_omission_is_rejected(self) -> None:
        path = self.root / "index.html"
        path.write_text(
            path.read_text().replace('href="apiary/"', 'href="bivy/"', 1),
            encoding="utf-8",
        )
        self.assert_has_error("index.html: missing app link 'apiary'")

    def test_inventory_name_mismatch_is_rejected(self) -> None:
        inventory_path = self.root / "legal-pages.json"
        inventory_path.write_text(
            inventory_path.read_text().replace('"name": "Apiary"', '"name": "Wrong"'),
            encoding="utf-8",
        )
        self.assert_has_error("h1 does not identify 'Wrong'")

    def test_device_local_disclosures_match_release_boundaries(self) -> None:
        expected_privacy_copy = {
            "almanac": ("device-bound", "automatic operating-system backup"),
            "apiary": ("device-bound", "automatic iOS backups"),
            "paws": ("device-bound", "automatic operating-system backup"),
            "reach-me": ("device-bound", "automatic iOS backups"),
            "use-by": ("device-bound", "automatic operating-system backup"),
        }

        for slug, fragments in expected_privacy_copy.items():
            source = (self.root / slug / "privacy/index.html").read_text(
                encoding="utf-8"
            )
            for fragment in fragments:
                self.assertIn(fragment, source, msg=f"{slug} is missing {fragment!r}")

    def test_hub_disclosures_match_the_submission_boundary(self) -> None:
        privacy = (self.root / "majestic-made-hub/privacy/index.html").read_text()
        self.assertIn("Supabase", privacy)
        self.assertIn("cannot read stored records", privacy)
        self.assertIn("does not intentionally set cookies", privacy)
        self.assertNotIn("Stripe", privacy)


if __name__ == "__main__":
    unittest.main()
