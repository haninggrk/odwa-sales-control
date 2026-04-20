# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ── Connection ────────────────────────────────────────────

    odwa_webhook_url = fields.Char(
        string='ODWA Webhook URL',
        config_parameter='odwa_sales_control.odwa_webhook_url',
        help='URL to send WhatsApp notifications (delivery date lock, manual send, etc). '
             'A JSON POST request with a "type" field will be sent.',
    )

    # ── Verification ──────────────────────────────────────────

    bypass_contact_verification = fields.Boolean(
        string='Bypass Contact Verification (WhatsApp)',
        config_parameter='odwa_sales_control.bypass_contact_verification',
        help='If enabled, WhatsApp bot can confirm orders even if the contact is not verified. '
             'Odoo UI will still show the verification warning.',
        default=False,
    )

    # ── Auto-Invoice ──────────────────────────────────────────

    auto_invoice_on_delivery = fields.Selection(
        [('off', 'Off'), ('full', 'Full Quantity Only'), ('on', 'Always')],
        string='Auto-Invoice on Delivery Validation',
        config_parameter='odwa_sales_control.auto_invoice_on_delivery',
        help='Off: no auto-invoice.\n'
             'Full Quantity Only: auto-create invoice only when all delivered quantities match demand.\n'
             'Always: auto-create invoice on every delivery validation.',
        default='full',
    )

    # ── WhatsApp Notifications ────────────────────────────────

    whatsapp_ui_sales_notification = fields.Boolean(
        string='WhatsApp Notification for UI Sales',
        config_parameter='odwa_sales_control.whatsapp_ui_sales_notification',
        help='If enabled, confirming a quotation from the Odoo UI will also '
             'send a WhatsApp notification to the customer.',
        default=False,
    )

    # ── Quotation Edit Link ───────────────────────────────────

    enable_quotation_edit_link = fields.Boolean(
        string='Quotation Edit Link (WhatsApp)',
        config_parameter='odwa_sales_control.enable_quotation_edit_link',
        help='If enabled, the WhatsApp bot includes an edit link when '
             'sending quotations, allowing customers to modify items.',
        default=False,
    )

    # ── Overdue Reminders ─────────────────────────────────────

    overdue_reminder_days = fields.Integer(
        string='Overdue Payment Reminder (days)',
        config_parameter='odwa_sales_control.overdue_reminder_days',
        help='Number of days after the invoice due date to send a WhatsApp reminder. '
             '0 = disabled.',
        default=0,
    )

    # ── Delivery Notification Timezone ────────────────────────

    odwa_delivery_timezone = fields.Char(
        string='Delivery Notification Timezone',
        config_parameter='odwa_sales_control.delivery_timezone',
        help='Timezone used for the delivery-ready notification send window (07:00–20:00). '
             'Use a pytz timezone name, e.g. Asia/Jakarta (WIB), Asia/Makassar (WITA), '
             'Asia/Jayapura (WIT). Defaults to Asia/Jakarta if not set.',
        default='Asia/Jakarta',
    )
