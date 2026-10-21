from odoo import models, fields


class ProductCategory(models.Model):
    _inherit = "product.category"


    gp_margin = fields.Float() # sales price - (raw material cost + packing cost) need to implemeknt with manufacturing module