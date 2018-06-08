# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.multi
    def _purchase_invoice_count(self):
        """
        Método modificado
        :return: object
        """
        PurchaseOrder = self.env['purchase.order']
        Invoice = self.env['account.invoice']
        for partner in self:
            partner.purchase_order_count = PurchaseOrder.search_count([('partner_id', 'child_of', partner.id)])
            invoices = Invoice.search([('partner_id', '=', partner.id), ('state', '!=', 'cancel')])
            partner.supplier_invoice_count = round(float(sum(line.amount_total for line in invoices)),
                                                   2)  # Total facturado
            partner.pending_balance = round(float(sum(line.residual for line in invoices)),
                                            2)  # Total de saldo pendiente

    @api.onchange('property_account_payable_id')
    def _onchange_property_account_payable(self):
        """
        Se realiza esto para manejar cuentas seperadas de Proveedor/Cliente
        :return: self
        """
        if self.property_account_payable_id:
            self.property_account_receivable_id = self.property_account_payable_id.id

    pending_balance = fields.Float(compute='_purchase_invoice_count', string='Saldo')
    payment_conditions = fields.Selection([('cash', 'Contado'), ('credit', 'Crédito')], string='Condición de pago')
    way_to_pay = fields.Selection([('transfer', 'Transferencia'), ('check', 'Cheque'), ('cash', 'Efectivo')],
                                  string='Forma de pago')
    property_account_payable_id = fields.Many2one('account.account',
                                                  string='Cuenta a pagar',
                                                  domain=[('account_type', '=', 'movement')])
