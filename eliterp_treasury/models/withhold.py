# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def add_withhold(self):
        """
        Abrir ventana emergente para crear retención en compra
        :return: dict
        """
        view = self.env.ref('eliterp_treasury.eliterp_view_withhold_purchase_wizard')
        context = {
            'default_invoice_id': self.id,
            'default_partner_id': self.partner_id.id,
            'default_type': 'purchase',
            'default_base_iva': self.amount_tax,
            'default_base_taxable': self.amount_untaxed
        }
        return {
            'name': "Retención en compra",
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'eliterp.withhold',
            'view_id': view.id,
            'target': 'new',
            'context': context,
        }

    @api.multi
    def open_withhold(self):
        """
        Abrimos retención relacionada a factura
        :return: self
        """
        withhold = self.env['eliterp.withhold'].search([('invoice_id', '=', self.id)])
        imd = self.env['ir.model.data']
        if self.type == 'out_invoice':
            action = imd.xmlid_to_object('eliterp_treasury.eliterp_action_withhold_sale')
            list_view_id = imd.xmlid_to_res_id('eliterp_treasury.eliterp_view_tree_withhold_sale')
            form_view_id = imd.xmlid_to_res_id('eliterp_treasury.eliterp_view_form_withhold_sale')
        else:
            action = imd.xmlid_to_object('eliterp_treasury.eliterp_action_withhold_purchase')
            list_view_id = imd.xmlid_to_res_id('eliterp_treasury.eliterp_view_form_withhold_purchase')
            form_view_id = imd.xmlid_to_res_id('eliterp_treasury.eliterp_view_form_withhold_purchase')
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[list_view_id, 'tree'], [form_view_id, 'form']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        if len(withhold) > 1:
            result['domain'] = "[('id','in',%s)]" % withhold.ids
        elif len(withhold) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = withhold.ids[0]
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result

    have_withhold = fields.Boolean('Tiene retención?', default=False, copy=False)
    withhold_id = fields.Many2one('eliterp.withhold', string='Retención', copy=False)
    withhold_number = fields.Char('No. Retención', related='withhold_id.withhold_number')


class LinesWithhold(models.Model):
    _name = 'eliterp.lines.withhold'

    _description = 'Líneas de retención'

    @api.onchange('retention_type')
    def _onchange_retention_type(self):
        """
        Calculamos la Base imponible al cambiar de tipo
        :return: self
        """
        if not self.retention_type:
            return
        if self.retention_type == 'iva':
            self.base_taxable = self.withhold_id.base_iva
        if self.retention_type == 'rent':
            self.base_taxable = self.withhold_id.base_taxable

    @api.onchange('tax_id')
    def _onchange_tax_id(self):
        """
        Calculamos el monto a cambiar de Impuesto
        :return: self
        """
        self.amount = (self.tax_id.amount * self.base_taxable) / 100

    retention_type = fields.Selection([('iva', 'IVA'), ('rent', 'Renta')], string='Tipo de retención', required=True)
    tax_id = fields.Many2one('account.tax', string='Impuesto', required=True)
    base_taxable = fields.Float('Base imponible')
    amount = fields.Float('Monto')
    withhold_id = fields.Many2one('eliterp.withhold', string='Retención')
    retention_tax_id = fields.Many2one('account.invoice.tax', string='Impuesto de retención')


class WithholdCancelReason(models.TransientModel):
    _name = 'eliterp.withhold.cancel.reason'

    _description = 'Razón para cancelar retención'

    @api.multi
    def confirm_cancel_withhold(self):
        """
        Confirmamos la cancelación de la retención
        """
        withhold = self.env['eliterp.withhold'].browse(self._context['active_id'])
        withhold.move_id.with_context(from_withhold=True).reverse_moves(
            withhold.date_withhold,
            withhold.journal_id or False
        )
        withhold.move_id.write({
            'state': 'cancel',
            'ref': self.description
        })
        withhold.cancel_withhold()
        return True

    description = fields.Text('Descripción', required=True)


class Withhold(models.Model):
    _name = 'eliterp.withhold'

    _description = 'Retención'

    @api.multi
    def open_withhold_cancel_reason(self):
        """
        Abrimos ventana emergente para cancelar retención
        :return:self
        """
        context = dict(self._context or {})
        if self.state == 'draft':  # Cancelamos la retención si está en estado Borrador
            return self.cancel_withhold()
        else:
            return {
                'name': "Explique la razón",
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'eliterp.withhold.cancel.reason',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': context,
            }

    @api.multi
    def cancel_withhold(self):
        """
        Cancelamos la retención de venta
        :return: boolean
        """
        self.invoice_id.write({
            'withhold_id': False,
            'have_withhold': False
        })
        if not self.lines_withhold:
            return
        invoice_tax = self.env['account.invoice.tax'].search([
            ('invoice_id', '=', self.invoice_id.id),
            ('name', '=', self.lines_withhold.tax_id.name),
            ('tax_id', '=', self.lines_withhold.tax_id.id),
            ('account_id', '=', self.lines_withhold.tax_id.account_id.id)
        ])[0]
        invoice_tax.unlink()
        self.invoice_id._compute_amount()
        self.invoice_id._compute_residual()
        self.write({
            'state': 'cancel',
            'withhold_number': "Cancelado [%s]" % (self.withhold_number)
        })
        return True

    @api.multi
    def print_withhold_purchase(self):
        """
        Imprimir Retención en compra
        """
        self.ensure_one()
        return self.env.ref('eliterp_treasury.action_report_withhold_purchase').report_action(self, config=False)

    @api.multi
    def confirm_withhold(self):
        """
        Confirmamos la retención
        :return: self        """

        move_id = self.env['account.move'].create({
            'journal_id': self.journal_id.id,
            'ref': "Retención de factura [%s]" % (self.invoice_id.invoice_number),
            'date': self.date_withhold
        })
        line_move_withhold = self.env['account.move.line'].with_context(check_move_validity=False).create({
            'name': self.partner_id.name,
            'journal_id': self.journal_id.id,
            'partner_id': self.invoice_id.partner_id.id,
            'account_id': self.partner_id.property_account_receivable_id.id,
            'move_id': move_id.id,
            'credit': self.total,
            'debit': 0.0,
            'date': self.date_withhold
        })
        count = len(self.lines_withhold)
        for line in self.lines_withhold:
            count -= 1
            if count == 0:
                move_line = self.env['account.move.line']
            else:
                move_line = self.env['account.move.line'].with_context(check_move_validity=False)
            move_line.create({
                'name': line.tax_id.name,
                'account_id': line.tax_id.account_id.id,
                'partner_id': self.invoice_id.partner_id.id,
                'journal_id': self.journal_id.id,
                'move_id': move_id.id,
                'credit': 0.0,
                'debit': line.amount,
                'date': self.date_withhold
            })
        move_id.post()
        self.name = move_id.name
        line_move_invoice = self.invoice_id.move_id.line_ids.filtered(
            lambda x: x.account_id == self.partner_id.property_account_receivable_id)
        (line_move_invoice + line_move_withhold).reconcile()
        self.invoice_id._compute_amount()
        self.invoice_id._compute_residual()
        return self.write({
            'state': 'confirm',
            'move_id': move_id.id
        })

    @api.one
    @api.depends('lines_withhold')
    def _get_total_lines(self):
        """
        Calculamos el total de la retención
        """
        self.total = sum(line.amount for line in self.lines_withhold)

    @api.onchange('invoice_id')
    def _onchange_invoice_id(self):
        """
        Al cambiar de factura, cambiamos son valores bases
        """
        self.base_taxable = self.invoice_id.amount_untaxed
        self.base_iva = self.invoice_id.amount_tax

    @api.multi
    def write(self, values):
        if 'lines_withhold' in values:
            for line in values['lines_withhold']:
                if line[0] == 0:
                    retention = self.env['account.tax'].browse(line[2]['tax_id'])
                    amount = line[2]['amount'] if 'amount' in line[2] else 0.00
                    self.env['account.invoice.tax'].create({
                        'invoice_id': self.invoice_id.id,
                        'name': retention.name,
                        'tax_id': retention.id,
                        'account_id': retention.account_id.id,
                        'amount': -1 * amount
                    })
                if line[0] == 1:
                    tax_id = self.env['account.tax'].browse(line[2]['tax_id'])
                    if self.lines_withhold.tax_id:
                        self.lines_withhold.tax_id.write({
                            'name': tax_id.name,
                            'tax_id': tax_id.id,
                            'account_id': tax_id.account_id.id,
                            'amount': line[2]['amount'] if 'amount' in line[2] else 0.00
                        })
                    else:
                        line_withhold = self.lines_withhold.browse(line[1])
                        amount = line[2]['monto'] if 'monto' in line[2] else 0.00
                        invoice_tax = self.env['account.invoice.tax'].search([('invoice_id', '=', self.invoice_id.id),
                                                                              ('name', '=',
                                                                               line_withhold.tax_id.name),
                                                                              ('tax_id', '=',
                                                                               line_withhold.tax_id.id),
                                                                              ('account_id', '=',
                                                                               line_withhold.tax_id.account_id.id)])[
                            0]
                        invoice_tax.write({
                            'name': tax_id.name,
                            'tax_id': tax_id.id,
                            'account_id': tax_id.account_id.id,
                            'amount': -1 * amount
                        })
                if line[0] == 2:
                    if not self.modified_bill:
                        if self.lines_withhold.tax_id:
                            self.lines_withhold.tax_id.unlink()
                        else:
                            line_withhold = self.lines_withhold.browse(line[1])
                            invoice_tax = \
                                self.env['account.invoice.tax'].search([('invoice_id', '=', self.invoice_id.id),
                                                                        ('name', '=', line_withhold.tax_id.name),
                                                                        ('tax_id', '=', line_withhold.tax_id.id),
                                                                        ('account_id', '=',
                                                                         line_withhold.tax_id.account_id.id)])[0]
                            invoice_tax.unlink()
                    else:
                        values.update({'modified_bill': False})
            self.invoice_id._compute_amount()
            self.invoice_id._compute_residual()
        return super(Withhold, self).write(values)

    @api.model
    def create(self, values):
        self.env['eliterp.global.functions'].valid_period(values[
                                                              'date_withhold'])  # Verificamos Período contable sea correcto
        if values['type'] == 'purchase':
            if values['is_sequential']:
                authorisation = self.env.user.company_id._get_authorisation(
                    'retention_in_invoice')  # TODO revisar si es la mejor opción
                if not authorisation:
                    raise UserError(_("No hay Autorización del SRI para Retención en compra."))
                else:
                    values.update({'withhold_number': authorisation[0].sequence_id.next_by_id()})
            if 'is_sequential' in values:  # Consecutivo con código de procesos internos
                if not values['is_sequential']:
                    values.update({
                        'withhold_number': self.env['ir.sequence'].next_by_code('internal.process')
                    })
        invoice = self.env['account.invoice'].browse(values['invoice_id'])
        withhold = super(Withhold, self).create(values)
        invoice.write({
            'have_withhold': True,
            'withhold_id': withhold.id
        })
        invoice_tax = self.env['account.invoice.tax']
        for line in withhold.lines_withhold:
            tax_id = invoice_tax.create({
                'invoice_id': invoice.id,
                'name': line.tax_id.name,
                'tax_id': line.tax_id.id,
                'account_id': line.tax_id.account_id.id,
                'amount': -1 * line.amount
            })
            line.write({'retention_tax_id': tax_id.id})
        invoice._compute_amount()
        return withhold

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super(Withhold, self).fields_get(allfields=allfields, attributes=attributes)
        if 'partner_id' in res and 'default_type' in self.env.context:
            if self.env.context['default_type'] == 'sale':
                res['partner_id']['string'] = 'Cliente'
            if self.env.context['default_type'] == 'purchase':
                res['partner_id']['string'] = 'Proveedor'
        return res

    def _default_journal(self):
        """
        Definimos el diario por defecto
        """
        if self._context['default_type'] == 'sale':
            return self.env['account.journal'].search([('name', '=', 'Retención en venta')])[0].id
        else:
            return self.env['account.journal'].search([('name', '=', 'Retención en compra')])[0].id

    @api.multi
    def copy(self, default=None):
        """
        Evitamos duplicar el registro, no se puede por motivos qué se liga la Factura a la misma
        :param default:
        """
        raise UserError(_("No se puede duplicar una retención, tiene qué crearla con"
                          " relación a la Factura."))

    @api.multi
    def unlink(self):
        """
        Verificar antes de borrar el registro
        :return: object
        """
        for withhold in self:
            if withhold.state == 'confirm':
                raise UserError(_("No se puede eliminar una retención en estado confirmada."))
            else:
                # TODO: Falta eliminar las líneas de impuestos de la retención
                withhold.invoice_id.have_withhold = False
                withhold.invoice_id.withhold_id = False
        return super(Withhold, self).unlink()

    name = fields.Char('Nombre', default='Nueva retención')
    withhold_number = fields.Char('No. Retención')
    base_taxable = fields.Float('Base imponible')
    base_iva = fields.Float('Base IVA')
    date_withhold = fields.Date('Fecha de emisión', default=fields.Date.context_today, required=True)
    partner_id = fields.Many2one('res.partner', string='Cliente/Proveedor')
    invoice_id = fields.Many2one('account.invoice', string='Factura')
    type = fields.Selection([('sale', 'Venta'), ('purchase', 'Compra')], string='Aplicado a')
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirm', 'Confirmada'),
        ('cancel', 'Cancelada')
    ], string='Estado', default='draft')
    lines_withhold = fields.One2many('eliterp.lines.withhold', 'withhold_id', string='Líneas de retención')
    total = fields.Float(compute='_get_total_lines', string='Total')
    is_sequential = fields.Boolean('Es secuencial?',
                                   help="Si se marca, a la hora de validar la factura creará un consecutivo con Autorización del SRI")
    journal_id = fields.Many2one('account.journal', string='Diario', default=_default_journal, readonly=True)
    move_id = fields.Many2one('account.move', string='Asiento contable')
    modified_bill = fields.Boolean('Factura modificada?', default='False')

    _sql_constraints = [
        ('withhold_number_unique', 'unique (withhold_number)',
         "El No. Retención ya está registrado.")
    ]
