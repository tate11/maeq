# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models, _
from datetime import datetime, timedelta


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.onchange('payment_conditions')
    def _onchange_payment_conditions(self):
        if self.payment_conditions:
            if self.payment_conditions != 'credit':
                self.payment_term_id = False
                self.date_due = self.date_invoice

    @api.onchange('payment_term_id', 'date_invoice')
    def _onchange_payment_term_date_invoice(self):
        """
        Método modificado
        :return: self
        """
        if not self.payment_term_id:
            return
        if self.payment_conditions == 'credit' or self._context['type'] == 'out_invoice':
            pterm = self.payment_term_id
            pterm_list = pterm.with_context(currency_id=self.company_id.currency_id.id).compute(value=1,
                                                                                                date_ref=self.date_invoice)[
                0]
            self.date_due = max(line[0] for line in pterm_list)
        elif self.date_due and (self.date_invoice > self.date_due):
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

    account_analytic_id = fields.Many2one('account.analytic.account', 'Centro de costo',
                                          states={'draft': [('readonly', False)]})
    attach_invoice = fields.Binary('Adjuntar factura', attachment=True)
    attached_name = fields.Char('Nombre de adjunto')
    concept = fields.Char('Concepto')
    payment_conditions = fields.Selection([('cash', 'Contado'), ('credit', 'Crédito')], 'Condiciones de pago')
