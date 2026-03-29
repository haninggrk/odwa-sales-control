# -*- coding: utf-8 -*-
{
    'name': 'ODWA Sales Control',
    'version': '19.0.2.0.2',
    'category': 'Sales',
    'summary': 'WhatsApp sales control: verification, auto-invoice, delivery lock, reminders & more',
    'description': """
        ODWA Sales Control - Complete WhatsApp Sales Package

        Features:
        - Contact verification with audit trail
        - Quotation confirmation control (verify & proceed wizard)
        - Delivery date locking with WhatsApp notifications
        - Auto-invoice on delivery validation (Off / Full Qty Only / Always)
        - WhatsApp notification for UI-triggered sales (optional)
        - Quotation edit link via WhatsApp (optional)
        - Overdue payment reminders via WhatsApp cron (configurable days)
        - Multiple delivery naming (Delivery 1 of N)
        - Date change → lock prompt wizard
        - Send to WhatsApp buttons on SO and Delivery forms
    """,
    'author': 'ODWA',
    'depends': ['sale_management', 'stock', 'account', 'portal'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'wizard/sale_confirm_wizard_views.xml',
        'wizard/stock_picking_lock_wizard_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/stock_picking_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
