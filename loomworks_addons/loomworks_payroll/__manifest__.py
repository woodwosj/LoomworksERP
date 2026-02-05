# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

{
    'name': 'Loomworks Payroll',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Manage employee payroll with flexible salary rules',
    'description': """
Loomworks Payroll
=================

A comprehensive payroll management system for computing employee salaries with
a flexible rules-based engine. Designed for US Federal and California state
tax compliance.

Features:
---------
* Flexible salary structure configuration
* Rules-based computation engine with Python expressions
* Multiple salary structure types (monthly, hourly)
* US Federal tax calculations (2026 brackets)
* California state tax support (PIT, SDI)
* Social Security and Medicare withholding
* Payslip generation (individual and batch)
* Worked days computation
* PDF payslip reports
* Integration with hr_contract and hr_timesheet

Security:
---------
* Payroll User: View payslips, run computations
* Payroll Manager: Full access, configure rules
* Employees see only their own payslips

AI Integration:
---------------
* payroll_generate_payslip: Generate payslips for employees
* payroll_compute_salary: Preview salary computation

This is part of Loomworks ERP, a fork of Odoo Community v18 (LGPL v3).
    """,
    'author': 'Loomworks',
    'website': 'https://loomworks.app',
    'license': 'LGPL-3',
    'depends': [
        'hr_contract',
        'hr_holidays',
        'mail',
        'loomworks_core',
        'loomworks_ai',
    ],
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/payroll_category_data.xml',
        'data/payroll_structure_data.xml',
        'data/payroll_rule_data.xml',
        # Views
        'views/hr_payroll_structure_views.xml',
        'views/hr_salary_rule_views.xml',
        'views/hr_payslip_views.xml',
        'views/hr_contract_views.xml',
        'views/payroll_menus.xml',
        # Reports
        'report/payslip_report.xml',
        'report/payslip_templates.xml',
        # Wizards
        'wizard/hr_payslip_employees_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'loomworks_payroll/static/src/scss/payroll.scss',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 20,
}
