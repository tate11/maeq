# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models, _
from odoo.tools import float_is_zero


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
        No hacemos nada
        :return: self
        """
        return

    @api.multi
    def action_view_pending_balance(self):
        """
        Facturas con saldo pendiente de proveedor
        """
        if float_is_zero(self.pending_balance, precision_rounding=3):  # Si es 0 no se lleva a la acción
            return
        invoices = self.env['account.invoice'].search([('partner_id', '=', self.id), ('state', '=', 'open')])
        invoices = invoices.filtered(lambda invoice: not invoice.reconciled)
        action = self.env.ref('purchase.act_res_partner_2_supplier_invoices')
        result = action.read()[0]
        if len(invoices) > 1:
            result['domain'] = "[('id','in',%s)]" % (invoices.ids)
        elif len(invoices) == 1:
            res = self.env.ref('account.invoice_supplier_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = invoices.id
        return result

    pending_balance = fields.Float(compute='_purchase_invoice_count', string='Saldo')
    tradename = fields.Char('Nombre comercial')
    payment_conditions = fields.Selection([
        ('cash', 'Contado'),
        ('credit', 'Crédito'),
        ('credit_fees', 'Crédito cuotas')
    ], string='Condición de pago')
    way_to_pay = fields.Selection([('transfer', 'Transferencia'), ('check', 'Cheque'), ('cash', 'Efectivo')],
                                  string='Forma de pago')
    property_account_payable_id = fields.Many2one('account.account',
                                                  string='Cuenta a pagar',
                                                  domain=[('account_type', '=', 'movement')])
