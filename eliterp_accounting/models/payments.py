# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models, _
from _datetime import date


class ReasonCancelPayment(models.TransientModel):
    _name = 'eliterp.reason.cancel.payment'

    _description = 'Razón para cancelar depósito/transferencia'

    description = fields.Text('Descripción', required=True)

    @api.multi
    def cancel_payment(self):
        """
        Cancelamos depósito/transferencia
        """
        payment = self.env['account.payment'].browse(self._context['active_id'])
        move_id = payment.move_id
        move_id.with_context(from_payment=True, payment_id=payment.id).reverse_moves(fields.Date.today(),
                                                                                     payment.journal_id or False)
        move_id.write({'state': 'cancel', 'ref': self.description})
        payment.write({'state': 'cancel'})
        if payment:
            if payment.deposit_type == 'check':
                for check in payment.lines_deposits_checks:
                    check.check_id.write({'state': 'received'})
        return


class LinesDepositsCash(models.Model):
    _name = 'eliterp.lines.deposits.cash'

    _description = 'Lineas de depósitos en efectivo'

    account_id = fields.Many2one('account.account', 'Cuenta', domain=[('account_type', '=', 'movement')])
    reference = fields.Char('Referencia')
    amount = fields.Float('Monto')
    payment_id = fields.Many2one('account.payment', string="Depósito")


class LinesDepositsCheck(models.Model):
    _name = 'eliterp.lines.deposits.check'

    _description = 'Lineas de depósitos en cheque'

    amount = fields.Float('Monto')
    check_number = fields.Char('No. Cheque')
    bank_id = fields.Many2one('res.bank', 'Banco origen')
    payment_id = fields.Many2one('account.payment', string="Depósito")
    check_id = fields.Many2one('eliterp.checks', string="Cheque")
    date_due = fields.Date("Fecha vencimiento")
    account_id = fields.Many2one('account.account', string='Cuenta', domain=[('account_type', '=', 'movement')])


class LineDepositsChecksExternal(models.Model):
    _name = 'eliterp.lines.deposits.checks.external'

    _description = 'Lineas de depósitos en cheques externos'

    bank_id = fields.Many2one('res.bank', string='Banco')
    check_account = fields.Char('No. Cuenta')
    check_number = fields.Char('No. Cheque')
    drawer = fields.Char('Girador')
    account_id = fields.Many2one('account.account', 'Cuenta', domain=[('account_type', '=', 'movement')])
    amount = fields.Float('Monto')
    payment_id = fields.Many2one('account.payment', string="Depósito")


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.onchange('amount', 'currency_id')
    def _onchange_amount(self):
        """
        MM: TODO, me sale error en moneda
        """
        return

    @api.multi
    def print_payment(self):
        """
        Imprimir depósito/transferencia
        """
        self.ensure_one()
        pass

    @api.multi
    def open_reason_cancel_payment(self):
        """
        Abrimos venta emergente para cancelar depósito/transferencia
        :return: dict
        """
        return {
            'name': "Explique la razón",
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'eliterp.reason.cancel.payment',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    @api.model
    def create(self, vals):
        """
        MM: Creamos nuevo registro
        :param vals:
        :return: object
        """
        self.env['eliterp.global.functions'].valid_period(
            vals['payment_date'])  # Validamos período contable sea el correcto
        res = super(AccountPayment, self).create(vals)
        res.name = ""
        return res

    @api.one
    def confirm_transfer(self):
        """
        Confirmamos la transferencia
        """
        move_id = self.env['account.move'].create({'journal_id': self.journal_id.id,
                                                   'date': self.payment_date
                                                   })
        self.env['account.move.line'].with_context(check_move_validity=False).create(
            {'name': self.concept,
             'journal_id': self.journal_id.id,
             'account_id': self.account_credit_id.id,
             'move_id': move_id.id,
             'debit': 0.0,
             'credit': self.amount_transfer,
             'date': self.payment_date
             })
        self.env['account.move.line'].with_context(check_move_validity=True).create(
            {'name': self.concept,
             'journal_id': self.journal_id.id,
             'account_id': self.account_debit_id.account_id.id,
             'move_id': move_id.id,
             'debit': self.amount_transfer,
             'credit': 0.0,
             'date': self.payment_date
             })
        new_name = self.journal_id.sequence_id.next_by_id()
        move_id.with_context(eliterp_moves=True, move_name=new_name).post()
        move_id.write({'ref': "%s [%s]" % (new_name, self.concept)})
        return self.write({
            'state': 'posted',
            'name': new_name,
            'move_id': move_id.id
        })

    @api.one
    def confirm_deposit(self):
        """
        Confirmamos el depósito
        """
        if self.payment_type_customize == 'deposit':
            # Cheques recaudados
            if self.deposit_type == 'check':
                move_id = self.env['account.move'].create({'journal_id': self.journal_id.id,
                                                           'date': self.payment_date
                                                           })
                for line in self.lines_deposits_checks:
                    self.env['account.move.line'].with_context(check_move_validity=False).create(
                        {'name': self.concept,
                         'journal_id': self.journal_id.id,
                         'account_id': line.account_id.id,
                         'move_id': move_id.id,
                         'debit': 0.0,
                         'credit': line.amount,
                         'date': self.payment_date
                         })
                    line.check_id.write({'state': 'deposited'})
                self.env['account.move.line'].with_context(check_move_validity=True).create(
                    {'name': self.concept,
                     'journal_id': self.journal_id.id,
                     'account_id': self.bank_cash.account_id.id,
                     'move_id': move_id.id,
                     'debit': self.amount,
                     'credit': 0.0,
                     'date': self.payment_date
                     })
                new_name = self.journal_id.sequence_id.next_by_id()
                move_id.with_context(eliterp_moves=True, move_name=new_name).post()
                move_id.write({'ref': "%s [%s]" % (new_name, self.concept)})
                return self.write({'state': 'posted', 'name': new_name, 'move_id': move_id.id})
            # Efectivo
            if self.deposit_type == 'cash':
                move_id = self.env['account.move'].create({'journal_id': self.journal_id.id,
                                                           'date': self.payment_date
                                                           })
                for line in self.lines_deposits_cash:
                    self.env['account.move.line'].with_context(check_move_validity=False).create(
                        {'name': self.concept,
                         'journal_id': self.journal_id.id,
                         'account_id': line.account_id.id,
                         'move_id': move_id.id,
                         'debit': 0.0,
                         'credit': line.amount,
                         'date': self.payment_date
                         })
                self.env['account.move.line'].with_context(check_move_validity=True).create(
                    {'name': self.concept,
                     'journal_id': self.journal_id.id,
                     'account_id': self.bank_cash.account_id.id,
                     'move_id': move_id.id,
                     'debit': self.amount,
                     'credit': 0.0,
                     'date': self.payment_date
                     })
                new_name = self.journal_id.sequence_id.next_by_id()
                move_id.with_context(eliterp_moves=True, move_name=new_name).post()
                move_id.write({'ref': "%s [%s]" % (new_name, self.concept)})
                return self.write({'state': 'posted', 'name': new_name, 'move_id': move_id.id})
            # Cheques externos
            if self.deposit_type == 'external_check':
                move_id = self.env['account.move'].create({'journal_id': self.journal_id.id,
                                                           'date': self.payment_date
                                                           })
                for line in self.lines_deposits_checks_external:
                    self.env['account.move.line'].with_context(check_move_validity=False).create(
                        {'name': self.concept,
                         'journal_id': self.journal_id.id,
                         'account_id': line.account_id.id,
                         'move_id': move_id.id,
                         'debit': 0.0,
                         'credit': line.amount,
                         'date': self.payment_date
                         })
                self.env['account.move.line'].with_context(check_move_validity=True).create(
                    {'name': self.concept,
                     'journal_id': self.journal_id.id,
                     'account_id': self.bank_cash.account_id.id,
                     'move_id': move_id.id,
                     'debit': self.amount,
                     'credit': 0.0,
                     'date': self.payment_date
                     })
                new_name = self.journal_id.sequence_id.next_by_id()
                move_id.with_context(eliterp_moves=True, move_name=new_name).post()
                move_id.write({'ref': "%s [%s]" % (new_name, self.concept)})
                return self.write({'state': 'posted', 'name': new_name, 'move_id': move_id.id})

    def _default_journal(self):
        """
        MM: Definimos diario por defecto
        """
        if self._context['default_payment_type_customize'] == 'deposit':
            return self.env['account.journal'].search([('name', '=', 'Depósito bancario')], limit=1)[0].id
        if self._context['default_payment_type_customize'] == 'transfer':
            return self.env['account.journal'].search([('name', '=', 'Transferencia bancaria')], limit=1)[0].id

    def load_amount(self):
        """
        Sumar total de cada línea de depósito
        """
        total = 0.00
        if self.deposit_type == 'check':
            for line in self.lines_deposits_checks:
                total += line.amount
        if self.deposit_type == 'external_check':
            for line in self.lines_deposits_checks_external:
                total += line.amount
        if self.deposit_type == 'cash':
            for line in self.lines_deposits_cash:
                total += line.amount
        return self.update({'amount': total})

    def load_checks(self):
        """
        Cargamos cheques mayores a la fecha actual y menores a la fecha de recepción
        """
        today = date.today().strftime('%Y-%m-%d')
        check_list = self.env['eliterp.checks'].search([
            ('date', '<=', today),
            ('check_date', '>=', today),
            ('type', '=', 'receipts'),
            ('state', '=', 'received')
        ])
        lines = []
        for check in check_list:
            lines.append([0, 0, {'check_id': check.id,
                                 'check_number': check.name,
                                 'account_id': check.account_id.id,
                                 'bank_id': check.bank_id.id,
                                 'amount': check.amount,
                                 'date_due': check.check_date}])
        return self.update({'lines_deposits_checks': lines})

    # Campo modificado
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Contabilizado'),
        ('sent', 'Sent'),
        ('reconciled', 'Reconciliación'),
        ('cancel', 'Cancelado')], readonly=True, default='draft', copy=False, string="Estado")
    account_debit_id = fields.Many2one('res.bank', string='Cuenta debe', domain=[('type_use', '=', 'payments')])
    account_credit_id = fields.Many2one('account.account', string='Cuenta haber',
                                        domain=[('account_type', '=', 'movement')])
    amount_transfer = fields.Float('Monto transferencia')
    payment_type_customize = fields.Selection([
        ('deposit', 'Depósito'),
        ('payment', 'Pago'),
        ('transfer', 'Transferencia')
    ])
    # Campo modificado
    journal_id = fields.Many2one('account.journal', 'Diario',
                                 required=True, readonly=True, states={'draft': [('readonly', False)]},
                                 default=_default_journal, domain=None)
    amount = fields.Monetary('Cantidad a depositar', default=1.00)
    deposit_type = fields.Selection([
        ('check', 'Cheques recaudados'),
        ('external_check', 'Cheques externos'),
        ('cash', 'Efectivo')
    ], string="Tipo de depósito", default='check')
    bank_cash = fields.Many2one('res.bank', string="Banco")
    concept = fields.Char('Concepto', required=True, default='/')
    lines_deposits_cash = fields.One2many('eliterp.lines.deposits.cash', 'payment_id', string='Líneas de efectivo')
    lines_deposits_checks_external = fields.One2many('eliterp.lines.deposits.checks.external', 'payment_id',
                                                     string='Cheques externos')
    lines_deposits_checks = fields.One2many('eliterp.lines.deposits.check', 'payment_id', string='Cheques recaudados')
    move_id = fields.Many2one('account.move', string="Asiento contable")
