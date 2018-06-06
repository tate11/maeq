# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models, _

STATES = [
    ('all', 'Todos'),
    ('new', 'Nuevo'),
    ('done', 'Realizado'),
    ('defeated', 'Vencido')
]


class ControlPanelReportPdf(models.AbstractModel):
    _name = 'report.eliterp_managerial.eliterp_report_control_panel'

    @staticmethod
    def _get_state(state):
        if state == 'new':
            return 'Nuevo'
        elif state == 'done':
            return 'Realizado'
        else:
            return 'Vencido'

    def _get_lines(self, doc):
        """
        Obtenemos líneas de reporte
        :param doc:
        :return: list
        """
        data = []
        arg = []
        arg.append(('date', '>=', doc.start_date))
        arg.append(('date', '<=', doc.end_date))
        if doc.state != 'all':
            arg.append(('state', '=', doc.state))
        records = self.env['eliterp.control.panel.line'].search(arg)
        for line in records:
            type = line.type_panel
            data.append({
                'institution': line.name_panel,
                'image': line.image_panel,
                'type': 'Mensual' if type == 'monthly' else 'Anual',
                'obligation': line.obligation_panel,
                'date': line.date,
                'comment': line.comment,
                'state': self._get_state(line.state),
            })
        return data

    @api.model
    def get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'doc_model': 'eliterp.control.panel.report',
            'docs': self.env['eliterp.control.panel.report'].browse(docids),
            'get_lines': self._get_lines,
            'data': data,
        }


class ControlPanelReport(models.TransientModel):
    _name = 'eliterp.control.panel.report'

    _description = "Ventana para reporte de panel de control"

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
        return self.env.ref('eliterp_managerial.eliterp_action_report_control_panel_report').report_action(self)

    start_date = fields.Date('Fecha inicio', required=True)
    end_date = fields.Date('Fecha fin', required=True)
    state = fields.Selection(STATES, "Estado", default='all')
