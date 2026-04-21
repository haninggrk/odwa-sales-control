# -*- coding: utf-8 -*-
import json
import logging

import requests as http_requests

from odoo import models, api

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    # ── Invoice posted → send invoice notification ────────────

    def action_post(self):
        res = super().action_post()
        for move in self:
            if move.move_type == 'out_invoice':
                move._send_invoice_created_webhook()
        return res

    def _send_invoice_created_webhook(self):
        """Send invoice_created webhook to Node.js when a customer invoice is posted."""
        webhook_url = self.env['ir.config_parameter'].sudo().get_param(
            'odwa_sales_control.odwa_webhook_url',
        )
        if not webhook_url:
            return

        partner = self.partner_id
        if not partner:
            return
        phone = partner.phone_sanitized or partner.phone or ''
        if not phone:
            return

        # Get / create access token for portal link
        access_token = ''
        try:
            access_token = self.access_token or ''
            if not access_token and hasattr(self, '_portal_ensure_token'):
                access_token = self._portal_ensure_token()
        except Exception:
            pass

        payload = {
            'type': 'invoice_created',
            'invoice_id': self.id,
            'invoice_name': self.name or '',
            'access_token': access_token,
            'amount_total': self.amount_total,
            'amount_residual': self.amount_residual,
            'currency': self.currency_id.name if self.currency_id else 'IDR',
            'invoice_date_due': self.invoice_date_due.isoformat() if self.invoice_date_due else '',
            'sale_order_name': self.invoice_origin or '',
            'partner_id': partner.id,
            'partner_name': partner.name or '',
            'partner_phone': phone,
        }

        try:
            http_requests.post(
                webhook_url,
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'},
                timeout=10,
            )
        except Exception as e:
            _logger.warning('Failed to send invoice webhook for %s: %s', self.name, e)

    # ── Overdue reminder cron ─────────────────────────────────

    @api.model
    def _cron_send_overdue_reminders(self):
        """Cron job: send WhatsApp reminders for overdue invoices."""
        days_str = self.env['ir.config_parameter'].sudo().get_param(
            'odwa_sales_control.overdue_reminder_days', '0',
        )
        try:
            days = int(days_str)
        except (ValueError, TypeError):
            days = 0
        if days <= 0:
            return

        webhook_url = self.env['ir.config_parameter'].sudo().get_param(
            'odwa_sales_control.odwa_webhook_url',
        )
        if not webhook_url:
            return

        from datetime import timedelta
        from odoo.fields import Date

        cutoff = Date.today() - timedelta(days=days)

        overdue_invoices = self.search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('invoice_date_due', '<=', cutoff),
        ])

        for inv in overdue_invoices:
            partner = inv.partner_id
            phone = partner.phone_sanitized or partner.phone or ''
            if not phone:
                continue

            payload = {
                'type': 'overdue_reminder',
                'invoice_id': inv.id,
                'invoice_name': inv.name or '',
                'amount_residual': inv.amount_residual,
                'currency': inv.currency_id.name if inv.currency_id else 'IDR',
                'invoice_date_due': inv.invoice_date_due.isoformat() if inv.invoice_date_due else '',
                'partner_id': partner.id,
                'partner_name': partner.name or '',
                'partner_phone': phone,
                'sale_order_name': inv.invoice_origin or '',
            }

            try:
                http_requests.post(
                    webhook_url,
                    data=json.dumps(payload),
                    headers={'Content-Type': 'application/json'},
                    timeout=10,
                )
            except Exception as e:
                _logger.warning('Failed to send overdue reminder for %s: %s', inv.name, e)
