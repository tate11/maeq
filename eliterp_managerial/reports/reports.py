# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from collections import defaultdict
import pytz
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from custom.addons.report_xlsx.report.report_xlsx import ReportXlsxAbstract


class ReportControlPanelXLSX(ReportXlsxAbstract):
    _name = 'report.eliterp_managerial.eliterp_report_control_panel.xlsx'

    def generate_xlsx_report(self, workbook, data, lines):
        sheet = workbook.add_worksheet("Panel de control")
        bold = workbook.add_format({'bold': True})
        sheet.write(0, 0, "Test", bold)


class ReportControlPanel(models.AbstractModel):
    _name = 'report.eliterp_managerial.eliterp_report_control_panel'

    _description = "Ventana reporte de panel de control"

    @api.multi
    def _get_records(self, doc):
        """
        Obtenemos las líneas del reporte
        :param doc:
        :return: list
        """
        self.ensure_one()
        records = []
        arg = []
        arg.append(('date', '>=', doc.start_date))
        arg.append(('date', '<=', doc.end_date))
        if doc.state != 'all':
            arg.append(('state', '=', doc.state))
        data = self.env['eliterp.control.panel.line'].search(arg)
        for line in data:
            records.append({
                'institution': line.name_panel,
                'image': line.image_panel,
                'type': line.type_panel,
                'obligation': line.obligation_panel,
                'date': line.date,
                'comment': line.comment,
                'state': line.state,
            })
        return data


class ReportControlPanelWizard(models.TransientModel):
    _name = 'eliterp.report.control.panel.wizard'

    _description = "Ventana reporte de panel de control"

    @api.multi
    def print_report_xlsx(self):
        """
        Imprimimos reporte en xlsx
        """
        data = self.read()[0]
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'eliterp_managerial.eliterp_report_control_panel.xlsx',
            'datas': data
        }

    @api.multi
    def print_report_pdf(self):
        """
        Imprimimos reporte en pdf
        """
        self.ensure_one()
        return self.env.ref('eliterp_managerial.eliterp_action_report_to_control_panel').report_action(self)

    start_date = fields.Date('Fecha inicio', required=True)
    end_date = fields.Date('Fecha fin', required=True)
    state = fields.Selection([
        ('all', 'Todos'),
        ('new', 'Nuevo'),
        ('done', 'Realizado'),
        ('defeated', 'Vencido')
    ], "Estado", default='all')
