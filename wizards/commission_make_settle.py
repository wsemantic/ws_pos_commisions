# -*- coding: utf-8 -*-

from odoo import models, _
from datetime import date, timedelta
from itertools import groupby

class CommissionMakeSettle(models.TransientModel):
    _inherit = "commission.make.settle"
    
    def _get_account_settle_domain(self, agent, date_to_agent):
        return [
            '|',
            ("invoice_date", "<", date_to_agent),
            ("date", "<", date_to_agent),
            ("agent_id", "=", agent.id),
            ("settled", "=", False),
            ("object_id.display_type", "=", "product"),
        ]
        
    def _get_agent_lines(self, agent, date_to_agent):
        """Filter sales invoice agent lines for this type of settlement."""
        # if self.settlement_type != "sale_invoice":
        #     return super()._get_agent_lines(agent, date_to_agent)
        return self.env["account.invoice.line.agent"].search(
            self._get_account_settle_domain(agent, date_to_agent),
            order="invoice_date",
        )
        
    def action_settle(self):
        self.ensure_one()
        settlement_obj = self.env["commission.settlement"]
        settlement_line_obj = self.env["commission.settlement.line"]
        settlement_ids = []
        agents = self.agent_ids or self.env["res.partner"].search(
            [("agent", "=", True)]
        )
        date_to = self.date_to
        settlement_line_vals = []
        for agent in agents:
            date_to_agent = self._get_period_start(agent, date_to)
            # Get non settled elements
            grouped_agent_lines = groupby(
                sorted(
                    self._get_agent_lines(agent, date_to_agent),
                    key=self._agent_lines_sorted,
                ),
                key=self._agent_lines_groupby,
            )
            for _k, grouper_agent_lines in grouped_agent_lines:
                agent_lines = list(grouper_agent_lines)
                pos = 0
                sett_to = date(year=1900, month=1, day=1)
                settlement_line_vals = []
                while pos < len(agent_lines):
                    line = agent_lines[pos]
                    pos += 1
                    if line._skip_settlement():
                        continue
                    if (line.invoice_date and line.invoice_date > sett_to) or (line.date and line.date > sett_to):
                        if line.invoice_date:
                            sett_from = self._get_period_start(agent, line.invoice_date)
                        if line.date:
                            sett_from = self._get_period_start(agent, line.date)

                        sett_to = self._get_next_period_date(agent, sett_from)
                        sett_to -= timedelta(days=1)
                        settlement = self._get_settlement(
                            agent, line.company_id, line.currency_id, sett_from, sett_to
                        )
                        if not settlement:
                            settlement = settlement_obj.create(
                                self._prepare_settlement_vals(
                                    agent,
                                    line.company_id,
                                    sett_from,
                                    sett_to,
                                )
                            )
                            settlement.currency_id = line.currency_id
                        settlement_ids.append(settlement.id)
                    settlement_line_vals.append(
                        self._prepare_settlement_line_vals(settlement, line)
                    )
                settlement_line_obj.create(settlement_line_vals)
        # go to results
        if len(settlement_ids):
            return {
                "name": _("Created Settlements"),
                "type": "ir.actions.act_window",
                "views": [[False, "list"], [False, "form"]],
                "res_model": "commission.settlement",
                "domain": [["id", "in", settlement_ids]],
            }
        
    def _prepare_settlement_line_vals(self, settlement, line):
        """Prepare extra settlement values when the source is a sales invoice agent
        line.
        """
        res = super()._prepare_settlement_line_vals(settlement, line)
        if self.settlement_type == "sale_invoice":
            res.update(
                {
                    "date": line.invoice_date or line.date,
                }
            )
        return res
