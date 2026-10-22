import unittest

from scripts.wizz_api import extract_wizz_api_base


class WizzApiResolverTests(unittest.TestCase):
    def test_extracts_current_versioned_api_base(self):
        html = 'window.apiUrl="https://be.wizzair.com/29.22.0/Api";'
        self.assertEqual(
            extract_wizz_api_base(html),
            "https://be.wizzair.com/29.22.0/Api",
        )

    def test_returns_none_without_official_api_url(self):
        self.assertIsNone(extract_wizz_api_base("https://www.wizzair.com/en-gb"))


if __name__ == "__main__":
    unittest.main()
