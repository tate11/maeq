# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import models


class AccountinHelps(models.TransientModel):
    _name = 'eliterp.accounting.help'
    _description = 'Ayudas para contabilidad'

    def _get_beginning_balance(self, account, start_date, end_date=None):
        """
        Obtenemos el saldo inicial de una cuenta contable
        :param account:
        :param start_date:
        :param end_date:
        :return: float
        """
        move_lines = self.env['account.move.line'].search([
            ('account_id', '=', account.id),
            ('date', '>=', '2000-01-01'),
            ('date', '<', start_date)
        ])
        balance = 0.00
        for line in move_lines:
            # Dependiendo del código inicial de cuenta se realizan los cáclculos
            # e.g 1.1.1.2.2 BANCO BOLIVARIANO
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
        return balance
