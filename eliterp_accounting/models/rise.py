# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models, _


class RiseCategory(models.Model):
    _name = 'eliterp.rise.category'
    _description = 'Categoría de RISE'

    @api.multi
    def name_get(self):
        result = []
        for data in self:
            result.append((data.id, "Categoría No. %s" % (data.name)))
        return result

    name = fields.Integer('Categoría No.')
    min_amount = fields.Float('Mínimo')
    max_amount = fields.Float('Máximo')


class RiseActivity(models.Model):
    _name = 'eliterp.rise.activity'
    _description = 'Actividad del RISE'

    name = fields.Char('Nombre', required=True)


class RiseCategoryActivity(models.Model):
    _name = 'eliterp.rise.category.activity'
    _description = 'Categoría - Actividad del RISE'

    @api.multi
    def name_get(self):
        result = []
        for data in self:
            result.append((data.id, "Categoría [%s]/Actividad[%s]" % (data.category_id.name, data.activity_id.name)))
        return result

    category_id = fields.Many2one('eliterp.rise.category', string='Categoría')
    activity_id = fields.Many2one('eliterp.rise.activity', string='Actividad')
    max_amount = fields.Float('Monto máximo (Mensual)')
    active = fields.Boolean('Activo?', default=True)
