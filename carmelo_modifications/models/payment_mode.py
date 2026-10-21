from odoo import models, fields


class PaymentMode(models.Model):
    _name = "payment.mode"
    _description = "Payment mode model"


    name = fields.Char()