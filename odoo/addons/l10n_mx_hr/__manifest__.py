# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

{
    'name': 'Employees - Mexico',
    'countries': ['mx'],
    'version': '1.0',
    'category': 'Human Resources/Employees',
    'sequence': 120,
    'summary': 'Adds specific fields to Employees for Mexican companies.',
    'depends': ['hr'],
    'data': [
        'views/hr_employee_views.xml',
    ],
    'demo': [
        'data/l10n_mx_hr_demo.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
