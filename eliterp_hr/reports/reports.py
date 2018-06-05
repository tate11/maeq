# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from collections import defaultdict
import pytz
from datetime import datetime, timedelta
from odoo import api, fields, models


class EmployeeReportPdf(models.AbstractModel):
    _name = 'report.eliterp_hr.eliterp_report_employee_report'

    @staticmethod
    def _get_civil_status(civil_status):
        """
        Estado civil en español
        :param civil_status:
        :return: string
        """
        if civil_status == 'single':
            return "Soltero(a)"
        if civil_status == 'married':
            return "Casado(a)"
        if civil_status == 'widower':
            return "Viudo(a)"
        if civil_status == 'divorced':
            return "Divorciado(a)"

    def _get_lines(self, doc):
        """
        Obtenemos líneas de reporte
        :param doc:
        :return: list
        """
        data = []
        arg = []
        arg.append(('admission_date', '>=', doc.start_date))
        arg.append(('admission_date', '<=', doc.end_date))
        employees = self.env['hr.employee'].search(arg)
        count = 0
        for employee in employees:
            count += 1
            data.append({
                'number': count,
                'identification_id': employee.identification_id,
                'name': employee.name,
                'birthday': employee.birthday,
                'age': employee.age,
                'civil_status': self._get_civil_status(employee.marital),
                'admission_date': employee.admission_date,
                'department_id': employee.department_id.name,
                'job_id': employee.job_id.name,
                'wage': employee.wage
            })
        return data

    @api.model
    def get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'doc_model': 'eliterp.employee.report',
            'docs': self.env['eliterp.employee.report'].browse(docids),
            'get_lines': self._get_lines,
            'data': data,
        }


class EmployeeReport(models.TransientModel):
    _name = 'eliterp.employee.report'

    _description = "Ventana para reporte de empleados"

    @api.multi
    def print_report_pdf(self):
        """
        Imprimimos reporte en pdf
        """
        self.ensure_one()
        return self.env.ref('eliterp_hr.eliterp_action_report_employee_report').report_action(self)

    start_date = fields.Date('Fecha inicio', required=True)
    end_date = fields.Date('Fecha fin', required=True, default=fields.Date.context_today)
    active = fields.Boolean('Activos?', default=True, required=True,
                            help="Si se marca selecciona a todos los empleados activos.")


class AttendanceReport(models.TransientModel):
    _name = 'eliterp.attendance.report'

    _description = 'Ventana para reporte de asistencias'

    start_date = fields.Date('Fecha inicio', required=True)
    end_date = fields.Date('Fecha fin', required=True, default=fields.Date.context_today)
    type_employees = fields.Selection([('all', 'Todos'), ('one', 'Empleado')], string='Tipo', default='all')
    employee_id = fields.Many2one('hr.employee', string='Empleado')


class ReportAbsencesPdf(models.AbstractModel):
    _name = 'report.eliterp_hr.eliterp_report_report_absences'

    def _get_lines(self, doc):
        """
        Obtenemos líneas de reporte
        :param doc:
        :return: list
        """
        data = []
        arg = []
        arg.append(('state', '=', 'validate'))
        arg.append(('holiday_type', '=', 'employee'))
        arg.append(('date_from', '>=', doc.start_date))
        arg.append(('date_from', '<=', doc.end_date))
        if context['filtro_ausencia'] != 'todas':
            if isinstance(context['ausencias'], int):
                arg.append(('holiday_status_id', '=', context['ausencias']))
            else:
                arg.append(('holiday_status_id', '=', context['ausencias'].id))
        if context['filtro_empleado'] != 'todos':
            if isinstance(context['empleados'], int):
                arg.append(('employee_id', '=', context['empleados']))
            else:
                arg.append(('employee_id', '=', context['empleados'].id))
        ausencias = self.env['hr.holidays'].search(arg)
        for ausencia in ausencias:
            data.append({
                'estado': ausencia.employee_id.state_laboral,
                'nombre': ausencia.employee_id.name,
                'tipo_ausencia': ausencia.name,
                'fecha_inicial': ausencia.date_from,
                'fecha_final': ausencia.date_to,
                'days': str(ausencia.number_of_days_temp),
                'comentario': ausencia.report_note
            })
        if context['filtro_empleado'] == 'todos':
            data = filter(lambda x: x['estado'] == context['state_laboral'], data)
        data = sorted(data, key=lambda x: (x['nombre'], x['fecha_inicial']))
        ausencias_todos = self.env['hr.holidays'].search([('state', '=', 'validate'),
                                                          ('date_from', '>=', context['fecha_inicio']),
                                                          ('date_from', '<=', context['fecha_fin']),
                                                          ('holiday_type', '=', 'category')])
        for ausencia in ausencias_todos:
            data.append({
                'nombre': 'NÓMINA',
                'tipo_ausencia': ausencia.name,
                'fecha_inicial': ausencia.date_from,
                'fecha_final': ausencia.date_to,
                'days': str(ausencia.number_of_days_temp),
                'comentario': ausencia.report_note
            })
        return data

    @api.model
    def get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'doc_model': 'eliterp.report.absences',
            'docs': self.env['eliterp.report.absences'].browse(docids),
            'get_lines': self._get_lines,
            'data': data,
        }


class ReportAbsences(models.TransientModel):
    _name = 'eliterp.report.absences'

    _description = 'Ventana para reporte de ausencias'

    @api.multi
    def print_report_pdf(self):
        """
        Imprimimos reporte en pdf
        """
        self.ensure_one()
        return self.env.ref('eliterp_hr.eliterp_action_report_report_absences').report_action(self)

    start_date = fields.Date('Fecha inicio', required=True)
    end_date = fields.Date('Fecha fin', required=True, default=fields.Date.context_today)
    type_employees = fields.Selection([('all', 'Todos'), ('one', 'Empleado')], string='Tipo', default='all')
    employee_id = fields.Many2one('hr.employee', string='Empleado')
    type_absences = fields.Selection([('all', 'Todas'), ('one', 'Asusencia')], string='Tipo de ausencias',
                                     default='all')
    holidays_status_id = fields.Many2one('hr.holidays.status', string='Ausencia')


class HolidayReport(models.TransientModel):
    _name = 'eliterp.holiday.report'

    _description = 'Ventana para reporte de vacaciones del personal'

    type_report = fields.Selection([('all', 'Todos'), ('one', 'Empleado')], default='all')
    employee_id = fields.Many2one('hr.employee', string='Empleado')
    start_date = fields.Date('Fecha inicio', required=True)
    end_date = fields.Date('Fecha fin', required=True, default=fields.Date.context_today)
