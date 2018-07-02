# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

{
    'name': "Módulo de Administración",
    'summary': "Administración.",
    'author': "Ing. Mario Rangel, Elitumgroup S.A",
    'website': "http://www.elitumgroup.com",
    'category': "Personalization",
    'license': "LGPL-3",
    'version': "1.0",
    'depends': [
        'account',
        'base',
        'mail',
        'web_widget_color',
        'board'
    ],
    'data': [
        'data/sequences.xml',
        'data/res.country.state.csv',
        'data/eliterp.canton.csv',
        'data/eliterp.parish.csv',
        'security/management_security.xml',
        'security/ir.model.access.csv',
        'reports/paperformat_reports.xml',
        'reports/layout_reports.xml',
        'views/company_views.xml',
        'views/dashboard.xml',
        # TODO: 'views/app_views.xml',
        'views/menus.xml',
    ],
    'init_xml': [],
    'update_xml': [],
    'installable': True,
    'active': False,
}
