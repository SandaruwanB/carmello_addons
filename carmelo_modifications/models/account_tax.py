from odoo import models, fields


class AccountTax(models.Model):
    _inherit = "account.tax"


    vat_type = fields.Selection(
        selection=[
            ('vat', 'VAT Registered'),
            ('svat', 'SVAT Registered'),
            ('non_vat', 'Non-VAT'),
        ],
        string="VAT Type",
        default='non_vat',
    )