# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).


from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def open_programmed_payment(self):
        """
        Abrimos los pagos programados creados para la factura
        :return: dict
        """
        imd = self.env['ir.model.data']
        list_view_id = imd.xmlid_to_res_id('eliterp_treasury.eliterp_view_tree_programmed_payment')
        action = imd.xmlid_to_object('eliterp_treasury.eliterp_action_programmed_payment')
        form_view_id = imd.xmlid_to_res_id('eliterp_treasury.eliterp_view_form_programmed_payment')
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[list_view_id, 'tree'], [form_view_id, 'form']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        if len(self.programmed_payment_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % self.programmed_payment_ids.ids
        elif len(self.programmed_payment_ids) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = self.programmed_payment_ids.ids[0]
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result

    @api.multi
    def add_programmed_payment(self):
        """
        Abrimos ventana para añadir pagos programados
        :return: dict
        """
        view = self.env.ref('eliterp_treasury.eliterp_view_form_programmed_payment_wizard')
        context = {
            'default_invoice_id': self.id
        }
        return {
            'name': "Pago programado",
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'eliterp.programmed.payment',
            'view_id': view.id,
            'target': 'new',
            'context': context,
        }

    @api.multi
    def payment(self):
        """
        Creamos un pago directo desde la pantalla de factura
        :return: dict
        """
        count = 0
        for p in self.programmed_payment_ids:
            if p.state == 'paid':
                count += 1
        if len(self.programmed_payment_ids) == count:
            raise ValidationError("No existen valores para generar pago, pagos programados abonados o cancelados.")
        bank = self.programmed_payment_ids.filtered(lambda x: x.way_to_pay == 'check')
        new_voucher = self.env['account.voucher'].with_context({'voucher_type': 'purchase'})._voucher(
            self,
            bank[0]['bank_id'] if bank else False
        )
        action = self.env.ref('eliterp_treasury.eliterp_action_voucher_purchase')
        result = action.read()[0]
        res = self.env.ref('eliterp_treasury.eliterp_view_form_voucher_purchase', False)
        result['views'] = [(res and res.id or False, 'form')]
        result['res_id'] = new_voucher.ids[0]
        return result

    @api.one
    def _get_programmed_payment(self):
        """
        Cantidad de pagos programados
        """
        self.have_programmed_payment = True if self.programmed_payment_ids else False

    @api.one
    def _get_amount_programmed(self):
        """
        Calcular el monto total de pagos programados
        """
        payments = self.programmed_payment_ids.filtered(lambda x: x.state != 'paid')
        if payments:
            self.amount_programmed = sum(line.amount_reference for line in payments)

    programmed_payment_ids = fields.One2many('eliterp.programmed.payment', 'invoice_id', string='Pagos programados')
    amount_programmed = fields.Float('Total programado', compute='_get_amount_programmed')
    have_programmed_payment = fields.Boolean(compute='_get_programmed_payment')
    approval_status = fields.Selection([
        ('pending', 'Pendiente'),
        ('partial_approved', 'Aprobado parcial'),
        ('approved', 'Aprobado')
    ], string='Aprobación de pago', default='pending')


class AccountVoucher(models.Model):
    _inherit = 'account.voucher'

    @api.multi
    @api.returns('self')
    def _voucher(self, invoice, bank):
        """
        Creamos un nuevo voucher a partir de la factura
        :param invoice:
        :return: self
        """
        values = {}
        values['voucher_type'] = 'purchase'
        values['partner_id'] = invoice.partner_id.id
        values['beneficiary'] = invoice.partner_id.name
        values['account_id'] = invoice.partner_id.property_account_payable_id.id
        if bank:
            values['bank_id'] = bank.id
        else:
            values['type_egress'] = 'cash'
        values['amount_cancel'] = invoice.amount_programmed
        values['concept'] = 'PAGO DE FACTURA %s' % invoice.number
        # Líneas de cuentas
        lines_account = []
        lines_account.append([0, 0, {'account_id': invoice.partner_id.property_account_payable_id.id,
                                     'amount': invoice.amount_programmed,
                                     }])
        values['lines_account'] = lines_account
        # Líneas de facturas
        lines_invoices = []
        lines_invoices.append([0, 0, {
            'invoice_id': invoice.id,
            'date_due_invoice': invoice.date_due,
            'amount_invoice': invoice.amount_total,
            'amount_programmed': invoice.amount_programmed,
            'amount_total': invoice.residual,
            'amount_payable': invoice.amount_programmed
        }])
        values['lines_invoice_purchases'] = lines_invoices
        voucher_invoice = self.create(values)
        return voucher_invoice


class ProgrammedPayment(models.Model):
    _name = 'eliterp.programmed.payment'

    _description = 'Pagos programados de facturas de proveedor'

    @api.multi
    def unlink(self):
        """
        Verificar antes de borrar el registro
        :return: object
        """
        for payment in self:
            if payment.amount != payment.amount_reference:
                raise ValidationError("No se puede eliminar un pago programado abonado o pagado.")
        return super(ProgrammedPayment, self).unlink()

    @api.model
    def create(self, values):
        status = 'partial_approved'
        if values['payment_type'] == 'total':
            status = 'approved'
        invoice = self.env['account.invoice'].browse(values['invoice_id'])
        payment = super(ProgrammedPayment, self).create(values)
        invoice.write({
            'approval_status': status,
        })
        return payment

    @api.onchange('payment_type', 'amount')
    def _onchange_payment_type(self):
        """
        Al cambiar el tipo de pago actualizamos monto
        """
        if self.payment_type == 'total':
            self.amount = self.residual
        else:  # Si es mayor al residual se coloca el máximo
            if self.amount > self.residual:
                self.amount = self.residual
        self.amount_reference = self.amount

    @api.one
    @api.constrains('date')
    def _check_date(self):
        """
        Verificamos la fecha programada
        """
        if self.date < self.invoice_id.date_invoice:
            raise ValidationError(
                "La fecha programada no puede ser menor a la de la factura [%s]." % self.invoice_id.date_invoice)

    @api.one
    @api.depends('invoice_id.programmed_payment_ids')
    def _get_residual(self):
        """
        Calculamos el monto total de pagos programados
        """
        amount_payments = 0.0
        if self.invoice_id.have_programmed_payment:
            for payment in self.invoice_id.programmed_payment_ids:
                amount_payments += payment.amount_reference
        self.residual = self.invoice_id.residual - amount_payments

    invoice_id = fields.Many2one('account.invoice', 'Factura')
    name = fields.Char('Name', default='Pago programado')
    residual = fields.Float('Saldo', compute='_get_residual', store=True)
    payment_type = fields.Selection([('total', 'Total'), ('partial', 'Parcial')],
                                    string="Tipo de pago", required=True, default='total')
    amount = fields.Float('Monto aprobado', required=True)
    amount_reference = fields.Float('Saldo', required=True)
    date = fields.Date('Fecha programada', default=fields.Date.context_today, required=True)
    way_to_pay = fields.Selection([('check', 'Cheque'), ('cash', 'Efectivo')], string='Forma de pago',
                                  required=True, default='check')
    bank_id = fields.Many2one('res.bank', string='Banco', domain=[('type_use', '=', 'payments')])
    state = fields.Selection([('draft', 'Borrador'), ('paid', 'Pagada')], string='Estado', default='draft')
