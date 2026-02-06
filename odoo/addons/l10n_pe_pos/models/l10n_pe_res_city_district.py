# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.
from loomworks import fields, models, api


class L10nPeResCityDistrict(models.Model):
    _name = "l10n_pe.res.city.district"
    _inherit = ["l10n_pe.res.city.district", "pos.load.mixin"]

    country_id = fields.Many2one(related="city_id.country_id")
    state_id = fields.Many2one(related="city_id.state_id")

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ["name", "city_id", "country_id", "state_id"]
