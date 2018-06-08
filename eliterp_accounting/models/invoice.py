# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo.tools import float_is_zero
from odoo import api, fields, models, _
from datetime import datetime, date
from odoo.exceptions import UserError


class ReasonCancelInvoice(models.TransientModel):
    _name = 'eliterp.reason.cancel.invoice'

    _description = 'Razón para cancelar factura'

    description = fields.Text('Descripción', required=True)

    @api.multi
    def cancel_invoice(self):
        """
        Cancelamos factura
        :return: boolean
        """
        invoice = self.env['account.invoice'].browse(self._context['active_id'])
        invoice.action_cancel()
        invoice.move_id.write({'ref': self.description})
        for line in invoice.withhold_id.lines_withhold:  # Borrramos las líneas de impuestos de la retención
            invoice_tax = self.env['account.invoice.tax'].search([
                ('invoice_id', '=', invoice.id),
                ('name', '=', line.tax_id.name),
                ('tax_id', '=', line.tax_id.id),
                ('account_id', '=', line.tax_id.account_id.id)
            ])
            invoice_tax.unlink()
        invoice.withhold_id.write({'state': 'cancel'})
        invoice.write({
            'withhold_id': False,
            'have_withhold': False,
            'comment': 'Factura [%s]: cancelada por %s' % (invoice.invoice_number, self.description),
        })
        if invoice.type == 'in_invoice':  # Colocamos No. Factura en False para no tener problemas al crear la misma
            invoice.write({'invoice_number': False})
        invoice._compute_amount()
        invoice._compute_residual()
        return True


class AccountInvoiceTax(models.Model):
    _inherit = 'account.invoice.tax'

    @api.model
    def create(self, values):
        if 'credit_note' in self._context:  # Si es nota de crédito se cambia impuestos a no manual
            values.update({'manual': False})
        return super(AccountInvoiceTax, self).create(values)


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    @api.onchange('product_id')
    def _onchange_product_id(self):
        domain = {}
        if not self.invoice_id:
            return

        part = self.invoice_id.partner_id
        fpos = self.invoice_id.fiscal_position_id
        company = self.invoice_id.company_id
        currency = self.invoice_id.currency_id
        type = self.invoice_id.type

        if not part:
            warning = {
                'title': _('Warning!'),
                'message': _('You must first select a partner!'),
            }
            return {'warning': warning}

        if not self.product_id:
            if type not in ('in_invoice', 'in_refund'):
                self.price_unit = 0.0
            domain['uom_id'] = []
        else:
            if part.lang:
                product = self.product_id.with_context(lang=part.lang)
            else:
                product = self.product_id

            self.name = product.partner_ref
            account = self.get_invoice_line_account(type, product, fpos, company)
            if account:
                self.account_id = account.id
            self._set_taxes()

            if type in ('in_invoice', 'in_refund'):  # MARZ
                if product.description_purchase:
                    self.name = product.description_purchase
            else:
                if product.description_sale:
                    self.name = product.description_sale

            if not self.uom_id or product.uom_id.category_id.id != self.uom_id.category_id.id:
                self.uom_id = product.uom_id.id
            domain['uom_id'] = [('category_id', '=', product.uom_id.category_id.id)]

            if company and currency:
                if company.currency_id != currency:
                    self.price_unit = self.price_unit * currency.with_context(
                        dict(self._context or {}, date=self.invoice_id.date_invoice)).rate

                if self.uom_id and self.uom_id.id != product.uom_id.id:
                    self.price_unit = product.uom_id._compute_price(self.price_unit, self.uom_id)
        return {'domain': domain}


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def action_cancel(self):
        """
        MM: Cancelamos la factura si no tiene pagos/cobros realizados
        """
        moves = self.env['account.move']
        for inv in self:
            if inv.move_id:
                moves += inv.move_id
            if inv.payment_move_line_ids:
                raise UserError(_(
                    'You cannot cancel an invoice which is partially paid. You need to '
                    'unreconcile related payment entries first.'))
        if moves:
            moves.with_context(from_invoice=True).reverse_moves(self.date_invoice, self.journal_id or False)
            moves.write({'state': 'cancel'})
        invoice_reference = self.reference if self.reference else "/"
        self.write({
            'state': 'cancel',
            'reference': "%s cancelada" % invoice_reference
        })
        return True

    @api.multi
    def name_get(self):
        """
        Cambiamos el nombre del registro para mostrar
        """
        types = {
            'out_invoice': _('Invoice'),
            'in_invoice': _('Vendor Bill'),
            'out_refund': _('Refund'),
            'in_refund': 'Nota de crédito',
        }
        result = []
        for invoice in self:
            result.append((invoice.id, "%s [%s]" % (types[invoice.type], invoice.reference or '/')))
        return result

    @api.multi
    def open_reason_cancel_invoice(self):
        """
        Abrimos ventana emergente para cancelar factura
        :return: dict
        """
        context = dict(self._context or {})
        return {
            'name': "Explique la razón",
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'eliterp.reason.cancel.invoice',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
        }

    @api.multi
    def action_invoice_open(self):
        """
        MM: Validamos la factura
        :return: object
        """
        # Notas de crédito
        if self.type in ('in_refund', 'out_refund'):
            notes_credit = self.env['account.invoice'].search(
                [('invoice_reference', '=', self.invoice_reference.id), ('state', '=', 'open')])
            amount_notes = self.invoice_reference.amount_untaxed - sum(note.amount_total for note in notes_credit)
            if self.amount_untaxed > amount_notes:
                raise UserError("Excede de la base imponible de la referencia [%s]." % self.invoice_reference.reference)
            res = super(AccountInvoice, self).action_invoice_open()
            # TODO: Venta
            if self.type == 'out_refund':
                self.write({
                    'state_notes': 'posted',
                    'invoice_number': self.invoice_number
                })
            # Compra
            else:
                self.write({
                    'state_notes': 'posted',
                    'invoice_number': self.invoice_number
                })
            return res
        # Facturas de proveedor
        if self.type == 'in_invoice':
            if not self.have_withhold:
                raise UserError("Debe ingresar la retención correspondiente a la factura.")
            else:
                res = super(AccountInvoice, self).action_invoice_open()
                self.withhold_id.write({
                    'state': 'confirm',
                    'name': self.withhold_id.journal_id.sequence_id.next_by_id()
                })
        # Facturas de cliente
        if self.type == 'out_invoice':
            self.action_number()
        return super(AccountInvoice, self).action_invoice_open()

    @api.one
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount', 'currency_id', 'company_id', 'date_invoice')
    def _compute_amount(self):
        """
        MM: Calculamos el total de la factura
        """
        round_curr = self.currency_id.round
        self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line_ids)
        # Cambiamos los valores de impuestos (Retención)
        total_tax = 0.00
        amount_retention = 0.00
        for line in self.tax_line_ids:
            if line.amount >= 0:
                total_tax += line.amount
            else:
                amount_retention += line.amount
        self.amount_tax = round_curr(total_tax)
        self.amount_retention = round_curr(-1 * (amount_retention))
        self.amount_total = self.amount_untaxed + self.amount_tax
        amount_total_company_signed = self.amount_total
        amount_untaxed_signed = self.amount_untaxed
        if self.currency_id and self.company_id and self.currency_id != self.company_id.currency_id:
            currency_id = self.currency_id.with_context(date=self.date_invoice)
            amount_total_company_signed = currency_id.compute(self.amount_total, self.company_id.currency_id)
            amount_untaxed_signed = currency_id.compute(self.amount_untaxed, self.company_id.currency_id)
        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        self.amount_total_company_signed = amount_total_company_signed * sign
        self.amount_total_signed = self.amount_total * sign
        self.amount_untaxed_signed = amount_untaxed_signed * sign
        # Cargar base cero IVA y base gravada
        total_base_taxed = 0.00
        total_base_zero_iva = 0.00
        for line in self.invoice_line_ids:
            for tax in line.invoice_line_tax_ids:
                if tax.amount > 0:
                    total_base_taxed += line.price_subtotal
                else:
                    total_base_zero_iva += line.price_subtotal
        self.base_zero_iva = total_base_zero_iva
        self.taxed = total_base_taxed

    @api.one
    @api.depends(
        'state', 'currency_id', 'invoice_line_ids.price_subtotal',
        'move_id.line_ids.amount_residual',
        'move_id.line_ids.currency_id')
    def _compute_residual(self):
        """
        MM: Calculamos el valor pendiente de pago/cobro
        :return: self
        """
        residual = 0.0
        residual_company_signed = 0.0
        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        for line in self.sudo().move_id.line_ids:
            if line.account_id.internal_type in (
                    'receivable', 'payable'):  # TODO: Si la cuenta no es de este tipo la pondrá como pagada
                residual_company_signed += line.amount_residual
                if line.currency_id == self.currency_id:
                    residual += line.amount_residual_currency if line.currency_id else line.amount_residual
                else:
                    from_currency = (line.currency_id and line.currency_id.with_context(
                        date=line.date)) or line.company_id.currency_id.with_context(date=line.date)
                    residual += from_currency.compute(line.amount_residual, self.currency_id)
        self.residual_company_signed = abs(residual_company_signed) * sign
        self.residual_signed = abs(residual) * sign
        self.residual = abs(residual)
        digits_rounding_precision = self.currency_id.rounding
        if float_is_zero(self.residual, precision_rounding=digits_rounding_precision):
            self.reconciled = True
        else:
            self.reconciled = False
        # Calcular nuevamente base cero IVA y base gravada
        total_base_taxed = 0.00
        total_base_zero_iva = 0.00
        for line in self.invoice_line_ids:
            for tax in line.invoice_line_tax_ids:
                if tax.amount > 0:
                    total_base_taxed += line.price_subtotal
                else:
                    total_base_zero_iva += line.price_subtotal
        self.base_zero_iva = total_base_zero_iva
        self.base_taxed = total_base_taxed

    @api.model
    def create(self, values):
        if not values.get('date_invoice'):
            values['date_invoice'] = date.today().strftime('%Y-%m-%d')
        self.env['eliterp.global.functions'].valid_period(
            values['date_invoice'])  # Validar período contable sea correcto
        return super(AccountInvoice, self).create(values)

    @api.multi
    def print_invoice(self):
        """
        Imprimimos factura
        """
        self.ensure_one()
        if self.type == 'out_invoice':  # TODO: Cliente
            pass
        else:  # Proveedor
            return self.env.ref('eliterp_accounting.action_report_invoice_supplier').report_action(self)

    def _default_new_currency(self):
        """
        TODO: Obtenemos la moneda (USD), si no se ha configurado en datos de compañía
        """
        return self.env['res.currency'].search([('name', '=', 'USD')])[0].id

    @api.depends('date_invoice')
    @api.one
    def _get_accounting_period(self):
        """
        Obtenemos el período contable con la fecha de factura
        """
        if not self.date_invoice:
            self.period = False
        else:
            date = datetime.strptime(self.date_invoice, "%Y-%m-%d")
            period = self.env['eliterp.account.period'].search([('year_accounting', '=', date.year)])
            if len(period) == 0:
                self.period = False  # Cambiar por testeo en ODOO.sh
            accounting_period = period.lines_period.filtered(lambda x: x.code == date.month)
            self.period = accounting_period.id

    # CM
    date_invoice = fields.Date('Fecha emisión',
                               readonly=True, states={'draft': [('readonly', False)]}, index=True,
                               help="Keep empty to use the current date", copy=False, default=fields.Date.context_today,
                               required=True)
    # CM
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  required=True, readonly=True, states={'draft': [('readonly', False)]},
                                  default=_default_new_currency, track_visibility='always')
    period = fields.Many2one('eliterp.lines.account.period', string='Período', store=True, readonly=True,
                             compute='_get_accounting_period')

    amount_retention = fields.Monetary('Total a retener', store=True,
                                       currency_field='currency_id', readonly=True, compute='_compute_amount')
    base_zero_iva = fields.Float('Base cero IVA', readonly=True)
    base_taxed = fields.Float('Base gravada', readonly=True)
