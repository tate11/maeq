# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import models, api, fields
from collections import defaultdict
import pytz
from datetime import datetime, timedelta
from odoo import api, fields, models


class FinancialSituationReportPdf(models.AbstractModel):
    _name = 'report.eliterp_accounting.eliterp_report_financial_situation'

    def _get_lines(self, doc):
        """
        Obtenemos líneas de reporte
        :param doc:
        :return: list
        """
        data = []

    @api.model
    def get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'doc_model': 'eliterp.financial.situation.report',
            'docs': self.env['eliterp.financial.situation.report'].browse(docids),
            'get_lines': self._get_lines,
            'data': data,
        }


class FinancialSituationReport(models.TransientModel):
    _name = 'eliterp.financial.situation.report'

    _description = "Ventana para reporte de situación financiera"

    @api.multi
    def print_report_pdf(self):
        """
        Imprimimos reporte en pdf
        """
        self.ensure_one()
        return self.env.ref('eliterp_accounting.eliterp_action_report_financial_situation').report_action(self)

    start_date = fields.Date('Fecha inicio', required=True)
    end_date = fields.Date('Fecha fin', required=True)


class GeneralLedgerReportPdf(models.AbstractModel):
    _name = 'report.eliterp_accounting.eliterp_report_general_ledger'

    def _get_lines(self, doc):
        """
        Obtenemos líneas de reporte
        :param doc:
        :return: list
        """
        data = []
        if doc.type == 'all':
            base_accounts = self.env['account.account'].search([('account_type', '=', 'movement')])  # Todas las cuentas
        else:
            base_accounts = doc.account_id
        accounts = []
        data = []
        for c in base_accounts:
            accounts.append(c)
        accounts.sort(key=lambda x: x.code, reverse=False)  # Ordenamos de menor a mayor por código
        for account in accounts:
            lines = self.env['account.move.line'].search(
                [('account_id', '=', account.id), ('date', '>=', doc.start_date), ('date', '<=', doc.end_date)],
                order="date")  # Movimientos de la cuenta ordenamos por fecha
            beginning_balance = self.env['eliterp.accounting.help']._get_beginning_balance(account, doc.start_date,
                                                                                           doc.end_date)
            balance = beginning_balance
            total_debit = 0.00
            total_credit = 0.00
            data_line = []  # Líneas de movimientos de la cuenta
            for line in lines:
                total_debit = total_debit + line.debit
                total_credit = total_credit + line.credit
                type = (account.code.split("."))[0]
                amount = line.debit - line.credit
                if type in ['1', '5']:
                    if line.debit < line.credit:
                        if amount > 0:
                            amount = -1 * round(line.debit - line.credit, 2)
                if type in ['2', '3', '4']:
                    if line.debit < line.credit:
                        if amount < 0:
                            amount = -1 * round(line.debit - line.credit, 2)
                    if line.debit > line.credit:
                        if amount > 0:
                            amount = -1 * round(line.debit - line.credit, 2)
                balance = balance + amount
                data_line.append({'name': line.move_id.name,
                                  'date': line.date,
                                  'detail': line.name,
                                  'debit': line.debit,
                                  'credit': line.credit,
                                  'balance': balance})

            total_balance = total_debit - total_credit
            if len(lines) != 0:  # Naturaleza de cuentas
                if type in ['1', '5']:
                    if total_debit < total_credit:
                        if total_balance > 0:
                            total_balance = -1 * round(total_debit - total_credit, 2)
                if type in ['2', '3', '4']:
                    if total_debit < total_credit:
                        if total_balance < 0:
                            total_balance = -1 * round(total_debit - total_credit, 2)
                    if total_debit > total_credit:
                        if total_balance > 0:
                            total_balance = -1 * round(total_debit - total_credit, 2)
            total_balance = beginning_balance + total_balance
            if data_line or beginning_balance > 0:  # Soló si tienes líneas de movimiento o saldo inicial
                data.append({
                    'account': account.name,
                    'code': account.code,
                    'moves': data_line,
                    'total_debit': total_debit,
                    'total_credit': total_credit,
                    'total_balance': total_balance,
                    'beginning_balance': beginning_balance
                })
        return data

    @api.model
    def get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'doc_model': 'eliterp.general.ledger.report',
            'docs': self.env['eliterp.general.ledger.report'].browse(docids),
            'get_lines': self._get_lines,
            'data': data,
        }


class GeneralLedgerReport(models.TransientModel):
    _name = 'eliterp.general.ledger.report'

    _description = "Ventana para reporte de libro mayor"

    @api.multi
    def print_report_pdf(self):
        """
        Imprimimos reporte en pdf
        """
        self.ensure_one()
        return self.env.ref('eliterp_accounting.eliterp_action_report_general_ledger').report_action(self)

    start_date = fields.Date('Fecha inicio', required=True)
    end_date = fields.Date('Fecha fin', required=True)
    type = fields.Selection([('all', 'Todas'), ('one', 'Individual')], default='all', string='Tipo de reporte')
    account_id = fields.Many2one('account.account', 'Cuenta', domain=[('account_type', '=', 'movement')])
