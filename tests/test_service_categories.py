"""Reporting-line crosswalk regression tests (run with python -m unittest discover -s tests)."""
import unittest
from app.service_categories import category_for_apt, category_for_operational, CATEGORY_LABELS
from app.services import get_all_routes
from app.compare_service import comparison_catalog, get_comparison


class ServiceCategoryTests(unittest.TestCase):
    def test_known_fra_reporting_lines(self):
        cases = {
            'APT_RT_01': 'acela',
            'APT_RT_05': 'nec_other',
            'APT_RT_09': 'state_supported',
            'APT_RT_27': 'long_distance',
            'APT_RT_99': 'special',
            'APT_RT_88': 'special',
        }
        for code, expected in cases.items():
            with self.subTest(code=code):
                self.assertEqual(category_for_apt(code), expected)

    def test_catalog_and_compare_agree(self):
        routes = get_all_routes()
        self.assertEqual(len(routes), 55)
        self.assertTrue(all(r['category'] in CATEGORY_LABELS for r in routes))
        self.assertEqual(
            {r['slug']: r['category'] for r in comparison_catalog()},
            {r['slug']: r['category'] for r in routes},
        )
        self.assertEqual(get_comparison(['downeaster'])['routes'][0]['category'], 'state_supported')

    def test_operational_unmapped_is_not_guessed(self):
        self.assertEqual(category_for_operational('Acela'), 'acela')
        self.assertEqual(category_for_operational('Northeast Regional'), 'nec_other')
        self.assertEqual(category_for_operational('Downeaster'), 'state_supported')
        self.assertEqual(category_for_operational('Unknown service name'), 'special')


if __name__ == '__main__':
    unittest.main()
