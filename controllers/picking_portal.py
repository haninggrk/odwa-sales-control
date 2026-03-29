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

    @http.route('/api/odwa/create_invoice', type='json', auth='api_key', methods=['POST'])
    def create_invoice(self, order_id, **kwargs):
        """Create and post an invoice from a sale order.
        Called by the Node.js app after delivery confirmation.
        Returns invoice info or error.
        """
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists():
            return {'error': 'Sale order not found'}

        if order.invoice_status != 'to invoice':
            return {'error': f'Order not invoiceable (status: {order.invoice_status})'}

        try:
            invoice = order._create_invoices()
            if not invoice:
                return {'error': 'No invoice created'}
            invoice.action_post()
            return {
                'success': True,
                'invoice_id': invoice.id,
                'invoice_name': invoice.name,
                'access_token': invoice.access_token or '',
            }
        except Exception as e:
            _logger.warning('ODWA create_invoice failed for SO %s: %s', order.name, e)
            return {'error': str(e)}
