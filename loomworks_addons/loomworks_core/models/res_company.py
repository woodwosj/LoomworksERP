# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

from loomworks import models


class ResCompany(models.Model):
    """Extension of res.company for Loomworks branding.

    This model extension provides hooks for future Loomworks-specific
    company configuration options.
    """
    _inherit = 'res.company'
