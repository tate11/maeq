# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models


class Checks(models.Model):
    _name = 'eliterp.checks'

    _description = 'Cheques'

    @api.one
    @api.depends('amount')
    def _get_amount_letters(self):
        """
        Obtenemos el monto en letras
        """
        currency = self.env['res.currency'].search([('name', '=', 'USD')], limit=1)
        text = currency[0].amount_to_text(self.amount).replace('Dollars', 'Dólares')  # Dollars, Cents
        text = text.replace('Cents', 'Centavos')
        self.amount_in_letters = text.upper()

    @api.one
    def print_check(self):
        # TODO
        self.ensure_one()
        pass

    recipient = fields.Char('Girador/Beneficiario')
    partner_id = fields.Many2one('res.partner', string='Cliente/Proveedor')
    supplier_id = fields.Many2one('res.partner', string='Proveedor')  #?
    customer_id = fields.Many2one('res.partner', string='Cliente')  #?
    name = fields.Char('No. Cheque')
    bank_account = fields.Char('Cuenta bancaria')  #?
    bank_id = fields.Many2one('res.bank', 'Banco')
    account_id = fields.Many2one('account.account', domain=[('account_type', '=', 'movement')],
                                 string='Cuenta contable')  #?
    amount = fields.Float('Monto', required=True)
    amount_in_letters = fields.Char('Monto en letras', compute='_get_amount_letters', readonly=True)
    date = fields.Date('Fecha Recepción/Emisión', required=True, default=fields.Date.context_today)
    check_date = fields.Date('Fecha cheque', required=True)
    type = fields.Selection([('receipts', 'Recibidos'), ('issued', 'Emitidos')], string='Tipo')
    check_type = fields.Selection([('current', 'Corriente'), ('to_date', 'A la fecha')], string='Tipo de cheque'
                                  , default='current')
    state = fields.Selection([
        ('received', 'Recibido'),
        ('deposited', 'Depositado'),
        ('issued', 'Emitido'),
        ('charged', 'Cobrado'),  # TODO
        ('protested', 'Protestado')  # TODO
    ], string='Estado')
    move_id = fields.Many2one('account.move', string='Asiento contable')
