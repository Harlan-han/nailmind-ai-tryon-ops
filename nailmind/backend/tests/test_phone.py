import unittest

from fastapi import HTTPException

from app.services.phone import normalize_phone


class PhoneNormalizationTest(unittest.TestCase):
    def test_normalize_phone_strips_non_digits(self):
        self.assertEqual(normalize_phone(" 139-2000-1041 "), "13920001041")

    def test_normalize_phone_rejects_too_short_value(self):
        with self.assertRaises(HTTPException) as context:
            normalize_phone("123")

        self.assertEqual(context.exception.status_code, 400)

    def test_normalize_phone_rejects_too_long_value(self):
        with self.assertRaises(HTTPException) as context:
            normalize_phone("1" * 21)

        self.assertEqual(context.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
