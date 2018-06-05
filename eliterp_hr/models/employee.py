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
    document = fields.Binary('Documento')
    documents_id = fields.Many2one('eliterp.employee.documents', string='Documentos')


class EmployeeDocuments(models.Model):
    _name = 'eliterp.employee.documents'

    _description = 'Documentos de empleado'

    def _get_lines_documents(self, type):
        """
        Obtenemos las líneas de documentos
        :param type:
        :return: list
        """
        list_documents = []
        if type == 1:
            list_documents = [
                'Acuerdo de Confidencialidad',
                'Aviso de Entrada IESS',
                'Contrato de Trabajo',
                'Hoja de Vida',
            ]
        if type == 2:
            list_documents = [
                'Copia de certificados de cursos, seminarios, talleres',
                'Copia de título o acta de grado',
                'Copia de título o prefesional registrado en Senescyt',
            ]
        if type == 3:
            list_documents = [
                'Copia a color Cédula de identidad',
                'Copia a color Certificado de Votación',
                'Fotografía tamaño carnet a color',
            ]
        if type == 4:
            list_documents = [
                'Copia acta de matrimonio ò declaración juramentada unión libre',
                'Copia de cédula de cargas familiares',
            ]
        if type == 5:
            list_documents = [
                'Certificado de salud del MSP',
                'Certificado de trabajo con números de contacto',
                'Copia de planilla de servicios básicos',
                'Referencias personales con números de contacto',
            ]

        if type == 6:
            list_documents = [
                'Aviso de Salida IESS',
                'Acta de Finiquito',
            ]

        list_lines = []
        # TODO: Se vuelven a grabar todos
        for line in list_documents:
            list_lines.append([0, 0, {'document_name': line, }])
        return list_lines

    @api.model
    def _get_lines_1(self):
        # Ingreso
        res = self._get_lines_documents(1)
        return res

    def _get_lines_2(self):
        # Formación académica
        res = self._get_lines_documents(2)
        return res

    @api.model
    def _get_lines_3(self):
        # Documentos personales
        res = self._get_lines_documents(3)
        return res

    @api.model
    def _get_lines_4(self):
        # Cargas familiares
        res = self._get_lines_documents(4)
        return res

    @api.model
    def _get_lines_5(self):
        # Otros
        res = self._get_lines_documents(5)
        return res

    @api.model
    def _get_lines_6(self):
        # Salida
        res = self._get_lines_documents(6)
        return res

    @api.model
    def create(self, values):
        if 'default_employee_id' in self._context:  # Cambiar el nombre del documento, para presentación
            employee_id = self.env['hr.employee'].search([('id', '=', self._context['default_employee_id'])], limit=1)
            values.update({'name': 'Documentos de ' + employee_id[0].name})
        return super(EmployeeDocuments, self).create(values)

    name = fields.Char('Nombre')
    lines_documents_1 = fields.One2many('eliterp.lines.employee.documents', 'documents_id',
                                        'Ingreso', default=_get_lines_1)
    lines_documents_2 = fields.One2many('eliterp.lines.employee.documents',
                                        'documents_id',
                                        string='Formación académica', default=_get_lines_2)
    lines_documents_3 = fields.One2many('eliterp.lines.employee.documents',
                                        'documents_id',
                                        'Documentos personales', default=_get_lines_3)
    lines_documents_4 = fields.One2many('eliterp.lines.employee.documents', 'documents_id',
                                        'Cargas familiares', default=_get_lines_4)
    lines_documents_5 = fields.One2many('eliterp.lines.employee.documents', 'documents_id', 'Otros',
                                        default=_get_lines_5)
    lines_documents_6 = fields.One2many('eliterp.lines.employee.documents', 'documents_id', 'Salida',
                                        default=_get_lines_6)
    employee_id = fields.Many2one('hr.employee', 'Empleado')


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
