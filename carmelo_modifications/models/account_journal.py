from odoo import models, fields


class AccountJournal(models.Model):
    _inherit = "account.journal"

    is_petty_cash = fields.Boolean(string="Is Petty Cash")
    enable_custom_sequence = fields.Boolean(string="Enable Custom Sequence")
    company_entity_code = fields.Char(string="Entity Code")
    sequence_reset_monthly = fields.Boolean(string="Reset Number Monthly")
    sequence_padding = fields.Integer(string="Number Padding")
    payment_sequence = fields.Boolean(string="Dedicated Payment Sequence")
    access_token = fields.Char(string="Security Token")
    renewal_contact_email = fields.Char(string="Connection Requests")
    autocheck_on_post = fields.Boolean(string="Auto-Check on Post")