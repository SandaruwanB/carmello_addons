import json
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"


    pdc_payment_ids = fields.Many2many("pdc.wizard", string="PDC Payments")
    pdc_id = fields.Many2one("pdc.wizard", string="PDC Reference")
    pdc_payment_count = fields.Integer(string="PDC Payment Count", compute="_compute_pdc_amounts")
    total_pdc_payment = fields.Monetary(string="Total", compute="_compute_pdc_amounts")
    total_pdc_pending = fields.Monetary(string="Total Pending", compute="_compute_pdc_amounts")
    total_pdc_cancel = fields.Monetary(string="Total Cancel", compute="_compute_pdc_amounts")
    total_pdc_received = fields.Monetary(string="Total Received", compute="_compute_pdc_amounts")

    @api.depends('pdc_payment_ids', 'pdc_payment_ids.payment_amount', 'pdc_payment_ids.state')
    def _compute_pdc_amounts(self):
        for move in self:
            move.pdc_payment_count = len(move.pdc_payment_ids)
            total_payment = sum(move.pdc_payment_ids.mapped('payment_amount'))
            total_cancel = sum(move.pdc_payment_ids.filtered(lambda p: p.state == 'cancel').mapped('payment_amount'))
            total_received = sum(move.pdc_payment_ids.filtered(lambda p: p.state in ('confirmed', 'approved', 'registered', 'deposited', 'done')).mapped('payment_amount'))
            total_pending = sum(move.pdc_payment_ids.filtered(lambda p: p.state == 'draft').mapped('payment_amount'))
            
            move.total_pdc_payment = total_payment
            move.total_pdc_cancel = total_cancel
            move.total_pdc_received = total_received
            move.total_pdc_pending = total_pending

    def action_register_pdc(self):
        self.ensure_one()
        payment_type = 'receive_money' if self.is_sale_document(include_receipts=True) else 'send_money'
        amount = self.amount_residual if self.amount_residual else self.amount_total
        return {
            'name': _('Register PDC Cheque'),
            'type': 'ir.actions.act_window',
            'res_model': 'pdc.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_invoice_id': self.id,
                'default_partner_id': self.partner_id.id,
                'default_payment_amount': amount,
                'default_currency_id': self.currency_id.id,
                'default_payment_type': payment_type,
                'default_company_id': self.company_id.id,
                'default_memo': self.name,
                'default_state': 'draft',
            },
        }

    def action_register_pdc_payment(self):
        return self.action_register_pdc()

    def action_pdc_payment(self):
        return self.action_register_pdc()

    def button_register_pdc(self):
        return self.action_register_pdc()

    def action_pdc_wizard(self):
        return self.action_register_pdc()

    def action_view_pdc_payments(self):
        self.ensure_one()
        pdc_ids = self.pdc_payment_ids.ids
        action = {
            'name': _('PDC Cheques'),
            'type': 'ir.actions.act_window',
            'res_model': 'pdc.wizard',
            'context': {
                'default_invoice_id': self.id,
                'default_partner_id': self.partner_id.id,
            },
        }
        if len(pdc_ids) == 1:
            form_view = self.env.ref('carmelo_modifications.view_pdc_wizard_form', raise_if_not_found=False)
            action['view_mode'] = 'form'
            action['views'] = [(form_view.id, 'form')] if form_view else [(False, 'form')]
            action['res_id'] = pdc_ids[0]
        else:
            search_view = self.env.ref('carmelo_modifications.view_pdc_wizard_search', raise_if_not_found=False)
            action['view_mode'] = 'list,form'
            action['domain'] = [('id', 'in', pdc_ids)]
            if search_view:
                action['search_view_id'] = search_view.id
        return action

    def action_open_pdc_payments(self):
        return self.action_view_pdc_payments()

    def open_pdc_payments(self):
        return self.action_view_pdc_payments()

    def open_pdc_payment(self):
        return self.action_view_pdc_payments()

    def action_open_pdc_payment(self):
        return self.action_view_pdc_payments()

    def action_view_pdc_payment(self):
        return self.action_view_pdc_payments()

    def open_pdc(self):
        return self.action_view_pdc_payments()

    def action_open_pdc(self):
        return self.action_view_pdc_payments()

    report_vat_type = fields.Selection(
        selection=[
            ('non_vat', 'Non-VAT'),
            ('vat', 'VAT Registered'),
            ('s_vat', 'SVAT Registered'),
            ('svat', 'SVAT Registered'),
        ],
        string="VAT Type",
        compute="_compute_report_vat_type",
        store=True,
        readonly=False,
        precompute=True,
        default='non_vat',
    )
    payment_mode_id = fields.Many2one("payment.mode", "Payment Mode")
    is_round_off = fields.Boolean()
    vat_type = fields.Selection(
        selection=[
            ('non_vat', 'Non-VAT'),
            ('vat', 'VAT Registered'),
            ('s_vat', 'SVAT Registered'),
            ('svat', 'SVAT Registered'),
        ],
        string="VAT Type",
        compute="_compute_vat_type",
        store=True,
        readonly=False,
    )

    @api.depends('partner_id', 'partner_id.vat_type')
    def _compute_report_vat_type(self):
        for move in self:
            if move.partner_id and move.partner_id.vat_type:
                move.report_vat_type = move.partner_id.vat_type
                move.vat_type = move.partner_id.vat_type
            elif not move.report_vat_type:
                move.report_vat_type = 'non_vat'
                move.vat_type = 'non_vat'

    @api.depends('report_vat_type')
    def _compute_vat_type(self):
        for move in self:
            move.vat_type = move.report_vat_type or 'non_vat'

    @api.onchange('partner_id')
    def _onchange_partner_id_vat_type(self):
        if self.partner_id:
            v_type = self.partner_id.vat_type or 'non_vat'
            self.report_vat_type = v_type
            self.vat_type = v_type

    @api.onchange('report_vat_type')
    def _onchange_report_vat_type(self):
        if self.report_vat_type:
            self.vat_type = self.report_vat_type

    @api.onchange('vat_type')
    def _onchange_vat_type(self):
        if self.vat_type:
            self.report_vat_type = self.vat_type

    def write(self, vals):
        if 'report_vat_type' in vals or 'vat_type' in vals:
            for move in self:
                if move.state and move.state != 'draft' and not self.env.context.get('force_vat_type_update'):
                    new_report_vat = vals.get('report_vat_type', move.report_vat_type)
                    new_vat = vals.get('vat_type', move.vat_type)
                    if new_report_vat != move.report_vat_type or new_vat != move.vat_type:
                        raise UserError(_("You cannot change the VAT Type once the invoice is not in Draft state."))
        return super().write(vals)

    @api.model
    def _register_hook(self):
        super()._register_hook()
        try:
            views = self.env['ir.ui.view'].sudo().search([
                ('model', '=', 'account.move'),
                '|', ('arch_db', 'like', 'report_vat_type'), ('arch_db', 'like', 'vat_type'),
            ])
            for view in views:
                arch = view.arch_db or ''
                modified = False
                if 'name="report_vat_type"' in arch and 'readonly="state != \'draft\'"' not in arch:
                    arch = arch.replace('name="report_vat_type"', 'name="report_vat_type" readonly="state != \'draft\'"')
                    modified = True
                if 'name="vat_type"' in arch and 'readonly="state != \'draft\'"' not in arch:
                    arch = arch.replace('name="vat_type"', 'name="vat_type" readonly="state != \'draft\'"')
                    modified = True
                if modified:
                    view.sudo().write({'arch_db': arch})

            # Deactivate old duplicate PDC button views on account.move
            current_view = self.env.ref('carmelo_modifications.view_move_form_inherit_carmelo_pdc', raise_if_not_found=False)
            old_pdc_views = self.env['ir.ui.view'].sudo().search([
                ('model', '=', 'account.move'),
                ('id', '!=', current_view.id if current_view else 0),
                '|', '|', ('arch_db', 'like', 'open_pdc_payment'),
                ('arch_db', 'like', 'PDC payments'),
                ('arch_db', 'like', 'action_open_pdc_payment'),
            ])
            for v in old_pdc_views:
                v.sudo().write({'active': False})
        except Exception:
            pass

    svat = fields.Float()
    no_followup = fields.Boolean(string="No Follow-Up", default=False)

    def _get_vat_invoice_next_name(self):
        self.ensure_one()
        inv_date = self.invoice_date or self.date or fields.Date.context_today(self)
        year_str = inv_date.strftime('%y')
        month_str = inv_date.strftime('%b').upper()
        prefix = f"{year_str}{month_str}_NUTRI_"

        self.env.cr.execute("""
            SELECT name FROM account_move 
            WHERE name LIKE %s AND company_id = %s
        """, (f"{prefix}%", self.company_id.id or self.env.company.id))

        existing = self.env.cr.fetchall()
        max_seq = 0
        for row in existing:
            name_val = row[0] or ''
            try:
                num = int(name_val.split(prefix)[-1])
                if num > max_seq:
                    max_seq = num
            except (ValueError, IndexError):
                pass

        next_seq = max_seq + 1
        return f"{prefix}{next_seq}"

    def _is_vat_invoice(self):
        self.ensure_one()
        if self.report_vat_type == 'non_vat' or self.vat_type == 'non_vat':
            return False
        if self.report_vat_type in ('vat', 's_vat', 'svat'):
            return True
        if self.vat_type in ('vat', 's_vat', 'svat'):
            return True
        return False

    def _get_last_sequence_domain(self, relaxed=False):
        self.ensure_one()
        if not self._is_vat_invoice():
            if not self.date or not self.journal_id:
                return "WHERE FALSE", {}
            where_string = "WHERE journal_id = %(journal_id)s AND name != '/' AND (name NOT LIKE '%%_NUTRI_%%' OR name IS NULL)"
            param = {'journal_id': self.journal_id.id}
            is_payment = self.origin_payment_id or self.env.context.get('is_payment')

            if not relaxed:
                domain = [
                    ('journal_id', '=', self.journal_id.id),
                    ('id', '!=', self.id or self._origin.id),
                    ('name', 'not in', ('/', '', False)),
                    ('name', 'not like', '_NUTRI_'),
                ]
                if self.journal_id.refund_sequence:
                    refund_types = ('out_refund', 'in_refund')
                    domain += [('move_type', 'in' if self.move_type in refund_types else 'not in', refund_types)]
                if self.journal_id.payment_sequence:
                    domain += [('origin_payment_id', '!=' if is_payment else '=', False)]

                reference_move_name = self.sudo().search(domain + [('date', '<=', self.date)], order='date desc', limit=1).name
                if not reference_move_name:
                    reference_move_name = self.sudo().search(domain, order='date asc', limit=1).name

                if reference_move_name:
                    sequence_number_reset = self._deduce_sequence_number_reset(reference_move_name)
                    date_start, date_end, *_ = self._get_sequence_date_range(sequence_number_reset)
                    where_string += """ AND date BETWEEN %(date_start)s AND %(date_end)s"""
                    param['date_start'] = date_start
                    param['date_end'] = date_end

                    if sequence_number_reset in ('year', 'year_range'):
                        param['anti_regex'] = self._make_regex_non_capturing(self._sequence_monthly_regex.split('(?P<seq>')[0]) + '$'
                    elif sequence_number_reset == 'never':
                        param['anti_regex'] = self._make_regex_non_capturing(self._sequence_yearly_regex.split('(?P<seq>')[0]) + '$'

                    if param.get('anti_regex') and not self.journal_id.sequence_override_regex and not self.env.context.get('no_anti_regex'):
                        where_string += " AND sequence_prefix !~ %(anti_regex)s "

            if self.journal_id.refund_sequence:
                if self.move_type in ('out_refund', 'in_refund'):
                    where_string += " AND move_type IN ('out_refund', 'in_refund') "
                else:
                    where_string += " AND move_type NOT IN ('out_refund', 'in_refund') "
            elif self.journal_id.payment_sequence:
                if is_payment:
                    where_string += " AND origin_payment_id IS NOT NULL "

            return where_string, param

        return super()._get_last_sequence_domain(relaxed=relaxed)

    def _set_next_sequence(self):
        for move in self:
            if move._is_vat_invoice() and move.is_sale_document(include_receipts=True):
                if not move.name or move.name == '/':
                    next_name = move._get_vat_invoice_next_name()
                    move.name = next_name
                    move[move._sequence_field] = next_name
                    self.env.cr.execute(
                        "UPDATE account_move SET name = %s WHERE id = %s",
                        (next_name, move.id)
                    )
            else:
                super(AccountMove, move)._set_next_sequence()

    def _post(self, soft=True):
        posted = super()._post(soft=soft)
        for move in posted:
            if move._is_vat_invoice() and move.is_sale_document(include_receipts=True):
                if not move.name or move.name == '/' or '_NUTRI_' not in (move.name or ''):
                    next_name = move._get_vat_invoice_next_name()
                    move.name = next_name
                    self.env.cr.execute(
                        "UPDATE account_move SET name = %s WHERE id = %s",
                        (next_name, move.id)
                    )
        return posted

    vat_rate_display = fields.Char(
        string="VAT Rate Display",
        compute="_compute_vat_rate_display",
    )

    @api.depends('invoice_line_ids.tax_ids')
    def _compute_vat_rate_display(self):
        for move in self:
            taxes = move.invoice_line_ids.tax_ids.filtered(lambda t: t.amount_type == 'percent')
            if taxes:
                rates = [f"{t.amount:g}%" for t in set(taxes)]
                move.vat_rate_display = ', '.join(rates)
            else:
                move.vat_rate_display = ''

    tax_totals_json = fields.Char(
        string="Tax Totals JSON",
        compute="_compute_tax_totals_json",
    )

    @api.depends('tax_totals', 'amount_untaxed', 'amount_tax', 'amount_total', 'line_ids.tax_line_id')
    def _compute_tax_totals_json(self):
        for move in self:
            subtotal_name = 'Untaxed Amount'
            totals = {
                'amount_total': move.amount_total,
                'amount_untaxed': move.amount_untaxed,
                'formatted_amount_total': f"{move.amount_total:,.2f}",
                'formatted_amount_untaxed': f"{move.amount_untaxed:,.2f}",
                'subtotals': [
                    {
                        'name': subtotal_name,
                        'amount': move.amount_untaxed,
                        'formatted_amount': f"{move.amount_untaxed:,.2f}",
                    }
                ],
                'groups_by_subtotal': {subtotal_name: []},
            }

            if hasattr(move, 'tax_totals') and isinstance(move.tax_totals, dict) and move.tax_totals.get('subtotals'):
                for sub in move.tax_totals.get('subtotals', []):
                    s_name = sub.get('name') or subtotal_name
                    if not any(s['name'] == s_name for s in totals['subtotals']):
                        totals['subtotals'].append({
                            'name': s_name,
                            'amount': sub.get('base_amount_currency', move.amount_untaxed),
                            'formatted_amount': f"{sub.get('base_amount_currency', move.amount_untaxed):,.2f}",
                        })
                    if s_name not in totals['groups_by_subtotal']:
                        totals['groups_by_subtotal'][s_name] = []

                    for tg in sub.get('tax_groups', []):
                        totals['groups_by_subtotal'][s_name].append({
                            'tax_group_name': tg.get('group_name', 'VAT'),
                            'tax_group_amount': tg.get('tax_amount_currency', 0.0),
                            'tax_group_base_amount': tg.get('base_amount_currency', move.amount_untaxed),
                            'formatted_tax_group_amount': f"{tg.get('tax_amount_currency', 0.0):,.2f}",
                            'formatted_tax_group_base_amount': f"{tg.get('base_amount_currency', move.amount_untaxed):,.2f}",
                            'tax_group_id': tg.get('id', 1),
                        })
            else:
                tax_lines = move.line_ids.filtered(lambda l: l.display_type == 'tax')
                if tax_lines:
                    for t_line in tax_lines:
                        g_name = t_line.tax_line_id.tax_group_id.name or t_line.tax_line_id.name or 'VAT'
                        totals['groups_by_subtotal'][subtotal_name].append({
                            'tax_group_name': g_name,
                            'tax_group_amount': abs(t_line.amount_currency),
                            'tax_group_base_amount': move.amount_untaxed,
                            'formatted_tax_group_amount': f"{abs(t_line.amount_currency):,.2f}",
                            'formatted_tax_group_base_amount': f"{move.amount_untaxed:,.2f}",
                            'tax_group_id': t_line.tax_line_id.tax_group_id.id if t_line.tax_line_id.tax_group_id else 1,
                        })
                elif move.amount_tax:
                    totals['groups_by_subtotal'][subtotal_name].append({
                        'tax_group_name': 'VAT',
                        'tax_group_amount': move.amount_tax,
                        'tax_group_base_amount': move.amount_untaxed,
                        'formatted_tax_group_amount': f"{move.amount_tax:,.2f}",
                        'formatted_tax_group_base_amount': f"{move.amount_untaxed:,.2f}",
                        'tax_group_id': 1,
                    })

            move.tax_totals_json = json.dumps(totals)

    global_discount_type = fields.Selection(
        selection=[
            ('percent', 'Percent'),
            ('fixed', 'Fixed'),
        ],
        string="Discount Type",
        default='percent',
    )
    global_order_discount = fields.Float(string="Global Discount", default=0.0)
    total_global_discount = fields.Monetary(
        string="Total Global Discount",
        currency_field="currency_id",
        compute="_compute_discount_amounts",
        store=True,
    )
    total_discount = fields.Monetary(
        string="Total Discount",
        currency_field="currency_id",
        compute="_compute_discount_amounts",
        store=True,
    )

    @api.depends(
        'invoice_line_ids.discount',
        'invoice_line_ids.discount_type',
        'invoice_line_ids.price_unit',
        'invoice_line_ids.quantity',
        'invoice_line_ids.price_subtotal',
        'global_order_discount',
        'global_discount_type',
    )
    def _compute_discount_amounts(self):
        for move in self:
            total_line_discount = 0.0
            for line in move.invoice_line_ids.filtered(lambda l: l.display_type == 'product' or not l.display_type):
                if line.discount_type == 'fixed':
                    total_line_discount += line.discount
                else:
                    total_line_discount += (line.quantity * line.price_unit) * (line.discount / 100.0)

            total_global_discount = 0.0
            if move.global_order_discount:
                if move.global_discount_type == 'percent':
                    base_amount = sum(line.price_subtotal for line in move.invoice_line_ids.filtered(lambda l: not l.is_global_line and (l.display_type == 'product' or not l.display_type)))
                    total_global_discount = base_amount * (move.global_order_discount / 100.0)
                elif move.global_discount_type == 'fixed':
                    total_global_discount = move.global_order_discount

            move.total_global_discount = total_global_discount
            move.total_discount = total_line_discount + total_global_discount


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    no_followup = fields.Boolean(string="No Follow-Up", default=False)
    pdc_id = fields.Many2one("pdc.wizard", string="PDC Reference")
    discount_type = fields.Selection(
        selection=[
            ('percent', 'Percent'),
            ('fixed', 'Fixed'),
        ],
        string="Discount Type",
        default='percent',
    )
    is_global_line = fields.Boolean(string="Global Discount Line", default=False)