# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class NotesCancelReason(models.TransientModel):
    _name = 'eliterp.notes.cancel.reason'

    _description = 'Razón para cancelar notas de crédito/débito'

    description = fields.Text(u'Descripción', required=True)

    @api.multi
    def cancel_note(self):
        """
        Cancelamos la nota
        :return:
        """
        note = self.env['eliterp.credit.debit.notes'].browse(self._context['active_id'])
        move_id = note.move_id
        move_id.with_context(from_note=True, note_id=note.id).reverse_moves(fields.Date.today(),
                                                                            note.journal_id or False)
        move_id.write({
            'state': 'cancel',
            'ref': self.description
        })
        note.write({'state': 'cancel'})
        return


class CreditDebitNotes(models.Model):
    _name = 'eliterp.credit.debit.notes'

    _description = 'Notas de crédito/débito'

    @api.model
    def create(self, vals):
        self.env['eliterp.global.functions'].valid_period(vals['date'])  # Validamos el período contable sea correcto
        res = super(CreditDebitNotes, self).create(vals)
        return res

    def line_move(self, name, debit, credit, account, flag, journal, move, date):
        """
        Creamos una línea de movimiento
        :param name:
        :param debit:
        :param credit:
        :param account:
        :param flag:
        :param journal:
        :param move:
        :param date:
        :return: object
        """
        self.env['account.move.line'].with_context(check_move_validity=flag).create({
            'name': name,
            'journal_id': journal,
            'account_id': account.id,
            'move_id': move,
            'debit': debit,
            'credit': credit,
            'date': date
        })

    @api.model
    def _default_journal(self):
        """
        Definimos diario por defecto
        """
        if 'default_type' in self._context:
            if self._context['default_type'] == 'credit':
                return self.env['account.journal'].search([('name', '=', 'Nota de crédito bancaria')])[0].id
            if self._context['default_type'] == 'debit':
                return self.env['account.journal'].search([('name', '=', 'Nota de débito bancaria')])[0].id

    @api.multi
    def print_note(self):
        """
        Imprimimos nota
        """
        self.ensure_one()
        if self.type == 'credit':  # Crédito
            return self.env.ref('eliterp_accounting.eliterp_action_report_credit_note').report_action(self)
        if self.type == 'debit':  # Débito
            return self.env.ref('eliterp_accounting.eliterp_action_report_debit_note').report_action(self)

    @api.one
    def confirm_note(self):
        """
        Confirmamos la nota
        """
        journal = self.journal_id.id
        move_id = self.env['account.move'].create({'journal_id': journal,
                                                   'date': self.date,
                                                   })
        if self.type == "debit":
            self.line_move(self.concept, 0.00, self.amount, self.bank_id.account_id, False, journal,
                           move_id.id, self.date)
            self.line_move(self.concept, self.amount, 0.00, self.account_id, True, journal, move_id.id,
                           self.date)
        if self.type == "credit":
            self.line_move(self.concept, 0.00, self.amount, self.account_id, False, journal, move_id.id,
                           self.date)
            self.line_move(self.concept, self.amount, 0.00, self.bank_id.account_id, True, journal,
                           move_id.id, self.date)
        move_id.post()
        move_id.write({'ref': 'Nota bancaria por ' + self.concept})
        return self.write({
            'state': 'posted',
            'name': move_id.name,
            'move_id': move_id.id
        })

    @api.multi
    def open_notes_cancel_reason(self):
        """
        Abrimos ventana emergente para cancelar nota
        :return: dict
        """
        return {
            'name': "Explique la razón",
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'eliterp.notes.cancel.reason',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    @api.one
    @api.constrains('amount')
    def _check_amount(self):
        """
        Verificamos qué el valor sea mayor a 0
        """
        if not self.amount > 0.0:
            raise ValidationError("La nota de crédito debe tener un monto mayor a 0.")

    name = fields.Char('No. Documento', copy=False)
    concept = fields.Char('Concepto', required=True)
    bank_id = fields.Many2one('res.bank', 'Banco', domain="[('type_use', '=', 'payments')]", required=True)
    date = fields.Date('Fecha', default=fields.Date.context_today, required=True)
    amount = fields.Float('Monto', required=True)
    account_id = fields.Many2one('account.account', 'Cuenta contable', domain=[('account_type', '=', 'movement')],
                                 required=True)
    journal_id = fields.Many2one('account.journal', 'Diario', default=_default_journal)
    move_id = fields.Many2one('account.move', string='Asiento contable', copy=False)
    type = fields.Selection([('credit', 'Crédito'), ('debit', 'Débito')], string='Tipo de nota')
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('posted', 'Contabilizado'),
        ('cancel', 'Cancelado')
    ], readonly=True, default='draft', copy=False, string="Estado")
