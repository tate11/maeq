# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models, api


class ConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    default_settlement_travel_expenses = fields.Many2one('account.account',
                                               'Cuenta para liquidación de viáticos',
                                               default_model='eliterp.liquidation.settlement',
                                               domain=[('account_type', '=', 'movement')]
                                               )
    default_expenses_pay = fields.Many2one('account.account',
                                           'Cuenta para pago de viáticos',
                                           default_model='account.voucher',
                                           domain=[('account_type', '=', 'movement')]
                                           )
