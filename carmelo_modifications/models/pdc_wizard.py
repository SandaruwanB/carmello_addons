from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class PdcWizard(models.Model):
    _name = "pdc.wizard"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "PDC Wizard model"
    _order = "id desc"

    name = fields.Char(string="Name", default=lambda self: _('New'), copy=False, tracking=True)
    check_amount_in_words = fields.Char(string="Amount in Words", compute="_compute_amount_in_words", store=True, readonly=False)
    payment_type = fields.Selection(
        selection=[
            ('receive_money', 'Receive Money'),
            ('send_money', 'Send Money'),
        ],
        string="Payment Type",
        default='receive_money',
        tracking=True,
    )
    partner_id = fields.Many2one('res.partner', string="Partner", tracking=True)
    currency_id = fields.Many2one('res.currency', string="Currency", default=lambda self: self.env.company.currency_id)
    payment_amount = fields.Monetary(string="Payment Amount", currency_field='currency_id', tracking=True)
    reference = fields.Char(string="Cheque No", tracking=True)
    journal_id = fields.Many2one('account.journal', string="Payment Journal", tracking=True)
    available_payment_method_line_ids = fields.Many2many(
        'account.payment.method.line',
        compute='_compute_available_payment_method_line_ids',
    )
    payment_method_line_id = fields.Many2one(
        'account.payment.method.line',
        string="Payment Method",
        domain="[('id', 'in', available_payment_method_line_ids)]",
        compute='_compute_payment_method_line_id',
        store=True,
        readonly=False,
        tracking=True,
    )
    cheque_status = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('deposit', 'Deposit'),
            ('paid', 'Paid'),
        ],
        string="Cheque Status",
        default='draft',
        tracking=True,
    )
    payment_date = fields.Date(string="Payment Date", default=fields.Date.context_today, tracking=True)
    due_date = fields.Date(string="Due Date", default=fields.Date.context_today, tracking=True)
    memo = fields.Char(string="Memo")
    agent = fields.Many2one("res.users", string="Agent", default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)

    main_bank_id = fields.Many2one('main.bank', string="Bank", tracking=True)
    bank_id = fields.Many2one('res.bank', string="Branch", domain="[('main_bank_id', '=', main_bank_id)]", tracking=True)
    partner_bank_account_id = fields.Many2one('res.partner.bank', string="Account No")
    attachment_ids = fields.Many2many('ir.attachment', string="Cheque Image")
    invoice_id = fields.Many2one('account.move', string="Invoice/Bill", tracking=True)
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('approved', 'Approved'),
            ('registered', 'Registered'),
            ('deposited', 'Deposited'),
            ('done', 'Done'),
            ('returned', 'Returned'),
            ('bounced', 'Bounced'),
            ('cancel', 'Cancelled'),
        ],
        string="State",
        default='draft',
        tracking=True,
    )
    deposited_debit = fields.Many2one('account.move.line', string="Deposited Debit")
    deposited_credit = fields.Many2one('account.move.line', string="Deposited Credit")
    custom_url = fields.Char(string="URL")
    approved_by = fields.Many2one('res.users', string="Approved/Rejected By", tracking=True)
    approve_Date = fields.Date(string="Approved/Rejected Date", tracking=True)
    comment = fields.Text(string="Approved/Rejected Comment")
    triggered_approval = fields.Boolean(string="Triggered Approval")
    receipt_id = fields.Many2one("account.receipt.payment", string="Receipt")
    payment_id = fields.Many2one('account.payment', string="Payment Entry", readonly=True, copy=False)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get('active_id')
        active_model = self.env.context.get('active_model')
        if active_model == 'account.move' and active_id:
            move = self.env['account.move'].browse(active_id)
            if move.exists():
                res.setdefault('invoice_id', move.id)
                res.setdefault('partner_id', move.partner_id.id)
                res.setdefault('payment_amount', move.amount_residual or move.amount_total)
                res.setdefault('currency_id', move.currency_id.id)
                res.setdefault('company_id', move.company_id.id)
                res.setdefault('memo', move.name)
                res.setdefault('payment_type', 'receive_money' if move.is_sale_document(include_receipts=True) else 'send_money')
                res.setdefault('state', 'draft')
        return res

    @api.onchange('invoice_id')
    def _onchange_invoice_id(self):
        if self.invoice_id:
            self.partner_id = self.invoice_id.partner_id
            self.payment_amount = self.invoice_id.amount_residual or self.invoice_id.amount_total
            self.currency_id = self.invoice_id.currency_id
            self.memo = self.invoice_id.name
            if self.invoice_id.is_sale_document(include_receipts=True):
                self.payment_type = 'receive_money'
            else:
                self.payment_type = 'send_money'

    @api.depends('payment_amount', 'currency_id')
    def _compute_amount_in_words(self):
        for record in self:
            if record.currency_id and record.payment_amount:
                record.check_amount_in_words = record.currency_id.amount_to_text(record.payment_amount)
            elif not record.check_amount_in_words:
                record.check_amount_in_words = ''

    @api.depends('journal_id', 'payment_type')
    def _compute_available_payment_method_line_ids(self):
        for record in self:
            if record.journal_id:
                ptype = 'inbound' if record.payment_type == 'receive_money' else 'outbound'
                record.available_payment_method_line_ids = record.journal_id._get_available_payment_method_lines(ptype)
            else:
                record.available_payment_method_line_ids = False

    @api.depends('journal_id', 'payment_type', 'available_payment_method_line_ids')
    def _compute_payment_method_line_id(self):
        for record in self:
            if not record.journal_id or not record.available_payment_method_line_ids:
                record.payment_method_line_id = False
                continue
            if record.payment_method_line_id and record.payment_method_line_id in record.available_payment_method_line_ids:
                continue
            check_methods = record.available_payment_method_line_ids.filtered(
                lambda m: 'check' in (m.code or '').lower() or 'cheque' in (m.name or '').lower() or 'check' in (m.name or '').lower() or 'pdc' in (m.name or '').lower()
            )
            if check_methods:
                record.payment_method_line_id = check_methods[0]
            else:
                record.payment_method_line_id = record.available_payment_method_line_ids[0]

    @api.model
    def _get_pdc_sequence_name(self, payment_type='receive_money'):
        seq_code = 'pdc.payment.customer' if payment_type == 'receive_money' else 'pdc.payment.vendor'
        seq_name = self.env['ir.sequence'].next_by_code(seq_code)
        if not seq_name:
            prefix = 'CUST.IN/PDC/' if payment_type == 'receive_money' else 'SUPP.OUT/PDC/'
            seq = self.env['ir.sequence'].sudo().search([('code', '=', seq_code)], limit=1)
            if not seq:
                seq = self.env['ir.sequence'].sudo().create({
                    'name': f'PDC {"Customer" if payment_type == "receive_money" else "Vendor"} Payment',
                    'code': seq_code,
                    'prefix': prefix,
                    'padding': 1,
                    'company_id': False,
                })
            seq_name = seq.next_by_id()
        return seq_name

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') in (_('New'), 'New', '/'):
                payment_type = vals.get('payment_type', 'receive_money')
                vals['name'] = self._get_pdc_sequence_name(payment_type) or vals.get('reference') or _('PDC')
        records = super().create(vals_list)
        for record in records:
            if record.invoice_id and record not in record.invoice_id.pdc_payment_ids:
                record.invoice_id.write({
                    'pdc_payment_ids': [(4, record.id)],
                    'pdc_id': record.id,
                })
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'invoice_id' in vals:
            for record in self:
                if record.invoice_id and record not in record.invoice_id.pdc_payment_ids:
                    record.invoice_id.write({
                        'pdc_payment_ids': [(4, record.id)],
                        'pdc_id': record.id,
                    })
        return res

    @api.model
    def _register_hook(self):
        super()._register_hook()
        try:
            current_menus = self.env['ir.ui.menu'].browse([
                menu.id for menu in [
                    self.env.ref('carmelo_modifications.menu_pdc_customer_cheques', raise_if_not_found=False),
                    self.env.ref('carmelo_modifications.menu_pdc_vendor_payments', raise_if_not_found=False),
                ] if menu
            ])
            current_ids = current_menus.ids
            old_menus = self.env['ir.ui.menu'].search([
                ('name', 'ilike', 'pdc'),
                ('id', 'not in', current_ids),
            ])
            if old_menus:
                old_menus.unlink()
        except Exception:
            pass

    def button_confirm(self):
        for record in self:
            if not record.payment_amount or record.payment_amount <= 0:
                raise ValidationError(_("Please enter a valid payment amount."))
            record.state = 'confirmed'
            if not record.name or record.name in (_('New'), 'New', '/'):
                record.name = self._get_pdc_sequence_name(record.payment_type) or record.reference or f"PDC/{record.id}"
            if record.invoice_id and record not in record.invoice_id.pdc_payment_ids:
                record.invoice_id.write({
                    'pdc_payment_ids': [(4, record.id)],
                    'pdc_id': record.id,
                })
            record.message_post(body=_("PDC Cheque confirmed and submitted for approval."))

            try:
                manager_group = self.env.ref('carmelo_modifications.group_pdc_manager', raise_if_not_found=False)
                approvers = manager_group.users if manager_group else self.env['res.users']
                if not approvers:
                    acc_group = self.env.ref('account.group_account_manager', raise_if_not_found=False)
                    approvers = acc_group.users if acc_group else self.env['res.users']

                todo_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
                for approver in approvers:
                    record.activity_schedule(
                        activity_type_id=todo_type.id if todo_type else False,
                        summary=_("PDC Cheque Approval Required: %s") % (record.reference or record.name),
                        note=_("A new PDC Cheque <b>%s</b> for amount <b>%s %s</b> from partner <b>%s</b> requires your approval.") % (
                            record.reference or record.name,
                            record.currency_id.symbol if record.currency_id else '',
                            record.payment_amount,
                            record.partner_id.name if record.partner_id else '',
                        ),
                        user_id=approver.id,
                        date_deadline=fields.Date.context_today(self),
                    )
            except Exception:
                pass
        return True

    def action_confirm(self):
        return self.button_confirm()

    def button_approve(self):
        for record in self:
            if not self.env.user.has_group('carmelo_modifications.group_pdc_manager') and not self.env.user.has_group('account.group_account_manager') and not self.env.is_admin():
                raise UserError(_("Only PDC Approvers / Managers are authorized to approve cheques."))
            record.write({
                'state': 'approved',
                'approved_by': self.env.user.id,
                'approve_Date': fields.Date.context_today(self),
            })

            try:
                todo_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
                if todo_type:
                    record.activity_feedback([todo_type.id], feedback=_("Approved by %s") % self.env.user.name)
                else:
                    record.activity_feedback(['mail.mail_activity_data_todo'], feedback=_("Approved by %s") % self.env.user.name)
            except Exception:
                pass

            requester = record.agent or record.create_uid
            partner_ids = [requester.partner_id.id] if requester and requester.partner_id else []
            record.message_post(
                body=_("PDC Cheque <b>%s</b> for amount <b>%s %s</b> has been <b>Approved</b> by %s.") % (
                    record.reference or record.name,
                    record.currency_id.symbol if record.currency_id else '',
                    record.payment_amount,
                    self.env.user.name,
                ),
                partner_ids=partner_ids,
                subject=_("PDC Cheque Approved: %s") % (record.reference or record.name),
            )

            if requester and requester != self.env.user:
                try:
                    todo_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
                    record.activity_schedule(
                        activity_type_id=todo_type.id if todo_type else False,
                        summary=_("PDC Cheque Approved: %s") % (record.reference or record.name),
                        note=_("Your PDC Cheque <b>%s</b> for amount <b>%s %s</b> has been approved by %s. You can now proceed to Register it.") % (
                            record.reference or record.name,
                            record.currency_id.symbol if record.currency_id else '',
                            record.payment_amount,
                            self.env.user.name,
                        ),
                        user_id=requester.id,
                        date_deadline=fields.Date.context_today(self),
                    )
                except Exception:
                    pass
        return True

    def action_approve(self):
        return self.button_approve()

    def button_reject(self):
        for record in self:
            if not self.env.user.has_group('carmelo_modifications.group_pdc_manager') and not self.env.user.has_group('account.group_account_manager') and not self.env.is_admin():
                raise UserError(_("Only PDC Approvers / Managers are authorized to reject cheques."))
            record.write({
                'state': 'cancel',
                'approved_by': self.env.user.id,
                'approve_Date': fields.Date.context_today(self),
            })
            try:
                todo_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
                if todo_type:
                    record.activity_feedback([todo_type.id], feedback=_("Rejected by %s") % self.env.user.name)
                else:
                    record.activity_feedback(['mail.mail_activity_data_todo'], feedback=_("Rejected by %s") % self.env.user.name)
            except Exception:
                pass

            requester = record.agent or record.create_uid
            partner_ids = [requester.partner_id.id] if requester and requester.partner_id else []
            comment_text = f"<br/><b>Reason/Comment:</b> {record.comment}" if record.comment else ""
            record.message_post(
                body=_("PDC Cheque <b>%s</b> for amount <b>%s %s</b> has been <b>Rejected</b> by %s.%s") % (
                    record.reference or record.name,
                    record.currency_id.symbol if record.currency_id else '',
                    record.payment_amount,
                    self.env.user.name,
                    comment_text,
                ),
                partner_ids=partner_ids,
                subject=_("PDC Cheque Rejected: %s") % (record.reference or record.name),
            )
        return True

    def action_reject(self):
        return self.button_reject()

    def button_register(self):
        for record in self:
            if not record.journal_id:
                raise UserError(_("Please select a Payment Journal before registering the cheque."))
            if not record.payment_amount or record.payment_amount <= 0:
                raise UserError(_("Please enter a valid payment amount."))
            if not record.partner_id:
                raise UserError(_("Please select a Partner before registering the cheque."))

            # Check for Overpayment or Settled Invoice Warning
            if record.invoice_id and not self.env.context.get('skip_amount_check'):
                currency_sym = record.currency_id.symbol or record.currency_id.name or ''
                residual = record.invoice_id.amount_residual
                if residual <= 0:
                    warning_msg = _(
                        "The linked Invoice/Bill (%s) is already fully settled (Remaining Due: %s 0.00).\n\n"
                        "Registering this PDC cheque for %s %s will create an open advance/credit on the partner's account.\n\n"
                        "Do you want to proceed and register this payment anyway?"
                    ) % (record.invoice_id.name, currency_sym, currency_sym, "{:,.2f}".format(record.payment_amount))
                    wizard = self.env['pdc.register.warning.wizard'].create({
                        'pdc_id': record.id,
                        'message': warning_msg,
                    })
                    return {
                        'name': _('Confirmation: Invoice Already Settled'),
                        'type': 'ir.actions.act_window',
                        'res_model': 'pdc.register.warning.wizard',
                        'res_id': wizard.id,
                        'view_mode': 'form',
                        'target': 'new',
                    }
                elif record.payment_amount > residual:
                    warning_msg = _(
                        "The cheque payment amount (%s %s) is greater than the remaining invoice due amount (%s %s) of %s.\n\n"
                        "Excess amount (%s %s) will remain as an open advance/credit on the partner's account.\n\n"
                        "Do you want to proceed and register this payment anyway?"
                    ) % (
                        currency_sym, "{:,.2f}".format(record.payment_amount),
                        currency_sym, "{:,.2f}".format(residual),
                        record.invoice_id.name,
                        currency_sym, "{:,.2f}".format(record.payment_amount - residual)
                    )
                    wizard = self.env['pdc.register.warning.wizard'].create({
                        'pdc_id': record.id,
                        'message': warning_msg,
                    })
                    return {
                        'name': _('Confirmation: Overpayment Detected'),
                        'type': 'ir.actions.act_window',
                        'res_model': 'pdc.register.warning.wizard',
                        'res_id': wizard.id,
                        'view_mode': 'form',
                        'target': 'new',
                    }

            if not record.payment_id:
                payment_type = 'inbound' if record.payment_type == 'receive_money' else 'outbound'
                partner_type = 'customer' if record.payment_type == 'receive_money' else 'supplier'
                memo = record.memo or f"{record.name} - Cheque #{record.reference or ''}"

                dest_account_id = False
                if record.invoice_id:
                    inv_rec_pay_lines = record.invoice_id.line_ids.filtered(
                        lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')
                    )
                    if inv_rec_pay_lines:
                        dest_account_id = inv_rec_pay_lines[0].account_id.id

                payment_vals = {
                    'payment_type': payment_type,
                    'partner_type': partner_type,
                    'partner_id': record.partner_id.id,
                    'amount': record.payment_amount,
                    'currency_id': record.currency_id.id,
                    'date': record.payment_date or fields.Date.context_today(record),
                    'journal_id': record.journal_id.id,
                    'payment_method_line_id': record.payment_method_line_id.id if record.payment_method_line_id else False,
                    'memo': memo,
                    'company_id': record.company_id.id or record.journal_id.company_id.id,
                }
                if dest_account_id:
                    payment_vals['destination_account_id'] = dest_account_id

                payment = self.env['account.payment'].create(payment_vals)
                if dest_account_id and payment.destination_account_id.id != dest_account_id:
                    payment.destination_account_id = dest_account_id

                payment.action_post()
                record.payment_id = payment.id

                # Capture debit/credit lines
                if payment.move_id:
                    for line in payment.move_id.line_ids:
                        if line.debit > 0 and not record.deposited_debit:
                            record.deposited_debit = line.id
                        elif line.credit > 0 and not record.deposited_credit:
                            record.deposited_credit = line.id

                # Reconcile with invoice/bill matching the same account
                if record.invoice_id and record.invoice_id.state == 'posted' and payment.move_id:
                    inv_lines = record.invoice_id.line_ids.filtered(
                        lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable') and not l.reconciled
                    )
                    pay_lines = payment.move_id.line_ids.filtered(
                        lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable') and not l.reconciled
                    )
                    for inv_line in inv_lines:
                        matching_pay = pay_lines.filtered(lambda p: p.account_id == inv_line.account_id and not p.reconciled)
                        if matching_pay:
                            (inv_line + matching_pay).reconcile()

            record.write({
                'state': 'registered',
            })
            record.message_post(body=_("PDC Cheque registered and Payment <b>%s</b> posted &amp; reconciled.") % (record.payment_id.name if record.payment_id else ''))
        return True

    def action_register(self):
        return self.button_register()

    def button_deposit(self):
        for record in self:
            if not record.journal_id:
                raise ValidationError(_("Please select a Deposit Journal before depositing to bank."))
            record.write({
                'state': 'deposited',
                'cheque_status': 'deposit',
            })
            record.message_post(body=_("PDC Cheque marked as Deposited to %s.") % (record.journal_id.name))
        return True

    def action_deposit(self):
        return self.button_deposit()

    def button_deposited(self):
        return self.button_deposit()

    def action_deposited(self):
        return self.button_deposit()

    def _cancel_linked_payment(self):
        for record in self:
            if record.payment_id:
                try:
                    if record.payment_id.move_id:
                        record.payment_id.move_id.line_ids.remove_move_reconcile()
                    if record.payment_id.state == 'posted':
                        record.payment_id.action_draft()
                        record.payment_id.action_cancel()
                except Exception as e:
                    record.message_post(body=_("Warning: Could not automatically cancel payment %s: %s") % (record.payment_id.name, str(e)))

    def button_bounced(self):
        for record in self:
            record._cancel_linked_payment()
            record.write({
                'state': 'bounced',
            })
            record.message_post(body=_("PDC Cheque marked as Bounced/Dishonoured. Linked payment unreconciled and cancelled."))
        return True

    def action_bounced(self):
        return self.button_bounced()

    def button_bounce(self):
        return self.button_bounced()

    def action_bounce(self):
        return self.button_bounced()

    def button_return(self):
        for record in self:
            record._cancel_linked_payment()
            record.write({
                'state': 'returned',
            })
            record.message_post(body=_("PDC Cheque returned. Linked payment unreconciled and cancelled."))
        return True

    def action_return(self):
        return self.button_return()

    def button_returned(self):
        return self.button_return()

    def action_returned(self):
        return self.button_return()

    def button_done(self):
        for record in self:
            record.write({
                'state': 'done',
                'cheque_status': 'paid',
            })
            record.message_post(body=_("PDC Cheque cleared and marked as Done/Paid."))
        return True

    def action_done(self):
        return self.button_done()

    def button_paid(self):
        return self.button_done()

    def action_paid(self):
        return self.button_done()

    def button_cancel(self):
        for record in self:
            record._cancel_linked_payment()
            record.write({
                'state': 'cancel',
            })
            record.message_post(body=_("PDC Cheque cancelled. Linked payment unreconciled and cancelled."))
        return True

    def action_cancel(self):
        return self.button_cancel()

    def button_draft(self):
        for record in self:
            record._cancel_linked_payment()
            record.write({
                'state': 'draft',
                'cheque_status': 'draft',
                'approved_by': False,
                'approve_Date': False,
                'payment_id': False,
                'deposited_debit': False,
                'deposited_credit': False,
            })
            record.message_post(body=_("PDC Cheque reset to Draft."))
        return True

    def action_draft(self):
        return self.button_draft()

    def open_journal_items(self):
        self.ensure_one()
        move_line_ids = []
        if self.payment_id and self.payment_id.move_id:
            move_line_ids.extend(self.payment_id.move_id.line_ids.ids)
        if self.deposited_debit:
            move_line_ids.append(self.deposited_debit.id)
        if self.deposited_credit:
            move_line_ids.append(self.deposited_credit.id)

        domain = [('id', 'in', list(set(move_line_ids)))] if move_line_ids else [
            '|', ('move_id.ref', '=', self.reference or self.name),
            ('ref', '=', self.reference or self.name)
        ]

        return {
            'name': _('Journal Items'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'domain': domain,
            'context': {
                'default_partner_id': self.partner_id.id,
                'search_default_partner_id': self.partner_id.id,
            },
        }

    def action_open_journal_items(self):
        return self.open_journal_items()

    def action_view_journal_items(self):
        return self.open_journal_items()

    def open_journal_entries(self):
        self.ensure_one()
        move_ids = []
        if self.payment_id and self.payment_id.move_id:
            move_ids.append(self.payment_id.move_id.id)
        if self.deposited_debit and self.deposited_debit.move_id:
            move_ids.append(self.deposited_debit.move_id.id)
        if self.deposited_credit and self.deposited_credit.move_id:
            move_ids.append(self.deposited_credit.move_id.id)
        if self.invoice_id:
            move_ids.append(self.invoice_id.id)

        domain = [('id', 'in', list(set(move_ids)))] if move_ids else [
            '|', ('ref', '=', self.reference or self.name),
            ('name', '=', self.name or self.reference)
        ]
        return {
            'name': _('Journal Entries'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': domain,
        }

    def open_journal_entry(self):
        return self.open_journal_entries()

    def action_open_journal_entry(self):
        return self.open_journal_entries()

    def action_view_journal_entry(self):
        return self.open_journal_entries()

    def action_open_journal_entries(self):
        return self.open_journal_entries()

    def action_view_journal_entries(self):
        return self.open_journal_entries()

    def open_attachments(self):
        self.ensure_one()
        return {
            'name': _('Attachments'),
            'type': 'ir.actions.act_window',
            'res_model': 'ir.attachment',
            'view_mode': 'kanban,list,form',
            'domain': [('id', 'in', self.attachment_ids.ids)],
            'context': {'default_res_model': self._name, 'default_res_id': self.id},
        }

    def action_view_attachments(self):
        return self.open_attachments()

    def action_open_attachments(self):
        return self.open_attachments()

    def open_invoices(self):
        self.ensure_one()
        domain = [('id', '=', self.invoice_id.id)] if self.invoice_id else [
            ('id', 'in', self.partner_id.invoice_ids.ids)
        ]
        return {
            'name': _('Invoices'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': domain,
        }

    def open_invoice(self):
        return self.open_invoices()

    def action_view_invoices(self):
        return self.open_invoices()

    def action_view_invoice(self):
        return self.open_invoices()


class PdcRegisterWarningWizard(models.TransientModel):
    _name = 'pdc.register.warning.wizard'
    _description = 'PDC Register Warning'

    pdc_id = fields.Many2one('pdc.wizard', string="PDC Cheque", required=True)
    message = fields.Text(string="Warning Message", readonly=True)

    def action_proceed(self):
        self.ensure_one()
        return self.pdc_id.with_context(skip_amount_check=True).button_register()