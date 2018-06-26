# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PaymentRequestLines(models.Model):
    _name = 'eliterp.payment.request.lines'

    _description = 'Líneas de requerimiento de pago'

    payment_request_id = fields.Many2one('eliterp.payment.request', string="Requerimiento de pago")
    detail = fields.Char('Detalle', required=True)
    amount = fields.Float('Monto', required=True)


class PaymentRequest(models.Model):
    _name = 'eliterp.payment.request'

    _description = 'Requerimiento de pago'

    @api.depends('lines_request')
    @api.one
    def _get_total(self):
        """
        Total de líneas de solicitud
        """
        self.total = round(sum(line.amount for line in self.lines_request), 2)

    @api.multi
    def approve(self):
        """
        Aprobar solicitud
        """
        self.write({
            'state': 'approve',
            'approval_user': self._uid,
        })

    @api.multi
    def deny(self):
        """
        Negar solicitud
        """
        self.write({
            'state': 'deny'
        })

    @api.multi
    def to_approve(self):
        """
        Solicitar aprobación
        """
        for request in self:
            if not request.lines_request:
                raise UserError('No existen líneas en solicitud.')
        self.write({
            'state': 'to_approve',
            'name': self.env['ir.sequence'].sudo().next_by_code('payment.request')
        })

    name = fields.Char('No. Documento', default='Nueva solicitud', copy=False)
    application_date = fields.Date('Fecha solicitud', default=fields.Date.context_today, required=True, readonly=True,
                                   states={'draft': [('readonly', False)]})
    payment_date = fields.Date('Fecha de pago', default=fields.Date.context_today, required=True, readonly=True,
                               states={'draft': [('readonly', False)]})
    beneficiary = fields.Char('Titular', required=True, readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('to_approve', 'A aprobar'),
        ('approve', 'Aprobada'),
        ('paid', 'Pagada'),
        ('deny', 'Negada'), ], "Estado", default='draft', copy=False)
    comments = fields.Text('Notas y comentarios')
    document = fields.Binary('Documento', attachment=True, copy=False)
    document_name = fields.Char('Nombre de documento', copy=False)
    lines_request = fields.One2many('eliterp.payment.request.lines', 'payment_request_id',
                                    string='Líneas de solicitud', readonly=True,
                                    states={'draft': [('readonly', False)]})
    total = fields.Float(compute='_get_total', string="Total", store=True)
    approval_user = fields.Many2one('res.users', 'Aprobado por', readonly=True, states={'draft': [('readonly', False)]},
                                    copy=False)
