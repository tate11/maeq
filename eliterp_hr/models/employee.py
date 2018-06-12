# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models
from datetime import datetime
from odoo.exceptions import ValidationError


class SectoralCode(models.Model):
    _name = 'eliterp.sectoral.code'

    _description = 'Código sectorial IESS'

    name = fields.Char('Código de cargo', size=13, required=True)

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'EL Código de cargo ya existe en registros.'),
    ]


class TypeHistory(models.Model):
    _name = 'eliterp.type.history'

    _description = 'Tipo de historial'

    name = fields.Char('Nombre')


class LinesHistoryEmployee(models.Model):
    _name = 'eliterp.lines.history.employee'

    _description = 'Líneas de documentos de empleado'

    @api.constrains('date')
    def _check_date(self):
        """
        Fecha de validez no puede ser menor a la de registro
        """
        if self.date > self.date_validity:
            raise ValidationError("La fecha de vigencia no puede ser menor a la "
                                  "fecha de registro.")

    type = fields.Many2one('eliterp.type.history', 'Tipo', required=True)
    date = fields.Date('Fecha de registro', default=fields.Date.context_today, required=True)
    comment = fields.Text('Comentarios')
    date_validity = fields.Date('Fecha de vigencia')
    employee_id = fields.Many2one('hr.employee', string='Empleado')


class LinesEmployeeDocuments(models.Model):
    _name = 'eliterp.lines.employee.documents'

    _description = 'Líneas de documentos de empleado'

    document_name = fields.Char('Nombre de documento')
    adjunt = fields.Binary('Documento')
    adjunt_name = fields.Char('Nombre')
    documents_id = fields.Many2one('eliterp.employee.documents', string='Documentos')


class EmployeeDocuments(models.Model):
    _name = 'eliterp.employee.documents'

    _description = 'Documentos de empleado'

    @api.model
    def _get_lines_documents(self):
        """
        Obtenemos las líneas de documentos
        :param type:
        :return: object
        """
        list_documents = []
        list_names = [
            'Acuerdo de Confidencialidad',
            'Aviso de Entrada IESS',
            'Contrato de Trabajo',
            'Hoja de Vida',
            'Copia de certificados de cursos, seminarios, talleres',
            'Copia de título o acta de grado',
            'Copia de título o prefesional registrado en Senescyt',
            'Copia a color Cédula de identidad',
            'Copia a color Certificado de Votación',
            'Fotografía tamaño carnet a color',
            'Copia acta de matrimonio ó declaración juramentada unión libre',
            'Copia de cédula de cargas familiares',
            'Certificado de salud del MSP',
            'Certificado de trabajo con números de contacto',
            'Copia de planilla de servicios básicos',
            'Referencias personales con números de contacto',
            'Aviso de Salida IESS',
            'Acta de Finiquito',
        ]
        for line in list_names:
            list_documents.append([0, 0, {'document_name': line, }])
        return list_documents

    @api.model
    def create(self, values):
        if 'default_employee_id' in self._context:  # Cambiar el nombre del documento, para presentación
            employee_id = self.env['hr.employee'].search([('id', '=', self._context['default_employee_id'])], limit=1)
            values.update({'name': 'Documentos de ' + employee_id[0].name})
        return super(EmployeeDocuments, self).create(values)

    name = fields.Char('Nombre')
    employee_id = fields.Many2one('hr.employee', 'Empleado')
    lines_documents = fields.One2many('eliterp.lines.employee.documents', 'documents_id',
                                      'Líneas de documento', default=_get_lines_documents)


class EmployeesChildren(models.Model):
    _name = 'eliterp.employees.children'

    _description = 'Hijos de empleados'

    @api.depends('birthday')
    def _get_age_children(self):
        """
        Obtenemos la edad de cada hijo
        """
        for children in self:
            age = 0
            if children.birthday:
                age = (datetime.now().date() - datetime.strptime(children.birthday, '%Y-%m-%d').date()).days / 365
            children.update({'age': age})

    names = fields.Char('Nombres', required=True)
    documentation_number = fields.Char('Nº de identificación', size=10)
    birthday = fields.Date('Fecha de nacimiento', required=True)
    age = fields.Integer('Edad', compute='_get_age_children')
    employee_id = fields.Many2one('hr.employee', string='Empleado')


class Employee(models.Model):
    _inherit = 'hr.employee'

    @api.model_cr_context
    def _init_column(self, column_name):
        """
        Actualizamos columna wage en empleados creados por defecto (Test)
        :param column_name:
        :return:
        """
        query = """UPDATE hr_employee SET names='Sin nombres', surnames='Sin apellidos', wage=386
                    WHERE wage is NULL AND names is NULL AND surnames is NULL
                        """
        self.env.cr.execute(query)

    @api.onchange('names', 'surnames')
    def _onchange_names(self):
        """
        Actualizamos nombre de empleado
        :return: dict
        """
        value = {}
        if self.names and self.surnames:
            value['name'] = self.surnames + ' ' + self.names
            return {'value': value}

    @api.depends('birthday')
    @api.one
    def _get_age(self):
        """
        Obtenemos la edad del empleado
        """
        for employee in self:
            age = 0
            if employee.birthday:
                age = (datetime.now().date() - datetime.strptime(employee.birthday, '%Y-%m-%d').date()).days / 365
            employee.age = age

    @api.onchange('user_id')
    def _onchange_user(self):
        """
        MM
        """
        pass

    @api.multi
    def open_documents(self):
        """
        Abrimos los documentos realacionados al empleado
        :return: dict
        """
        documents_id = self.env['eliterp.employee.documents'].search([('employee_id', '=', self[0].id)])
        res = {
            'type': 'ir.actions.act_window',
            'res_model': 'eliterp.employee.documents',
            'view_mode': 'form',
            'view_type': 'form',
        }
        if documents_id:
            res['res_id'] = documents_id[0].id
            res['context'] = "{}"
        else:
            res['context'] = "{'default_employee_id': " + str(self[0].id) + "}"
        return res

    @api.multi
    def write(self, vals):
        """
        Modificamos la fecha de ingreso del contrato al cambiar la del empleado
        :param vals:
        :return: object
        """
        res = super(Employee, self).write(vals)
        if self.contract_id and 'admission_date' in vals:
            self.contract_id.update({'date_start': vals['admission_date']})
        return res

    @api.depends('apply_overtime', 'wage')
    @api.one
    def _get_amount_hours(self):
        """
        Obtenemos valor de HE por empleado
        """
        if self.apply_overtime:
            self.extra_hours = round((self.wage / 240) * 2, 2)
            self.additional_hours = round((self.wage / 240) * 1.5, 2)

    names = fields.Char('Nombres', required=True)
    surnames = fields.Char('Apellidos', required=True)
    education_level = fields.Selection([
        ('basic', 'Educación básica'),
        ('graduate', 'Bachiller'),
        ('professional', 'Tercer nivel'),
        ('master', 'Postgrado')
    ], 'Nivel de educación', default='basic')
    blood_type = fields.Selection([
        ('a_most', 'A+'),
        ('a_minus', 'A-'),
        ('b_most', 'B+'),
        ('b_minus', 'B-'),
        ('ab_most', 'AB+'),
        ('ab_minus', 'AB-'),
        ('o_most', 'O+'),
        ('o_minus', 'O-')
    ], 'Tipo de sangre', default='o_most')
    sectoral_code = fields.Many2one('eliterp.sectoral.code', 'Código sectorial')
    wage = fields.Float('Sueldo', required=True)
    age = fields.Integer('Edad', compute='_get_age')
    benefits = fields.Selection([('yes', 'Si'), ('no', 'No')], string='Acumula beneficios?', default='no',
                                required=True)
    lines_children = fields.One2many('eliterp.employees.children', 'employee_id', 'Hijos')
    contact_1 = fields.Char('Contacto')
    relationship_1 = fields.Char('Parentesco')
    phone_1 = fields.Char('Teléfono')
    contact_2 = fields.Char('Contacto')
    relationship_2 = fields.Char('Parentesco')
    phone_2 = fields.Char('Teléfono')
    admission_date = fields.Date('Fecha de ingreso', required=True, default=fields.Date.context_today)
    struct_id = fields.Many2one('hr.payroll.structure', string='Estructura salarial')
    extension = fields.Char('Extensión', size=3)
    personal_phone = fields.Char('Teléfono personal')
    home_address = fields.Char('Dirección de domicilio')

    lines_history = fields.One2many('eliterp.lines.history.employee', 'employee_id', string='Historial de empleado')
    apply_overtime = fields.Boolean('Aplica?', default=False)
    extra_hours = fields.Float('Monto HE 100%', compute='_get_amount_hours', store=True)
    additional_hours = fields.Float('Monto HE 50%', compute='_get_amount_hours', store=True)
    mobilization = fields.Float('Movilización',
                                help='Será dado al empleado la mitad en ADQ y la otra mitad en Rol consolidado.')
