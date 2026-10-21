# -*- coding: utf-8 -*-
from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    issued_petty_cash = fields.Float(string="Total Issued", compute="_compute_petty_cash_totals")
    expensed_petty_cash = fields.Float(string="Total Expensed", compute="_compute_petty_cash_totals")
    pay_petty_cash = fields.Float(string="Pay to Employee", compute="_compute_petty_cash_totals", store=True)
    pay_to_employee = fields.Float(string="Pay to Employee", compute="_compute_petty_cash_totals")
    cash_issue_ids = fields.One2many("petty.cash.release", "employee_id", string="Cash Release")
    cash_out_ids = fields.One2many("petty.cash.out", "employee_id", string="Cash Out")

    @api.depends('cash_issue_ids.released_amount', 'cash_issue_ids.state', 'cash_out_ids.expensed_amount', 'cash_out_ids.state')
    def _compute_petty_cash_totals(self):
        for employee in self:
            issued = sum(employee.cash_issue_ids.filtered(lambda r: r.state == 'released').mapped('released_amount'))
            expensed = sum(employee.cash_out_ids.filtered(lambda o: o.state == 'complete').mapped('expensed_amount'))
            employee.issued_petty_cash = issued
            employee.expensed_petty_cash = expensed
            employee.pay_petty_cash = expensed - issued
            employee.pay_to_employee = expensed - issued

    def button_view_cash_issues(self):
        self.ensure_one()
        return {
            'name': 'IOU Requests',
            'type': 'ir.actions.act_window',
            'res_model': 'petty.cash.release',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }

    def button_view_cash_out(self):
        self.ensure_one()
        return {
            'name': 'Reimbursements',
            'type': 'ir.actions.act_window',
            'res_model': 'petty.cash.out',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }
