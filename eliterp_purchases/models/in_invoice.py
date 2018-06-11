# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models, _
from datetime import datetime
from odoo.exceptions import ValidationError


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.onchange('payment_conditions')
    def _onchange_payment_conditions(self):
        if self.payment_conditions:
            if self.payment_conditions != 'credit':
                self.payment_term_id = False
                self.date_due = self.date_invoice

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """
        Obtenemos Condiciones de pago de Proveedor si existen
        :return: object
        """
        res = super(AccountInvoice, self)._onchange_partner_id()
        self.payment_conditions = self.partner_id.payment_conditions
        if self.partner_id.payment_conditions == 'credit':
            self.payment_term_id = self.partner_id.property_supplier_payment_term_id.id
        return res

    # Load all unsold PO lines
    @api.onchange('purchase_id')
    def purchase_order_change(self):
        """
        MM: Agregamos los centro de costo y proyecto desde la Orde de compra, también la cuenta del proveedor
        si es que existe
        """
        if not self.purchase_id:
            return {}
        if not self.partner_id:
            self.partner_id = self.purchase_id.partner_id.id

        new_lines = self.env['account.invoice.line']
        for line in self.purchase_id.order_line - self.invoice_line_ids.mapped('purchase_line_id'):
            data = self._prepare_invoice_line_from_po_line(line)
            new_line = new_lines.new(data)
            new_line._set_additional_fields(self)
            new_lines += new_line

        self.invoice_line_ids += new_lines
        self.payment_term_id = self.purchase_id.payment_term_id
        self.account_analytic_id = self.purchase_id.account_analytic_id.id if self.purchase_id.account_analytic_id else False
        self.project_id = self.purchase_id.project_id.id if self.purchase_id.project_id else False
        self.account_id = self.partner_id.property_account_receivable_id
        self.env.context = dict(self.env.context, from_purchase_order_change=True)
        self.purchase_id = False
        return {}

    @api.constrains('expiration_fee')
    def _check_expiration_fee(self):
        """
        Verificar que fecha no sea mayor a la de vencimiento ni menor a la fecha de factura
        """
        date_fee = datetime.strptime(self.expiration_fee, '%Y-%m-%d')
        date_invoice = datetime.strptime(self.date_invoice, '%Y-%m-%d')
        date_due = datetime.strptime(self.date_due, '%Y-%m-%d')
        if (date_fee < date_invoice):
            raise ValidationError('La fecha de cuota no puede ser menor a la de la factura.')
        if (date_fee > date_due):
            raise ValidationError('La fecha de cuota no puede ser mayor a la de vencimiento de la factura.')


    account_analytic_id = fields.Many2one('account.analytic.account', 'Centro de costo', readonly=True,
                                          states={'draft': [('readonly', False)]})
    attach_invoice = fields.Binary('Adjuntar factura', attachment=True)
    attached_name = fields.Char('Nombre de adjunto')
    concept = fields.Char('Concepto', readonly=True,
                          states={'draft': [('readonly', False)]})
    payment_conditions = fields.Selection([('cash', 'Contado'), ('credit', 'Crédito')], 'Condiciones de pago'
                                          , readonly=True, states={'draft': [('readonly', False)]}
                                          )
    dues = fields.Boolean('Cuotas?', default=False, readonly=True, states={'draft': [('readonly', False)]})
    fee_number = fields.Integer('No. Cuota', readonly=True, states={'draft': [('readonly', False)]})
    expiration_fee = fields.Date('Fecha vencimiento cuota', default=fields.Date.context_today,  readonly=True, states={'draft': [('readonly', False)]})