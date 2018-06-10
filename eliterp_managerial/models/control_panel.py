# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models, _
import datetime

YEARS = [
    (2018, '2018'),
    (2019, '2019'),
    (2020, '2020'),
    (2021, '2021'),
    (2022, '2022'),
    (2023, '2023'),
    (2024, '2024'),
    (2025, '2025'),
]

MONTHS = [
    (1, 'Enero'), (2, 'Febrero'),
    (3, 'Marzo'), (4, 'Abril'),
    (5, 'Mayo'), (6, 'Junio'),
    (7, 'Julio'), (8, 'Agosto'),
    (9, 'Septiembre'), (10, 'Octubre'),
    (11, 'Noviembre'), (12, 'Diciembre'),
]


class ControlPanelLine(models.Model):
    _name = 'eliterp.control.panel.line'

    _description = 'Lineas de proceso en panel de control'

    @api.multi
    def export_file(self):
        """
        Exportamos archivo
        :return: dict
        """
        self.ensure_one()
        if self.adjunt:
            return {
                'type': 'ir.actions.act_url',
                'url': '/web/content?model=eliterp.control.panel.line&field=adjunt&id=%s&download=true&filename_field=adjunt_name' % (
                    self.id),
                'target': 'self'
            }
        else:
            return

    @api.depends('date')
    @api.one
    def _get_status(self):
        """
        Obtenemos el estado del registro
        """
        today = datetime.datetime.today().date()
        if datetime.datetime.strptime(self.date, "%Y-%m-%d").date() < today:
            if not self.adjunt:
                self.write({'state': 'defeated'})
            else:
                self.write({'state': 'done'})
                self.flag = True

    flag = fields.Boolean(compute='_get_status', default=False)
    state = fields.Selection([('new', 'Nuevo'),
                              ('done', 'Realizado'),
                              ('defeated', 'Vencido')], "Estado", default='new')

    comment = fields.Text('Novedades y comentarios')
    date = fields.Date('Fecha programada')
    management_date = fields.Date('Fecha de gestión', default=fields.Date.context_today)
    adjunt = fields.Binary('Adjunto')
    adjunt_name = fields.Char('Nombre de adjunto')
    control_panel_id = fields.Many2one('eliterp.control.panel', ondelete='cascade', string='Obligación')
    name_panel = fields.Char('Institución', related="control_panel_id.name", store=True)
    image_panel = fields.Binary(store=True, related="control_panel_id.image")
    type_panel = fields.Selection([('monthly', 'Mensual'), ('annual', 'Anual')], 'Frecuencia', default='monthly',
                                  related="control_panel_id.type", store=True)
    obligation_panel = fields.Char('Obligación', related="control_panel_id.obligation", store=True)
    departament_panel = fields.Many2one('hr.department', "Departamento", related="control_panel_id.departament",
                                        store=True)


class ControlPanel(models.Model):
    _name = 'eliterp.control.panel'

    _description = 'Panel de control'

    @api.multi
    def load_months(self):
        """
        Cargamos meses
        """
        list_lines = []
        today = datetime.date.today()
        if self.type == 'monthly':
            date = today.replace(year=int(self.year))
            date = today.replace(day=self.management_day)
            for x in range(1, 13):
                if x == 12:  # Mes de enero del siguiente año
                    date = date.replace(year=int(self.year) + 1)
                    date = date.replace(month=1)
                    list_lines.append([0, 0, {'code': x,
                                              'date': date,
                                              'state': 'new'}])
                else:
                    date = date.replace(month=(x + 1))
                    list_lines.append([0, 0, {'code': x,
                                              'date': date,
                                              'estado': 'new'}])

        else:  # Control anual
            date = today.replace(year=int(self.year))
            date = today.replace(month=int(self.month))
            date = today.replace(day=self.management_day)
            list_lines.append([0, 0, {'code': self.month,
                                      'date': date,
                                      'state': 'new'}])

        return self.update({'lines_process': list_lines, 'type': self.type})

    @api.depends('type')
    def _get_months(self):
        """
        Obtener cantidad de meses:
        """
        if self.type == 'monthly':
            result = 12 if len(self.lines_process) else False
        else:
            result = 1 if len(self.lines_process) else False
        self.count_months = result

    name = fields.Char('Institución', required=True)
    image = fields.Binary('Imagen institución')
    type = fields.Selection([('monthly', 'Mensual'), ('annual', 'Anual')], 'Frecuencia', default='monthly')
    year = fields.Selection(YEARS, string='Año', default=2018, required=True)
    month = fields.Selection(MONTHS, string='Mes', default=1)
    management_day = fields.Integer('Día gerencia', size=2, default=15, required=True)
    institution_day = fields.Integer('Día institución', size=2, default=12, required=True)
    obligation = fields.Char('Obligación', required=True)
    document = fields.Char('Documento')
    responsable = fields.Many2one('hr.employee', 'Responsable', required=True)
    departament = fields.Many2one('hr.department', "Departamento", related="responsable.department_id", store=True)
    lines_process = fields.One2many('eliterp.control.panel.line', 'control_panel_id', string='Líneas de proceso')
    count_months = fields.Boolean(compute='_get_months', default=False)


