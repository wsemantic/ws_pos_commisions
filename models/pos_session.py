from odoo import api, fields, models, _, Command

from collections import defaultdict

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _accumulate_amounts(self, data):
        # We call the original method to obtain the base data.
        data = super(PosSession, self)._accumulate_amounts(data)
        
        # We create a new dictionary to accumulate by product, including tax_amount
        new_sales = defaultdict(lambda: {'amount': 0.0, 'amount_converted': 0.0, 'tax_amount': 0.0, 'product_id': None})
        
        # We process each closed order
        for order in self._get_closed_orders(): #17.0 self._get_closed_orders():
            if not order.is_invoiced:  # Only unbilled orders
                for order_line in order.lines:
                    line = self._prepare_line(order_line)
                    # We define the new key including product_id
                    sale_key = (
                        line['income_account_id'],
                        -1 if line['amount'] < 0 else 1,
                        tuple((tax['id'], tax['account_id'], tax['tax_repartition_line_id']) for tax in line['taxes']),
                        line['base_tags'],
                        order_line.product_id.id  # Add the product_id directly
                    )
                    # We accumulate the amounts
                    new_sales[sale_key] = self._update_amounts(
                        new_sales[sale_key],
                        {'amount': line['amount']},
                        line['date_order'],
                        round=False
                    )
                    # We accumulate tax_amount for each tax in line
                    for tax in line['taxes']:
                        new_sales[sale_key]['tax_amount'] += tax['amount']
                    # Save the product_id
                    new_sales[sale_key]['product_id'] = order_line.product_id.id
        
        # We replace the original dictionary
        data['sales'] = new_sales
        return data

    def _get_sale_vals(self, key, amount, amount_converted):
        # Unpack the key including product_id
        account_id, sign, tax_keys, base_tag_ids, product_id = key
        tax_ids = set(tax[0] for tax in tax_keys)
        applied_taxes = self.env['account.tax'].browse(tax_ids)
        title = _('Sales') if sign == 1 else _('Refund')
        name = _('%s untaxed', title)
        if applied_taxes:
            name = _('%s with %s', title, ', '.join([tax.name for tax in applied_taxes]))
        
        # Create the dictionary for the accounting line
        partial_vals = {
            'name': name,
            'account_id': account_id,
            'move_id': self.move_id.id,
            'tax_ids': [(6, 0, tax_ids)],
            'tax_tag_ids': [(6, 0, base_tag_ids)],
            'product_id': product_id,  # Añadimos el product_id
        }
        return self._credit_amounts(partial_vals, amount, amount_converted)