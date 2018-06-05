# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo.exceptions import UserError
from odoo import api, fields, models, _
from datetime import date

YEARS = [
    (2015, '2015'),
    (2016, '2016'),
    (2017, '2017'),
    (2018, '2018'),
    (2019, '2019'),
    (2020, '2020'),
    (2021, '2021'),
    (2022, '2022'),
    (2023, '2023'),
    (2024, '2024'),
    (2025, '2025'),
]


class LinesAccountPeriod(models.Model):
    _name = 'eliterp.lines.account.period'

    _description = 'Líneas de Período contable'

    name = fields.Char('Nombre')
    month = fields.Char('Mes')
    code = fields.Integer('Código')
    start_date = fields.Date('Fecha inicio')
    closing_date = fields.Date('Fecha cierre')
    period_id = fields.Many2one('eliterp.account.period', 'Año contable')


class AccountPeriod(models.Model):
    _name = 'eliterp.account.period'
    _description = 'Período contable'

    @api.one
    def load_months(self):
        """
        Generamos Líneas de período contable
        :return: self
        """
        global_functions = self.env['eliterp.global.functions']
        if len(self.lines_period) >= 12:
            raise UserError(_("No puede asignar más meses al Año Contable."))
        list = []
        for x in range(1, 13):
            list.append([0, 0, {
                'code': x,
                'name': global_functions._get_month_name(x) + " del " + str(self.year_accounting),
                'month': global_functions._get_month_name(x),
                'start_date': date(int(self.year_accounting), x, 1),
                'closing_date': global_functions._get_last_day_month(date(int(self.year_accounting), x, 1))
            }])
        return self.update({'lines_period': list, 'name': 'Año [%s]' % self.year_accounting})

    @api.onchange('year_accounting')
    def _onchange_year_accounting(self):
        """
        Generamos un rango de fechas por defecto
        :return: self
        """
        if self.year_accounting:
            self.start_date = date(self.year_accounting, 1, 1)
            self.closing_date = date(self.year_accounting, 12, 31)

    name = fields.Char('Nombre')
    year_accounting = fields.Selection(YEARS, string='Año contable', required=True)
    start_date = fields.Date('Fecha inicio', required=True)
    closing_date = fields.Date('Fecha cierre', required=True)
    lines_period = fields.One2many('eliterp.lines.account.period', 'period_id', string='Líneas de Período contable')


class AccountAccountType(models.Model):
    _inherit = 'account.account.type'

    # Campo modificado
    type = fields.Selection(selection_add=[('bank', 'Banco')])


class AccountAccount(models.Model):
    _inherit = 'account.account'

    account_type = fields.Selection([
        ('view', 'Vista'),
        ('movement', 'Movimiento'),
    ], 'Tipo de cuenta', required=True, default='movement')


class AccountCommonReport(models.TransientModel):
    _inherit = "account.common.report"

    # TODO: Campo modificado
    target_move = fields.Selection([('posted', 'All Posted Entries'),
                                    ('all', 'All Entries'),
                                    ], string='Target Moves', required=True, default='all')


class WebPlanner(models.Model):
    _inherit = 'web.planner'

    def _prepare_planner_account_data(self):
        """
        TODO: Método modificado
        :return: dict
        """
        values = {
            'company_id': self.env.user.company_id,
            'is_coa_installed': bool(self.env['account.account'].search_count([])),
            'payment_term': self.env['account.payment.term'].search([])
        }
        return values


class Bank(models.Model):
    _inherit = 'res.bank'

    @api.model
    @api.returns('self', lambda value: value.id)
    def create(self, values):
        if values['type_use'] == 'payments':
            # Creamos secuencia para nuevo banco, soló en pagos
            new_sequence = self.env['ir.sequence'].sudo().create({
                'name': "Banco " + values['name'].lower(),
                'number_next': values['start'],
                'code': values['account_number'],
                'padding': values['padding']
            })
            values.update({'sequence_id': new_sequence.id})
        return super(Bank, self).create(values)

    type_use = fields.Selection([('charges', 'Cobros'), ('payments', 'Pagos')], string='Tipo de uso',
                                default='charges')
    account_id = fields.Many2one('account.account', string='Cuenta contable',
                                 domain=[('account_type', '=', 'movement')])
    account_number = fields.Char('No. Cuenta')
    start = fields.Integer('Inicio')
    end = fields.Integer('Fin')
    padding = fields.Integer('Dígitos', default=7, help="Cantidad de dígitos en el talonario de la chequera")
    sequence_id = fields.Many2one('ir.sequence', string='Secuencia')
    number_next = fields.Integer('No. Siguiente', related='sequence_id.number_next', readonly=True)
    state_id = fields.Many2one("res.country.state", string='Provincia')
