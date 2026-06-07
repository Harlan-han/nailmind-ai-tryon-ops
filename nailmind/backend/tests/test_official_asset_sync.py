import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

import sync_official_assets as sync_assets


class OfficialAssetSyncTest(unittest.TestCase):
    def test_build_asset_plan_maps_official_links_to_deployable_upload_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            workbook_path = temp_path / "official.xlsx"
            uploads_dir = temp_path / "uploads"

            workbook = Workbook()
            designs = workbook.active
            designs.title = "款式图"
            designs.append(["序号", "原始款式图URL", "增强后款式图URL"])
            designs.append([1, "https://example.com/original-1.png", "https://example.com/enhanced-1.png"])
            hands = workbook.create_sheet("手图")
            hands.append(["手图URL", "款式图URL"])
            hands.append(["https://example.com/hand-1.png", "https://example.com/enhanced-1.png"])
            workbook.save(workbook_path)

            plan = sync_assets.build_asset_plan(workbook_path, uploads_dir)

        self.assertEqual(
            [(item.category, item.source_url, item.target_path.as_posix().split("/uploads/", 1)[1]) for item in plan],
            [
                ("design_original", "https://example.com/original-1.png", "designs/originals/design_01.jpg"),
                ("design_cover", "https://example.com/enhanced-1.png", "designs/design_01.jpg"),
                ("hand_photo", "https://example.com/hand-1.png", "hands/hand_01.jpg"),
            ],
        )

    def test_needs_download_skips_existing_valid_files_but_refreshes_tiny_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            valid_file = temp_path / "valid.jpg"
            tiny_file = temp_path / "tiny.jpg"
            valid_file.write_bytes(b"x" * 2048)
            tiny_file.write_bytes(b"x")

            self.assertFalse(sync_assets.needs_download(valid_file, force=False))
            self.assertTrue(sync_assets.needs_download(tiny_file, force=False))
            self.assertTrue(sync_assets.needs_download(valid_file, force=True))
