# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).r

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round, float_is_zero


class Company(models.Model):
    _inherit = "res.company"

    report_color = fields.Char(
        string="Color de reporte",
        help="Color para las líneas de reporte."
    )

