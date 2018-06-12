# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models


class RecordOvertime(models.Model):
    _name = 'eliterp.record.overtime'
    _description = 'Horas extras'
    _order = 'name asc, date desc'

    name = fields.Many2one('hr.employee', string='Empleado')
    job_id = fields.Many2one('hr.job', related='name.job_id', string='Cargo')
    date = fields.Date('Fecha registro')
    additional_hours = fields.Float('HE 50%')
    amount_additional_hours = fields.Float(related='name.additional_hours', string='Monto HE 50%')
    total_additional_hours = fields.Float('Total HE 50%')
