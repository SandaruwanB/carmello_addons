from odoo import models, fields



class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"


    main_bank_id = fields.Many2one("main.bank", "Main Bank")
    account_type = fields.Selection(selection=[
        ('savings', 'Savings'),
        ('hold', 'Hold'),
        ('current', 'Current'),
    ],)