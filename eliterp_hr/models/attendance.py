# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models
from datetime import datetime, time, timedelta
import math


class Attendance(models.Model):
    _name = 'eliterp.attendance'
    _description = 'Asistencias'
    _order = 'date desc'

    def _get_default_lines(self):
        """
        Obtenemos líneas por defecto de empleados, dependiendo de la jornada de
        trabajo dada a cada contrato se generarán los horarios
        """
        day = str(datetime.now().weekday())
        employees = self.env['hr.employee'].search([])
        lines = []
        for employee in employees:
            if employee.contract_id:  # Soló los que tienen contrato se realiza
                calendar = employee.contract_id.resource_calendar_id
                working_day = calendar.attendance_ids.filtered(lambda x: x.dayofweek == day)
                lines.append([0, 0, {
                    'employee_id': employee.id,
                    'state': 'no news',
                    'check_in_am': working_day[0]['hour_from'],
                    'check_out_am': working_day[0]['hour_to'],
                    'check_in_pm': working_day[1]['hour_from'],
                    'check_out_pm': working_day[1]['hour_to']
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
        self.name = "Semana %d del %s" % (self.week, self.date[:4])

    @staticmethod
    def float_to_time(float_hour):
        """
        Transformamos de flotante a tiempo
        :param float_hour:
        :return: time
        """
        return time(int(math.modf(float_hour)[1]), int(60 * math.modf(float_hour)[0]), 0)

    @api.multi
    def validate(self):
        """
        Validamos documento luego de realizar inspecciones y
        creamos registros de asistencias
        """
        object_attendance = self.env['hr.attendance']
        for line in self.lines_employee:
            entry_time = self.float_to_time(line.check_in_am)
            departure_time = self.float_to_time(line.check_out_pm)
            year, month, day = int(self.date[:4]), int(self.date[5:7]), int(self.date[8:])
            check_in = datetime(
                year,
                month,
                day,
                entry_time.hour,
                entry_time.minute,
                entry_time.second
            )
            check_out = datetime(
                year,
                month,
                day,
                departure_time.hour,
                departure_time.minute,
                departure_time.second
            )
            object_attendance.create({
                'employee_id': line.employee_id.id,
                'check_in': check_in + timedelta(hours=5),
                'check_out': check_out + timedelta(hours=5)
            })
        self.write({'state': 'validate'})

    name = fields.Char('Nombre', compute='_compute_name', store=True)
    responsable = fields.Many2one('hr.employee', string='Responsable', required=True,
                                  readonly=True, states={'draft': [('readonly', False)]})
    date = fields.Date('Fecha registro', default=fields.Date.context_today, required=True,
                       readonly=True, states={'draft': [('readonly', False)]})
    week = fields.Integer('Semana', compute='_get_week', store=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('validate', 'Validado')
    ], string='Estado', default='draft')
    lines_employee = fields.One2many('eliterp.attendance.lines', 'attendance_id', 'Empleados',
                                     default=_get_default_lines,
                                     readonly=True, states={'draft': [('readonly', False)]})


class AttendanceLines(models.Model):
    _name = 'eliterp.attendance.lines'
    _description = 'Línea de asistencias'

    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True)
    state = fields.Selection([
        ('no news', 'Sin novedad'),
        ('free', 'Libre'),
        ('lack', 'Falta')
    ], string='Estado', default='no news', required=True)
    check_in_am = fields.Float('Entrada')
    check_out_am = fields.Float('Inicio')
    check_in_pm = fields.Float('Fin')
    check_out_pm = fields.Float('Salida')
    news = fields.Text('Novedades')
    attendance_id = fields.Many2one('eliterp.attendance', string='Registro diario de asistencia')
