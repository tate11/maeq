# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models, _
from datetime import date, datetime
from odoo.exceptions import UserError, ValidationError


class TypeDocument(models.Model):
    _name = 'eliterp.type.document'
    _description = 'Tipos de documento'

    @api.multi
    def name_get(self):
        res = []
        for data in self:
            res.append((data.id, "%s [%s]" % (data.name, data.code)))
        return res

    name = fields.Char('Nombre', required=True)
    code = fields.Char('Código', size=2, required=True)
    tax_support_ids = fields.Many2many('eliterp.tax.support',
                                       'relation_type_document_tax_support_ids',
                                       'type_document_id',
                                       'tax_support_id',
                                       string='Sustentos tributarios')
    have_authorization = fields.Boolean('Tiene autorización?', default=False,
                                        help='Marcar si el Tipo de documento tiene Autorización del SRI')
    _sql_constraints = [
        ('code_unique', 'unique (code)', 'El Código del Tipo de documento debe ser único.')
    ]


class TaxSupport(models.Model):
    _name = 'eliterp.tax.support'
    _description = 'Sustento tributario'
    _order = "code asc"

    @api.multi
    def name_get(self):
        res = []
        for data in self:
            res.append((data.id, "%s [%s]" % (data.name, data.code)))
        return res

    name = fields.Char('Nombre', required=True)
    code = fields.Char('Código', size=2, required=True)

    _sql_constraints = [
        ('code_unique', 'unique (code)', 'El Código del Sustento tributario debe ser único.')
    ]


class SriAuthorization(models.Model):
    _name = 'eliterp.sri.authorization'
    _description = 'Autorizaciones del SRI'

    @api.multi
    def name_get(self):
        res = []
        for data in self:
            res.append((data.id, "Documento %s [%s]" % (data.type_document.code, data.authorization)))
        return res

    @api.model
    @api.returns('self', lambda value: value.id)
    def create(self, values):
        result = self.search([
            ('company_id', '=', values['company_id']),
            ('type_document', '=', values['type_document']),
            ('establishment', '=', values['establishment']),
            ('emission_point', '=', values['emission_point']),
            ('active', '=', True)
        ])
        if result:
            MESSAGE = 'Ya existe una Autorización activa para %s-%s.' % (
                values['establishment'], values['emission_point'])
            raise UserError(_(MESSAGE))
        partner_id = self.env.user.company_id.partner_id.id
        if values['company_id'] == partner_id:
            authorization = values['authorization']
            number_next = values['initial_number']
            new_sequence = self.env['ir.sequence'].sudo().create({
                'name': "Secuencia de autorización " + authorization,
                'number_next': number_next,
                'code': authorization,
                'prefix': values['establishment'] + "-" + values['emission_point'] + "-",
                'padding': 9
            })
            values.update({'sequence_id': new_sequence.id})
        return super(SriAuthorization, self).create(values)

    @api.one
    @api.depends('expiration_date')
    def _get_status(self):
        """
        Confirmamos si la Autorización del SRI está vencida
        :return: self
        """
        if not self.expiration_date:
            return
        self.active = date.today() < datetime.strptime(self.expiration_date, '%Y-%m-%d').date()

    @api.multi
    def unlink(self):
        """
        Al borrar Autorización verificar no existan documentos asociados
        """
        invoices = self.env['account.invoice']
        res = invoices.search([('sri_authorization_id', '=', self.id)])
        if res:
            raise ValidationError("Está Autorización está relacionada a un documento.")
        return super(SriAuthorization, self).unlink()

    def _get_company(self):
        return self.env.user.company_id

    def is_valid_number(self, number):
        """
        Verificar si el número de la secuencia es válido
        :param number:
        :return: boolean
        """
        if self.initial_number <= number <= self.final_number:
            return True
        return False

    establishment = fields.Char('No. Establecimiento', size=3, default='001', required=True)
    emission_point = fields.Char('Punto emisión', size=3, default='001', required=True)
    initial_number = fields.Integer('No. inicial', default=1, required=True)
    final_number = fields.Integer('No. final', required=True)
    authorization = fields.Char('No. Autorización', required=True)
    type_document = fields.Many2one('eliterp.type.document', 'Tipo de documento',
                                    domain=[('have_authorization', '=', True)], required=True)
    expiration_date = fields.Date('Fecha de expiración', required=True)
    active = fields.Boolean('Activo?', compute='_get_status', store=True)
    company_id = fields.Many2one('res.company', string='Compañía', required=True, default=_get_company)
    sequence_id = fields.Many2one('ir.sequence', 'Secuencia')
    is_electronic = fields.Boolean('Es electónica?', default=False)  # TODO

    _sql_constraints = [(
        'sri_authorization_unique',
        'unique (type_document,establishment,emission_point)',
        'Ya existe una Autorización activa del SRI para estos parámetros.'
    )]


class WayPay(models.Model):
    _name = 'eliterp.way.pay'
    _description = 'Forma de pago'
    _order = "code asc"

    @api.multi
    def name_get(self):
        res = []
        for data in self:
            res.append((data.id, "%s [%s]" % (data.name, data.code)))
        return res

    name = fields.Char('Nombre', required=True)
    code = fields.Char('Código', size=2, required=True)

    _sql_constraints = [
        ('code_unique', 'unique (code)', 'El Código de Forma de pago debe ser único.')
    ]


class ResCompany(models.Model):
    _inherit = 'res.company'

    authorization_ids = fields.One2many(
        'eliterp.sri.authorization',
        'company_id',
        string='Autorizaciones del SRI'
    )

    @api.multi
    def _get_authorisation(self, type_document):
        """
        Obtenemos la autorización del SRI por código de documento
        :param type_document:
        """
        map_type = {
            'out_refund': '04',
            'retention_in_invoice': '07',
            'out_invoice': '18',
        }
        code = map_type[type_document]
        for authorisation in self.authorization_ids:
            if authorisation.active and authorisation.type_document.code == code:
                return authorisation
        return False


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    ISSUANCE_DOCUMENTS = ['out_invoice', 'out_refund']  # Factura de venta, Nota de crédito en venta...

    @api.onchange('journal_id', 'sri_authorization_id')
    def _onchange_journal_id(self):
        """
        Obtener la el número de la secuencia del documento
        :return: self
        """
        super(AccountInvoice, self)._onchange_journal_id()
        if self.journal_id and self.type in self.ISSUANCE_DOCUMENTS:
            authorisation = self.env.user.company_id._get_authorisation(self.type)
            if authorisation:
                if self.type == 'out_invoice':
                    self.sri_authorization_id = authorisation.id
                elif self.type == 'out_refund':
                    self.sri_authorization_id = authorisation.id
                self.authorization = not self.sri_authorization_id.is_electronic and self.sri_authorization_id.authorization
                number = '{0}'.format(str(self.sri_authorization_id.sequence_id.number_next_actual).zfill(9))
                self.reference = number
        else:
            self.sri_authorization_id = False

    @api.one
    @api.depends('sri_authorization_id', 'reference')
    def _compute_invoice_number(self):
        """
        Calcular el número de documento
        :return: self
        """
        if self.reference:
            self.invoice_number = '{0}-{1}-{2}'.format(
                self.sri_authorization_id.establishment if self.sri_authorization_id else self.establishment,
                self.sri_authorization_id.emission_point if self.sri_authorization_id else self.emission_point,
                self.reference
            )
        else:
            self.invoice_number = False

    @api.onchange('reference')
    def _onchange_reference(self):
        """
        Validar número para rango de Autorización
        """
        if self.reference:
            self.reference = self.reference.zfill(9)
            if not self.sri_authorization_id.is_valid_number(
                    int(self.reference)) and self.type in self.ISSUANCE_DOCUMENTS:
                return {
                    'value': {
                        'reference': ''
                    },
                    'warning': {
                        'title': 'Error',
                        'message': 'Número no coincide con la autorización ingresada.'
                    }
                }

    @api.constrains('authorization')
    def _check_authorization(self):
        """
        Verificar la longitud de la autorización
        10: Documento físico
        35: Documento electrónico, online
        49: Documento electrónico, offline
        """
        if self.type not in ['in_invoice']:
            return
        if self.authorization and len(self.authorization) not in [10, 35, 49]:
            raise ValidationError('Debe ingresar 10, 35 o 49 dígitos según el documento.')

    def _default_way_pay(self):
        """
        Obtenemos forma de pago por defecto mayor
        """
        return self.env['eliterp.way.pay'].search([])[0].id

    def _default_tax_support(self):
        """
        Obtenemos sustento tributario por defecto
        """
        type = self._context.get('type')
        if type in ['in_invoice', 'in_refund']:
            return self.env['eliterp.tax.support'].search([])[0].id

    way_pay_id = fields.Many2one('eliterp.way.pay', string='Forma de pago', default=lambda self: self._default_way_pay()
                                 , readonly=True, states={'draft': [('readonly', False)]})
    sri_authorization_id = fields.Many2one('eliterp.sri.authorization', string='Autorización del SRI', copy=False)
    authorization = fields.Char('No. Autorización')
    invoice_number = fields.Char('No. Factura', compute='_compute_invoice_number', store=True, readonly=True,
                                 copy=False)
    tax_support_id = fields.Many2one('eliterp.tax.support', string='Sustento tributario', default=lambda self: self._default_tax_support())
    # Campos para documentos no emitidos por Companía
    establishment = fields.Char('No. Establecimiento', size=3, default='001')
    emission_point = fields.Char('Punto emisión', size=3, default='001')

    _sql_constraints = [(
        'invoice_unique', 'unique (invoice_number, type, state)',
        'El No. Factura es único por autorización y empresa.'
    )]
