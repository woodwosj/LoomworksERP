# -*- coding: utf-8 -*-
# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

import loomworks


def db_list(force=False, host=None):
    return []

loomworks.http.db_list = db_list
