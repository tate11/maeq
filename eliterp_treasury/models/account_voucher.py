# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).


from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


# TODO: Para que sirve
class BalanceVoucherPayment(models.Model):
    _name = 'eliterp.balance.voucher.payment'
    _description = 'Saldo en cobro'

    def confirm_balance(self):
        voucher = self.env['account.voucher'].browse(self._context['active_id'])
        voucher.write({
            'balance_account': self.balance_account.id,
            'balance': self.balance,
            'show_account': True,
            'flag': True
        })
        voucher.validate_voucher()
        return True

    balance = fields.Float('Saldo')
    balance_account = fields.Many2one('account.account', string='Cuenta saldo',
                                      domain=[('account_type', '=', 'movement')])


class LinesPayment(models.Model):
    _name = "eliterp.lines.payment"

    _description = 'Líneas de cobro'

    @api.constrains('amount')
    def _check_amount(self):
        """
        Validamos monto
        """
        if self.amount <= 0:
            raise ValidationError("Monto no puede ser menor o igual a 0.")

    @api.one
    @api.constrains('date_issue')
    def _check_date(self):
        """
        Verificamos la fechas
        """
        if self.date_due < self.date_issue:
            raise ValidationError('La fecha de vencimiento no puede ser menor a la de emisión.')

    @api.onchange('drawer')
    def _onchange_drawer(self):
        self.is_beneficiary = True

    type_payment = fields.Selection([
        ('bank', 'Cheque'),
        ('cash', 'Efectivo'),
        ('transfer', 'Transferencia')
    ], string='Tipo de cobro')
    drawer = fields.Char('Girador')
    account_number = fields.Char('No. Cuenta')
    check_number = fields.Char('No. Cheque')
    bank_id = fields.Many2one('res.bank', 'Banco')
    account_id = fields.Many2one('account.account', string='Cuenta', domain=[('account_type', '=', 'movement')])
    amount = fields.Float('Monto')
    voucher_id = fields.Many2one('account.voucher', 'Cobro')
    check_type = fields.Selection([('current', 'Corriente'), ('to_date', 'A la fecha')], string='Tipo de cheque')
    date_issue = fields.Date('Fecha de emisión', default=fields.Date.context_today)
    date_due = fields.Date('Fecha vencimiento', default=fields.Date.context_today)
    is_beneficiary = fields.Boolean('Es beneficiario?', default=False)
    move_id = fields.Many2one('account.move', string='Asiento contable')


class LinesCreditNotes(models.Model):
    _name = 'eliterp.lines.credit.notes'

    _description = 'Lineas de nota de crédito'

    invoice_id = fields.Many2one('account.invoice', string='Nota de crédito')
    name = fields.Char('No. Factura', related="invoice_id.invoice_number")
    journal_id = fields.Many2one('account.journal', string='Diario',
                                 domain=[('type', 'in', ('bank', 'cash'))])
    date_due_invoice = fields.Date('Fecha vencimiento')
    amount_note = fields.Float('Total de nota')
    apply = fields.Boolean('Aplicar?', default=False)
    invoices_affect = fields.Many2one('eliterp.lines.invoice', string='Facturas a aplicar')
    voucher_id = fields.Many2one('account.voucher', 'Comprobante')


class LinesInvoice(models.Model):
    _name = 'eliterp.lines.invoice'

    _description = 'Líneas de Factura'

    invoice_id = fields.Many2one('account.invoice', 'Factura')
    name = fields.Char('No. Factura', related="invoice_id.invoice_number")
    journal_id = fields.Many2one('account.journal', string="Diario",
                                 domain=[('type', 'in', ('bank', 'cash'))])
    date_due_invoice = fields.Date('Fecha vencimiento')
    amount_invoice = fields.Float('Total de factura')
    amount_payable = fields.Float('Monto a cobrar/pagar')
    amount_total = fields.Float('Total adeudado')
    amount_programmed = fields.Float('Total programado')
    voucher_id = fields.Many2one('account.voucher', 'Comprobante')


class LinesAccount(models.Model):
    _name = 'eliterp.lines.account'

    _description = 'Líneas de cuenta'

    account_id = fields.Many2one('account.account', string="Cuenta", domain=[('account_type', '=', 'movement')])
    amount = fields.Float('Monto')
    voucher_id = fields.Many2one('account.voucher', string='Comprobante')


class VoucherCancelReason(models.Model):
    _name = 'eliterp.voucher.cancel.reason'

    _description = 'Razón para cancelar recibo'

    description = fields.Text('Descripción', required=True)

    @api.multi
    def cancel_voucher(self):
        """
        Cancelamos el voucher
        """
        voucher = self.env['account.voucher'].browse(self._context['active_id'])
        move_id = voucher.move_id
        for line in move_id.line_ids:
            if line.full_reconcile_id:
                line.remove_move_reconcile()
        move_id.with_context(from_voucher=True, voucher_id=voucher.id).reverse_moves(voucher.check_date,
                                                                                     voucher.journal_id or False)
        move_id.write({'state': 'cancel', 'ref': self.description})
        voucher.write({'state': 'cancel', 'reason_cancel': self.description})
        return


class AccountVoucher(models.Model):
    _inherit = "account.voucher"

    @api.multi
    def print_voucher(self):
        """
        Imprimimos comprobante
        """
        self.ensure_one()
        if self.voucher_type == 'purchase':
            return self.env.ref('eliterp_treasury.eliterp_action_report_account_voucher_purchase').report_action(self)
        else:
            return self.env.ref('eliterp_treasury.eliterp_action_report_account_voucher_sale').report_action(self)

    @api.multi
    def open_voucher_cancel_reason(self):
        context = dict(self._context or {})
        return {
            'name': "Explique la razón",
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'eliterp.voucher.cancel.reason',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
        }

    @api.depends('lines_payment')
    @api.multi
    def _get_total_payments(self):
        """
        Total de las líneas de cobro/pago
        :return:
        """
        for voucher in self:
            total = 0.00
            for line in voucher.lines_payment:
                total += line.amount
            voucher.total_payments = total

    @api.depends('lines_invoice_sales')
    @api.multi
    def _get_total_invoices(self):
        """
        Total de las líneas de factura
        """
        for voucher in self:
            total = 0.00
            for line in voucher.lines_invoice_sales:
                total += line.amount_invoice
            voucher.total_invoices = total

    def move_voucher_sale(self, name, voucher, credit, debit, account_credit, account_debit, balance):
        """
        Creamos movmiento para comprobante de ingreso
        :param name:
        :param voucher:
        :param credit:
        :param debit:
        :param account_credit:
        :param account_debit:
        :param balance:
        :return: object
        """
        move_id = self.env['account.move'].create({
            'journal_id': voucher.journal_id.id,
            'date': voucher.date
        })
        if balance > 0:
            self.env['account.move.line'].with_context(check_move_validity=False).create({
                'name': name,
                'journal_id': voucher.journal_id.id,
                'partner_id': voucher.partner_id.id,
                'account_id': account_debit,
                'move_id': move_id.id,
                'credit': balance,
                'debit': 0.0,
                'date': voucher.date
            })
        self.env['account.move.line'].with_context(check_move_validity=False).create({
            'name': voucher.partner_id.name,
            'journal_id': voucher.journal_id.id,
            'partner_id': voucher.partner_id.id,
            'account_id': account_credit,
            'move_id': move_id.id,
            'credit': (credit - balance) if balance > 0 else credit,
            'debit': 0.0,
            'date': voucher.date
        })
        self.env['account.move.line'].with_context(check_move_validity=True).create({
            'name': voucher.partner_id.name,
            'journal_id': voucher.journal_id.id,
            'partner_id': voucher.partner_id.id,
            'account_id': account_debit,
            'move_id': move_id.id,
            'credit': 0.0,
            'debit': debit,
            'date': voucher.date
        })
        return move_id

    def _get_names(self, type, bank=None):
        """
        Obtenemos el nombre del asiento y del registro
        :param type:
        :param data:
        """
        check = ""
        if bank:
            check = bank.sequence_id.next_by_id()
        if type == 'bank':
            new_name = "Cheque No. " + check
            move_name = 'Egreso/Cheque No. ' + check
        elif type == 'cash':
            sequence = self.env['ir.sequence'].next_by_code('account.voucher.purchase.cash')
            new_name = 'Efectivo No. ' + sequence
            move_name = 'Egreso/Efectivo No. ' + sequence
        else:
            sequence = self.env['ir.sequence'].next_by_code('account.voucher.purchase.transfer')
            new_name = 'Transferencia No. ' + sequence
            move_name = 'Egreso/Transferencia No. ' + sequence
        return new_name, move_name, check

    @api.multi
    def validate_voucher(self):
        # Validar comprobante de egreso
        if self.voucher_type == 'purchase':
            account = False
            if self.type_egress == 'cash' and self.receipt_for == 'supplier':
                account = self.partner_id.property_account_payable_id
            elif self.receipt_for == 'viaticum':
                account = self.expenses_pay
                if not account:
                    raise UserError('No ha definido una cuenta para el pago de viáticos.')
            else:
                account = self.account_id
            for line in self.lines_invoice_purchases:
                if line.amount_payable == 0.00:
                    raise ValidationError(_("Debe eliminar las líneas def acturas con monto a pagar igual a 0"))
            if self.receipt_for == 'supplier':  # Soló para proveedores se realiza está validación
                if round((sum(line.amount_payable for line in self.lines_invoice_purchases)), 2) != round(((
                        self.lines_account.filtered(
                            lambda
                                    x: x.account_id == account))).amount,
                                                                                                          2):
                    raise ValidationError(_("Revise los montos de las líneas de cuenta"))
            new_name, move_name, check = self._get_names(self.type_egress, self.bank_id)
            if self.type_egress == 'bank':  # Soló con cheques generamos el consecutivo
                self.env['eliterp.checks'].create({
                    'partner_id': self.partner_id.id,
                    'name': check,
                    'recipient': self.beneficiary,
                    'type': 'issued',
                    'date': self.date,
                    'check_date': self.check_date,
                    'bank_id': self.bank_id.id,
                    'bank_account': self.bank_id.account_number,
                    'account_id': self.bank_id.account_id.id,
                    'check_type': 'current',
                    'state': 'issued',
                    'amount': self.amount_cancel
                })
            move_id = self.env['account.move'].create({
                'journal_id': self.journal_id.id,
                'date': self.date
            })
            self.env['account.move.line'].with_context(check_move_validity=False).create({
                'name': self.concept,
                'journal_id': self.journal_id.id,
                'partner_id': self.partner_id.id,
                'account_id': self.bank_id.account_id.id if self.type_egress != 'cash' else self.account_id.id,
                'move_id': move_id.id,
                'debit': 0.0,
                'credit': self.amount_cancel,
                'date': self.date
            })
            count = len(self.lines_account)
            for line in self.lines_account:
                count -= 1
                if count == 0:
                    self.env['account.move.line'].with_context(check_move_validity=True).create({
                        'name': self.concept,
                        'journal_id': self.journal_id.id,
                        'partner_id': self.partner_id.id,
                        'account_id': line.account_id.id,
                        'move_id': move_id.id,
                        'credit': 0.0,
                        'debit': line.amount,
                        'date': self.date
                    })
                else:
                    self.env['account.move.line'].with_context(check_move_validity=False).create({
                        'name': self.concept,
                        'journal_id': self.journal_id.id,
                        'partner_id': self.partner_id.id,
                        'account_id': line.account_id.id,
                        'move_id': move_id.id,
                        'credit': 0.0,
                        'debit': line.amount,
                        'date': self.date
                    })
            if self.receipt_for == 'supplier':
                for line_note in self.lines_note_credit:
                    line_move_invoice = line_note.invoices_affect.invoice_id.move_id.line_ids.filtered(
                        lambda x: x.account_id == account)
                    line_move_note = line_note.invoice_id.move_id.line_ids.filtered(
                        lambda x: x.account_id == account)
                    (line_move_invoice + line_move_note).reconcile()
                line_move_voucher = move_id.line_ids.filtered(lambda x: x.account_id == account)
                for line_invoice in self.lines_invoice_purchases:
                    total = line_invoice.amount_payable  # Total a pagar por factura
                    line_move_invoice = line_invoice.invoice_id.move_id.line_ids.filtered(
                        lambda x: x.account_id == account)
                    (line_move_invoice + line_move_voucher).reconcile()
                    #  Pagos programados (Actualizamos las líneas de pagos)
                    payments = line_invoice.invoice_id.programmed_payment_ids.sorted(lambda x: x.amount_reference)
                    for payment in payments:
                        if total == 0.00:
                            continue
                        if payment.amount_reference <= total:
                            total = total - payment.amount_reference
                            payment.update({
                                'amount_reference': 0,
                                'state': 'paid'
                            })
                        else:
                            payment.update({
                                'amount_reference': payment.amount_reference - total
                            })
                            total = 0.00
            if self.receipt_for == 'viaticum':
                self.env['account.move.line'].with_context(check_move_validity=True).create({
                    'name': self.viaticum_id.name,
                    'journal_id': self.journal_id.id,
                    'partner_id': False,
                    'account_id': account.id,
                    'move_id': move_id.id,
                    'credit': 0.0,
                    'debit': self.amount_cancel,
                    'date': self.date
                })
            if self.receipt_for == 'small_box':
                for line in self.custodian_id.replacement_small_box_id.lines_voucher:
                    if line.check_reposition:
                        line.update({'state_reposition': 'paid'})
                self.custodian_id.replacement_small_box_id.update({'replacement_date': self.date})

            if self.receipt_for == 'viaticum':
                self.viaticum_id.update({
                    'state': 'managed'
                })

            move_id.write({'ref': move_name})
            move_id.with_context(eliterp_moves=True, move_name=new_name).post()
            return self.write({
                'state': 'posted',
                'name': new_name,
                'move_id': move_id.id
            })
        # Validar comprobante de ingreso
        else:
            voucher_moves = []
            voucher = self
            balance = self.total_payments - self.total_invoices
            if balance > 0:
                if not self.flag:
                    return {
                        'name': "Escoja la cuenta saldo",
                        'view_mode': 'form',
                        'view_type': 'form',
                        'res_model': 'eliterp.balance.voucher.payment',
                        'type': 'ir.actions.act_window',
                        'target': 'new',
                        'context': {'default_saldo': balance},
                    }
            # Verificamos en líneas de cobro por tipo
            for payment in self.lines_payment:
                # Banco
                if payment.type_payment == 'bank':
                    # Creamos cheque del cobro
                    self.env['eliterp.checks'].create({
                        'partner_id': self.partner_id.id,
                        'check_number': payment.check_number,
                        'recipient': payment.drawer,
                        'type': 'receipts',
                        'date': payment.date_issue,
                        'check_date': payment.date_due,
                        'bank_id': payment.bank_id.id,
                        'bank_account': payment.account_number,
                        'account_id': payment.account_id.id,
                        'check_type': payment.check_type,
                        'state': 'received',
                        'amount': payment.amount
                    })
                    move_id = self.move_voucher_sale(
                        self.concept,
                        voucher,
                        payment.amount,
                        payment.amount,
                        self.partner_id.property_account_receivable_id.id,
                        payment.account_id.id,
                        balance
                    )
                    move_id.with_context(eliterp_moves=True, internal_voucher=True).post()
                    payment.write({'move_id': move_id.id})
                    line_move_bank = move_id.line_ids.filtered(
                        lambda x: x.account_id == self.partner_id.property_account_receivable_id)
                    for line in self.lines_invoice_sales:
                        line_move_invoice = line.invoice_id.move_id.line_ids.filtered(
                            lambda x: x.account_id == self.partner_id.property_account_receivable_id)
                        (line_move_bank + line_move_invoice).reconcile()
                        voucher_moves.append(move_id)
                # Efectivo
                if payment.type_payment == 'cash':
                    move_id = self.move_voucher_sale(
                        self.concept,
                        voucher,
                        payment.amount,
                        payment.amount,
                        self.partner_id.property_account_receivable_id.id,
                        payment.account_id.id,
                        balance
                    )
                    move_id.with_context(eliterp_moves=True, internal_voucher=True).post()
                    payment.write({'move_id': move_id.id})
                    line_move_cash = move_id.line_ids.filtered(
                        lambda x: x.account_id == self.partner_id.property_account_receivable_id)
                    for line in self.lines_invoice_sales:
                        line_move_invoice = line.invoice_id.move_id.line_ids.filtered(
                            lambda x: x.account_id == self.partner_id.property_account_receivable_id)
                        (line_move_cash + line_move_invoice).reconcile()
                        voucher_moves.append(move_id)
                # Transferencia
                if payment.type_payment == 'transfer':
                    move_id = self.move_voucher_sale(
                        self.concept,
                        voucher,
                        payment.amount,
                        payment.amount,
                        self.partner_id.property_account_receivable_id.id,
                        payment.account_id.id,
                        balance
                    )
                    move_id.with_context(eliterp_moves=True, internal_voucher=True).post()
                    payment.write({'move_id': move_id.id})
                    line_move_transfer = move_id.line_ids.filtered(
                        lambda x: x.account_id == self.partner_id.property_account_receivable_id)
                    for line in self.lines_invoice_sales:
                        line_move_invoice = line.invoice_id.move_id.line_ids.filtered(
                            lambda x: x.account_id == self.partner_id.property_account_receivable_id)
                        (line_move_transfer + line_move_invoice).reconcile()
                    voucher_moves.append(move_id)
            new_name = self.journal_id.sequence_id.next_by_id()
            for move in voucher_moves:
                move.write({'ref': new_name})
            return self.write({
                'state': 'posted',
                'name': new_name,
                'move_id': move_id.id
            })

    def apply_amount(self):
        """
        Aplicamos la suma de las líneas de cuenta
        """
        self.amount_cancel = sum(line.amount for line in self.lines_account)

    def load_amount(self):
        journal_id = self.env['account.journal'].search(
            [('name', '=', 'Efectivo')]).id  # El diario del pago/cobro siempre en efectivo
        # Cargar montos de comprobante de ingreso
        if self.voucher_type == 'sale':
            if not self.lines_invoice_sales:
                raise UserError(_("Necesita cargar líneas de factura"))
            if not self.lines_payment:
                raise UserError(_("No tiene ninguna líneas de tipo de pago"))
            else:
                total = 0.00
                for payment in self.lines_payment:
                    total += payment.amount
            for invoice in self.lines_invoice_sales:
                if total == 0.00:
                    continue
                if invoice.amount_total <= total:
                    invoice.update({
                        'amount_payable': invoice.amount_total,
                        'journal_id': journal_id
                    })
                    total = total - invoice.amount_total
                else:
                    invoice.update({
                        'amount_payable': total,
                        'journal_id': journal_id
                    })
                    total = 0.00
        # Cargar montos de comprobante de egreso
        else:
            self.amount_cancel = sum(line.amount for line in self.lines_account)
            if self.type_egress == 'cash' and self.receipt_for == 'supplier':
                total = self.lines_account.filtered(
                    lambda x: x.account_id == self.partner_id.property_account_payable_id).amount
            else:
                total = self.lines_account.filtered(lambda x: x.account_id == self.account_id).amount
            for invoice in self.lines_invoice_purchases:
                if total == 0.00:
                    continue
                if invoice.amount_programmed <= total:  # Monto programado
                    invoice.update({'amount_payable': invoice.amount_programmed, 'journal_id': journal_id})
                    total = total - invoice.amount_total
                else:
                    invoice.update({'amount_payable': total, 'journal_id': journal_id})
                    total = 0.00
        return

    def apply_notes(self):
        """
        Aplicamos notas de crédito en facturas seleccionadas
        """
        for line in self.lines_note_credit:
            line_invoice = self.lines_invoice_purchases.filtered(lambda x: x.id == line.invoices_affect.id)
            line_invoice.write({'amount_total': line_invoice.amount_total + line.amount_note})
        return True

    def load_data(self):
        """
        Cargamos la información necesaria
        """
        if not self.partner_id:
            if self.voucher_type == 'sale':
                raise UserError(_("Necesita seleccionar al Cliente."))
            else:
                raise UserError(_("Necesita seleccionar al Proveedor."))
        else:
            if self.voucher_type == 'sale':
                self.lines_invoice_sales.unlink()  # Limpiamos líneas anteriores
                invoices_list = self.env['account.invoice'].search([
                    ('partner_id', '=', self.partner_id.id), ('state', '=', 'open')
                ])
            else:
                # Cargamos facturas de proveedor
                invoices_list = self.env['account.invoice'].search([
                    ('partner_id', '=', self.partner_id.id),
                    ('state', '=', 'open'),
                    ('approval_status', '!=', 'pending')
                ])
                # Cargamos notas de crédito
                notes_list = self.env['account.invoice'].search([
                    ('partner_id', '=', self.partner_id.id),
                    ('state', '=', 'open'),
                    ('type', '=', 'in_refund')
                ])
            list_invoices = []
            for invoice in invoices_list:
                list_invoices.append([0, 0, {
                    'invoice_id': invoice.id,
                    'date_due_invoice': invoice.date_due,
                    'amount_invoice': invoice.amount_total,
                    'amount_programmed': invoice.amount_programmed,
                    'amount_total': invoice.residual
                }])
            list_notes = []
            list_account = []
            if self.voucher_type == 'purchase':
                self.lines_invoice_purchases.unlink()  # Limpiamos líneas anteriores
                self.lines_account.unlink()
                self.lines_note_credit.unlink()
                if notes_list:
                    list_notes = []
                    for note in notes_list:
                        list_notes.append([0, 0, {
                            'invoice_id': note.id,
                            'date_due_invoice': note.date_due,
                            'amount_note': -1 * note.amount_total
                        }])
                list_account.append([0, 0, {'amount': 0.00,
                                            'account_id': self.account_id.id if not self.type_egress == 'cash'
                                                                                and not self.receipt_for == 'supplier'
                                            else self.partner_id.property_account_payable_id.id}])
                return self.update({
                    'lines_invoice_purchases': list_invoices,
                    'lines_account': list_account,
                    'lines_note_credit': list_notes
                })
            return self.update({'lines_invoice_sales': list_invoices})

    @api.onchange('partner_id', 'pay_now')
    def _onchange_partner_id(self):
        """
        MM: TODO: Para que sirve esto?
        """
        if self.pay_now == 'pay_now':
            liq_journal = self.env['account.journal'].search([('type', 'in', ('bank', 'cash'))], limit=1)
            self.account_id = liq_journal.default_debit_account_id \
                if self.voucher_type == 'sale' else liq_journal.default_credit_account_id
        else:
            if self.partner_id:
                if self.voucher_type == 'sale':
                    self.account_id = self.partner_id.property_account_receivable_id
                else:
                    if self.type_egress != 'cash':
                        self.account_id = self.partner_id.property_account_payable_id
                    else:
                        self.account_id = False
            else:
                self.account_id = self.journal_id.default_debit_account_id \
                    if self.voucher_type == 'sale' else self.journal_id.default_credit_account_id
        self.beneficiary = self.partner_id.name

    @api.model
    def _default_journal(self):
        """
        Método modificado: Obtenemos nuevo diario por defecto
        """
        if self._context['voucher_type'] == 'sale':
            return self.env['account.journal'].search([('name', '=', 'Comprobante de ingreso')])[0].id
        else:
            return self.env['account.journal'].search([('name', '=', 'Comprobante de egreso')])[0].id

    @api.onchange('balance_account')
    def _onchange_balance_account(self):
        """
        Al cambiar la cuenta saldo si es diferente de 0 la mostramos
        """
        if len(self.balance_account) != 0:
            self.show_account = True

    @api.onchange('bank_id', 'type_egress')
    def _onchange_bank_id(self):
        """
        Número del siguiente cheque según secuencia, caso contrario colocamos en falso
        """
        if self.bank_id:
            if self.type_egress == 'bank':
                check_number = self.bank_id.sequence_id.number_next_actual
                self.check_number = check_number
            else:
                self.check_number = False
        else:
            self.check_number = False

    @api.onchange('custodian_id')
    def _onchange_custodian_id(self):
        """
        Al cambiar de custodio
        """
        self.beneficiary = self.custodian_id.name
        if self.type_egress != 'cash':
            self.account_id = self.custodian_id.account_id.id
        else:
            self.account_id = False

    def load_small_box(self):
        """
        Cargamos montos de caja chica
        """
        if self.custodian_id.replacement_small_box_id.state == 'liquidated':
            line = []
            line.append([0, 0, {'amount': self.custodian_id.replacement_small_box_id.total_vouchers,
                                'account_id': self.custodian_id.account_id.id}])
            self.update({'lines_account': line})
        else:
            return True

    @api.onchange('viaticum_id')
    def _onchange_viaticum_id(self):
        """
        Al cambiar solicitud de viático
        """
        if self.viaticum_id:
            self.amount_cancel = self.viaticum_id.amount_total
            self.beneficiary = self.viaticum_id.beneficiary.name
            self.concept = self.viaticum_id.reason

    lines_payment = fields.One2many('eliterp.lines.payment', 'voucher_id', string='Líneas de cobro')
    lines_invoice_sales = fields.One2many('eliterp.lines.invoice', 'voucher_id',
                                          string='Líneas de factura en ventas')
    lines_invoice_purchases = fields.One2many('eliterp.lines.invoice', 'voucher_id',
                                              string='Líneas de factura en compras')
    lines_note_credit = fields.One2many('eliterp.lines.credit.notes', 'voucher_id',
                                        string='Líneas de nota de crédito')
    lines_account = fields.One2many('eliterp.lines.account', 'voucher_id', string='Líneas de cuenta')
    # CM
    journal_id = fields.Many2one('account.journal', 'Journal',
                                 required=True, readonly=True, states={'draft': [('readonly', False)]},
                                 default=_default_journal)

    type_egress = fields.Selection([
        ('bank', 'Cheque'),
        ('cash', 'Efectivo'),
        ('transfer', 'Transferencia')
    ], string='Forma de pago', default='bank', required=True)
    receipt_for = fields.Selection([
        ('supplier', 'Proveedor'),
        ('small_box', 'Caja chica'),
        ('viaticum', 'Solicitud de viático'),
        ('several', 'Varios')
    ], string="Tipo de comprobante", default='supplier', required=True)
    beneficiary = fields.Char('Beneficiario')
    check_number = fields.Char('No. Cheque')
    check_date = fields.Date('Fecha Cheque/Transferencia')
    bank_id = fields.Many2one('res.bank', string="Banco")
    amount_cancel = fields.Float('Monto a cancelar')
    total_payments = fields.Monetary('Total de cobros', compute='_get_total_payments')
    total_invoices = fields.Monetary('Total facturas', compute='_get_total_invoices')
    # CM
    account_id = fields.Many2one('account.account', string='Cuenta',
                                 domain=[('deprecated', '=', False), ('account_type', '=', 'movement')])
    concept = fields.Char('Concepto', required=True, readonly=True, states={'draft': [('readonly', False)]})
    # TODO: Para que sirven estos campos
    flag = fields.Boolean('Ya no hay saldo?', default=False)
    show_account = fields.Boolean('Se muestra la cuenta?', default=False)
    balance_account = fields.Many2one('account.account', string="Cuenta saldo",
                                      domain=[('account_type', '=', 'movement')])
    balance = fields.Float('Saldo')
    # Caja chica
    custodian_id = fields.Many2one('eliterp.custodian.small.box', 'Custodio caja chica')
    # Viático (Soló las qué estén aprobadas)
    viaticum_id = fields.Many2one('eliterp.travel.allowance.request', string="Solicitud",
                                  domain=[('state', '=', 'approve')])
    expenses_pay = fields.Many2one('account.account', string="Cuenta contable")
