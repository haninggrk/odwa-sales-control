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

    @http.route('/api/odwa/create_invoice', type='http', auth='public', methods=['POST'], csrf=False)
    def create_invoice(self, **kwargs):
        """Create and post an invoice from a sale order.
        Called by the Node.js app after delivery confirmation.
        Validates Bearer token using Odoo's API key system.
        Returns invoice info or error as JSON.
        """
        import json

        def _json_response(data, status=200):
            body = json.dumps({'jsonrpc': '2.0', 'result': data})
            return request.make_response(body, headers=[
                ('Content-Type', 'application/json'),
            ])

        # Validate bearer token via Odoo's API key lookup
        auth_header = request.httprequest.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return _json_response({'error': 'Unauthorized'}, 401)
        api_key = auth_header[7:].strip()
        if not api_key:
            return _json_response({'error': 'Unauthorized'}, 401)

        try:
            uid = request.env['res.users.apikeys'].sudo()._check_credentials(scope='rpc', key=api_key)
        except Exception:
            uid = None
        if not uid:
            return _json_response({'error': 'Unauthorized'}, 401)

        # Parse JSON body
        try:
            body = json.loads(request.httprequest.get_data(as_text=True))
            order_id = body.get('params', {}).get('order_id')
        except Exception:
            return _json_response({'error': 'Invalid request body'})

        if not order_id:
            return _json_response({'error': 'order_id is required'})

        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists():
            return _json_response({'error': 'Sale order not found'})

        # Check if invoice already exists (e.g. auto-created on delivery validation)
        existing_invoices = order.invoice_ids.filtered(lambda i: i.state == 'posted' and i.move_type == 'out_invoice')
        if existing_invoices:
            invoice = existing_invoices[0]
            return _json_response({
                'success': True,
                'invoice_id': invoice.id,
                'invoice_name': invoice.name,
                'access_token': invoice.access_token or '',
                'already_existed': True,
            })

        if order.invoice_status != 'to invoice':
            return _json_response({'error': f'Order not invoiceable (status: {order.invoice_status})'})

        try:
            invoice = order._create_invoices()
            if not invoice:
                return _json_response({'error': 'No invoice created'})
            invoice.action_post()
            return _json_response({
                'success': True,
                'invoice_id': invoice.id,
                'invoice_name': invoice.name,
                'access_token': invoice.access_token or '',
                'already_existed': False,
            })
        except Exception as e:
            _logger.warning('ODWA create_invoice failed for SO %s: %s', order.name, e)
            return _json_response({'error': str(e)})
