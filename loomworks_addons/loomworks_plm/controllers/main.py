# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class PlmController(http.Controller):
    """PLM Portal and API Controllers"""

    @http.route('/plm/eco/<int:eco_id>', type='http', auth='user', website=True)
    def eco_detail(self, eco_id, **kwargs):
        """Display ECO details page."""
        eco = request.env['plm.eco'].browse(eco_id)
        if not eco.exists():
            return request.redirect('/my')

        return request.render('loomworks_plm.eco_detail_page', {
            'eco': eco,
        })

    @http.route('/plm/api/eco/<int:eco_id>/approve', type='json', auth='user')
    def api_approve_eco(self, eco_id, comments=None):
        """API endpoint to approve ECO."""
        eco = request.env['plm.eco'].browse(eco_id)
        if not eco.exists():
            return {'error': 'ECO not found'}

        try:
            eco.action_approve()
            return {
                'success': True,
                'approval_state': eco.approval_state,
                'message': 'ECO approved successfully'
            }
        except Exception as e:
            return {'error': str(e)}

    @http.route('/plm/api/bom/<int:bom_id>/compare', type='json', auth='user')
    def api_compare_bom(self, bom_id, compare_bom_id=None):
        """API endpoint to compare BOMs."""
        bom = request.env['mrp.bom'].browse(bom_id)
        if not bom.exists():
            return {'error': 'BOM not found'}

        compare_bom = None
        if compare_bom_id:
            compare_bom = request.env['mrp.bom'].browse(compare_bom_id)
        else:
            compare_bom = bom.previous_bom_id

        if not compare_bom:
            return {'error': 'No comparison BOM available'}

        diff = bom.get_bom_diff(compare_bom)
        return {
            'success': True,
            'diff': diff,
            'bom1_revision': bom.revision_code,
            'bom2_revision': compare_bom.revision_code,
        }
