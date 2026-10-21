from odoo import models, fields


class ResBank(models.Model):
    _inherit = "res.bank"


    main_bank_id = fields.Many2one('main.bank', "Main bank")
    is_slips_allowed = fields.Boolean()