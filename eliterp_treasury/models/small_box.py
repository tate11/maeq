# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import json
from datetime import datetime


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.model
    def create(self, vals):
        if 'active_model' in self._context:  # Verificamos modelo activo
            # Comprobante de caja chica
            if self._context['active_model'] == 'eliterp.voucher.small.box':
                vals.update({
                    'small_box': True,
                    'voucher_small_box_id': self._context['active_id']
                })
                beneficiary = self.env['res.partner'].browse(vals['partner_id'])[0].name
                self.env['eliterp.voucher.small.box'].browse(self._context['active_id']).write({
                    'has_invoice': True,
                    'beneficiary': beneficiary,
                    'concept': vals['concept']
                })
        return super(AccountInvoice, self).create(vals)

    voucher_small_box_id = fields.Many2one('eliterp.voucher.small.box', 'Comprobante caja chica')
    small_box = fields.Boolean('Caja chica?', default=False)


class CustodianSmallBox(models.Model):
    _name = 'eliterp.custodian.small.box'

    _description = 'Custodio de caja chica'

    @api.constrains('amount')
    def _check_amount(self):
        """
        Validamos monto
        """
        if self.amount <= 0:
            raise ValidationError("Monto no puede ser menor o igual a 0.")

    name = fields.Char('Nombre', required=True)
    account_id = fields.Many2one('account.account', string='Cuenta contable',
                                 domain=[('account_type', '=', 'movement')], required=True)
    amount = fields.Float('Monto')
    replacement_small_box_id = fields.Many2one('eliterp.replacement.small.box', 'Reposición caja chica')


class AccountSmallBoxLine(models.Model):
    _name = 'eliterp.account.small.box.line'

    _description = 'Línea de cuenta en voucher de caja chica'

    @api.constrains('amount')
    def _check_amount(self):
        """
        Validamos qué las líneas sea mayor a 0
        """
        if self.amount <= 0:
            raise ValidationError("Debe eliminar las líneas de cuentas con monto igual a 0.")

    account_id = fields.Many2one('account.account', string="Cuenta Contable",
                                 domain=[('account_type', '=', 'movement')], required=True)
    amount = fields.Float('Monto', required=True)
    voucher_small_box_id = fields.Many2one('eliterp.voucher.small.box', string="Comprobante caja chica")


class VoucherSmallBox(models.Model):
    _name = 'eliterp.voucher.small.box'

    _description = 'Comprobante de caja chica'

    @api.multi
    def print_voucher(self):
        """
        Imprimir comprobante de caja chica
        """
        self.ensure_one()
        return self.env.ref('eliterp_treasury.eliterp_action_report_voucher_small_box').report_action(self)

    @api.one
    def confirm_voucher(self):
        """
        Confirmamos qué voucher este correctamente llenado y lo confirmamos,
        si es factura se debe ver qué este validada
        """
        if self.type_voucher == 'invoice':
            invoice = self.env['account.invoice'].search([('voucher_small_box_id', '=', self.id)])[0]
            if invoice.state == 'draft':
                raise UserError("Se debe validar la factura No. %s" % invoice.invoice_number)
        else:
            if not self.lines_account:
                raise UserError("Debe ingresar al menos una línea de cuenta.")
        return self.write({
            'state': 'confirm',
            'name': self.journal_id.sequence_id.next_by_id(),
            'replacement_small_box_id': self.custodian_id.replacement_small_box_id.id
        })

    @api.model
    def _default_journal(self):
        """
        Obtenemos diario por defecto
        """
        return self.env['account.journal'].search([('name', '=', 'Comprobante caja chica')])[0].id

    @api.multi
    def view_invoice(self):
        """
        Revisamos la factura creada
        :return: dict
        """
        invoice = self.env['account.invoice'].search([('voucher_small_box_id', '=', self.id)])
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('account.action_invoice_tree2')
        form_view_id = imd.xmlid_to_res_id('account.invoice_supplier_form')
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[form_view_id, 'form']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
            'res_id': invoice[0].id
        }
        return result

    @api.multi
    def create_invoice(self):
        """
        Creamos factura de caja chica
        :return: dict
        """
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('account.action_invoice_tree2')
        form_view_id = imd.xmlid_to_res_id('account.invoice_supplier_form')
        context = json.loads(str(action.context).replace("'", '"'))
        context.update({'default_small_box': True})
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[form_view_id, 'form']],
            'target': action.target,
            'context': context,
            'res_model': action.res_model,
        }
        return result

    @api.one
    @api.depends('lines_account.amount')
    def _get_amount_total(self):
        """
        Obtenemos el total del comprobante
        """
        if self.type_voucher == 'vale':
            self.amount_total = sum(line.amount for line in self.lines_account)
        else:
            invoice = self.env['account.invoice'].search([('voucher_small_box_id', '=', self.id)])
            if not invoice:
                self.amount_total = 0.00
            else:
                self.amount_total = invoice[0].amount_total

    @api.model
    def create(self, vals):
        """
        AL crear comprobante debemos validar qué la caja chica este aperturada
        :param vals:
        :return: object
        """
        if not self.env['eliterp.replacement.small.box'].search([('custodian_id', '=', vals['custodian_id'])]):
            raise ValidationError("Debe aperturar caja chica del custodio.")
        res = super(VoucherSmallBox, self).create(vals)
        return res

    name = fields.Char(string="No. Documento", copy=False)
    type_voucher = fields.Selection([('vale', 'Vale'), ('invoice', 'Factura')], string="Tipo", default='vale',
                                    readonly=True, states={'draft': [('readonly', False)]})
    journal_id = fields.Many2one('account.journal', 'Diario', default=_default_journal)
    beneficiary = fields.Char(string="Beneficiario", readonly=True, states={'draft': [('readonly', False)]})
    date = fields.Date('Fecha registro', default=fields.Date.context_today, required=True,
                       readonly=True, states={'draft': [('readonly', False)]})
    amount_total = fields.Float(string="Monto total", compute='_get_amount_total')
    concept = fields.Char(string="Concepto", readonly=True, states={'draft': [('readonly', False)]})
    has_invoice = fields.Boolean('Tiene factura?', default=False, copy=False)
    lines_account = fields.One2many('eliterp.account.small.box.line', 'voucher_small_box_id',
                                    string="Línea de cuenta")
    custodian_id = fields.Many2one('eliterp.custodian.small.box', string='Custodio', required=True
                                   , readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection([('draft', 'Borrador'), ('confirm', 'Confirmado')], string="Estado", default='draft')
    replacement_small_box_id = fields.Many2one('eliterp.replacement.small.box', 'Reposición caja chica', copy=False)
    check_reposition = fields.Boolean('Reponer?', default=False, copy=False)
    state_reposition = fields.Selection([('pending', 'Pendiente'), ('paid', 'Pagado')], string="Estado",
                                        default='pending', copy=False)


class ReplacementSmallBox(models.Model):
    _name = 'eliterp.replacement.small.box'

    _description = 'Reposición de caja chica'

    # Funciones para impresión de documento
    @api.model
    def _get_period(self, lines):
        """
        Obtenemos fecha inicial y final desde apertura de caja
        :param lines:
        :return:
        """
        dates = []
        dates_sorted = []
        for line in lines:
            dates.append(datetime.strptime(line.date, "%Y-%m-%d"))
        dates_sorted = sorted(dates)
        if dates_sorted:
            period = "Del " + dates_sorted[0].date().strftime("%Y-%m-%d") + " hasta " + dates_sorted[
                len(dates_sorted) - 1].date().strftime("%Y-%m-%d")
        else:
            period = "/"
        return period

    @api.model
    def _get_invoice(self, id):
        """
        Retornamos la factura del voucher
        :param id:
        :return: object:
        """
        invoice = self.env['account.invoice'].search([('voucher_small_box_id', '=', id)])
        return invoice


    @api.multi
    def print_replacement(self):
        """
        Imprimimos reposición Caja Chica
        """
        self.ensure_one()
        return self.env.ref('eliterp_treasury.eliterp_action_report_replacement_small_box').report_action(self)

    @api.model
    def _default_journal(self):
        """
        Definimos diario por defecto
        """
        return self.env['account.journal'].search([('name', '=', 'Reposición caja chica')], limit=1)[0].id

    @api.multi
    def to_approve(self):
        """
        Solicitamos aprobación
        """
        if not self.lines_voucher:
            raise  UserError("No tiene líneas de comprobantes para aprobar.")
        self.write({'state': 'to_approve'})

    @api.multi
    def approve(self):
        """
        Aprobamos
        """
        self.write({
            'state': 'approve',
            'approval_user': self.env.uid
        })

    @api.multi
    def open_small_box(self):
        """
        Aperturamos caja chica para poder enlazar registros de comprobantes
        """
        voucher_ids = self.env['eliterp.voucher.small.box'].search([
            ('check_reposition', '=', False),
            ('state_reposition', '=', 'pending'),
            ('custodian_id', '=', self.custodian_id.id)
        ])
        for voucher in voucher_ids:
            voucher.update({'replacement_small_box_id': False})
            voucher.write({'replacement_small_box_id': self[0].id})
        self.write({
            'state': 'open',
            'name': self.journal_id.sequence_id.next_by_id(),
            'opening_date': self.date
        })

    @api.multi
    def liquidate_small_box(self):
        """
        Liquidamos caja chica para generar asiento contable
        """
        move_id = self.env['account.move'].create({'journal_id': self.journal_id.id,
                                                   'date': self.date,
                                                   'ref': self.name})
        self.env['account.move.line'].with_context(check_move_validity=False).create({
            'name': self.custodian_id.name,
            'journal_id': self.journal_id.id,
            'account_id': self.custodian_id.account_id.id,
            'move_id': move_id.id,
            'debit': 0.00,
            'credit': self.total_vouchers,
            'date': self.date
        })

        count = len(self.lines_voucher)
        for line in self.lines_voucher:
            if line.type_voucher == 'invoice':
                invoice = self.env['account.invoice'].search([('voucher_small_box_id', '=', line.id)])
                self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'name': invoice.account_id.name,
                    'journal_id': self.journal_id.id,
                    'account_id': invoice.account_id.id,
                    'move_id': move_id.id,
                    'debit': line.amount_total,
                    'credit': 0.00,
                    'date': self.date
                })
            count -= 1
            if line.check_reposition and line.state_reposition == 'pending':
                count_line = len(line.lines_account)
                for line_voucher in line.lines_account:
                    count_line -= 1
                    if count == 0 and count_line == 0:
                        self.env['account.move.line'].with_context(check_move_validity=True).create(
                            {'name': line_voucher.account_id.name,
                             'journal_id': self.journal_id.id,
                             'account_id': line_voucher.account_id.id,
                             'move_id': move_id.id,
                             'debit': line_voucher.amount,
                             'credit': 0.00,
                             'date': self.date})
                    else:
                        self.env['account.move.line'].with_context(check_move_validity=False).create(
                            {'name': line_voucher.account_id.name,
                             'journal_id': self.journal_id.id,
                             'account_id': line_voucher.account_id.id,
                             'move_id': move_id.id,
                             'debit': line_voucher.amount,
                             'credit': 0.00,
                             'date': self.date})
                    line.write({'replacement_small_box_id': self.id})
        move_id.with_context(eliterp_moves=True, move_name=self.name).post()
        move_id.write({'ref': self.name})
        return self.write(
            {'state': 'liquidated', 'move_id': move_id.id})

    @api.model
    def create(self, vals):
        res = super(ReplacementSmallBox, self).create(vals)
        # Luego de crear reposición de caja chica le asiganmos la misma a el custodio
        res.custodian_id.replacement_small_box_id = res.id
        res.amount_allocated = res.custodian_id.amount
        res.residual = res.custodian_id.amount
        return res

    @api.multi
    def load_amount(self):
        """
        Cargamos el monto de los comprobantes
        """
        total = 0.00
        for line in self.lines_voucher:
            if line.check_reposition:
                total += line.amount_total
        if total > (self.residual):
            raise ValidationError("El monto a reponer es mayor que el monto asignado a %s" % self.custodian_id.name)
        self.write({'total_vouchers': total, 'residual': self.amount_allocated - total})

    @api.onchange('custodian_id')
    def _onchange_custodian_id(self):
        """
        Al cambiar custodio actualizamos monto y saldo del mismo
        """
        self.amount_allocated = self.custodian_id.amount
        self.residual = self.custodian_id.amount

    name = fields.Char('No. Documento')
    amount_allocated = fields.Float('Monto asignado')
    total_vouchers = fields.Float('Total comprobantes')
    residual = fields.Float('Saldo')
    move_id = fields.Many2one('account.move', 'Asiento contable', copy=False)
    journal_id = fields.Many2one('account.journal', 'Diario', default=_default_journal)
    date = fields.Date('Fecha documento', default=fields.Date.context_today)
    custodian_id = fields.Many2one('eliterp.custodian.small.box', 'Custodio', required=True)
    state = fields.Selection([('draft', 'Borrador'), ('open', 'Abierta'),
                              ('to_approve', 'A aprobar'), ('approve', 'Aprobado'),
                              ('liquidated', 'Liquidada')], string="Estado", default='draft')
    lines_voucher = fields.One2many('eliterp.voucher.small.box', 'replacement_small_box_id',
                                    string="Linea de comprobante")
    opening_date = fields.Date('Fecha apertura')
    replacement_date = fields.Date(
        'Fecha reposición')  # La fecha de reposición es cuando se realiza el comprobante de egreso
    approval_user = fields.Many2one('res.users', 'Aprobado por')
