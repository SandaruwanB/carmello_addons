import json
from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = "sale.order"
    _description = "Sales order inherited model"

    gp_approved_by = fields.Many2one('res.users', "GP Approved By") # gate pass approval
    credit_approved_by = fields.Many2one('res.users', "Credit Approved By")
    pt_approved_by = fields.Many2one('res.users', "PT Approved By")
    triggered_gp_margin_validation = fields.Boolean()
    triggered_credit_limit_validation = fields.Boolean()
    triggered_payment_term_validation = fields.Boolean()
    triggered_gp_margin_validation1 = fields.Boolean()
    triggered_credit_limit_validation1 = fields.Boolean()
    triggered_payment_term_validation1 = fields.Boolean()

    tax_totals_json = fields.Char(
        string="Tax Totals JSON",
        compute="_compute_tax_totals_json",
    )

    @api.depends('tax_totals', 'amount_untaxed', 'amount_tax', 'amount_total')
    def _compute_tax_totals_json(self):
        for order in self:
            subtotal_name = 'Untaxed Amount'
            totals = {
                'amount_total': order.amount_total,
                'amount_untaxed': order.amount_untaxed,
                'formatted_amount_total': f"{order.amount_total:,.2f}",
                'formatted_amount_untaxed': f"{order.amount_untaxed:,.2f}",
                'subtotals': [
                    {
                        'name': subtotal_name,
                        'amount': order.amount_untaxed,
                        'formatted_amount': f"{order.amount_untaxed:,.2f}",
                    }
                ],
                'groups_by_subtotal': {subtotal_name: []},
            }
            if order.amount_tax:
                totals['groups_by_subtotal'][subtotal_name].append({
                    'tax_group_name': 'VAT',
                    'tax_group_amount': order.amount_tax,
                    'tax_group_base_amount': order.amount_untaxed,
                    'formatted_tax_group_amount': f"{order.amount_tax:,.2f}",
                    'formatted_tax_group_base_amount': f"{order.amount_untaxed:,.2f}",
                    'tax_group_id': 1,
                })
            order.tax_totals_json = json.dumps(totals)

    global_discount_type = fields.Selection(
        selection=[
            ('percent', 'Percent'),
            ('fixed', 'Fixed'),
        ],
        string="Discount Type",
        default='percent',
    )
    global_order_discount = fields.Float(string="Global Discount", default=0.0)
    total_global_discount = fields.Monetary(
        string="Total Global Discount",
        currency_field="currency_id",
        compute="_compute_discount_amounts",
        store=True,
    )
    total_discount = fields.Monetary(
        string="Discount",
        currency_field="currency_id",
        compute="_compute_discount_amounts",
        store=True,
    )

    @api.depends(
        'order_line.discount',
        'order_line.discount_type',
        'order_line.price_unit',
        'order_line.product_uom_qty',
        'order_line.price_subtotal',
        'global_order_discount',
        'global_discount_type',
    )
    def _compute_discount_amounts(self):
        for order in self:
            total_line_discount = 0.0
            for line in order.order_line.filtered(lambda l: not l.display_type):
                if line.discount_type == 'fixed':
                    total_line_discount += line.discount
                else:
                    total_line_discount += (line.product_uom_qty * line.price_unit) * (line.discount / 100.0)

            total_global_discount = 0.0
            if order.global_order_discount:
                if order.global_discount_type == 'percent':
                    base_amount = sum(line.price_subtotal for line in order.order_line.filtered(lambda l: not l.display_type))
                    total_global_discount = base_amount * (order.global_order_discount / 100.0)
                elif order.global_discount_type == 'fixed':
                    total_global_discount = order.global_order_discount

            order.total_global_discount = total_global_discount
            order.total_discount = total_line_discount + total_global_discount


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    discount_type = fields.Selection(
        selection=[
            ('percent', 'Percent'),
            ('fixed', 'Fixed'),
        ],
        string="Discount Type",
        default='percent',
    )