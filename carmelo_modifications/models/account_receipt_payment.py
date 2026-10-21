from odoo import models, fields


class AccountReceiptPayment(models.Model):
    _name = "account.receipt.payment"
    _description = "Account Payment Receipt"

    name = fields.Char(string="Name")
    partner_id = fields.Many2one('res.partner', string="Partner")
    user_id = fields.Many2one('res.users', string="Sales Person", default=lambda self: self.env.user, required=True)
    receipt_date = fields.Date(string="Receipt Date", default=fields.Date.context_today)
    manual_receipt_no = fields.Char(string="Manual Receipt No")
    remark = fields.Char(string="Remark")
    total_amount = fields.Monetary(string="Total Amount", currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string="Currency", default=lambda self: self.env.company.currency_id)
    invoice_ids = fields.One2many('temp.account.move', 'line_id', string="Invoice")
    cash_payment_ids = fields.One2many('account.payment', 'receipt_id', string="Cash Payment")
    over_payment_ids = fields.One2many('account.payment', 'receipt_id', string="Over Payment")
    deposit_payment_ids = fields.One2many('account.payment', 'receipt_id', string="Deposit Payment")
    cheque_payment_ids = fields.One2many('pdc.wizard', 'receipt_id', string="Cheque Payment")
    payment_method_line_id = fields.Many2one('account.payment.method.line', string="Payment Method")
    available_payment_method_line_ids = fields.Many2many('account.payment.method.line', string="Available Payment Method Line")
    hide_payment_method_line = fields.Boolean(string="Hide Payment Method Line")
    payment_method_name = fields.Char(string="Payment Method")
    payment_type = fields.Selection(
        selection=[
            ('inbound', 'Receive Money'),
            ('outbound', 'Send Money'),
        ],
        string="Payment Type",
        default='inbound',
    )
    partner_type = fields.Selection(
        selection=[
            ('customer', 'Customer'),
            ('supplier', 'Vendor'),
        ],
        string="Partner Type",
        default='customer',
    )
    journal_id = fields.Many2one('account.journal', string="Journal")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)
    over_payment_amount = fields.Float(string="Over Payment Amount")
    main_bank_id = fields.Many2one('main.bank', string="Bank")
    branch_id = fields.Many2one('res.bank', string="Branch", domain="[('main_bank_id', '=', main_bank_id)]")
    partner_bank_account_id = fields.Many2one('res.partner.bank', string="Account No")
    cheque_no = fields.Char(string="Cheque No")
    cheque_date = fields.Date(string="Cheque Date")
    reference_no = fields.Char(string="Reference No")
    deposited_date = fields.Date(string="Deposited Date")
    lock = fields.Boolean(string="Source", default=False)
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('paid', 'Paid'),
        ],
        string="State",
        default='draft',
    )

