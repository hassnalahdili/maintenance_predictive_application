import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.schemas.common import validate_password_strength
from app.services.export_utils import build_plain_pdf


class AddedFeaturesTest(unittest.TestCase):
    def test_password_policy_rejects_weak_password(self):
        with self.assertRaises(ValueError):
            validate_password_strength("short")

    def test_password_policy_accepts_strong_password(self):
        self.assertEqual(validate_password_strength("Strong123"), "Strong123")

    def test_plain_pdf_builder_returns_pdf_bytes(self):
        payload = build_plain_pdf("Rapport test", ["Machine A", "Alerte critique"])
        self.assertTrue(payload.startswith(b"%PDF-1.4"))
        self.assertIn(b"%%EOF", payload)


if __name__ == "__main__":
    unittest.main()
