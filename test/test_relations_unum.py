import unittest

import relations_unum


class TestModule(unittest.TestCase):

    maxDiff = None

    def test_module(self):

        self.assertIn("Relations Unum", relations_unum.__doc__)
