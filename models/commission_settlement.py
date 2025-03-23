# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import groupby


class CommissionSettlement(models.Model):
    _inherit = "commission.settlement"

    def _get_invoice_partner(self):
        partner = fields.first(self).agent_id
        related_company = self.env['res.company'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        if related_company and related_company.parent_id:
            return related_company.parent_id.partner_id
        return partner