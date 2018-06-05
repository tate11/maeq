# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import models, fields


class Canton(models.Model):
    _name = 'eliterp.canton'
    _description = 'Cantón'

    state_id = fields.Many2one('res.country.state', string='Provincia', required=True)
    code = fields.Char('Código', size=4, required=True)
    name = fields.Char('Nombre', required=True)


class Parish(models.Model):
    _name = 'eliterp.parish'
    _description = 'Parroquia'

    canton_id = fields.Many2one('eliterp.canton', string='Cantón', required=True)
    code = fields.Char('Código', size=6, required=True)
    name = fields.Char('Nombre', required=True)