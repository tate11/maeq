# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models, _


class ConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    default_wage = fields.Float(
        'Sueldo básico unficado',
        default_model='hr.employee',
        default=386
    )
    default_test_days = fields.Integer(
        'Días de período de prueba',
        default_model='hr.contract',
        default=90
    )
