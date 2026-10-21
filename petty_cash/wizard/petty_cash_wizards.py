# -*- coding: utf-8 -*-
from typing import Any, Dict
from odoo import models, fields, api, _


class PettyCashApproverUserWizard(models.TransientModel):
    _name = "petty.cash.approver.user.wizard"
    _description = "Petty Cash Approver Wizard"

    user_id = fields.Many2one("res.users", string="Approver", required=True)
    model_id = fields.Many2one("ir.model", string="Model")

    def approval_submission(self):
        self.ensure_one()
        active_model = self._context.get('active_model')
        active_id = self._context.get('active_id')
        if active_model and active_id and active_model in self.env:
            record = self.env[active_model].browse(active_id)
            if record.exists():
                vals: Dict[str, Any] = {'state': 'awaiting_approval'}
                if 'approved_by' in record._fields and self.user_id:
                    vals['approved_by'] = self.user_id.id
                record.write(vals)
        return {'type': 'ir.actions.act_window_close'}


class PettyCashApprovedCommentWizard(models.TransientModel):
    _name = "petty.cash.approved.comment.wizard"
    _description = "Petty Cash Approved Comment Wizard"

    user_id = fields.Many2one("res.users", string="Approver", default=lambda self: self.env.user)
    model_id = fields.Many2one("ir.model", string="Model")
    approver_comment = fields.Char(string="Approver Comment")

    def approval_submission(self):
        self.ensure_one()
        active_model = self._context.get('active_model')
        active_id = self._context.get('active_id')
        if active_model and active_id and active_model in self.env:
            record = self.env[active_model].browse(active_id)
            if record.exists():
                vals: Dict[str, Any] = {
                    'state': 'approved',
                    'approved_by': self.env.user.id,
                    'approved_date': fields.Datetime.now(),
                }
                if self.approver_comment and 'approver_comment' in record._fields:
                    vals['approver_comment'] = self.approver_comment
                record.write(vals)
        return {'type': 'ir.actions.act_window_close'}


class PettyCashBalanceWizard(models.TransientModel):
    _name = "petty.cash.balance.wizard"
    _description = "Petty Cash Balance Wizard"

    user_id = fields.Many2one("res.users", string="Responsible User", default=lambda self: self.env.user)
    journal_id = fields.Many2one("account.journal", string="Journal")
    petty_cash_id = fields.Many2one("petty.cash", string="Petty Cash Drawer")
    cash_balance = fields.Float(string="Cash Balance")
    note = fields.Char(string="Note")
    return_journal = fields.Many2one("account.journal", string="Return Account", required=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self._context.get('active_id')
        if active_id and self._context.get('active_model') == 'petty.cash':
            drawer = self.env['petty.cash'].browse(active_id)
            if drawer.exists():
                res.update({
                    'petty_cash_id': drawer.id,
                    'journal_id': drawer.journal_id.id if drawer.journal_id else False,
                    'cash_balance': drawer.cash_balance,
                    'user_id': self.env.user.id,
                })
        return res

    def approval_submission(self):
        self.ensure_one()
        if self.petty_cash_id:
            self.petty_cash_id.write({
                'state': 'complete',
            })
        return {'type': 'ir.actions.act_window_close'}


class PettyCashDraftReason(models.TransientModel):
    _name = "petty.cash.draft.reason"
    _description = "Petty Cash Draft Reason Wizard"

    user_id = fields.Many2one("res.users", string="User", default=lambda self: self.env.user)
    cancel_reason = fields.Char(string="Reject / Draft Reason", required=True)

    def approval_submission(self):
        self.ensure_one()
        active_model = self._context.get('active_model')
        active_id = self._context.get('active_id')
        if active_model and active_id and active_model in self.env:
            record = self.env[active_model].browse(active_id)
            if record.exists():
                vals: Dict[str, Any] = {'state': 'draft'}
                if 'reject_reason' in record._fields:
                    vals['reject_reason'] = self.cancel_reason
                elif 'approver_comment' in record._fields:
                    vals['approver_comment'] = self.cancel_reason
                record.write(vals)
        return {'type': 'ir.actions.act_window_close'}
