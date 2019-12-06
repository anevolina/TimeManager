import unittest
from single_timer import check_single_timer

class TestSingle(unittest.TestCase):

    def test_check_single_timer(self):

        self.assertFalse(check_single_timer('  67  '))
        self.assertTrue(check_single_timer('50 check email'))
        self.assertFalse(check_single_timer('call Jane'))
