# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

{
    'name': "Módulo de Ventas",
    'summary': "Ventas.",
    'author': "Ing. Mario Rangel, Elitumgroup S.A",
    'website': "http://www.elitumgroup.com",
    'category': "Personalization",
    'license': "LGPL-3",
    'version': "1.0",
    'depends': [
        'account',
        'eliterp_accounting',
        'sale_management',
        'sale',
        'hr',
        'eliterp_operations'
    ],
    'data': [
        'views/out_invoice_views.xml',
        'views/customer_views.xml',
        'views/sale_order_views.xml',
        'views/menus.xml',
        'views/dashboard.xml',
    ],
    'init_xml': [],
    'update_xml': [],
    'installable': True,
    'active': False,
}
