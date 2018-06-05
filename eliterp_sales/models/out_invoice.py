# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models, _
from odoo.exceptions import Warning

RATE = [
    (10, '10'),
    (20, '20'),
    (30, '30'),
    (40, '40'),
    (50, '50')
]


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def action_number(self):
        """
        Siguiente número en consecutivo de autorización
        :return: self
        """
        sequence = self.sri_authorization_id.sequence_id
        invoice_number = sequence.next_by_id()
        self.write({'invoice_number': invoice_number})

    @api.one
    def apply_discount(self):
        """
        Aplicamos descuento a cada línea del Detalle de factura
        """
        if not self.invoice_line_ids:
            raise Warning("No hay Detalle de factura creado para aplicar descuento.")
        else:
            for line in self.invoice_line_ids:
                line.update({'discount': self.discount_rate})
        return

    @api.depends('invoice_line_ids.price_subtotal')
    @api.one
    def _get_total_discount(self):
        """
        Obtenemos el total a descontar
        :return: self
        """
        if not self.invoice_line_ids:
            return 0.00
        else:
            total_discount = 0.00
            for line in self.invoice_line_ids:
                sub_total = round(line.price_unit * line.quantity * (line.discount / 100), 2)
                total_discount += sub_total
            self.update({'total_discount': total_discount})

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """
        Método modificado
        :return: object
        """
        res = super(AccountInvoice, self)._onchange_partner_id()
        # Si el cliente tiene asesor se lo coloca en la factura
        if self.partner_id:
            if self.partner_id.consultant_id:
                self.consultant_id = self.partner_id.consultant_id
        return res

    consultant_id = fields.Many2one('hr.employee', string='Asesor')
    have_discount = fields.Boolean('Lleva descuento?', default=False, readonly=True, states={'draft': [('readonly', False)]})
    discount_rate = fields.Selection(RATE, string='Porcentaje de descuento')
    total_discount = fields.Monetary('Descuento', compute='_get_total_discount', readonly=True, store=True)
