# -*- coding: utf-8 -*-
from odoo import fields, models, _


class StockPickingLockWizard(models.TransientModel):
    _name = 'stock.picking.lock.wizard'
    _description = 'Lock Delivery Date Prompt'

    picking_id = fields.Many2one('stock.picking', required=True, readonly=True)

    def action_lock(self):
        self.ensure_one()
        self.picking_id.action_lock_date()
        return {'type': 'ir.actions.act_window_close'}

    def action_skip(self):
        return {'type': 'ir.actions.act_window_close'}
