# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models
from odoo.exceptions import UserError
from datetime import datetime

class Employee(models.Model):
    _inherit = 'hr.employee'

    account_advance_payment = fields.Many2one('account.account', string="Cuenta anticipo",
                                              domain=[('account_type', '=', 'movement')])


class LinesAdvancePayment(models.Model):
    _name = 'eliterp.lines.advance.payment'

    _description = 'Líneas de anticipo de quincena'

    @api.one
    def _get_total(self):
        """
        Total de línea
        """
        self.amount_total = round(self.amount_advance + self.mobilization, 2)

    employee_id = fields.Many2one('hr.employee', string='Empleado')
    job_id = fields.Many2one('hr.job', string='Cargo', related='employee_id.job_id', store=True)
    admission_date = fields.Date(related='employee_id.admission_date', store=True, string='Fecha ingreso')
    account_id = fields.Many2one('account.account', string="Cuenta", domain=[('account_type', '=', 'movement')])
    amount_advance = fields.Float('Monto', default=0.00)
    mobilization = fields.Float(string='Movilización')
    antiquity = fields.Integer('Días')
    amount_total = fields.Float('Total', compute='_get_total')
    advanced_id = fields.Many2one('eliterp.advance.payment', 'Anticipo')


class ReasonDenyAdvance(models.TransientModel):
    _name = 'eliterp.reason.deny.advance'

    _description = 'Razón para negar anticipo de quincena'

    description = fields.Text('Descripción', required=True)

    @api.multi
    def deny_advance(self):
        """
        Cancelamos el anticipo de quincena
        """
        advance_id = self.env['eliterp.advance.payment'].browse(self._context['active_id'])
        advance_id.update({
            'state': 'deny',
            'reason_deny': self.description
        })
        return advance_id


class AdvancePayment(models.Model):
    _name = 'eliterp.advance.payment'

    _description = 'Anticipo de quincena'

    @api.model
    def _default_account(self):
        """
        Cuenta por defecto de nómina en empleado
        """
        account = self.env['account.account'].search([('name', '=', 'NÓMINA POR PAGAR')], limit=1)
        return account[0].id if account else False

    @api.multi
    def print_advance(self):
        """
        Imprimimos anticipo
        """
        self.ensure_one()
        return self.env.ref('eliterp_hr.eliterp_action_report_advance_payment').report_action(self)

    def _get_antiquity(self, employee):
        """
        Obtener días de antiguedad con fecha de documento
        :param employee:
        :return: integer
        """
        start_date = datetime.strptime(employee.admission_date, '%Y-%m-%d')
        end_date = datetime.strptime(self.date, '%Y-%m-%d')
        time = (str(end_date - start_date)).strip(', 0:00:00')
        days = 0
        if time:
            days = int("".join([x for x in time if x.isdigit()]))
        return days

    def load_employees(self):
        """
        Cargamos empleados para total de anticipo, debe tener un contrato el empleado
        """
        if self.lines_advance:
            self.lines_advance.unlink()  # Borramos líneas anteriores, no montar
        list_employees = []
        for employee in self.env['hr.employee'].search([
            ('active', '=', True),
            ('contract_id', '!=', False)
        ]):
            amount_advance = 0.0  # Para MAEQ se trabajará así por el momento la variable está configurada en Ajustes RRHH
            antiquity = self._get_antiquity(employee)
            if antiquity >= self.advance_days:
                amount_advance = round(float((employee.wage * 40) / 100), 2)
            else:
                amount_advance = 80.0
            list_employees.append([0, 0, {
                'employee_id': employee.id,
                'account_id': employee.account_advance_payment.id,
                'antiquity': antiquity,
                'mobilization': round(employee.mobilization / 2, 2),
                'amount_advance': amount_advance,
            }])
        return self.write({'lines_advance': list_employees})

    @api.one
    @api.depends('lines_advance')
    def _get_total(self):
        """
        Total de líneas de anticipo
        """
        self.total = sum(line.amount_total for line in self.lines_advance)

    @api.multi
    def to_approve(self):
        """
        Solicitar aprobación de anticipo de quincena
        """
        if not self.lines_advance:
            raise UserError("No hay líneas de anticipo creadas.")
        self.update({'state': 'to_approve'})

    @api.multi
    def reviewed(self):
        """
        Revisado
        """
        self.update({
            'state': 'reviewed',
            'reviewed_user': self._uid
        })

    @api.multi
    def approve(self):
        """
        Aprobar anticipo de quincena
        """
        self.update({
            'state': 'approve',
            'approval_user': self._uid
        })

    @api.multi
    def open_reason_deny_advance(self):
        """
        Abrir ventana emergente para cancelar anticipo
        :return: dict
        """
        return {
            'name': "Explique la razón",
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'eliterp.reason.deny.advance',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    @api.multi
    def posted_advance(self):
        """
        Contabilizar anticipo
        """
        move_id = self.env['account.move'].create({'journal_id': self.journal_id.id,
                                                   'date': self.date
                                                   })
        self.env['account.move.line'].with_context(check_move_validity=False).create({
            'name': self.account_id.name,
            'journal_id': self.journal_id.id,
            'account_id': self.account_id.id,
            'move_id': move_id.id,
            'debit': 0.0,
            'credit': self.total,
            'date': self.date
        })
        count = len(self.lines_advance)
        for line in self.lines_advance:
            count -= 1
            if count == 0:
                self.env['account.move.line'].with_context(check_move_validity=True).create(
                    {'name': line.account_id.name + ": " + line.employee_id.name,
                     'journal_id': self.journal_id.id,
                     'account_id': line.account_id.id,
                     'move_id': move_id.id,
                     'credit': 0.0,
                     'debit': line.amount_total,
                     'date': self.date})
            else:
                self.env['account.move.line'].with_context(check_move_validity=False).create(
                    {'name': line.account_id.name + ": " + line.employee_id.name,
                     'journal_id': self.journal_id.id,
                     'account_id': line.account_id.id,
                     'move_id': move_id.id,
                     'credit': 0.0,
                     'debit': line.amount_total,
                     'date': self.date})

        move_id.post()
        move_id.write({'ref': "Anticipo de " + self.period})
        return self.write({
            'name': move_id.name,
            'state': 'posted',
            'move_id': move_id.id
        })

    @api.model
    def _default_journal(self):
        """
        Definimos diario por defecto para anticipo
        """
        return self.env['account.journal'].search([('name', '=', 'Anticipo de quincena')], limit=1)[0].id

    @api.depends('date')
    @api.one
    def _get_period(self):
        """
        Obtenemos el período con la fecha de emisión
        """
        if self.date:
            month = self.env['eliterp.global.functions']._get_month_name(int(self.date[5:7]))
            self.period = "%s [%s]" % (month, self.date[:4])

    @api.depends('lines_advance')
    @api.one
    def _get_count_lines(self):
        """
        Cantidad de líneas de anticipo
        """
        self.count_lines = len(self.lines_advance) if self.lines_advance else 0

    name = fields.Char('No. Documento')
    period = fields.Char('Período', compute='_get_period', store=True)
    date = fields.Date('Fecha de emisión', default=fields.Date.context_today, required=True)
    account_id = fields.Many2one('account.account', string="Cuenta", domain=[('account_type', '=', 'movement')],
                                 default=_default_account)
    lines_advance = fields.One2many('eliterp.lines.advance.payment', 'advanced_id', string='Líneas de anticipo')
    move_id = fields.Many2one('account.move', string='Asiento contable')
    total = fields.Float('Total de anticipo', compute='_get_total', store=True)
    journal_id = fields.Many2one('account.journal', string="Diario", default=_default_journal)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('to_approve', 'A aprobar'),
        ('reviewed', 'Revisado'),  # MAEQ
        ('approve', 'Aprobado'),
        ('posted', 'Contabilizado'),
        ('deny', 'Negado')], string="Estado", default='draft')
    approval_user = fields.Many2one('res.users', string='Aprobado por')
    reviewed_user = fields.Many2one('res.users', string='Revisado por')  # MAEQ
    reason_deny = fields.Text('Negado por')
    count_lines = fields.Integer('Nº de empleados', compute='_get_count_lines')
    comment = fields.Text('Notas y comentarios')
    advance_days = fields.Integer('Días de ADQ')
