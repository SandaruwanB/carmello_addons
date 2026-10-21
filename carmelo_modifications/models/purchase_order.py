from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

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
        string="Total Discount",
        currency_field="currency_id",
        compute="_compute_discount_amounts",
        store=True,
    )

    @api.depends(
        'order_line.discount',
        'order_line.discount_type',
        'order_line.price_unit',
        'order_line.product_qty',
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
                    total_line_discount += (line.product_qty * line.price_unit) * (line.discount / 100.0)

            total_global_discount = 0.0
            if order.global_order_discount:
                if order.global_discount_type == 'percent':
                    base_amount = sum(line.price_subtotal for line in order.order_line.filtered(lambda l: not l.display_type))
                    total_global_discount = base_amount * (order.global_order_discount / 100.0)
                elif order.global_discount_type == 'fixed':
                    total_global_discount = order.global_order_discount

            order.total_global_discount = total_global_discount
            order.total_discount = total_line_discount + total_global_discount


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    discount = fields.Float(string="Discount", default=0.0)
    discount_type = fields.Selection(
        selection=[
            ('percent', 'Percent'),
            ('fixed', 'Fixed'),
        ],
        string="Discount Type",
        default='percent',
    )
    line_sub_total = fields.Monetary(
        string="Subtotal",
        compute="_compute_line_sub_total",
        currency_field="currency_id",
    )

    @api.depends('price_subtotal')
    def _compute_line_sub_total(self):
        for line in self:
            line.line_sub_total = line.price_subtotal
