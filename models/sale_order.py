# -*- coding: utf-8 -*-
import json
import logging

import requests as http_requests

from odoo import fields, models, _

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    partner_verified = fields.Boolean(
        related='partner_id.is_verified',
        string='Contact Verified',
    )

    def action_confirm(self):
        for order in self:
            if not order.partner_id.is_verified:
                return {
                    'type': 'ir.actions.act_window',
                    'name': _('Contact Not Verified'),
                    'res_model': 'sale.confirm.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'default_sale_order_id': order.id,
                        'default_partner_id': order.partner_id.id,
                    },
                }
        res = super().action_confirm()
        # Send WhatsApp notification for UI sales if enabled
        self._send_ui_sales_notification()
        return res

    def _send_ui_sales_notification(self):
        """Send WhatsApp notification to customer when order is confirmed from UI."""
        enabled = self.env['ir.config_parameter'].sudo().get_param(
            'odwa_sales_control.whatsapp_ui_sales_notification', 'False',
        )
        if enabled not in ('True', 'true'):
            return

        webhook_url = self.env['ir.config_parameter'].sudo().get_param(
            'odwa_sales_control.odwa_webhook_url',
        )
        if not webhook_url:
            return

        for order in self:
            if order.state != 'sale':
                continue
            partner = order.partner_id
            phone = partner.phone_sanitized or partner.phone or ''
            if not phone:
                continue

            # Ensure portal access token exists
            access_token = ''
            try:
                access_token = order.access_token or ''
                if not access_token and hasattr(order, '_portal_ensure_token'):
                    access_token = order._portal_ensure_token()
            except Exception:
                access_token = ''

            payload = {
                'type': 'order_confirmed_ui',
                'order_id': order.id,
                'order_name': order.name or '',
                'state': order.state or '',
                'access_token': access_token or '',
                'partner_id': partner.id,
                'partner_name': partner.name or '',
                'partner_phone': phone,
                'amount_total': order.amount_total or 0,
                'currency': order.currency_id.name if order.currency_id else 'IDR',
            }

            try:
                http_requests.post(
                    webhook_url,
                    data=json.dumps(payload),
                    headers={'Content-Type': 'application/json'},
                    timeout=10,
                )
            except Exception as e:
                _logger.warning('Failed to send UI sales WA notification for %s: %s', order.name, e)

    def _get_safe_access_token(self):
        """Return portal access token if available, empty string otherwise."""
        self.ensure_one()
        try:
            token = self.access_token or ''
            if not token and hasattr(self, '_portal_ensure_token'):
                token = self._portal_ensure_token()
            return token or ''
        except Exception:
            return ''

    def action_send_to_whatsapp(self):
        """Manually send quotation/order to customer via WhatsApp."""
        self.ensure_one()
        webhook_url = self.env['ir.config_parameter'].sudo().get_param(
            'odwa_sales_control.odwa_webhook_url',
        )
        if not webhook_url:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                    'params': {
                    'title': _('WhatsApp'),
                    'message': _('Webhook URL is not configured in settings.'),
                    'type': 'warning',
                    'sticky': False,
                },
            }

        partner = self.partner_id
        payload = {
            'type': 'send_order',
            'order_id': self.id,
            'order_name': self.name or '',
            'state': self.state or '',
            'access_token': self._get_safe_access_token(),
            'partner_id': partner.id if partner else False,
            'partner_name': partner.name if partner else '',
            'partner_phone': (partner.phone_sanitized or partner.phone or '') if partner else '',
            'amount_total': self.amount_total or 0,
            'currency': self.currency_id.name if self.currency_id else 'IDR',
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
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                    'params': {
                    'title': _('WhatsApp'),
                    'message': _('Failed to send WhatsApp notification.'),
                    'type': 'danger',
                    'sticky': False,
                },
            }

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
                'params': {
                'title': _('WhatsApp'),
                'message': _('Quotation sent to customer via WhatsApp.'),
                'type': 'success',
                'sticky': False,
            },
        }
