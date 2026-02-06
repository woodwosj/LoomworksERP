# -*- coding: utf-8 -*-
# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

import base64

import loomworks.tests
from loomworks.tools import mute_logger


@loomworks.tests.common.tagged('post_install', '-at_install')
class TestMedia(loomworks.tests.HttpCase):

    @mute_logger('loomworks.addons.http_routing.models.ir_http', 'loomworks.http')
    def test_01_replace_media(self):
        SVG = base64.b64encode(b'<svg xmlns="http://www.w3.org/2000/svg"></svg>')
        self.env['ir.attachment'].create({
            'name': 'sample.svg',
            'public': True,
            'mimetype': 'image/svg+xml',
            'datas': SVG,
        })
        self.start_tour("/", 'test_replace_media', login="admin")

    def test_02_image_link(self):
        self.start_tour("/", 'test_image_link', login="admin")
