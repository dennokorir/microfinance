# -*- coding: utf-8 -*-
{
    'name': "microfinance",

    'summary': """
        This module provides a subset of the functionality provided by the sacco module.
        """,

    'description': """
        This module provides a subset of the functionality provided by the sacco module.
        This will facilitate taking of no interest loans, interest loans that only span
        one month, checkoff recovery and employer advice and member management
    """,

    'author': "Tritel Technologies",
    'website': "http://www.tritel.co.ke",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Microfinance',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'templates.xml',
        'views/wizards.xml',
        'views/views.xml',
        'views/sequences.xml',

    ],
    # only loaded in demonstration mode
    'demo': [
        'demo.xml',
    ],
}
