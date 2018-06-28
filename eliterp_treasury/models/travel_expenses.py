# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models
from odoo.exceptions import ValidationError, UserError
import json

CONCEPTS = [
    ('alimentation', 'ALIMENTACIÓN'),
    ('lodging', 'HOSPEDAJE'),
    ('gas', 'COMBUSTIBLE'),
    ('others', 'OTROS')
]


class ViaticalConcepts(models.Model):
    _name = 'eliterp.viatical.concepts'

    _description = 'Conceptos de viático'

    @api.model
    def name_get(self):
        result = []
        for data in self:
            row = list(filter(lambda x: x[0] == data.name, CONCEPTS))
            result.append((data.id, "%s" % row[0][1]))
        return result

    @api.constrains('max_amount')
    def _check_amount(self):
        """
        Verificamos qué el valor sea mayor a 0
        """
        if not self.max_amount > 0:
            raise ValidationError("El monto debe ser mayor a 0.")

    name = fields.Selection(CONCEPTS, 'Concepto', default='alimentation', required=True)
    account_id = fields.Many2one('account.account', string="Cuenta contable",
                                 domain=[('account_type', '=', 'movement')], required=True)
    max_amount = fields.Float('Monto máximo (Diario)')

    _sql_constraints = [
        ('name_unique', 'unique (name)', "Ya existe un concepto creado de viáticos.")
    ]


class TravelDestinations(models.Model):
    _name = 'eliterp.travel.destinations'

    _description = 'Destinos para viático'

    name = fields.Many2one('eliterp.parish', 'Destino', required=True)
    distance = fields.Float('Distancia', required=True)
    amount = fields.Float('Monto', help="Monto aproximado de la cantidad de dinero gastado según KM's")


class ViaticalConceptsLine(models.Model):
    _name = 'eliterp.viatical.concepts.line'

    _description = 'Línea de conceptos para viático'

    @api.one
    @api.depends('daily_value', 'days', 'number_of_people')
    def _get_total(self):
        """
        Obtenemos el total de la línea
        """
        self.total = round(float(self.daily_value * self.days * self.number_of_people), 2)

    @api.onchange('viatical_concepts_id')
    def _onchange_viatical_concepts_id(self):
        """
        Al cambiar de conceptos si está marcado combustible y es ida y vuelta
        """
        if self.viatical_concepts_id.name == 'gas':
            destination = self.travel_allowance_request_id.destination
            if self.travel_allowance_request_id.round_trip:
                self.daily_value = destination.amount * 2
            else:
                self.daily_value = destination.amount
        else:
            self.daily_value = self.viatical_concepts_id.max_amount

    viatical_concepts_id = fields.Many2one('eliterp.viatical.concepts', string="Concepto", required=True)
    travel_allowance_request_id = fields.Many2one('eliterp.travel.allowance.request', string="Solicitud")
    daily_value = fields.Float('Valor diario')
    days = fields.Integer('No. días', default=1)
    number_of_people = fields.Integer('No. personas', default=1)
    total = fields.Float('Total', compute='_get_total')


class TravelAllowanceRequest(models.Model):
    _name = 'eliterp.travel.allowance.request'

    _description = 'Solicitud de viáticos'

    _inherit = ['mail.thread']

    @api.multi
    def print_request(self):
        """
        Imprimimos solicitud
        """
        self.ensure_one()
        return self.env.ref('eliterp_treasury.eliterp_action_report_travel_allowance_request').report_action(self)

    @api.one
    @api.depends('application_lines')
    def _get_amount_total(self):
        """
        Obtenemos el total de las líneas para solicitud
        """
        if self.have_request:
            self.amount_total = sum(line.total for line in self.application_lines)

    @api.model
    def create(self, values):
        """
        TODO: Al crear si no tenemos solicitud se crea sin nombre
        :param values:
        :return: object
        """
        if values['have_request']:
            object_sequence = self.env['ir.sequence']
            viaticum = super(TravelAllowanceRequest, self).create(values)
            viaticum.name = object_sequence.next_by_code('travel.allowance.request')
        else:
            viaticum = super(TravelAllowanceRequest, self).create(values)
        return viaticum

    @api.multi
    def approve(self):
        """
        Aprobar solicitud
        """
        self.write({
            'state': 'approve',
            'approval_user': self.env.uid
        })

    @api.multi
    def to_approve(self):
        """
        Solicitar aprobación
        """
        if not self.application_lines:
            raise ValidationError("No tiene línea de conceptos creadas para solicitud.")
        self.write({
            'state': 'to_approve'
        })

    @api.model
    def _default_employee(self):
        """
        Obtenemos el empleado por defecto del usuario
        """
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

    name = fields.Char('No. Documento', copy=False, default='Nueva solicitud')
    application_date = fields.Date('Fecha de solicitud', default=fields.Date.context_today, required=True)
    trip_date = fields.Date('Fecha de viaje', default=fields.Date.context_today, required=True)
    beneficiary = fields.Many2one('hr.employee', string='Beneficiario', required=True,
                                  default=_default_employee)
    destination = fields.Many2one('eliterp.travel.destinations', string='Destino', required=True)
    account_analytic_id = fields.Many2one('account.analytic.account', domain=[('usage', '=', 'movement')], string="Centro de costo")
    project_id = fields.Many2one('eliterp.project', 'Proyecto')
    reason = fields.Char('Motivo', required=True)
    amount_total = fields.Float(compute='_get_amount_total', string="Monto total", store=True)
    approval_user = fields.Many2one('res.users', 'Aprobado por')
    round_trip = fields.Boolean('Ida y vuelta?', default=False)
    reason_deny = fields.Text('Negado por')
    have_request = fields.Boolean('Tiene solicitud?', default=True)  # TODO
    application_lines = fields.One2many('eliterp.viatical.concepts.line', 'travel_allowance_request_id',
                                        string='Línea de conceptos')
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('to_approve', 'A aprobación'),
        ('approve', 'Aprobada'),
        ('managed', 'Gestionada'),
        ('liquidated', 'Liquidada'),
        ('deny', 'Negada')
    ], "Estado", default='draft')
    # TODO: Campos para crear sin solicitud de viático
    number_days = fields.Integer('No. días')
    number_of_people = fields.Integer('No. personas')


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.model
    def create(self, vals):
        if 'active_model' in self._context:  # Verificamos modelo activo
            # Comprobante de viático
            if self._context['active_model'] == 'eliterp.voucher.viatic':
                vals.update({
                    'viaticum': True,
                    'voucher_viaticum_id': self._context['active_id']
                })
                self.env['eliterp.voucher.viatic'].browse(self._context['active_id']).write({
                    'has_invoice': True
                })
        return super(AccountInvoice, self).create(vals)

    voucher_viaticum_id = fields.Many2one('eliterp.voucher.viatic', 'Comprobante viático')
    viaticum = fields.Boolean('Viático?', default=False)


class VoucherViatic(models.Model):
    _name = 'eliterp.voucher.viatic'

    _description = 'Comprobante de viático'

    @api.multi
    def print_voucher(self):
        """
        Imprimir comprobante
        """
        self.ensure_one()
        pass

    @api.one
    def confirm_voucher(self):
        """
        Confirmamos qué voucher este correctamente llenado y lo confirmamos,
        si es factura se debe ver qué este validada
        """
        if self.type_voucher == 'invoice':
            invoice = self.env['account.invoice'].search([('voucher_viaticum_id', '=', self.id)])[0]
            if invoice.state == 'draft':
                raise UserError("Se debe validar la factura No. %s" % invoice.invoice_number)
        return self.write({
            'state': 'confirm',
            'name': self.journal_id.sequence_id.next_by_id()
        })

    @api.model
    def _default_journal(self):
        """
        Obtenemos diario por defecto
        """
        return self.env['account.journal'].search([('name', '=', 'Comprobante viático')], limit=1)[0].id

    @api.multi
    def view_invoice(self):
        """
        Revisamos la factura creada
        :return: dict
        """
        invoice = self.env['account.invoice'].search([('voucher_viaticum_id', '=', self.id)])
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
        context.update({'default_viaticum': True})
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
    @api.depends('type_voucher')
    def _get_amount_total(self):
        """
        Obtenemos el total del comprobante
        """
        if self.type_voucher == 'vale':
            self.amount_total = self.amount_worth
        else:
            invoice = self.env['account.invoice'].search([('voucher_viaticum_id', '=', self.id)])
            if not invoice:
                self.amount_total = 0.00
            else:
                self.amount_total = invoice[0].amount_total

    name = fields.Char(string="No. Documento", copy=False)
    type_voucher = fields.Selection([('vale', 'Vale'), ('invoice', 'Factura')], string="Tipo", default='vale',
                                    readonly=True, states={'draft': [('readonly', False)]})
    travel_allowance_request_id = fields.Many2one('eliterp.travel.allowance.request', string="Solicitud")
    journal_id = fields.Many2one('account.journal', 'Diario', default=_default_journal)
    date = fields.Date('Fecha registro', default=fields.Date.context_today, required=True,
                       readonly=True, states={'draft': [('readonly', False)]})
    amount_total = fields.Float(string="Monto total", compute='_get_amount_total')
    amount_worth = fields.Float('Monto de vale', required=True)
    viatical_concepts_id = fields.Many2one('eliterp.viatical.concepts', string="Concepto", required=True
                                           , readonly=True, states={'draft': [('readonly', False)]})
    has_invoice = fields.Boolean('Tiene factura?', default=False, copy=False)
    state = fields.Selection([('draft', 'Borrador'), ('confirm', 'Confirmado'), ('not valid', 'No válido')],
                             string="Estado", default='draft')
    validate = fields.Boolean('Válidado?', default=False)  # TODO


class VoucherLiquidationSettlement(models.Model):
    _name = 'eliterp.voucher.liquidation.settlement'

    _description = 'Comprobante de viático en liquidación'

    name = fields.Char(string="No. Documento")
    voucher_viatic_id = fields.Many2one('eliterp.voucher.viatic', 'Comprobante de viático')
    type_voucher = fields.Selection([('vale', 'Vale'), ('invoice', 'Factura')], string="Tipo")
    liquidation_settlement_id = fields.Many2one('eliterp.liquidation.settlement', string="Liquidación")
    date = fields.Date('Fecha registro')
    amount_total = fields.Float("Monto total")
    viatical_concepts_id = fields.Many2one('eliterp.viatical.concepts', string="Concepto")
    type_validation = fields.Selection([
        ('none', '-'),
        ('not_approved', 'Monto no aprobado'),
        ('not_valid', 'Comprobante no válido'),
        ('assumes_company', 'Asume empresa')
    ], string="Tipo de validación", default='none')


class LiquidationSettlement(models.Model):
    _name = 'eliterp.liquidation.settlement'

    _description = 'Liquidación de viáticos'

    @api.multi
    def print_liquidation(self):
        """
        Imprimimos solicitud
        """
        self.ensure_one()
        return self.env.ref('eliterp_treasury.eliterp_action_report_liquidation_settlement').report_action(self)

    @api.model
    def _default_journal(self):
        return self.env['account.journal'].search([('name', '=', 'Liquidación de viático')], limit=1)[0].id

    def validate(self):
        for line in self.document_lines:
            if line.type_validation == 'none':
                raise UserError("Tiene documentos sin realizar la validación.")
        self.write({
            'state': 'validate'
        })

    def open_(self):
        return {
            'name': "Explique la Razón",
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'eliterp.provision.liquidate.cancel.reason',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {},
        }

    @api.multi
    def approve(self):
        self.write({
            'state': 'approve',
            'approval_user': self.env.uid
        })

    @api.multi
    def to_approve(self):
        """
        Aprobamos la liquidación
        """
        if not self.document_lines:
            raise UserError("No tiene líneas de documentos confirmadas o ingresadas.")
        self.write({
            'name': self.journal_id.sequence_id.next_by_id(),
            'state': 'to_approve'
        })

    @api.depends('document_lines')
    def _get_difference(self):
        """
        Calculamos la diferencia entre total de solicitud y registro de documentos
        """
        amount_total = sum(line['amount_total'] for line in self.document_lines)
        difference = self.travel_allowance_request_id.amount_total - amount_total
        self.difference = round(difference, 2)

    def liquidate(self):
        """
        Realizamos la liquidación
        """
        if not self.settlement_travel_expenses:
            raise UserError("No ha creado cuenta para liquidación de viáticos.")
        # TODO: Validamos qué el Benficiario tenga Cuenta
        account_employee = False
        if not account_employee:
            raise UserError(
                "No tiene cuenta asignada el Empleado(a): %s" % self.travel_allowance_request_id.beneficiary.name)
        list = []
        for line in self.document_lines:
            # Documento no válido
            if line.type_validation == 'not_valid':
                line.voucher_viatic_id.write({'state': 'not_valid'})
            # Asume empresa valor no aprobado
            else:
                account = False
                partner = False
                if line.type_voucher == 'invoice':
                    invoice = self.env['account.invoice'].search(
                        [('voucher_viaticum_id', '=', line.voucher_viatic_id.id)])
                    partner = invoice.partner_id.id
                    account = partner.account_id.id
                else:
                    account = line.viatical_concepts_id.account_id.id
                list.append({
                    # True -> Debe, False -> Haber
                    'type': True,
                    'partner': partner,
                    'name': line.viatical_concepts_id.name,
                    'account': account,
                    'amount': line.amount_total
                })
                list.append({
                    'type': False,
                    'partner': partner,
                    'name': line.viatical_concepts_id.name,
                    'account': self.settlement_travel_expenses.id,
                    'amount': line.amount_total
                })
            # Documentos ya procesados
            line.voucher_viatic_id.write({'validate': True})
        # Generamos Asiento contable
        move_id = self.env['account.move'].create({
            'journal_id': self.journal_id.id,
            'date': self.date
        })
        for register in list:
            # Línea del Debe
            if register['type']:
                self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'name': register['name'],
                    'journal_id': self.journal_id.id,
                    'partner_id': register['partner'],
                    'account_id': register['account'],
                    'move_id': move_id.id,
                    'debit': register['amount'],
                    'credit': 0.0,
                    'date': self.date
                })
            # Línea del Haber
            else:
                self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'name': register['name'],
                    'journal_id': self.journal_id.id,
                    'partner_id': register['partner'],
                    'account_id': register['account'],
                    'move_id': move_id.id,
                    'debit': 0.0,
                    'credit': register['amount'],
                    'date': self.date
                })
        if self.difference < 0:
            self.env['account.move.line'].with_context(check_move_validity=False).create({
                'name': self.settlement_travel_expenses.name,
                'journal_id': self.journal_id.id,
                'partner_id': False,
                'account_id': self.settlement_travel_expenses.id,
                'move_id': move_id.id,
                'debit': abs(self.difference),
                'credit': 0.0,
                'date': self.date
            })
            self.env['account.move.line'].with_context(check_move_validity=False).create({
                'name': account_employee.name,
                'journal_id': self.journal_id.id,
                'partner_id': False,
                'account_id': account_employee.id,
                'move_id': move_id.id,
                'debit': abs(self.difference),
                'credit': 0.0,
                'date': self.date
            })
            move_id.with_context(eliterp_moves=True, move_name=self.name).post()
        move_id.write({'ref': self.name})
        self.travel_allowance_request_id.write({'state': 'liquidated'})  # Cambiamos el estado de solicitud de viáticos
        self.write({
            'state': 'liquidated',
            'move_id': move_id.id
        })

    @api.multi
    def load_documents(self):
        """
        Cargamos los documentos confirmados y sin validar de solicitud
        """
        voucher_ids = self.env['eliterp.voucher.viatic'].search([
            ('travel_allowance_request_id', '=', self.travel_allowance_request_id.id),
            ('state', '=', 'confirm'),
            ('validate', '=', False)
        ])
        lines = []
        for voucher in voucher_ids:
            lines.append([0, 0, {'voucher_viatic_id': voucher.id,
                                 'name': voucher.name,
                                 'viatical_concepts_id': voucher.viatical_concepts_id,
                                 'type_voucher': voucher.type_voucher,
                                 'date': voucher.date,
                                 'amount_total': voucher.amount_total, }])
        return self.update({'document_lines': lines})

    name = fields.Char('No. Documento', copy=False)
    date = fields.Date('Fecha de documento', default=fields.Date.context_today, required=True)
    travel_allowance_request_id = fields.Many2one('eliterp.travel.allowance.request', string="Solicitud",
                                                  domain=[('state', '=', 'managed')])

    application_date = fields.Date(related='travel_allowance_request_id.application_date')
    trip_date = fields.Date(related='travel_allowance_request_id.trip_date')
    beneficiary = fields.Many2one(related='travel_allowance_request_id.beneficiary')
    destination = fields.Many2one(related='travel_allowance_request_id.destination')
    reason = fields.Char(related='travel_allowance_request_id.reason')
    amount_total = fields.Float(related='travel_allowance_request_id.amount_total')

    approval_user = fields.Many2one('res.users', 'Aprobado por')
    move_id = fields.Many2one('account.move', string='Asiento contable')
    journal_id = fields.Many2one('account.journal', string="Diario", default=_default_journal)
    reason_deny = fields.Text('Negado por')
    comment = fields.Text('Notas y comentarios')
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('to_approve', 'A aprobar'),
        ('approve', 'Aprobada'),
        ('validate', 'Validada'),
        ('liquidated', 'Liquidada'),
        ('deny', 'Negada')
    ], "Estado", default='draft')
    document_lines = fields.One2many('eliterp.voucher.liquidation.settlement', 'liquidation_settlement_id',
                                     "Comprobantes")
    difference = fields.Float('Diferencia', compute='_get_difference', store=True)
    # Está cuenta sirve para liquidar viáticos
    settlement_travel_expenses = fields.Many2one('account.account', string="Cuenta contable")
