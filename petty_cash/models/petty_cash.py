# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PettyCashReason(models.Model):
    _name = "petty.cash.reason"
    _description = "Petty Cash Reason"

    name = fields.Char(string="Name", required=True)


class PettyCash(models.Model):
    _name = "petty.cash"
    _description = "Petty Cash Drawer"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Name", compute="_compute_name")
    start_date = fields.Date(string="Start Date", required=True, default=fields.Date.context_today)
    end_date = fields.Date(string="End Date", required=True)
    user_id = fields.Many2one("res.users", string="Responsible User", default=lambda self: self.env.user, required=True)
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one("res.currency", string="Currency", compute="_compute_currency_id")
    cash_flow = fields.Float(string="Cash IN", tracking=True)
    cash_out = fields.Float(string="Cash Out", tracking=True)
    cash_balance = fields.Float(string="Cash Balance", compute="_compute_cash_balance", store=False)
    journal_id = fields.Many2one("account.journal", string="Journal", required=True)
    is_transferred = fields.Boolean(string="Is Transferred")
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('in_progress', 'In Progress'),
            ('complete', 'Completed'),
            ('balance', 'Balanced'),
        ],
        string="State",
        default='draft',
        tracking=True,
    )
    move_id = fields.Many2many("account.move", string="Journal Entries")
    cash_in_line_ids = fields.One2many("petty.cash.in", "petty_cash_id", string="Petty Cash IN")
    cash_issue_line_ids = fields.One2many("petty.cash.release", "petty_cash_id", string="Petty Cash Out")
    cash_out_line_ids = fields.One2many("petty.cash.out", "petty_cash_id", string="Settlement")
    petty_cash_line_ids = fields.One2many("petty.cash.line", "petty_cash_id", string="Transactions")

    @api.depends('journal_id', 'start_date', 'end_date')
    def _compute_name(self):
        for rec in self:
            journal_name = rec.journal_id.name or 'Petty Cash'
            start = rec.start_date.strftime('%Y-%m-%d') if rec.start_date else ''
            end = rec.end_date.strftime('%Y-%m-%d') if rec.end_date else ''
            if start and end:
                rec.name = f"{journal_name} ({start} to {end})"
            elif start:
                rec.name = f"{journal_name} ({start})"
            else:
                rec.name = journal_name

    @api.depends('cash_flow', 'cash_out')
    def _compute_cash_balance(self):
        for rec in self:
            rec.cash_balance = (rec.cash_flow or 0.0) - (rec.cash_out or 0.0)

    @api.depends('company_id')
    def _compute_currency_id(self):
        for rec in self:
            rec.currency_id = rec.company_id.currency_id or self.env.company.currency_id

    def _compute_cash_totals(self):
        for rec in self:
            topup_total = sum(rec.cash_in_line_ids.filtered(lambda l: l.state == 'toppedup').mapped('amount'))
            out_total = sum(rec.cash_out_line_ids.filtered(lambda l: l.state == 'complete').mapped('expensed_amount'))
            release_total = sum(rec.cash_issue_line_ids.filtered(lambda l: l.state in ('released', 'complete')).mapped('released_amount'))
            rec.write({
                'cash_flow': topup_total,
                'cash_out': out_total + release_total,
            })

    def button_confirm_petty_cash(self):
        self.write({'state': 'in_progress'})

    def button_petty_cash_in(self):
        self.ensure_one()
        return {
            'name': _('Top Up Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'petty.cash.in',
            'view_mode': 'form',
            'context': {'default_petty_cash_id': self.id},
            'target': 'current',
        }

    def button_petty_cash_iou_request(self):
        self.ensure_one()
        return {
            'name': _('IOU Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'petty.cash.release',
            'view_mode': 'form',
            'context': {'default_petty_cash_id': self.id},
            'target': 'current',
        }

    def button_petty_reimbursement(self):
        self.ensure_one()
        return {
            'name': _('Reimbursement Settlement'),
            'type': 'ir.actions.act_window',
            'res_model': 'petty.cash.out',
            'view_mode': 'form',
            'context': {'default_petty_cash_id': self.id},
            'target': 'current',
        }

    def button_petty_cash_complete(self):
        self.ensure_one()
        if self.cash_balance != 0:
            return {
                'name': _('Return Petty Cash Balance'),
                'type': 'ir.actions.act_window',
                'res_model': 'petty.cash.balance.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_petty_cash_id': self.id,
                    'default_journal_id': self.journal_id.id,
                    'default_cash_balance': self.cash_balance,
                    'active_id': self.id,
                    'active_model': 'petty.cash',
                },
            }
        self.write({'state': 'complete'})

    def button_view_journal_entries(self):
        self.ensure_one()
        return {
            'name': _('Journal Entries'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.move_id.ids)],
        }

    def action_button_petty_cash_in(self):
        self.ensure_one()
        return {
            'name': _('Top Up(s)'),
            'type': 'ir.actions.act_window',
            'res_model': 'petty.cash.in',
            'view_mode': 'list,form',
            'domain': [('petty_cash_id', '=', self.id)],
            'context': {'default_petty_cash_id': self.id},
        }

    def action_button_iou_requests(self):
        self.ensure_one()
        return {
            'name': _('IOU Request(s)'),
            'type': 'ir.actions.act_window',
            'res_model': 'petty.cash.release',
            'view_mode': 'list,form',
            'domain': [('petty_cash_id', '=', self.id)],
            'context': {'default_petty_cash_id': self.id},
        }

    def action_button_reimbursement(self):
        self.ensure_one()
        return {
            'name': _('Reimbursement(s)'),
            'type': 'ir.actions.act_window',
            'res_model': 'petty.cash.out',
            'view_mode': 'list,form',
            'domain': [('petty_cash_id', '=', self.id)],
            'context': {'default_petty_cash_id': self.id},
        }


class PettyCashLine(models.Model):
    _name = "petty.cash.line"
    _description = "Petty Cash Lines"

    name = fields.Char(string="Reference")
    petty_cash_id = fields.Many2one("petty.cash", string="Petty Cash Drawer", ondelete='cascade')
    from_acc = fields.Many2one("account.account", string="Source Account")
    to_acc = fields.Many2one("account.account", string="Destination Account")
    reason = fields.Char(string="Reason")
    amount = fields.Float(string="Amount")
    type = fields.Selection(
        selection=[
            ('topup', 'Top-Up'),
            ('iou_request', 'IOU Request'),
            ('reimbursement', 'Reimbursement'),
            ('balance', 'Balance'),
        ],
        string="Type",
    )
    employee_id = fields.Many2one("hr.employee", string="Employee")
    approved_by = fields.Many2one("res.users", string="Approved By")
    user_id = fields.Many2one("res.users", string="Responsible User", default=lambda self: self.env.user)
    petty_cash_in = fields.Many2one("petty.cash.in", string="TopUp")
    cash_release_id = fields.Many2one("petty.cash.release", string="IOU Request")
    cash_reimbursement_id = fields.Many2one("petty.cash.out", string="Reimbursements")


class PettyCashIn(models.Model):
    _name = "petty.cash.in"
    _description = "Petty Cash Top Up"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Number", required=True, copy=False, default=lambda self: _('New'))
    request_date = fields.Datetime(string="Requested Date", default=fields.Datetime.now)
    cash_date = fields.Datetime(string="Processed Date")
    petty_cash_id = fields.Many2one("petty.cash", string="Petty Cash Drawer")
    user_id = fields.Many2one("res.users", string="Requested User", default=lambda self: self.env.user)
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company)
    currency_id = fields.Many2one("res.currency", string="Currency", default=lambda self: self.env.company.currency_id)
    amount = fields.Float(string="Amount")
    reason = fields.Char(string="Reason")
    note = fields.Char(string="Note")
    approved_by = fields.Many2one("res.users", string="Approved/Rejected User")
    approved_date = fields.Datetime(string="Approved/Rejected Date")
    approver_comment = fields.Char(string="Approve/Reject Comment")
    petty_cash_journal_id = fields.Many2one("account.journal", string="Journal")
    journal_id = fields.Many2one("account.journal", string="Source Account (Journal)")
    move_id = fields.Many2one("account.move", string="Journal Entries")
    petty_cash_line_id = fields.Many2one("petty.cash.line", string="Petty Cash Line")
    is_wizard = fields.Boolean(string="Is Wizard")
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('awaiting_approval', 'Awaiting Approval'),
            ('approved', 'Approved'),
            ('reject', 'Rejected'),
            ('toppedup', 'Topped Up'),
        ],
        string="Status",
        default='draft',
        tracking=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('petty.cash.in') or _('New')
        return super().create(vals_list)

    def button_awaiting_approval_petty_cash_in(self):
        self.ensure_one()
        return {
            'name': _('Select Approver'),
            'type': 'ir.actions.act_window',
            'res_model': 'petty.cash.approver.user.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'active_model': 'petty.cash.in',
            },
        }

    def button_approve_petty_cash_in(self):
        self.ensure_one()
        return {
            'name': _('Approve Top Up'),
            'type': 'ir.actions.act_window',
            'res_model': 'petty.cash.approved.comment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'active_model': 'petty.cash.in',
            },
        }

    def set_to_draft(self):
        self.ensure_one()
        return {
            'name': _('Reset to Draft Reason'),
            'type': 'ir.actions.act_window',
            'res_model': 'petty.cash.draft.reason',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'active_model': 'petty.cash.in',
            },
        }

    def button_reject_petty_cash_in(self):
        self.ensure_one()
        return {
            'name': _('Reject Reason'),
            'type': 'ir.actions.act_window',
            'res_model': 'petty.cash.draft.reason',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'active_model': 'petty.cash.in',
            },
        }

    def button_petty_cash_toppedup(self):
        self.ensure_one()
        self.write({
            'state': 'toppedup',
            'cash_date': fields.Datetime.now(),
        })
        if self.petty_cash_id:
            # Create petty cash transaction line
            line = self.env['petty.cash.line'].create({
                'name': self.name,
                'petty_cash_id': self.petty_cash_id.id,
                'amount': self.amount,
                'type': 'topup',
                'from_acc': self.journal_id.default_account_id.id if self.journal_id else False,
                'to_acc': self.petty_cash_id.journal_id.default_account_id.id if self.petty_cash_id.journal_id else False,
                'reason': self.reason,
                'user_id': self.user_id.id,
                'approved_by': self.approved_by.id if self.approved_by else False,
                'petty_cash_in': self.id,
            })
            self.petty_cash_line_id = line.id
            self.petty_cash_id._compute_cash_totals()

    def button_view_journal_entries(self):
        self.ensure_one()
        return {
            'name': _('Journal Entries'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.move_id.id,
        }


class PettyCashRelease(models.Model):
    _name = "petty.cash.release"
    _description = "IOU Request"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Number", required=True, copy=False, default=lambda self: _('New'))
    release_date = fields.Datetime(string="Requested Date", default=fields.Datetime.now)
    petty_cash_id = fields.Many2one("petty.cash", string="Petty Cash Drawer")
    employee_id = fields.Many2one("hr.employee", string="Requested Employee")
    user_id = fields.Many2one("res.users", string="Responsible Person", default=lambda self: self.env.user)
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company)
    currency_id = fields.Many2one("res.currency", string="Currency", default=lambda self: self.env.company.currency_id)
    released_amount = fields.Float(string="Released Amount")
    expensed_amount = fields.Float(string="Expensed Amount")
    balanced_amount = fields.Float(string="Balanced Amount")
    reason = fields.Many2one("petty.cash.reason", string="Reason")
    approved_by = fields.Many2one("res.users", string="Approved/Rejected User")
    approved_date = fields.Datetime(string="Approved/Rejected Date")
    approver_comment = fields.Char(string="Approved/Rejected Reason")
    checked_by = fields.Many2one("res.users", string="Checked By")
    cheque_no = fields.Char(string="Cheque No")
    remarks = fields.Text(string="Remarks")
    comment = fields.Text(string="Comment")
    move_id = fields.Many2many("account.move", string="Journal Entries")
    petty_cash_line_id = fields.Many2one("petty.cash.line", string="Petty Cash Line")
    expenses_line = fields.One2many("petty.cash.release.line", "cash_release_id", string="Expenses line")
    is_wizard = fields.Boolean(string="Is Wizard")
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('awaiting_approval', 'Awaiting Approval'),
            ('approved', 'Approved'),
            ('reject', 'Rejected'),
            ('released', 'Cash Issued'),
            ('complete', 'Completed'),
        ],
        string="Status",
        default='draft',
        tracking=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('petty.cash.release') or _('New')
        return super().create(vals_list)

    def button_request_approval_petty_cash_release(self):
        self.ensure_one()
        return {
            'name': _('Select Approver'),
            'type': 'ir.actions.act_window',
            'res_model': 'petty.cash.approver.user.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'active_model': 'petty.cash.release',
            },
        }

    def button_approve_petty_cash_release(self):
        self.ensure_one()
        return {
            'name': _('Approve IOU Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'petty.cash.approved.comment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'active_model': 'petty.cash.release',
            },
        }

    def button_reject_petty_cash_release(self):
        self.ensure_one()
        return {
            'name': _('Reject Reason'),
            'type': 'ir.actions.act_window',
            'res_model': 'petty.cash.draft.reason',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'active_model': 'petty.cash.release',
            },
        }

    def set_to_draft(self):
        self.ensure_one()
        return {
            'name': _('Reset to Draft Reason'),
            'type': 'ir.actions.act_window',
            'res_model': 'petty.cash.draft.reason',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'active_model': 'petty.cash.release',
            },
        }

    def button_petty_cash_released(self):
        self.ensure_one()
        self.write({'state': 'released'})
        if self.petty_cash_id:
            line = self.env['petty.cash.line'].create({
                'name': self.name,
                'petty_cash_id': self.petty_cash_id.id,
                'amount': self.released_amount,
                'type': 'iou_request',
                'employee_id': self.employee_id.id if self.employee_id else False,
                'reason': self.reason.name if self.reason else '',
                'user_id': self.user_id.id,
                'approved_by': self.approved_by.id if self.approved_by else False,
                'cash_release_id': self.id,
            })
            self.petty_cash_line_id = line.id
            self.petty_cash_id._compute_cash_totals()

    def button_petty_cash_complete(self):
        self.ensure_one()
        total_exp = sum(self.expenses_line.mapped('amount'))
        bal = (self.released_amount or 0.0) - total_exp
        self.write({
            'state': 'complete',
            'expensed_amount': total_exp,
            'balanced_amount': bal,
        })
        if self.petty_cash_id:
            self.petty_cash_id._compute_cash_totals()

    def button_view_journal_entries(self):
        self.ensure_one()
        return {
            'name': _('Journal Entries'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.move_id.ids)],
        }


class PettyCashReleaseLine(models.Model):
    _name = "petty.cash.release.line"
    _description = "IOU requests Line"

    name = fields.Char(string="Description")
    cash_release_id = fields.Many2one("petty.cash.release", string="IOU Requests", ondelete='cascade')
    expense_account_id = fields.Many2one("account.account", string="Expense Account")
    attachment_id = fields.Many2many("ir.attachment", string="Attachment")
    amount = fields.Float(string="Amount")


class PettyCashOut(models.Model):
    _name = "petty.cash.out"
    _description = "Petty Cash Out"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Number", required=True, copy=False, default=lambda self: _('New'))
    cash_date = fields.Datetime(string="Requested Date", default=fields.Datetime.now)
    petty_cash_id = fields.Many2one("petty.cash", string="Petty Cash Drawer")
    petty_cash_line_id = fields.Many2one("petty.cash.line", string="Petty Cash Line")
    employee_id = fields.Many2one("hr.employee", string="Requested Employee")
    user_id = fields.Many2one("res.users", string="User", default=lambda self: self.env.user)
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company)
    currency_id = fields.Many2one("res.currency", string="Currency", default=lambda self: self.env.company.currency_id)
    expensed_amount = fields.Float(string="Total Amount")
    expenses_line = fields.One2many("petty.cash.out.line", "cash_out_id", string="Cash Lines")
    reason = fields.Many2one("petty.cash.reason", string="Reason")
    reject_reason = fields.Char(string="Reject Reason")
    approved_by = fields.Many2one("res.users", string="Approved/rejected User")
    approved_date = fields.Datetime(string="Approved/Rejected Date")
    approver_comment = fields.Char(string="Approve/reject Comment")
    checked_by = fields.Many2one("res.users", string="Checked By")
    cheque_no = fields.Char(string="Cheque No")
    remarks = fields.Text(string="Remarks")
    move_id = fields.Many2many("account.move", string="Journal Entries")
    is_approve = fields.Boolean(string="Is Approve")
    is_exceed_the_minimum = fields.Boolean(string="Exceed the minimum amount")
    is_wizard = fields.Boolean(string="Is Wizard")
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('awaiting_approval', 'Awaiting Approval'),
            ('approved', 'Approved'),
            ('reject', 'Rejected'),
            ('complete', 'Completed'),
        ],
        string="Status",
        default='draft',
        tracking=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('petty.cash.out') or _('New')
        return super().create(vals_list)

    def button_awaiting_approval_petty_cash_out(self):
        self.ensure_one()
        return {
            'name': _('Select Approver'),
            'type': 'ir.actions.act_window',
            'res_model': 'petty.cash.approver.user.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'active_model': 'petty.cash.out',
            },
        }

    def button_approve_petty_cash_out(self):
        self.ensure_one()
        return {
            'name': _('Approve Reimbursement'),
            'type': 'ir.actions.act_window',
            'res_model': 'petty.cash.approved.comment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'active_model': 'petty.cash.out',
            },
        }

    def button_reject_petty_cash_out(self):
        self.ensure_one()
        return {
            'name': _('Reject Reason'),
            'type': 'ir.actions.act_window',
            'res_model': 'petty.cash.draft.reason',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'active_model': 'petty.cash.out',
            },
        }

    def button_function_set_to_draft(self):
        self.ensure_one()
        return {
            'name': _('Reset to Draft Reason'),
            'type': 'ir.actions.act_window',
            'res_model': 'petty.cash.draft.reason',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'active_model': 'petty.cash.out',
            },
        }

    def button_reimbursement_petty_cash_out(self):
        self.ensure_one()
        total_exp = sum(self.expenses_line.mapped('amount'))
        self.write({
            'state': 'complete',
            'expensed_amount': total_exp,
        })
        if self.petty_cash_id:
            line = self.env['petty.cash.line'].create({
                'name': self.name,
                'petty_cash_id': self.petty_cash_id.id,
                'amount': total_exp,
                'type': 'reimbursement',
                'employee_id': self.employee_id.id if self.employee_id else False,
                'reason': self.reason.name if self.reason else '',
                'user_id': self.user_id.id,
                'approved_by': self.approved_by.id if self.approved_by else False,
                'cash_reimbursement_id': self.id,
            })
            self.petty_cash_line_id = line.id
            self.petty_cash_id._compute_cash_totals()

    def button_view_journal_entries(self):
        self.ensure_one()
        return {
            'name': _('Journal Entries'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.move_id.ids)],
        }


class PettyCashOutLine(models.Model):
    _name = "petty.cash.out.line"
    _description = "Petty Cash Out Line"

    name = fields.Char(string="Description")
    cash_out_id = fields.Many2one("petty.cash.out", string="Petty Cash", ondelete='cascade')
    expense_account_id = fields.Many2one("account.account", string="Expense Account")
    attachment_id = fields.Many2many("ir.attachment", string="Attachment")
    amount = fields.Float(string="Amount")
