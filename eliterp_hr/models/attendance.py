# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models
from datetime import datetime

class Attendance(models.Model):
    _name = 'eliterp.attendance'
    _description = 'Asistencias'
    _order = 'date desc'

    def _get_default_lines(self):
        """
        Obtenemos líneas por defecto de empleados, colocar en configuraciones el departamento
        para carga de datos
        """
        employees = self.env['hr.employee'].search([])
        lines = []
        for employee in employees:
            lines.append([0, 0, {
                'employee_id': employee.id,
            }])
        return lines

    @api.one
    @api.depends('date')
    def _get_week(self):
        """
        Obtenemos la semanas de la fecha
        """
        if self.date:
            object_date = datetime.strptime(self.date, "%Y-%m-%d")
            self.week = object_date.isocalendar()[1]

    @api.one
    @api.depends('date', 'week')
    def _compute_name(self):
        """
        Obtenemos el nombre
        """
        self.name = "Semana %d del %s" % (self.week ,self.date[:4])

    name = fields.Char('Nombre', compute='_compute_name', store=True, index=True)
    responsable = fields.Many2one('hr.employee', string='Empleado', required=True)
    date = fields.Date('Fecha registro', default=fields.Date.context_today, required=True)
    week = fields.Integer('Semana', compute='_get_week', store=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('validate', 'Validado')
    ], string='Estado', default='draft')
    lines_employee = fields.One2many('eliterp.attendance.lines', 'attendance_id', 'Empleados', default=_get_default_lines)

class AttendanceLines(models.Model):
    _name = 'eliterp.attendance.lines'
    _description = 'Línea de asistencias'

    employee_id = fields.Many2one('hr.employee', string='Empleado')
    news = fields.Text('Novedades')
    attendance_id = fields.Many2one('eliterp.attendance', string='Registro de asistencia')
