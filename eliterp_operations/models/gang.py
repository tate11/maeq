# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import models, fields, api, _


class LinesEmployee(models.Model):
    _name = 'eliterp.lines.employee'

    _description = 'Líneas de empleado para cuadrilla'

    @api.model
    def name_get(self):
        result = []
        for data in self:
            result.append((data.id, data.employee_id.name))
        return result

    employee_id = fields.Many2one('hr.employee', string='Empleado')
    gang_id = fields.Many2one('hr.employee', string='Empleado')


class Gang(models.Model):
    _name = 'eliterp.gang'

    _description = 'Cuadrilla de operación'

    @api.depends('lines_employees')
    @api.one
    def _get_employees(self):
        """
        Obtenemos la cantidad de empleados
        """
        if self.lines_employees:
            self.count_employees = len(self.lines_employees)

    name = fields.Char('Nombre', required=True)
    code = fields.Char('Código', size=3)
    lines_employees = fields.One2many('eliterp.lines.employee', 'gang_id', string='Empleados')
    count_employees = fields.Integer('Nº empleados', compute='_get_employees')

    _sql_constraints = [
        ('code_unique', 'unique (code)', "El Código de la cuadrilla debe ser único.")
    ]
