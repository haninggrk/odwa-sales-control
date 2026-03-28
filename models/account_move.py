# -*- coding: utf-8 -*-
import json
import logging

import requests as http_requests

from odoo import models, api

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

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
