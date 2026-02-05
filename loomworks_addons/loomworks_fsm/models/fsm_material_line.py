# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class FSMMaterialLine(models.Model):
    """
    FSM Material Line - Products/materials used during field service.

    Tracks materials consumed on-site for inventory and invoicing purposes.
    """
    _name = 'fsm.material.line'
    _description = 'FSM Material Used'
    _order = 'id'

    task_id = fields.Many2one(
        'project.task',
        string='Task',
        required=True,
        ondelete='cascade',
        domain=[('is_fsm', '=', True)])
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        domain=[('type', 'in', ['consu', 'product'])])
    name = fields.Char(
        string='Description',
        compute='_compute_name',
        store=True,
        readonly=False)
    quantity = fields.Float(
        string='Quantity',
        default=1.0,
        required=True)
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        compute='_compute_product_uom',
        store=True,
        readonly=False)

    # Pricing
    price_unit = fields.Float(
        string='Unit Price',
        compute='_compute_price_unit',
        store=True,
        readonly=False)
    subtotal = fields.Float(
        string='Subtotal',
        compute='_compute_subtotal',
        store=True)

    # Currency
    currency_id = fields.Many2one(
        related='task_id.company_id.currency_id')

    # Inventory tracking (optional)
    lot_id = fields.Many2one(
        'stock.lot',
        string='Lot/Serial Number',
        domain="[('product_id', '=', product_id)]")

    @api.depends('product_id')
    def _compute_name(self):
        for line in self:
            if line.product_id:
                line.name = line.product_id.display_name
            else:
                line.name = ''

    @api.depends('product_id')
    def _compute_product_uom(self):
        for line in self:
            if line.product_id:
                line.product_uom_id = line.product_id.uom_id
            else:
                line.product_uom_id = False

    @api.depends('product_id')
    def _compute_price_unit(self):
        for line in self:
            if line.product_id:
                line.price_unit = line.product_id.list_price
            else:
                line.price_unit = 0.0

    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price_unit

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.display_name
            self.product_uom_id = self.product_id.uom_id
            self.price_unit = self.product_id.list_price
