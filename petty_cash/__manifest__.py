# -*- coding: utf-8 -*-
{
    'name': 'Petty Cash Management',
    'version': '18.0.1.0.0',
    'summary': 'Manage Petty Cash Drawers, IOU Requests, Settlements, and Top-Ups',
    'sequence': 10,
    'description': """
Petty Cash Management Module
============================
- Petty Cash Drawers
- Top Up Requests
- IOU / Cash Release Requests
- Expense Settlements / Cash Out
- Approval Workflows and Journal Entries
    """,
    'category': 'Accounting/Accounting',
    'author': 'Sandy',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'account',
        'hr',
    ],
    'data': [
        'security/petty_cash_security.xml',
        'security/ir.model.access.csv',
        'data/petty_cash_sequence.xml',
        'wizard/petty_cash_wizard_views.xml',
        'views/petty_cash_views.xml',
        'views/petty_cash_menus.xml',
    ],



    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
