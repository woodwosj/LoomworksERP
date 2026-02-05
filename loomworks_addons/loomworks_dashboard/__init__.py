# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

from . import models
from . import controllers
from . import services


def _register_dashboard_tools(env):
    """
    Post-init hook to register dashboard AI tools.
    Called after module installation to ensure tools are available.
    """
    if 'loomworks.ai.tool.registry' in env:
        env['loomworks.ai.tool.registry'].discover_and_register_all_tools()
