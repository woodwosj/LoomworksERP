# -*- coding: utf-8 -*-
# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.
from loomworks.tests.common import BaseCase
from loomworks.addons.google_calendar.utils.google_calendar import GoogleEvent


class TestGoogleEvent(BaseCase):
    def test_google_event_readonly(self):
        event = GoogleEvent()
        with self.assertRaises(TypeError):
            event._events['foo'] = 'bar'
        with self.assertRaises(AttributeError):
            event._events.update({'foo': 'bar'})
        with self.assertRaises(TypeError):
            dict.update(event._events, {'foo': 'bar'})
