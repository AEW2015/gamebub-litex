# SPDX-License-Identifier: 0BSD
"""Check local Markdown links after repository layout changes."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DocumentationTests(unittest.TestCase):
    def test_local_links_exist(self):
        documents = list(ROOT.glob("*.md"))
        for directory in ("docs", "examples", "tests"):
            documents.extend((ROOT / directory).rglob("*.md"))
        for document in documents:
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
                if "://" in target or target.startswith(("#", "mailto:")):
                    continue
                with self.subTest(document=document.relative_to(ROOT), target=target):
                    self.assertTrue((document.parent / target.split("#")[0]).exists())
