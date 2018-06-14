# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).


from datetime import datetime
from odoo import api, fields, models


class AccountsReceivableReportPDF(models.AbstractModel):
    _name = 'report.eliterp_treasury.eliterp_report_accounts_receivable'

    def _get_lines(self, doc):
        """
        Obtenemos líneas de reporte
        :param doc:
        :return: list
        """
        data = []
        arg = []
        if doc['customer_type'] != 'todos':
            if isinstance(doc['partner'], int):
                arg.append(('partner_id', '=', doc['partner']))
            else:
                arg.append(('partner_id', '=', doc['partner'].id))
        if doc['estado'] != 'todos':
            arg.append(('date_due', '<=', fields.date.today()))
        arg.append(('date_invoice', '>=', doc['start_date']))
        arg.append(('date_invoice', '<=', doc['end_date']))
        arg.append(('state', '=', 'open'))  # MARZ, Soló pendientes de cobro
        arg.append(('type', '=', 'out_invoice'))
        facturas = self.env['account.invoice'].search(arg)
        count = 0
        for factura in facturas:
            count += 1
            expiration_date = datetime.strptime(factura.date_due, "%Y-%m-%d").date()
            delinquency = 0
            days_expire = 0
            defeated = False
            overcome = False
            if factura.residual != 0.00:
                if fields.date.today() > expiration_date:
                    delinquency = (fields.date.today() - expiration_date).days
                    defeated = True
            if factura.residual != 0.00:
                if expiration_date < fields.date.today():
                    overcome = True
                    days_expire = (expiration_date - fields.date.today()).days
            amount = factura.amount_total_signed
            data.append({
                'partner': factura.partner_id.name,
                'number': factura.invoice_number,
                'amount': amount,
                'outstanding_balance': factura.residual,
                'expedition_date': factura.date_invoice,
                'expiration_date': factura.date_due,
                'delinquency': delinquency,
            })
            if doc['report_type'] == 'completo':
                data[-1].update(
                    {'overcome_30': amount if overcome == True and (days_expire >= 1 and days_expire <= 30) else float(
                        0.00),
                     'overcome_90': amount if overcome == True and (days_expire >= 31 and days_expire <= 90) else 0.00,
                     'overcome_180': amount if overcome == True and (
                                 days_expire >= 91 and days_expire <= 180) else 0.00,
                     'overcome_360': amount if overcome == True and (
                                 days_expire >= 181 and days_expire <= 360) else 0.00,
                     'overcome_mayor': amount if overcome == True and (days_expire > 360) else 0.00,
                     'defeated_30': amount if defeated == True and (delinquency >= 1 and delinquency <= 30) else 0.00,
                     'defeated_90': amount if defeated == True and (delinquency >= 31 and delinquency <= 90) else 0.00,
                     'defeated_180': amount if defeated == True and (
                                 delinquency >= 91 and delinquency <= 180) else 0.00,
                     'defeated_360': amount if defeated == True and (
                                 delinquency >= 181 and delinquency <= 360) else 0.00,
                     'defeated_mayor': amount if defeated == True and (delinquency > 360) else 0.00, })
        return data

    @api.model
    def get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'doc_model': 'eliterp.accounts.receivable.report',
            'docs': self.env['eliterp.accounts.receivable.report'].browse(docids),
            'get_lines': self._get_lines,
            'data': data,
        }


class AccountsReceivableReport(models.TransientModel):
    _name = 'eliterp.accounts.receivable.report'

    _description = "Ventana para reporte de cuentas por cobrar"

    @api.multi
    def print_report_pdf(self):
        """
        Imprimimos reporte en pdf
        """
        self.ensure_one()
        return self.env.ref('eliterp_treasury.eliterp_action_report_accounts_receivable_report').report_action(self)

    start_date = fields.Date('Fecha inicio', required=True)
    end_date = fields.Date('Fecha fin', required=True, default=fields.Date.context_today)
    report_type = fields.Selection([('completo', 'Completo'), ('resumido', 'Resumido')], default='completo')
    estado = fields.Selection([('todas', 'Todas'), ('vencidas', 'Vencidas')], default='todas')
    delinquency = fields.Integer('Morosidad')
    customer_type = fields.Selection([('todos', 'Todos'), ('partner', 'Individual')], 'Tipo de Cliente',
                                     default='todos')
    partner = fields.Many2one('res.partner', 'Cliente')


class AccountsToPayReportPDF(models.AbstractModel):
    _name = 'report.eliterp_treasury.eliterp_report_accounts_to_pay'

    def _get_lines(self, doc):
        data = []
        arg = []
        if doc['provider_type'] != 'todos':
            if isinstance(doc['provider'], int):
                arg.append(('partner_id', '=', doc['provider']))
            else:
                arg.append(('partner_id', '=', doc['provider'].id))
        if doc['estado'] != 'todos':
            arg.append(('date_due', '<=', fields.date.today()))
        arg.append(('date_invoice', '>=', doc['start_date']))
        arg.append(('date_invoice', '<=', doc['end_date']))
        arg.append(('state', 'in', ('open', 'paid')))
        arg.append(('type', '=', 'in_invoice'))
        facturas = self.env['account.invoice'].search(arg)
        count = 0
        for factura in facturas:
            if factura.residual == 0.00:
                continue
            count += 1
            expiration_date = datetime.strptime(factura.date_due, "%Y-%m-%d").date()
            nota_credito = self.env['account.invoice'].search([('invoice_number', '=', factura.id)])
            delinquency = 0
            days_expire = 0
            defeated = False
            overcome = False
            if factura.residual != 0.00:
                if fields.date.today() > expiration_date:
                    delinquency = (fields.date.today() - expiration_date).days
                    defeated = True
            if factura.residual != 0.00:
                if expiration_date < fields.date.today():
                    overcome = True
                    days_expire = (expiration_date - fields.date.today()).days
            amount = factura.amount_total
            saldo_p = factura.residual  # MARZ
            if expiration_date > fields.date.today():
                delinquency = fields.date.today() - expiration_date
            data.append({
                'provider': factura.partner_id.name,
                'number': factura.invoice_number,
                'subtotal': factura.amount_untaxed,
                'iva': factura.amount_tax,
                'amount': amount,
                'credit_note_number': nota_credito.numero_factura_interno if len(nota_credito) > 0 else "-",
                'amount_note_number': nota_credito.amount_untaxed if len(nota_credito) > 0 else 0.00,
                'outstanding_balance': factura.residual,
                'broadcast_date': factura.date_invoice,
                'expiration_date': factura.date_due,
                'delinquency': delinquency,
            })
            if doc['report_type'] == 'completo':
                data[-1].update(
                    {
                        'overcome_30': saldo_p if overcome and (days_expire >= 1 and days_expire <= 30) else float(
                            0.00),
                        'overcome_90': saldo_p if overcome and (days_expire >= 31 and days_expire <= 90) else 0.00,
                        'overcome_180': saldo_p if overcome and (days_expire >= 91 and days_expire <= 180) else 0.00,
                        'overcome_360': saldo_p if overcome and (days_expire >= 181 and days_expire <= 360) else 0.00,
                        'overcome_mayor': saldo_p if overcome and (days_expire > 360) else 0.00,
                        'defeated_30': saldo_p if defeated and (delinquency >= 1 and delinquency <= 30) else 0.00,
                        'defeated_90': saldo_p if defeated and (delinquency >= 31 and delinquency <= 90) else 0.00,
                        'defeated_180': saldo_p if defeated and (delinquency >= 91 and delinquency <= 180) else 0.00,
                        'defeated_360': saldo_p if defeated and (delinquency >= 181 and delinquency <= 360) else 0.00,
                        'defeated_mayor': saldo_p if defeated and (delinquency > 360) else 0.00,
                    })
        return data

    @api.model
    def get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'doc_model': 'eliterp.accounts.to.pay.report',
            'docs': self.env['eliterp.accounts.to.pay.report'].browse(docids),
            'get_lines': self._get_lines,
            'data': data,
        }


class AccountsToPayReport(models.TransientModel):
    _name = 'eliterp.accounts.to.pay.report'

    _description = "Ventana para reporte de cuentas por pagar"

    @api.multi
    def print_report_pdf(self):
        """
        Imprimimos reporte en pdf
        """
        self.ensure_one()
        return self.env.ref('eliterp_treasury.eliterp_action_report_accounts_to_pay').report_action(self)

    start_date = fields.Date('Fecha inicio', required=True)
    end_date = fields.Date('Fecha fin', required=True, default=fields.Date.context_today)
    report_type = fields.Selection([('completo', 'Completo'), ('resumido', 'Resumido')], default='completo')
    estado = fields.Selection([('todas', 'Todas'), ('vencidas', 'Vencidas')], default='todas')
    delinquency = fields.Integer('Morosidad')
    provider_type = fields.Selection([('todos', 'Todos'), ('provider', 'Individual')], 'Tipo de Proveedor',
                                     default='todos')
    provider = fields.Many2one('res.partner', 'Proveedor')


class ChecksReceivedReportPDF(models.AbstractModel):
    _name = 'report.eliterp_treasury.eliterp_report_checks_received_report'

    def get_facturas(self, facturas):
        bill_number = ""
        count = 0
        for f in facturas:
            if count == 0:
                bill_number = bill_number + f.name[-5:]
                count = count + 1
            else:
                bill_number = bill_number + "-" + f.name[-5:]
        return bill_number

    def _get_lines(self, doc):
        data = []
        arg = []
        if doc['customer_type'] != 'todos':
            if isinstance(doc['partner'], int):
                arg.append(('partner_id', '=', doc['partner']))
            else:
                arg.append(('partner_id', '=', doc['partner'].id))
        arg.append(('voucher_type', '=', 'sale'))
        vouchers = self.env['account.voucher'].search(arg)
        for voucher in vouchers:
            facturas = self.get_facturas(voucher.lines_invoice_sales)
            for line in voucher.lines_payment:
                if (line.type_payment == 'bank'):
                    if line.check_type == 'current':
                        datev = voucher.date
                    else:
                        datev = line.create_date
                    if (datev >= doc['start_date'] and datev <= doc['end_date']):
                        data.append({
                            'date_received': voucher.date,
                            'document_date': voucher.date if line.check_type == 'corriente' else line.create_date,
                            'credit_date': voucher.date if line.check_type == 'corriente' else line.date_due,
                            'partner': voucher.partner_id.name,
                            'facturas': facturas,
                            'issuing_bank': line.bank_id.name,
                            'number_check': line.check_number,
                            'amount': line.amount,
                        })
        return data

    @api.model
    def get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'doc_model': 'eliterp.checks.received.report',
            'docs': self.env['eliterp.checks.received.report'].browse(docids),
            'get_lines': self._get_lines,
            'data': data,
        }


class ChecksReceivedReport(models.TransientModel):
    _name = 'eliterp.checks.received.report'

    _description = "Ventana para reporte de cheques recibidos"

    @api.multi
    def print_report_pdf(self):
        """
        Imprimimos reporte en pdf
        """
        self.ensure_one()
        return self.env.ref('eliterp_treasury.eliterp_action_report_checks_received_report').report_action(self)

    start_date = fields.Date('Fecha inicio', required=True)
    end_date = fields.Date('Fecha fin', required=True, default=fields.Date.context_today)
    customer_type = fields.Selection([('todos', 'Todos'), ('partner', 'Individual')], 'Tipo de Cliente',
                                     default='todos')
    partner = fields.Many2one('res.partner', 'Cliente')
    bank_type = fields.Selection([('todos', 'Todos'), ('bank', 'Individual')], 'Tipo de Asesor', default='todos')
    bank = fields.Many2one('res.bank', 'Banco')


class ChecksIssuedReportPDF(models.AbstractModel):
    _name = 'report.eliterp_treasury.eliterp_report_checks_issued_report'

    def get_state(self, state):
        if state == 'draft':
            return "Borrador"
        if state == 'posted':
            return "Publicado"

    def _get_lines(self, doc):
        data = []
        arg = []
        if doc['type_check'] == 'varios':
            arg.append(('beneficiario_proveedor', '=', 'beneficiario'))
        if doc['type_check'] == 'provider':
            arg.append(('beneficiario_proveedor', '=', 'supplier'))
        if doc['type_check'] == 'caja_chica':
            arg.append(('beneficiario_proveedor', '=', 'caja_chica'))
        # MARZ
        if doc['type_check'] == 'solicitud_pago':
            arg.append(('beneficiario_proveedor', '=', 'caja_chica'))
        if doc['type_check'] == 'caja_chica':
            arg.append(('beneficiario_proveedor', '=', 'caja_chica'))
        arg.append(('voucher_type', '=', 'purchase'))
        arg.append(('check_date', '>=', doc['start_date']))
        arg.append(('check_date', '<=', doc['end_date']))
        vouchers = self.env['account.voucher'].search(arg)
        for voucher in vouchers:
            data.append({
                'number_check': voucher.check_number,
                'bank': voucher.bank_id.name,
                'broadcast_date': voucher.date,
                'pay_day': voucher.check_date,
                'beneficiary': voucher.beneficiary,
                'concept': voucher.concept,
                'amount': voucher.amount_cancel,
                'state': self.get_state(voucher.state),
            })

        return data

    @api.model
    def get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'doc_model': 'eliterp.checks.issued.report',
            'docs': self.env['eliterp.checks.issued.report'].browse(docids),
            'get_lines': self._get_lines,
            'data': data,
        }


class ChecksIssuedReport(models.TransientModel):
    _name = 'eliterp.checks.issued.report'

    _description = "Ventana para reporte de cheques emitidos"

    @api.multi
    def print_report_pdf(self):
        """
        Imprimimos reporte en pdf
        """
        self.ensure_one()
        return self.env.ref('eliterp_treasury.eliterp_action_report_checks_issued_report').report_action(self)

    start_date = fields.Date('Fecha inicio', required=True)
    end_date = fields.Date('Fecha fin', required=True, default=fields.Date.context_today)
    type_check = fields.Selection([('todos', 'Todos'),
                                   ('varios', 'Varios'),
                                   ('provider', 'Proveedor'),
                                   ('caja_chica', 'Caja Chica'),
                                   ('solicitud_pago', 'Solicitud de Pago'),
                                   ('viaticos', 'Solicitud de Viáticos')], 'Tipo de Cheque', default='todos')
    bank_type = fields.Selection([('todos', 'Todos'), ('bank', 'Individual')], 'Tipo de Asesor', default='todos')
    bank = fields.Many2one('res.bank', 'Banco')


class ScheduledPaymentsReportPDF(models.AbstractModel):
    _name = 'report.eliterp_treasury.eliterp_report_scheduled_payments'

    def get_days_mora(self, vencimiento):
        delinquency = 0
        delinquency = (fields.date.today() - vencimiento).days
        return str(delinquency)

    def _get_lines(self, doc):
        data = []
        arg = []
        if doc['form_pay'] != 'todas':
            arg.append(('way_to_pay', '=', doc['form_pay']))
        pays = self.env['eliterp.programmed.payment'].search(arg)
        for pay in pays:
            pay_day = pay.date
            if (pay_day >= doc['start_date'] and pay_day <= doc['end_date']):
                expiration_date = datetime.strptime(pay.invoice_id.date_due, "%Y-%m-%d").date()
                partner = self.env['res.partner'].browse(pay.invoice_id.partner_id['id'])
                if pay.invoice_id.state == 'open':  # Soló facturas por pagar
                    data.append({
                        'provider': partner.name,
                        'number_factura': pay.invoice_id.invoice_number,
                        'subtotal': pay.invoice_id.amount_untaxed,
                        'iva': pay.invoice_id.amount_tax,
                        'amount': pay.invoice_id.amount_total,
                        'outstanding_balance': pay.invoice_id.residual,
                        'expiration_date': pay.invoice_id.date_due,
                        'delinquency': "SIN MORA" if pay.invoice_id.residual == 0.00 else self.get_days_mora(
                            expiration_date),
                        'payment_value': pay.amount,
                        'form_pay': "EFECTIVO" if not pay.bank_id else self.env['res.bank'].browse(
                            pay.bank_id.id).name,
                        'pay_day': pay.date,
                    })
        return data

    @api.model
    def get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'doc_model': 'eliterp.scheduled.payments.report',
            'docs': self.env['eliterp.scheduled.payments.report'].browse(docids),
            'get_lines': self._get_lines,
            'data': data,
        }


class ScheduledPaymentsReport(models.TransientModel):
    _name = 'eliterp.scheduled.payments.report'

    _description = "Ventana para reporte de pagos programados"

    @api.multi
    def print_report_pdf(self):
        """
        Imprimimos reporte en pdf
        """
        self.ensure_one()
        return self.env.ref('eliterp_treasury.eliterp_action_report_scheduled_payments_report').report_action(self)

    start_date = fields.Date('Fecha inicio', required=True)
    end_date = fields.Date('Fecha fin', required=True, default=fields.Date.context_today)
    form_pay = fields.Selection([('todas', 'Todas'), ('efectivo', 'Efectivo'), ('cheque', 'Cheque')], 'Forma de Pago',
                                  default='todas')
