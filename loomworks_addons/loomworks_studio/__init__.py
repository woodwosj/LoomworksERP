# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

from . import models
from . import controllers


def post_init_hook(env):
    """Register Studio AI tools after module installation."""
    registry = env['loomworks.ai.tool.registry']
    registry.discover_and_register_all_tools()


def uninstall_hook(env):
    """Unregister Studio AI tools before module uninstallation."""
    try:
        provider = env['loomworks.studio.tool.provider']
        provider._unregister_tools()
    except Exception:
        pass
