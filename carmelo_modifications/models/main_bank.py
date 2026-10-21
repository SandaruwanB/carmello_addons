from odoo import models, fields


class MainBank(models.Model):
    _name = "main.bank"
    _description = "Main bank model"


    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code")
    branch_ids = fields.One2many("res.bank", "main_bank_id", string="Branches")