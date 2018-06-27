# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

{
    'name': "Módulo de Tesorería",
    'summary': "Tesorería.",
    'author': "Ing. Mario Rangel, Elitumgroup S.A",
    'website': "http://www.elitumgroup.com",
    'category': "Personalization",
    'license': "LGPL-3",
    'version': "1.0",
    'depends': [
        'base',
        'eliterp_management',
        'mail',
        'account',
        'eliterp_accounting',
        'account_voucher',
        'eliterp_start',
        'purchase',
        'eliterp_hr'
    ],
    'data': [
        'data/sequences.xml',
        'security/treasury_security.xml',
        'security/ir.model.access.csv',
        'views/withhold_views.xml',
        'views/programmed_payment_views.xml',
        'views/invoice_views.xml',
        'views/small_box_views.xml',
        'views/travel_expenses_views.xml',
        'views/voucher_views.xml',
        'views/payment_advance_supplier_views.xml',
        'views/payment_request_views.xml',
        'views/pay_order_views.xml',
        'views/setting_views.xml',
        'reports/reports_views.xml',
        'reports/treasury_reports.xml',
        'views/menus.xml',
        'views/dashboard.xml',
    ],
    'init_xml': [],
    'update_xml': [],
    'installable': True,
    'active': False,
}
