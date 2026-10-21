from collections import defaultdict
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        self._check_available_inventory_balance()
        return super().button_validate()

    def _check_available_inventory_balance(self):
        for picking in self:
            demand_by_product_location = defaultdict(float)
            precision_by_product = {}

            for move in picking.move_ids.filtered(lambda m: m.state not in ('done', 'cancel')):
                # Only check moves that consume / issue stock from an internal location
                if move.location_id.usage != 'internal':
                    continue

                product = move.product_id
                if not product or not (getattr(product, 'is_storable', False) or getattr(product, 'type', '') == 'product'):
                    continue

                qty_to_issue = move.quantity if not float_is_zero(
                    move.quantity, precision_rounding=move.product_uom.rounding
                ) else move.product_uom_qty

                if float_is_zero(qty_to_issue, precision_rounding=move.product_uom.rounding):
                    continue

                # Convert to product's default UoM
                qty_in_prod_uom = move.product_uom._compute_quantity(qty_to_issue, product.uom_id)
                demand_by_product_location[(product, move.location_id)] += qty_in_prod_uom
                precision_by_product[product] = product.uom_id.rounding

            error_messages = []
            for (product, location), required_qty in demand_by_product_location.items():
                rounding = precision_by_product.get(product, 0.01)

                # Search directly in stock.quant with sudo to get physical on-hand quantity
                quant_domain = [
                    ('product_id', '=', product.id),
                    ('location_id', 'child_of', location.id),
                ]
                if picking.company_id:
                    quant_domain.append(('company_id', 'in', (picking.company_id.id, False)))

                quants = self.env['stock.quant'].sudo().search(quant_domain)
                available_qty = sum(quants.mapped('quantity'))

                # Fallback: check warehouse view location if location quants return 0
                if float_compare(available_qty, 0.0, precision_rounding=rounding) <= 0:
                    warehouse = picking.picking_type_id.warehouse_id or getattr(location, 'warehouse_id', False)
                    if warehouse and warehouse.view_location_id:
                        wh_quants = self.env['stock.quant'].sudo().search([
                            ('product_id', '=', product.id),
                            ('location_id', 'child_of', warehouse.view_location_id.id),
                            ('company_id', 'in', (picking.company_id.id, False)),
                        ])
                        wh_qty = sum(wh_quants.mapped('quantity'))
                        if wh_qty > available_qty:
                            available_qty = wh_qty

                if float_compare(available_qty, required_qty, precision_rounding=rounding) < 0:
                    error_messages.append(
                        _("- %(product)s: Required %(required).2f %(uom)s, Available in %(location)s is %(available).2f %(uom)s",
                          product=product.display_name,
                          required=required_qty,
                          available=available_qty,
                          location=location.display_name,
                          uom=product.uom_id.name)
                    )

            if error_messages:
                raise ValidationError(_(
                    "Cannot validate delivery '%(picking)s' due to insufficient inventory:\n\n%(details)s\n\nPlease adjust the quantity or receive stock before validating.",
                    picking=picking.name,
                    details="\n".join(error_messages)
                ))
