# -*- coding: utf-8 -*-
from odoo import fields, models, _


class SaleConfirmWizard(models.TransientModel):
    _name = 'sale.confirm.wizard'
    _description = 'Sale Order Confirmation - Unverified Contact'

    sale_order_id = fields.Many2one('sale.order', string='Sale Order', required=True)
    partner_id = fields.Many2one('res.partner', string='Contact', required=True)

    def action_verify_and_proceed(self):
        """Verify the contact and then confirm the sale order."""
        self.partner_id.action_verify_contact()
        return self.sale_order_id.action_confirm()

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}
