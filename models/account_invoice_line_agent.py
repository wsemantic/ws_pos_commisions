# -*- coding: utf-8 -*-

from odoo import fields, models

class AccountInvoiceLineAgent(models.Model):
    _inherit = "account.invoice.line.agent"
    
    date = fields.Date(
        string="Accounting date",
        related="invoice_id.date",
        store=True,
        readonly=True,
    )
