# Copyright 2019 Camptocamp (https://www.camptocamp.com)

import unittest

from odoo.tests import common


class TestPickingZone(common.SavepointCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_success(self):
        self.assertTrue(True)

    @unittest.expectedFailure
    def test_fail(self):
        self.assertTrue(False)
