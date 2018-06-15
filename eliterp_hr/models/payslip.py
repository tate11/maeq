# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo import api, fields, models, tools, _
from datetime import datetime
import time
from odoo.tools.safe_eval import safe_eval


class Employee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def _default_account(self):
        """
        Cuenta por defecto de nómina en empleado
        """
        account = self.env['account.account'].search([('name', '=', 'NÓMINA POR PAGAR')], limit=1)
        return account[0].id if account else False

    account_payroll = fields.Many2one('account.account', string="Cuenta nómina",
                                      domain=[('account_type', '=', 'movement')], default=_default_account)


class SalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    account_id = fields.Many2one('account.account', string="Cuenta contable",
                                 domain=[('account_type', '=', 'movement')])
    _sql_constraints = [
        ('code_unique', 'unique (code)', "El Código de la regla salarial debe ser único.")
    ]


class PayslipInput(models.Model):
    _inherit = 'hr.payslip.input'

    account_id = fields.Many2one('account.account', string='Cuenta contable',
                                 domain=[('account_type', '=', 'movement')])
    total = fields.Float('Total')
    contract_id = fields.Many2one('hr.contract', string='Contract', required=False,
                                  help="The contract for which applied this input")  # CM


class PayslipInput2(models.Model):
    _name = 'eliterp.payslip.input.2'
    _description = 'Egresos de rol'
    _order = 'payslip_id, sequence'

    name = fields.Char(string='Descripción', required=True)
    payslip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(required=True, index=True, default=10)
    code = fields.Char(required=True, help="The code that can be used in the salary rules")
    amount = fields.Float(help="It is used in computation. For e.g. A rule for sales having "
                               "1% commission of basic salary for per product can defined in expression "
                               "like result = inputs.SALEURO.amount * contract.wage*0.01.")
    contract_id = fields.Many2one('hr.contract', string='Contract', required=False,
                                  help="The contract for which applied this input")
    account_id = fields.Many2one('account.account', string="Cuenta contable",
                                 domain=[('account_type', '=', 'movement')])
    total = fields.Float('Total')


class PayslipInput3(models.Model):
    _name = 'eliterp.payslip.input.3'
    _description = 'Provisión de rol'
    _order = 'payslip_id, sequence'

    name = fields.Char(string='Descripción', required=True)
    payslip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(required=True, index=True, default=10)
    code = fields.Char(required=True, help="The code that can be used in the salary rules")
    amount = fields.Float(help="It is used in computation. For e.g. A rule for sales having "
                               "1% commission of basic salary for per product can defined in expression "
                               "like result = inputs.SALEURO.amount * contract.wage*0.01.")
    contract_id = fields.Many2one('hr.contract', string='Contract', required=False,
                                  help="The contract for which applied this input")
    account_id = fields.Many2one('account.account', string="Cuenta contable",
                                 domain=[('account_type', '=', 'movement')])
    total = fields.Float('Total')


class Payslip(models.Model):
    _inherit = 'hr.payslip'

    @api.multi
    def print_role(self):
        """
        Imprimimos rol individual
        """
        self.ensure_one()
        return self.env.ref('eliterp_hr.eliterp_action_report_hr_payslip').report_action(self)

    @api.model
    def create(self, vals):
        res = super(Payslip, self).create(vals)
        month = self.env['eliterp.global.functions']._get_month_name(datetime.strptime(res.date_from, "%Y-%m-%d").month)
        res.write({'number': "%s [%s]" % (month, str(datetime.strptime(res.date_from, "%Y-%m-%d").year))})
        return res

    @api.one
    @api.depends('input_line_ids', 'input_line_ids_2')
    def _get_net_receive(self):
        """
        Obtenemos el valor a recibir (INGRESOS - EGRESOS)
        """
        self.net_receive = round(sum(round(line.amount, 3) for line in self.input_line_ids), 3) - round(sum(
            round(line2.amount, 3) for line2 in self.input_line_ids_2), 3)

    @api.multi
    def action_payslip_done(self):
        """
        MM
        """
        return self.write({'state': 'done'})

    @api.model
    def get_inputs(self, employee_id, role=None):
        """
        MM: Obtenemos la lista de reglas salariales
        :param employee_id:
        :return: list
        """
        res = []
        structure_ids = employee_id.struct_id.id  # Seleccionamos soló la estructura
        rule_ids = self.env['hr.payroll.structure'].browse(structure_ids).get_all_rules()
        sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x: x[1])]
        inputs = self.env['hr.salary.rule'].browse(sorted_rule_ids)
        local_dict = {
            'contract': employee_id.contract_id,  # Último contrato de empleado
            'employee': employee_id,
            'payslip': role if role else self,
            'additional_hours': employee_id._get_additional_hours_period(
                self.date_from,
                self.date_to
            ),
            'result': 0.00
        }

        for input in inputs:  # Operaciones de reglas salariales
            if input.condition_select == 'python' and input.code != 'ADQ':
                safe_eval(input.condition_python, local_dict, mode='exec', nocopy=True)
                amount = local_dict['result']
            elif input.code == 'ADQ':  # TODO: Esto se hace para MAEQ
                last_advance_payment = self.env['eliterp.advance.payment'].search([('state', '=', 'posted')])
                if last_advance_payment:
                    for line in last_advance_payment[-1].lines_advance:
                        if line.employee_id == self.employee_id:
                            amount = line.amount_total
                            break
                else:
                    amount = 0.00
            else:
                amount = 0.00
            input_data = {
                'name': input.name,
                'code': input.code,
                'account_id': input.account_id.id,
                'amount': amount,
                'type': input.category_id.name  # Para verificar si es de ingresos, egresos, etc
            }
            res += [input_data]
        return res

    @api.onchange('employee_id', 'date_from')
    def onchange_employee(self):
        """
        MM: Cálculo de ingresos, egresos y provisiones
        """
        if (not self.employee_id) or (not self.date_from) or (not self.date_to):
            return

        employee = self.employee_id
        date_from = self.date_from
        date_to = self.date_to

        ttyme = datetime.fromtimestamp(time.mktime(time.strptime(date_from, "%Y-%m-%d")))
        locale = self.env.context.get('lang') or 'en_US'
        # TODO: locale=locale
        self.name = 'Rol de %s por %s' % (employee.name, tools.ustr(ttyme.strftime('%B-%Y')))
        self.company_id = employee.company_id

        if not employee.struct_id:
            return
        self.struct_id = employee.struct_id

        input_line_ids = self.get_inputs(employee)
        # Vacíamos las líneas para nuevo cálculo
        input_lines = self.input_line_ids.browse([])
        input_lines_2 = self.input_line_ids_2.browse([])
        input_lines_3 = self.input_line_ids_3.browse([])
        for r in input_line_ids:
            if r['type'] == 'INGRESOS':
                input_lines += input_lines.new(r)
            if r['type'] == 'EGRESOS':
                input_lines_2 += input_lines_2.new(r)
            if r['type'] == 'PROVISIÓN':
                input_lines_3 += input_lines_3.new(r)
        # Actualizamos categoría de rol
        self.input_line_ids = input_lines
        self.input_line_ids_2 = input_lines_2
        self.input_line_ids_3 = input_lines_3

        return

    worked_days = fields.Integer(string="Días trabajados", default=30)
    number_absences = fields.Integer(string="Nº de ausencias", default=0)
    # Egresos
    input_line_ids_2 = fields.One2many('eliterp.payslip.input.2', 'payslip_id', string='Egresos rol',
                                       readonly=True, states={'draft': [('readonly', False)]})
    # Provisión
    input_line_ids_3 = fields.One2many('eliterp.payslip.input.3', 'payslip_id', string='Provisión rol',
                                       readonly=True, states={'draft': [('readonly', False)]})
    journal_id = fields.Many2one('account.journal', 'Diario', readonly=True,
                                 states={'draft': [('readonly', False)]},
                                 default=lambda self: self.env['account.journal'].search([('type', '=', 'general')],
                                                                                         limit=1))
    net_receive = fields.Float('Neto a recibir', compute='_get_net_receive', store=True)
    approval_user = fields.Many2one('res.users', 'Aprobado por')
