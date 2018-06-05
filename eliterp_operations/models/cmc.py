# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import models, fields, api
from odoo.addons import decimal_precision as dp
from odoo.exceptions import ValidationError, UserError

STATES = [
    ('draft', 'Borrador'),
    ('validate', 'Validado'),
    ('cancel', 'Cancelado')
]


class PrefixCMCCode(models.Model):
    _name = 'eliterp.prefix.cmc.code'

    @api.model
    def create(self, vals):
        new_sequence = self.env['ir.sequence'].create({
            'name': "Código de CMC " + vals['name'],
            'code': 'prefix.' + vals['name'],
            'prefix': vals['name'] + '-',
            'padding': 3
        })
        vals.update({'sequence_id': new_sequence.id})  # Actualizamos nueva secuencia
        return super(PrefixCMCCode, self).create(vals)

    name = fields.Char('Código', required=True, size=5)
    sequence_id = fields.Many2one('ir.sequence', 'Secuencia')

    _sql_constraints = [
        ('name_unique', 'unique (name)', "El Código debe ser único.")
    ]


class PrefixCMC(models.Model):
    _name = 'eliterp.prefix.cmc'
    _description = 'Prefijo para creación de CMC'

    @api.model
    def create(self, vals):
        code_prefix = self.env['eliterp.prefix.cmc.code'].browse(vals['code'])
        object_sequence = self.env['ir.sequence']
        sequence = object_sequence.next_by_code(code_prefix.sequence_id.code)
        vals.update({'name': sequence})  # Actualizamos nuevo nombre
        return super(PrefixCMC, self).create(vals)

    code = fields.Many2one('eliterp.prefix.cmc.code', 'Código', required=True)
    name = fields.Char('Nombre de prefijo')
    responsable = fields.Many2one('hr.employee', string='Responsable')
    cmc_ids = fields.One2many('eliterp.cmc', 'prefix_id', string="CMC's")


class PartsManagement(models.Model):
    _name = 'eliterp.parts.management'

    _description = 'Administración y registro de piezas'

    date = fields.Date('Fecha', default=fields.Date.context_today, required=True)
    technical_report = fields.Char('Informe técnico')  # TODO: Falta crear informe
    movement_type = fields.Selection([
        ('transfer', 'Transferencia'),
        ('other', 'Otro')
    ], string='Tipo de movimiento', default='transfer')
    detail = fields.Text('Detalle', required=True)
    reference = fields.Many2one('eliterp.machine', 'De máquina')
    horometro = fields.Integer('Horómetro')
    responsable = fields.Many2one('hr.employee', 'Responsable')
    cmc_id = fields.Many2one('eliterp.cmc', 'CMC')


class SuppliesCMC(models.Model):
    _name = 'eliterp.supplies.cmc'

    _description = 'Insumos usados en CMC'

    product_id = fields.Many2one('product.product', domain=[('purchase_ok', '=', True)], string='Insumo')
    product_quantity = fields.Float('Cantidad', digits=dp.get_precision('Product Unit of Measure'), required=True)
    product_uom_id = fields.Many2one('product.uom', string='Unidad de medida')
    cmc_id = fields.Many2one('eliterp.cmc', 'CMC')


class CMC(models.Model):
    _name = 'eliterp.cmc'
    _description = 'CMC'

    def _get_initial_horometro(self, machine):
        """
        Actualizar horómetro inicial del nuevo CMC, seleccionamos el último
        CMC en estado validado
        """
        last_cmc = self.env['eliterp.cmc'].search([
            ('machine_id', '=', machine.id),
            ('state', '=', 'validate'),
            ('id', '!=', self.id if self.id else False),
        ], order='id desc', limit=1)
        if last_cmc:
            horometro = last_cmc['final_horometro']
        else:
            horometro = machine.horometro_initial
        return horometro

    @api.multi
    def validate(self):
        """
        Cambiamos el estado a validado y creamos de existir diferencia entre
        horómetros y si hay registros de piezas
        """
        object_history = self.env['eliterp.lines.history.machine']
        if self.horometro_difference:
            object_history.create({
                'type': 'horometro',
                'description': self.reason,
                'machine_id': self.machine_id.id
            })
        if self.piece_ids:
            for line in self.piece_ids:
                object_history.create({
                    'type': 'piece',
                    'description': line.detail,
                    'machine_id': self.machine_id.id
                })
        self.write({
            'state': 'validate'
        })
        return True

    @api.multi
    def unlink(self):
        """
        Evitamos borrar los validado
        """
        if self.filtered(lambda r: r.state != 'draft'):
            raise UserError('No puedes borrar un CMC en estado validado.')
        return super(CMC, self).unlink()

    @api.onchange('name')
    def _onchange_name(self):
        """
        Rellenamos de 0 al cambiar de nombre
        """
        if self.name:
            self.name = self.name.zfill(3)

    @api.constrains('final_horometro')
    def _check_final_horometro(self):
        """
        Verificar que horómetro final no sea menor al inicial
        """
        if self.final_horometro < self.initial_horometro:
            raise ValidationError('El Horómetro final no puede ser menor al inicial.')

    @api.onchange('operator')
    def _onchange_operator(self):
        """
        Obtenemos si existe la cuadrilla por defecto asignada al empleado
        """
        if self.operator:
            gang = self.env['eliterp.lines.employee'].search([
                ('employee_id', '=', self.operator.id)
            ], limit=1)
            if gang:
                self.gang_id = gang[0].gang_id.id
            else:
                self.gang_id = False

    @api.onchange('machine_id')
    def _onchange_machine_id(self):
        """
        Obtenemos el horómetro inicial al cambiar de máquina
        """
        if self.machine_id:
            horometro = self._get_initial_horometro(self.machine_id)
            self.initial_horometro = horometro
            self.initial_horometro_old = horometro

    @api.onchange('initial_horometro')
    def _onchange_initial_horometro(self):
        """
        Verificamos qué no exista cambio entre horómetros
        """
        if self.initial_horometro:
            self.horometro_difference = self.initial_horometro != self.initial_horometro_old

    @api.depends('initial_horometro', 'final_horometro')
    @api.one
    def _get_worked_hours(self):
        worked_hours = round(self.final_horometro - self.initial_horometro, 2)
        if worked_hours > 8:
            self.extra_hours = worked_hours - 8
        self.worked_hours = worked_hours


    prefix_id = fields.Many2one('eliterp.prefix.cmc', 'Prefijo CMC', required=True, readonly=True,
                                states={'draft': [('readonly', False)]})
    name = fields.Char('Nº', size=3, required=True, readonly=True,
                       states={'draft': [('readonly', False)]})
    date = fields.Date('Fecha documento', default=fields.Date.context_today, required=True, readonly=True,
                       states={'draft': [('readonly', False)]}
                       )
    project_id = fields.Many2one('eliterp.project', string='Proyecto', required=True,
                                 readonly=True,
                                 states={'draft': [('readonly', False)]})
    customer = fields.Many2one('res.partner', related='project_id.customer', string='Cliente')
    machine_id = fields.Many2one('eliterp.machine', string='Máquina', required=True, readonly=True,
                                 states={'draft': [('readonly', False)]})
    operator = fields.Many2one('hr.employee', related='prefix_id.responsable', string='Operador', readonly=True,
                               required=True,
                               states={'draft': [('readonly', False)]})
    assistant = fields.Many2one('hr.employee', string='Ayudante', readonly=True,
                                states={'draft': [('readonly', False)]})
    ubication_id = fields.Many2one('eliterp.location', 'Ubicación', required=True, readonly=True,
                                   states={'draft': [('readonly', False)]})
    gang_id = fields.Many2one('eliterp.gang', 'Cuadrilla', required=True, readonly=True,
                              states={'draft': [('readonly', False)]})
    work_id = fields.Many2one('eliterp.work', 'Obra', required=True, readonly=True,
                              states={'draft': [('readonly', False)]})
    block = fields.Char('Bloque', required=True, readonly=True,
                        states={'draft': [('readonly', False)]})

    initial_horometro = fields.Float('Horómetro inicial', required=True, readonly=True,
                                       states={'draft': [('readonly', False)]})
    initial_horometro_old = fields.Float('Horómetro inicial viejo')  # Para motivos de cálculos
    final_horometro = fields.Float('Horómetro final', copy=False, readonly=True,
                                     states={'draft': [('readonly', False)]})
    horometro_difference = fields.Boolean('Hay diferencia?', default=False, copy=False,
                                          help='En caso de diferencia con la información del CMC físico se indicará la información')
    reason = fields.Text('Motivo', copy=False, readonly=True,
                         states={'draft': [('readonly', False)]})
    supplies = fields.One2many('eliterp.supplies.cmc', 'cmc_id', 'Insumos de CMC')
    piece_ids = fields.One2many('eliterp.parts.management', 'cmc_id', 'Administración de piezas')

    check_in_am = fields.Datetime('Hora ingreso AM', readonly=True,
                                  states={'draft': [('readonly', False)]})
    check_out_am = fields.Datetime('Hora salida AM', readonly=True,
                                   states={'draft': [('readonly', False)]})
    check_in_pm = fields.Datetime('Hora ingreso PM', readonly=True,
                                  states={'draft': [('readonly', False)]})
    check_out_pm = fields.Datetime('Hora salida PM', readonly=True,
                                   states={'draft': [('readonly', False)]})

    worked_hours = fields.Float('Horas trabajadas', compute='_get_worked_hours', store=True)
    extra_hours = fields.Float('Horas extras', compute='_get_worked_hours', store=True)

    state = fields.Selection(STATES, string='Estado', default='draft')
    comment = fields.Text('Notas y comentarios', readonly=True,
                                     states={'draft': [('readonly', False)]})

    _sql_constraints = [
        ('number_unique', 'unique (prefix_id, name, state)', "El Nº de CMC debe ser único por prefijo.")
    ]
