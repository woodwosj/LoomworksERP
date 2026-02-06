# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard


def uninstall_hook(env):
    env["res.partner"]._clear_removed_edi_formats("vn_sinvoice")
