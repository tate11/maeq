# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

{
    'name': "Módulo de Operaciones",
    'summary': "Operaciones de MAEQ.",
    'author': "Ing. Mario Rangel, Elitumgroup S.A",
    'website': "http://www.elitumgroup.com",
    'category': "Personalization",
    'license': "LGPL-3",
    'version': "1.0",
    'depends': [
        'base',
        'eliterp_management',
        'eliterp_purchases',
        'mail',
        'hr',
        'eliterp_hr',
        'stock',
        'sale',
        'account',
        'account_asset'
    ],
    'data': [
        'data/sequences.xml',
        'security/operations_security.xml',
        'security/ir.model.access.csv',
        'views/project_views.xml',
        'views/gang_views.xml',
        'views/machine_views.xml',
        'views/cmc_views.xml',
        'views/maintenance_views.xml',
        'views/dashboard.xml'
    ],
    'init_xml': [],
    'update_xml': [],
    'installable': True,
    'active': False,
}
