# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

{
    'name': "Módulo de Compras",
    'summary': "Compras.",
    'author': "Ing. Mario Rangel, Elitumgroup S.A",
    'website': "http://www.elitumgroup.com",
    'category': "Personalization",
    'license': "LGPL-3",
    'version': "1.0",
    'depends': [
        'base',
        'eliterp_accounting',
        'purchase',
        'purchase_requisition',
        'stock',
        'product',
        'contacts',
        'stock_account',
    ],
    'data': [
        'data/sequences.xml',
        'security/ir.model.access.csv',
        'views/in_invoice_views.xml',
        'views/supplier_views.xml',
        'views/purchase_requisition_views.xml',
        'views/purchase_order_views.xml',
        'views/menus.xml',
        'views/dashboard.xml',
    ],
    'init_xml': [],
    'update_xml': [],
    'installable': True,
    'active': False,
}
