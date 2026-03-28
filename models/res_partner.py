# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_verified = fields.Boolean('Verified', default=False, tracking=True)
    verified_by = fields.Many2one(
        'res.users', string='Verified By', readonly=True, tracking=True,
    )
    verified_date = fields.Datetime(
        'Verified Date', readonly=True, tracking=True,
    )

    def action_verify_contact(self):
        self.write({
            'is_verified': True,
            'verified_by': self.env.uid,
            'verified_date': fields.Datetime.now(),
        })

    def action_unverify_contact(self):
        self.write({
            'is_verified': False,
            'verified_by': False,
            'verified_date': False,
        })
