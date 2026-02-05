# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SignRequestItemValue(models.Model):
    """Completed Signature Field Value

    Stores the values entered by signers for each template field.
    Provides audit trail of what was signed.
    """
    _name = 'sign.request.item.value'
    _description = 'Signature Field Value'
    _order = 'create_date'

    signer_id = fields.Many2one(
        'sign.request.signer',
        string='Signer',
        required=True,
        ondelete='cascade',
        index=True
    )
    template_item_id = fields.Many2one(
        'sign.template.item',
        string='Template Field',
        required=True
    )

    # Related fields
    request_id = fields.Many2one(
        related='signer_id.request_id',
        store=True
    )
    item_type = fields.Selection(
        related='template_item_id.item_type',
        store=True
    )

    # Value Storage
    value = fields.Text(
        string='Text Value',
        help='Text content for text/date/name fields'
    )
    signature_image = fields.Binary(
        string='Signature Image',
        help='Base64 encoded signature/initial image'
    )

    # Metadata
    completed_date = fields.Datetime(
        string='Completed',
        default=fields.Datetime.now
    )

    def name_get(self):
        result = []
        for item_value in self:
            name = f"{item_value.template_item_id.type_id.name or 'Field'} - {item_value.signer_id.partner_id.name or 'Signer'}"
            result.append((item_value.id, name))
        return result
