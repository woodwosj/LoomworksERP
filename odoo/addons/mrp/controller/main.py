# -*- coding: utf-8 -*-
# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks.addons.product.controllers.product_document import ProductDocumentController


class MRPProductDocumentController(ProductDocumentController):

    def get_additional_create_params(self, **kwargs):
        super_values = super().get_additional_create_params(**kwargs)
        if kwargs.get('attached_on_bom'):
            return super_values | {'attached_on_mrp': 'bom'}
        return super_values
