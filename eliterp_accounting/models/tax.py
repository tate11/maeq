# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models, api


class AccountTax(models.Model):
    _inherit = 'account.tax'

    @api.multi
    def name_get(self):
        result = []
        for data in self:
            if data.tax_type == 'retention':
                result.append((data.id, "%s [%s]" % (str(data.code), data.name)))
            else:
                result.append((data.id, "%s" % (data.name)))
        return result

    code = fields.Char('Código')
    tax_type = fields.Selection([
        ('iva', 'IVA'),
        ('retention', 'Retención')
    ], string='Tipo de impuesto', default='iva', required=True)
    retention_type = fields.Selection([
        ('rent', 'Renta'),
        ('iva', 'IVA')
    ], string='Tipo de retención', default='rent')

    _sql_constraints = [
        ('code_unique', 'unique (code,type_tax_use)', 'El Código de Impuesto debe ser único por tipo.')
    ]
