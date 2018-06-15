# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models, api


class RecordOvertime(models.Model):
    _name = 'eliterp.record.overtime'
    _description = 'Horas extras'
    _order = 'name asc, date desc'

    name = fields.Many2one('hr.employee', string='Empleado')
    job_id = fields.Many2one('hr.job', related='name.job_id', string='Cargo')
    date = fields.Date('Fecha registro')
    additional_hours = fields.Float('HE 50%')
    amount_additional_hours = fields.Float(related='name.additional_hours', string='Monto HE 50%')
    total_additional_hours = fields.Float('Monto')


class Employee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def _get_additional_hours_period(self, date_from, date_to):
        """
        Obtenemos el total de las horas extras por período
        :param date_from:
        :param date_to:
        :return: float
        """
        total = 0.00
        for line in self.record_overtime_ids.filtered(lambda l: date_from <= l.date <= date_to):
            total += line.total_additional_hours
        return total

    record_overtime_ids = fields.One2many('eliterp.record.overtime', 'name',
                                          string='Registro de HE 50%')
