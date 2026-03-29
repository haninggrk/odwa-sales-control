# -*- coding: utf-8 -*-
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PickingPortalController(http.Controller):

    @http.route('/my/picking/pdf/<int:picking_id>', type='http', auth='public', website=False)
    def picking_pdf(self, picking_id, access_token=None, **kwargs):
        picking = request.env['stock.picking'].sudo().browse(picking_id)
        if not picking.exists():
            return request.not_found()
        if not access_token or not picking.access_token or access_token != picking.access_token:
            return request.not_found()

        pdf_content, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
            'stock.action_report_delivery', [picking.id],
        )
        headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', f'attachment; filename=Delivery_{picking.name}.pdf'),
            ('Content-Length', len(pdf_content)),
        ]
        return request.make_response(pdf_content, headers=headers)
