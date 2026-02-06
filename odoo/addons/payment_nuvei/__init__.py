# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models

from loomworks.addons.payment import reset_payment_provider, setup_provider


def post_init_hook(env):
    setup_provider(env, 'nuvei')


def uninstall_hook(env):
    reset_payment_provider(env, 'nuvei')
