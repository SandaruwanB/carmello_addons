from odoo import models, fields


class AccountPayment(models.Model):
    _inherit = "account.payment"

    payment_method_name = fields.Char(string="Payment Method Name")
    main_bank_id = fields.Many2one("main.bank", string="Main Bank")
    branch_id = fields.Many2one("res.bank", string="Branch", domain="[('main_bank_id', '=', main_bank_id)]")
    partner_bank_account_id = fields.Many2one("res.partner.bank", string="Account No")
    cheque_no = fields.Char(string="Cheque No")
    cheque_date = fields.Date(string="Cheque Date")
    reference_no = fields.Char(string="Reference No")
    deposited_date = fields.Date(string="Deposited Date")
    receipt_id = fields.Many2one("account.receipt.payment", string="Receipt")