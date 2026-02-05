# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

from . import models
from . import services
from . import controllers


def post_init_hook(env):
    """
    Post-installation hook to register snapshot AI tools.

    This ensures the snapshot tool provider is registered with the
    AI tool registry after module installation.
    """
    # Trigger tool registration
    registry = env['loomworks.ai.tool.registry']
    registry.discover_and_register_all_tools()
