# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models, _
from datetime import date
from odoo.exceptions import UserError

TODAY = date.today()


class BankConciliationWizard(models.TransientModel):
    _name = 'eliterp.bank.conciliation.wizard'

    _description = 'Conciliación bancaria emergente'

    def _check_conciliation(self, year, month):
        """
        Verificar no exista conciliación bancaria publicada
        :param year:
        :param month:
        :return: boolean
        """
        conciliation = self.env['eliterp.bank.conciliation'].search([
            ('state', '=', 'posted'),
            ('bank_id', '=', self.bank_id.id),
            ('code', '=', year + month)
        ])
        return conciliation

    @api.multi
    def save_conciliation(self):
        """
        Creamos una nueva conciliación bancaria
        :return: dict
        """
        moves = self.env['account.move.line'].search([
            ('account_id', '=', self.bank_id.account_id.id),
            ('date', '>=', self.start_date),
            ('date', '<=', self.end_date)
        ])
        year, month = self.start_date[:4], self.start_date[5:7]
        if self._check_conciliation(year, month):
            raise UserError(_("Ya existe una Conciliación bancaria del "
                              "año %s mes %s para %s") % (year, month, self.bank_id.name))
        move_lines = []
        conciliation_ids = self.env['eliterp.bank.conciliation'].search([
            ('state', '=', 'posted'),
            ('bank_id', '=', self.bank_id.id)
        ])
        beginning_balance = 0.00
        if len(conciliation_ids) == 0:
            # Saldo inicial de cuenta contable si no existe conciliación alguna
            beginning_balance = self.env['eliterp.accounting.help']._get_beginning_balance(
                self.bank_id.account_id,
                self.start_date
            )
        else:
            last_conciliation = conciliation_ids[-1]
            for line in last_conciliation.lines_banks_move:
                if not line.check:
                    move_lines.append([0, 0, {'move_line_id': line.move_line_id.id,
                                              'valor': line.amount}])
        for line in moves:
            if line.move_id.state == 'posted' and not line.move_id.reversed:
                amount = 0.00
                if line.credit == 0.00:
                    amount = abs(line.debit)
                if line.debit == 0.00:
                    amount = abs(line.credit)
                    amount = -1 * amount
                move_lines.append([0, 0, {'move_line_id': line.id,
                                          'amount': amount}])
        conciliation = self.env['eliterp.bank.conciliation'].create({
            'bank_id': self.bank_id.id,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'beginning_balance': beginning_balance,
            'lines_banks_move': move_lines,
            'code': '%s%s' % (year, month)
        })

        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('eliterp_accounting.eliterp_action_bank_conciliation')
        form_view_id = imd.xmlid_to_res_id('eliterp_accounting.eliterp_view_form_bank_conciliation')
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'res_id': conciliation.id,
            'views': [[form_view_id, 'form']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        return result

    def _default_start_date(self):
        """
        Fecha inicio por defecto
        """
        return date(TODAY.year, TODAY.month, 1)

    @api.onchange('start_date')
    def _onchange_star_date(self):
        """
        Fecha fin al cambiar fecha inicio
        """
        if self.start_date:
            end_date = self.env['eliterp.global.functions']._get_last_day_month(self.start_date)
            self.end_date = end_date

    bank_id = fields.Many2one('res.bank', string="Banco", domain=[('type_use', '=', 'payments')], required=True)
    start_date = fields.Date('Fecha inicio', required=True, default=_default_start_date)
    end_date = fields.Date('Fecha fin', required=True)


class LinesBanksMove(models.Model):
    _name = 'eliterp.lines.banks.move'

    _description = 'Lineas de movimientos bancarios'

    move_line_id = fields.Many2one('account.move.line', string='Movimiento')
    check = fields.Boolean(default=False, string="Seleccionar?")
    date = fields.Date(related='move_line_id.date', string="Fecha de movimiento", store=True)
    journal = fields.Many2one('account.journal', related='move_line_id.journal_id', string="Diario", store=True)
    concept = fields.Char(related='move_line_id.name', string="Concepto", store=True)
    reference = fields.Char(related='move_line_id.ref', string="Referencia", store=True)
    amount = fields.Float('Monto')
    conciliation_id = fields.Many2one('eliterp.bank.conciliation', ondelete='cascade', string="Conciliación bancaria")


class BankConciliation(models.Model):
    _name = 'eliterp.bank.conciliation'

    _description = 'Concilación bancaria'

    @api.one
    @api.depends('lines_banks_move')
    def _get_total(self):
        """
        Obtenemos saldo banco y saldo contable
        """
        total = 0.00
        total_account = 0.00
        if len(self.lines_banks_move) == 0:
            self.total = total
            self.amount_account = self.beginning_balance
        else:
            for line in self.lines_banks_move:
                if line.check:
                    total_account += line.amount
                total += line.amount
            self.total = total + self.beginning_balance
        self.amount_account = self.beginning_balance + total_account

    @api.multi
    def print_conciliation(self):
        """
        Imprimimos conciliación bancaria
        """
        self.ensure_one()
        pass

    @api.multi
    def posted_conciliation(self):
        """
        Confirmamos conciliación bancaria
        """
        new_name = self.journal_id.sequence_id.next_by_id()
        return self.write({
            'state': 'posted',
            'name': new_name,
            'posted_date': fields.Date.today(),
            'amount_conciliation': self.total
        })

    @api.model
    def _default_journal(self):
        """
        Definimos el diario por defecto
        """
        return self.env['account.journal'].search([('name', '=', 'Concilación bancaria')], limit=1)[0].id

    name = fields.Char('No. Documento', default='Nueva conciliación')
    bank_id = fields.Many2one('res.bank', string="Banco", domain=[('type_use', '=', 'payments')], required=True)
    account_id = fields.Many2one('account.account', related='bank_id.account_id', store=True)
    posted_date = fields.Date('Fecha de publicación')
    start_date = fields.Date('Fecha inicio', required=True)
    end_date = fields.Date('Fecha fin', required=True)
    concept = fields.Char('Concepto')
    beginning_balance = fields.Float('Saldo inicial', required=True)
    total = fields.Float('Saldo contable', compute='_get_total')
    amount_conciliation = fields.Float('Total de conciliación')
    journal_id = fields.Many2one('account.journal', string="Diario", default=_default_journal)
    amount_account = fields.Float('Saldo banco', compute='_get_total')
    lines_banks_move = fields.One2many('eliterp.lines.banks.move', 'conciliation_id',
                                       string=u"Líneas de Movimientos")
    state = fields.Selection([('draft', 'Borrador'), ('posted', 'Contabilizado')], string="Estado", default='draft')
    notes = fields.Text('Notas')
    code = fields.Char('Código', size=6, required=True)  # Para no crear dos conciliaciones del mismo mes
