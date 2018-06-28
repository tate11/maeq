# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import float_is_zero
import json


class PayWizard(models.TransientModel):
    _name = 'eliterp.pay.wizard'

    _description = 'Ventana para generar pago'

    @api.one
    @api.constrains('date')
    def _check_date(self):
        """
        Verificamos la fecha programada
        """
        if self.date < self.default_date:
            raise ValidationError(
                "La fecha programada no puede ser menor a [%s]." % self.default_date)

    @api.one
    @api.constrains('amount')
    def _check_amount(self):
        """
        Verificamos el monto
        """
        if self.amount > self.default_amount:
            raise ValidationError(
                "Monto mayor al del total del saldo del documento.")

    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        """
        Al cambiar el tipo de pago actualizamos monto
        """
        if self.payment_type == 'total':
            self.amount = self.default_amount

    @api.multi
    def confirm_payment(self):
        """
        Generamos OP
        """
        object_pay_order = self.env['eliterp.pay.order']
        name = self.env['ir.sequence'].next_by_code('pay.order')
        vals = {
            'name': name,
            'amount': self.amount,
            'type': self.type,
            'date': self.date
        }
        # Dependiendo del modelo activo
        if self._context['active_model'] == 'account.invoice':
            inv = self.env['account.invoice'].browse(self._context['active_id'])
            vals.update({
                'origin': inv.number,
                'invoice_id': inv.id
            })
        if self._context['active_model'] == 'purchase.order':
            po = self.env['purchase.order'].browse(self._context['active_id'])
            vals.update({
                'origin': po.name,
                'purchase_order_id': po.id
            })
        if self._context['active_model'] == 'eliterp.advance.payment':
            adq = self.env['eliterp.advance.payment'].browse(self._context['active_id'])
            vals.update({
                'origin': adq.name,
                'advance_payment_id': adq.id
            })
        if self._context['active_model'] == 'hr.payslip.run':
            rc = self.env['hr.payslip.run'].browse(self._context['active_id'])
            vals.update({
                'origin': rc.move_id.name,
                'payslip_run_id': rc.id
            })
        if self._context['active_model'] == 'eliterp.replacement.small.box':
            cajc = self.env['eliterp.replacement.small.box'].browse(self._context['active_id'])
            vals.update({
                'origin': cajc.name,
                'replacement_small_box_id': cajc.id
            })
        if self._context['active_model'] == 'eliterp.payment.request':
            pr = self.env['eliterp.payment.request'].browse(self._context['active_id'])
            vals.update({
                'origin': pr.name,
                'payment_request_id': pr.id
            })
        object_pay_order.create(vals)

    date = fields.Date('Fecha programada', default=fields.Date.context_today, required=True)
    payment_type = fields.Selection([('total', 'Total'), ('partial', 'Parcial')],
                                    string="Tipo de pago", required=True, default='total')
    type = fields.Char('Tipo')  # Selección para ver el tipo
    amount = fields.Float('Monto', required=True)
    default_amount = fields.Float('Monto ficticio')
    default_date = fields.Date('Fecha ficticia')


class AccountVoucher(models.Model):
    _inherit = 'account.voucher'

    @api.multi
    @api.returns('self')
    def _voucher(self, op):
        """
        Creamos un nuevo voucher a partir de OP
        :param op:
        :return: self
        """
        if float_is_zero(op.amount, precision_rounding=op.currency_id.rounding):
            return
        values = {}
        values['voucher_type'] = 'purchase'
        values['pay_order_id'] = op.id
        values['amount_cancel'] = op.amount
        # Factura
        if op.type == 'fap':
            invoice = op.invoice_id
            # Líneas de cuentas
            lines_account = []
            lines_account.append([0, 0, {'account_id': invoice.partner_id.property_account_payable_id.id,
                                         'amount': op.amount,
                                         }])
            values['lines_account'] = lines_account
            values['invoice_id'] = invoice.id
            values['concept'] = 'Pago de factura No. %s' % invoice.number
        # OC
        if op.type == 'oc':
            oc = op.purchase_order_id
            values['purchase_order_id'] = oc.id
            values['concept'] = 'Orden de compra %s' % oc.name
        # ADQ
        if op.type == 'adq':
            adq = op.advance_payment_id
            # Líneas de cuentas
            lines_account = []
            lines_account.append([0, 0, {'account_id': adq.account_id.id,
                                         'amount': op.amount,
                                         }])
            values['lines_account'] = lines_account
            values['concept'] = 'ADQ del mes de %s' % adq.period
        # RC
        if op.type == 'rc':
            rc = op.payslip_run_id
            account = self.env['account.account'].search([('name', '=', 'NÓMINA POR PAGAR')], limit=1)
            # Líneas de cuentas
            lines_account = []
            lines_account.append([0, 0, {'account_id': account.id,
                                         'amount': op.amount,
                                         }])
            values['lines_account'] = lines_account
            values['concept'] = 'Nómina de empleados %s' % rc.name
        # Caja chica
        if op.type == 'cajc':
            cjc = op.replacement_small_box_id.custodian_id
            values['custodian_id'] = cjc.id
            values['concept'] = 'Reposición de caja %s' % op.replacement_small_box_id.name
        # RP
        if op.type == 'rp':
            rp = op.payment_request_id
            values['payment_request_id'] = rp.id
            values['concept'] = rp.comments or '/'
        voucher_invoice = self.create(values)
        voucher_invoice._onchange_pay_order_id()  # Cambiamos
        return voucher_invoice


class PayOrder(models.Model):
    _name = 'eliterp.pay.order'

    _description = 'Orden de pago'

    @api.multi
    def pay(self):
        """
        Creamos pago
        """
        new_voucher = self.env['account.voucher'].with_context({'voucher_type': 'purchase'})._voucher(self)
        action = self.env.ref('eliterp_treasury.eliterp_action_voucher_purchase')
        result = action.read()[0]
        res = self.env.ref('eliterp_treasury.eliterp_view_form_voucher_purchase', False)
        result['views'] = [(res and res.id or False, 'form')]
        result['res_id'] = new_voucher.id
        return result

    def _default_currency(self):
        """
        Moneda
        """
        return self.env['res.currency'].search([('name', '=', 'USD')])[0].id

    name = fields.Char('No. Documento')
    origin = fields.Char('Origen', required=True)
    amount = fields.Float('Monto total', required=True)
    date = fields.Date('Fecha', required=True)
    # Dependiendo del origen
    type = fields.Selection([
        ('fap', 'Factura de proveedor'),
        ('oc', 'Orden de compra'),
        ('adq', 'Anticipo de quincena'),
        ('rc', 'Rol consolidado'),
        ('cajc', 'Caja chica'),
        ('rp', 'Requerimiento de pago'),
        ('svi', 'Solicitud de viático'),
    ], string="Tipo de origen", required=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('paid', 'Pagada'),
    ], default='draft', string="Estado", readonly=True, copy=False)
    currency_id = fields.Many2one('res.currency', string='Moneda', default=_default_currency)
    # Campos para traer los diferentes documentos para la OP
    # Factura
    invoice_id = fields.Many2one('account.invoice', 'Factura')
    # OC
    purchase_order_id = fields.Many2one('purchase.order', 'Orden de compra')
    # ADQ
    advance_payment_id = fields.Many2one('eliterp.advance.payment', 'ADQ')
    # RC
    payslip_run_id = fields.Many2one('hr.payslip.run', 'Rol consolidado')
    # Reposición caja chica
    replacement_small_box_id = fields.Many2one('eliterp.replacement.small.box', 'Reposición caja chica')
    # Requerimiento de pago
    payment_request_id = fields.Many2one('eliterp.payment.request', "Requerimiento de pago")
    # TODO: Viático
    viaticum_id = fields.Many2one('eliterp.travel.allowance.request', "Solicitud viático")


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_advanced = fields.Boolean('Es anticipo?', default=False, copy=False)  # Campo para anticipo de proveedores


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.one
    def _get_outstanding_info_JSON(self):
        self.outstanding_credits_debits_widget = json.dumps(False)
        if self.state == 'open':
            domain = [('account_id', '=', self.account_id.id),
                      ('partner_id', '=', self.env['res.partner']._find_accounting_partner(self.partner_id).id),
                      ('reconciled', '=', False), '|', ('amount_residual', '!=', 0.0),
                      ]
            if self.type in ('out_invoice', 'in_refund'):
                domain.extend([('amount_residual_currency', '!=', 0.0), ('credit', '>', 0), ('debit', '=', 0)])
                type_payment = _('Outstanding credits')
            else:
                domain.extend(
                    [('credit', '=', 0), ('debit', '>', 0), ('is_advanced', '=', True)])  # Anticipo de proveedor
                type_payment = 'Anticipos'
            info = {'title': '', 'outstanding': True, 'content': [], 'invoice_id': self.id}
            lines = self.env['account.move.line'].search(domain)
            currency_id = self.currency_id
            if len(lines) != 0:
                for line in lines:
                    # get the outstanding residual value in invoice currency
                    if line.currency_id and line.currency_id == self.currency_id:
                        amount_to_show = abs(line.amount_residual_currency)
                    else:
                        amount_to_show = line.company_id.currency_id.with_context(date=line.date).compute(
                            abs(line.amount_residual), self.currency_id)
                    if float_is_zero(amount_to_show, precision_rounding=self.currency_id.rounding):
                        continue
                    info['content'].append({
                        'journal_name': line.ref or line.move_id.name,
                        'amount': amount_to_show,
                        'currency': currency_id.symbol,
                        'id': line.id,
                        'position': currency_id.position,
                        'digits': [69, self.currency_id.decimal_places],
                    })
                info['title'] = type_payment
                self.outstanding_credits_debits_widget = json.dumps(info)
                self.has_outstanding = True

    @api.multi
    def generate_request(self):
        """
        Abrimos ventana para añadir pago
        :return: dict
        """
        self.flag_change = True
        view = self.env.ref('eliterp_treasury.eliterp_view_form_pay_wizard')
        context = {
            'default_default_date': self.date_invoice,
            'default_type': 'fap',
            'default_default_amount': self.residual_pay_order,
            'default_amount': self.residual_pay_order
        }
        return {
            'name': "Crear orden de pago",
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'eliterp.pay.wizard',
            'view_id': view.id,
            'target': 'new',
            'context': context,
        }

    @api.one
    @api.depends('flag_change')
    def _get_customize_amount(self):
        """
        Obtenemos estado de ADQ pra OP
        """
        pays = self.lines_pay_order
        if not pays:
            self.state_pay_order = 'generated'
            self.residual_pay_order = self.residual
        else:
            total = 0.00
            for pay in pays:  # Soló contabilizadas
                total += round(pay.amount, 2)
            self.improved_pay_order = total
            self.residual_pay_order = round(self.residual - self.improved_pay_order, 2)
            if float_is_zero(self.residual_pay_order, precision_rounding=0.01) or self.reconciled:
                self.state_pay_order = 'paid'
            else:
                self.state_pay_order = 'partial_payment'

    state_pay_order = fields.Selection([
        ('generated', 'Sin abonos'),
        ('partial_payment', 'Abono parcial'),
        ('paid', 'Pagada'),
    ], default='generated', string="Estado de pago", compute='_get_customize_amount', readonly=True, copy=False)
    improved_pay_order = fields.Float('Abonado OP', compute='_get_customize_amount', store=True)
    residual_pay_order = fields.Float('Saldo OP', compute='_get_customize_amount', store=True)
    lines_pay_order = fields.One2many('eliterp.pay.order', 'invoice_id', string='Órdenes de pago')
    flag_change = fields.Boolean('Bandera de cambio?')


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.multi
    def generate_request(self):
        """
        Abrimos ventana para añadir pago
        :return: dict
        """
        self.flag_change = True
        view = self.env.ref('eliterp_treasury.eliterp_view_form_pay_wizard')
        context = {
            'default_default_date': self.date_order,
            'default_type': 'oc',
            'default_default_amount': self.residual_pay_order,
            'default_amount': self.residual_pay_order
        }
        return {
            'name': "Crear orden de pago",
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'eliterp.pay.wizard',
            'view_id': view.id,
            'target': 'new',
            'context': context,
        }

    @api.one
    @api.depends('flag_change')
    def _get_customize_amount(self):
        """
        Obtenemos estado de ADQ pra OP
        """
        pays = self.lines_pay_order
        total_invoices = 0.00
        for inv in self.invoice_ids:  # Facturas ingresadas
            if inv and inv.state not in ('cancel', 'draft'):
                total_invoices += inv.residual
        _total = round(self.amount_total - total_invoices, 2)
        if self.invoice_status == 'invoiced':
            self.state_pay_order = 'paid'
        else:
            if not pays:
                self.state_pay_order = 'generated'
                self.residual_pay_order = _total
            else:
                total = 0.00
                for pay in pays:  # Soló contabilizadas
                    total += round(pay.amount, 2)
                self.improved_pay_order = total
                self.residual_pay_order = round(_total - self.improved_pay_order, 2)
                if float_is_zero(self.residual_pay_order, precision_rounding=0.01) or self.invoice_status == 'invoiced':
                    self.state_pay_order = 'paid'
                else:
                    self.state_pay_order = 'partial_payment'

    state_pay_order = fields.Selection([
        ('generated', 'Sin abonos'),
        ('partial_payment', 'Abono parcial'),
        ('paid', 'Pagada'),
    ], default='generated', string="Estado de pago", compute='_get_customize_amount', readonly=True, copy=False)
    improved_pay_order = fields.Float('Abonado OP', compute='_get_customize_amount', store=True)
    residual_pay_order = fields.Float('Saldo OP', compute='_get_customize_amount', store=True)
    lines_pay_order = fields.One2many('eliterp.pay.order', 'purchase_order_id', string='Órdenes de pago')
    flag_change = fields.Boolean('Bandera de cambio?')


class AdvancePayment(models.Model):
    _inherit = 'eliterp.advance.payment'

    @api.multi
    def generate_request(self):
        """
        Abrimos ventana para añadir pago
        :return: dict
        """
        self.flag_change = True
        view = self.env.ref('eliterp_treasury.eliterp_view_form_pay_wizard')
        context = {
            'default_default_date': self.date,
            'default_type': 'adq',
            'default_default_amount': self.residual_pay_order,
            'default_amount': self.residual_pay_order
        }
        return {
            'name': "Crear orden de pago",
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'eliterp.pay.wizard',
            'view_id': view.id,
            'target': 'new',
            'context': context,
        }

    @api.one
    @api.depends('flag_change')
    def _get_customize_amount(self):
        """
        Obtenemos estado de ADQ pra OP
        """
        pays = self.lines_pay_order
        if not pays:
            self.state_pay_order = 'generated'
            self.residual_pay_order = self.total
        else:
            total = 0.00
            for pay in pays:  # Soló contabilizadas
                total += round(pay.amount, 2)
            self.improved_pay_order = total
            self.residual_pay_order = round(self.total - self.improved_pay_order, 2)
            if float_is_zero(self.residual_pay_order, precision_rounding=0.01):
                self.state_pay_order = 'paid'
            else:
                self.state_pay_order = 'partial_payment'

    state_pay_order = fields.Selection([
        ('generated', 'Sin abonos'),
        ('partial_payment', 'Abono parcial'),
        ('paid', 'Pagada'),
    ], default='generated', string="Estado de pago", compute='_get_customize_amount', readonly=True, copy=False)
    improved_pay_order = fields.Float('Abonado OP', compute='_get_customize_amount', store=True)
    residual_pay_order = fields.Float('Saldo OP', compute='_get_customize_amount', store=True)
    lines_pay_order = fields.One2many('eliterp.pay.order', 'advance_payment_id', string='Órdenes de pago')
    flag_change = fields.Boolean('Bandera de cambio?')


class PayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    @api.multi
    def generate_request(self):
        """
        Abrimos ventana para añadir pago
        :return: dict
        """
        self.flag_change = True
        view = self.env.ref('eliterp_treasury.eliterp_view_form_pay_wizard')
        context = {
            'default_default_date': self.date_to,
            'default_type': 'rc',
            'default_default_amount': self.residual_pay_order,
            'default_amount': self.residual_pay_order
        }
        return {
            'name': "Crear orden de pago",
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'eliterp.pay.wizard',
            'view_id': view.id,
            'target': 'new',
            'context': context,
        }

    @api.one
    @api.depends('flag_change')
    def _get_customize_amount(self):
        """
        Obtenemos estado de ADQ pra OP
        """
        pays = self.lines_pay_order
        if not pays:
            self.state_pay_order = 'generated'
            self.residual_pay_order = self.total
        else:
            total = 0.00
            for pay in pays:  # Soló contabilizadas
                total += round(pay.amount, 2)
            self.improved_pay_order = total
            self.residual_pay_order = round(self.total - self.improved_pay_order, 2)
            if float_is_zero(self.residual_pay_order, precision_rounding=0.01):
                self.state_pay_order = 'paid'
            else:
                self.state_pay_order = 'partial_payment'

    state_pay_order = fields.Selection([
        ('generated', 'Sin abonos'),
        ('partial_payment', 'Abono parcial'),
        ('paid', 'Pagada'),
    ], default='generated', string="Estado de pago", compute='_get_customize_amount', readonly=True, copy=False)
    improved_pay_order = fields.Float('Abonado OP', compute='_get_customize_amount', store=True)
    residual_pay_order = fields.Float('Saldo OP', compute='_get_customize_amount', store=True)
    lines_pay_order = fields.One2many('eliterp.pay.order', 'payslip_run_id', string='Órdenes de pago')
    flag_change = fields.Boolean('Bandera de cambio?')


class ReplacementSmallBox(models.Model):
    _inherit = 'eliterp.replacement.small.box'

    @api.multi
    def generate_request(self):
        """
        Abrimos ventana para añadir pago
        :return: dict
        """
        self.flag_change = True
        view = self.env.ref('eliterp_treasury.eliterp_view_form_pay_wizard')
        context = {
            'default_default_date': self.opening_date,
            'default_type': 'cajc',
            'default_default_amount': self.residual_pay_order,
            'default_amount': self.residual_pay_order
        }
        return {
            'name': "Crear orden de pago",
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'eliterp.pay.wizard',
            'view_id': view.id,
            'target': 'new',
            'context': context,
        }

    @api.one
    @api.depends('flag_change')
    def _get_customize_amount(self):
        """
        Obtenemos estado de ADQ pra OP
        """
        pays = self.lines_pay_order
        if not pays:
            self.state_pay_order = 'generated'
            self.residual_pay_order = self.total_vouchers
        else:
            total = 0.00
            for pay in pays:  # Soló contabilizadas
                total += round(pay.amount, 2)
            self.improved_pay_order = total
            self.residual_pay_order = round(self.total_vouchers - self.improved_pay_order, 2)
            if float_is_zero(self.residual_pay_order, precision_rounding=0.01):
                self.state_pay_order = 'paid'
            else:
                self.state_pay_order = 'partial_payment'

    state_pay_order = fields.Selection([
        ('generated', 'Sin abonos'),
        ('partial_payment', 'Abono parcial'),
        ('paid', 'Pagada'),
    ], default='generated', string="Estado de pago", compute='_get_customize_amount', readonly=True, copy=False)
    improved_pay_order = fields.Float('Abonado OP', compute='_get_customize_amount', store=True)
    residual_pay_order = fields.Float('Saldo OP', compute='_get_customize_amount', store=True)
    lines_pay_order = fields.One2many('eliterp.pay.order', 'replacement_small_box_id', string='Órdenes de pago')
    flag_change = fields.Boolean('Bandera de cambio?')


class PaymentRequest(models.Model):
    _inherit = 'eliterp.payment.request'

    @api.multi
    def generate_request(self):
        """
        Abrimos ventana para añadir pago
        :return: dict
        """
        self.flag_change = True
        view = self.env.ref('eliterp_treasury.eliterp_view_form_pay_wizard')
        context = {
            'default_default_date': self.application_date,
            'default_type': 'rp',
            'default_default_amount': self.residual_pay_order,
            'default_amount': self.residual_pay_order
        }
        return {
            'name': "Crear orden de pago",
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'eliterp.pay.wizard',
            'view_id': view.id,
            'target': 'new',
            'context': context,
        }

    @api.one
    @api.depends('flag_change')
    def _get_customize_amount(self):
        """
        Obtenemos estado de ADQ pra OP
        """
        pays = self.lines_pay_order
        if not pays:
            self.state_pay_order = 'generated'
            self.residual_pay_order = self.total
        else:
            total = 0.00
            for pay in pays:  # Soló contabilizadas
                total += round(pay.amount, 2)
            self.improved_pay_order = total
            self.residual_pay_order = round(self.total - self.improved_pay_order, 2)
            if float_is_zero(self.residual_pay_order, precision_rounding=0.01):
                self.state_pay_order = 'paid'
            else:
                self.state_pay_order = 'partial_payment'

    state_pay_order = fields.Selection([
        ('generated', 'Sin abonos'),
        ('partial_payment', 'Abono parcial'),
        ('paid', 'Pagada'),
    ], default='generated', string="Estado de pago", compute='_get_customize_amount', readonly=True, copy=False)
    improved_pay_order = fields.Float('Abonado OP', compute='_get_customize_amount', store=True)
    residual_pay_order = fields.Float('Saldo OP', compute='_get_customize_amount', store=True)
    lines_pay_order = fields.One2many('eliterp.pay.order', 'payment_request_id', string='Órdenes de pago')
    flag_change = fields.Boolean('Bandera de cambio?')
