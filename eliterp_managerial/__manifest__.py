# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

{
    'name': "Módulo Gerencial",
    'summary': "Gerencial.",
    'author': "Ing. Mario Rangel, Elitumgroup S.A",
    'website': "http://www.elitumgroup.com",
    'category': "Personalization",
    'license': "LGPL-3",
    'version': "1.0",
    'depends': [
        'base',
        'eliterp_management',
        'hr',
        'hr_holidays',
        'eliterp_hr',
        'account',
        'eliterp_start',
    ],
    'data': [
        'security/managerial_security.xml',
        'security/ir.model.access.csv',
        'reports/reports_views.xml',
        'reports/managerial_reports.xml',
        'views/control_panel_views.xml',
        'views/dashboard.xml',
    ],
    'init_xml': [],
    'update_xml': [],
    'installable': True,
    'active': False,
}
