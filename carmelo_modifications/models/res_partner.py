from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    vat_type = fields.Selection(
        selection=[
            ('non_vat', 'Non-VAT'),
            ('vat', 'VAT Registered'),
            ('s_vat', 'SVAT Registered'),
            ('svat', 'SVAT Registered'),
        ],
        string="VAT Type",
        default='non_vat',
    )
    svat_no = fields.Text()
    remaining_credit_limit = fields.Float(readonly=True) # maximum credit limit - current credit limit (block invoicing if credit limit exceed)