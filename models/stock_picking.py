# -*- coding: utf-8 -*-
import json
import logging

import requests as http_requests

from odoo import fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = ['stock.picking', 'portal.mixin']
    _name = 'stock.picking'

    is_date_locked = fields.Boolean(
        'Delivery Date Locked', default=False, tracking=True,
    )

    def action_lock_date(self):
        self.ensure_one()
        if not self.scheduled_date:
            raise UserError(_('Please set the delivery date before locking it.'))
        self.is_date_locked = True
        self._send_odwa_webhook('delivery_locked')
        return True

    def action_unlock_date(self):
        self.ensure_one()
        self.is_date_locked = False
        self._send_odwa_webhook('delivery_unlocked')
        return True

    def action_send_to_whatsapp(self):
        """Manually send delivery notification to customer via WhatsApp."""
        self.ensure_one()
        self._send_odwa_webhook('send_delivery')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
                'params': {
                'title': _('WhatsApp'),
                'message': _('Delivery notification sent to customer.'),
                'type': 'success',
                'sticky': False,
            },
        }

    def write(self, vals):
        if 'scheduled_date' in vals and 'is_date_locked' not in vals:
            for picking in self:
                if picking.is_date_locked:
                    raise UserError(_(
                        'Delivery date is locked. '
                        'Please unlock it before changing the date.'
                    ))
        res = super().write(vals)
        # After saving a new scheduled_date, prompt to lock
        if 'scheduled_date' in vals and 'is_date_locked' not in vals:
            for picking in self:
                if not picking.is_date_locked and picking.scheduled_date and picking.sale_id:
                    return {
                        'type': 'ir.actions.act_window',
                        'name': _('Lock Delivery Date?'),
                        'res_model': 'stock.picking.lock.wizard',
                        'view_mode': 'form',
                        'target': 'new',
                        'context': {'default_picking_id': picking.id},
                    }
        return res

    def button_validate(self):
        """Override to auto-create invoice after delivery validation."""
        res = super().button_validate()
        self._try_auto_invoice()
        return res

    def _try_auto_invoice(self):
        """Auto-create invoices based on the auto_invoice_on_delivery setting."""
        setting = self.env['ir.config_parameter'].sudo().get_param(
            'odwa_sales_control.auto_invoice_on_delivery', 'full',
        )
        if setting == 'off':
            return

        for picking in self:
            if picking.state != 'done':
                continue
            sale_order = picking.sale_id if hasattr(picking, 'sale_id') else None
            if not sale_order:
                continue
            # Skip if already fully invoiced
            if sale_order.invoice_status != 'to invoice':
                continue

            if setting == 'full':
                # Only if all move lines have qty_done == demand
                all_match = all(
                    m.quantity == m.product_uom_qty
                    for m in picking.move_ids
                    if m.state == 'done'
                )
                if not all_match:
                    continue

            try:
                invoice = sale_order._create_invoices()
                if invoice:
                    invoice.action_post()
                    _logger.info(
                        'Auto-created invoice %s for SO %s (picking %s)',
                        invoice.name, sale_order.name, picking.name,
                    )
            except Exception as e:
                _logger.warning(
                    'Auto-invoice failed for SO %s (picking %s): %s',
                    sale_order.name, picking.name, e,
                )

    def _send_odwa_webhook(self, webhook_type):
        webhook_url = self.env['ir.config_parameter'].sudo().get_param(
            'odwa_sales_control.odwa_webhook_url',
        )
        if not webhook_url:
            return

        for picking in self:
            sale_order = picking.sale_id if hasattr(picking, 'sale_id') else None
            partner = picking.partner_id

            # Ensure portal access token exists for PDF download
            access_token = picking.access_token or ''
            if not access_token:
                access_token = picking._portal_ensure_token()

            # Determine delivery sequence (1 of N)
            delivery_index = 1
            delivery_total = 1
            if sale_order:
                all_pickings = self.env['stock.picking'].search(
                    [('sale_id', '=', sale_order.id), ('picking_type_code', '=', 'outgoing')],
                    order='id asc',
                )
                delivery_total = len(all_pickings)
                for idx, p in enumerate(all_pickings, 1):
                    if p.id == picking.id:
                        delivery_index = idx
                        break

            payload = {
                'type': webhook_type,
                'picking_id': picking.id,
                'picking_name': picking.name or '',
                'access_token': access_token,
                'sale_order_id': sale_order.id if sale_order else False,
                'sale_order_name': sale_order.name if sale_order else (picking.origin or ''),
                'scheduled_date': picking.scheduled_date.isoformat() if picking.scheduled_date else '',
                'partner_id': partner.id if partner else False,
                'partner_name': partner.name if partner else '',
                'partner_phone': (partner.phone_sanitized or partner.phone or '') if partner else '',
                'delivery_index': delivery_index,
                'delivery_total': delivery_total,
            }

            try:
                http_requests.post(
                    webhook_url,
                    data=json.dumps(payload),
                    headers={'Content-Type': 'application/json'},
                    timeout=10,
                )
            except Exception as e:
                _logger.warning('Failed to send ODWA webhook: %s', e)
