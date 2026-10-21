from odoo import models, fields


class TempAccountMove(models.Model):
    _name = "temp.account.move"
    _description = "Temporary Account Move"

    line_id = fields.Many2one('account.receipt.payment', string="Line", ondelete='cascade')
    is_ticked = fields.Boolean(string="Is Ticked", default=False)
    invoice_id = fields.Many2one('account.move', string="Invoice No")
    invoice_date = fields.Date(string="Invoice Date")
    invoice_age = fields.Integer(string="Invoice Age")
    invoice_total = fields.Monetary(string="Invoice Total", currency_field='currency_id')
    invoice_actual_due = fields.Monetary(string="Invoice Actual Due", currency_field='currency_id')
    invoice_current_due = fields.Monetary(string="Invoice Current Due", currency_field='currency_id')
    invoice_paying_amount = fields.Monetary(string="Paying Amount", currency_field='paying_currency_id')
    currency_id = fields.Many2one('res.currency', string="Currency")
    paying_currency_id = fields.Many2one('res.currency', string="Currency")