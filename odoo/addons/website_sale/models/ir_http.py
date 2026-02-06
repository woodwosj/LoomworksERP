# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import models
from loomworks.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _pre_dispatch(cls, rule, args):
        super()._pre_dispatch(rule, args)
        affiliate_id = request.httprequest.args.get('affiliate_id')
        if affiliate_id:
            request.session['affiliate_id'] = int(affiliate_id)
