# -*- coding: utf-8 -*-
# Copyright 2018 Elitumdevelop S.A, Ing. Mario Rangel
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import models, fields, api
from odoo.addons import decimal_precision as dp
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_is_zero

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

    @api.onchange('product_id')
    def onchange_product_id(self):
        """
        Actualizamos datos de producto al cambiar el mismo
        """
        self.name = self.product_id.description_purchase
        self.product_uom_id = self.product_id.uom_id.id
        return {'domain': {'product_uom_id': [('category_id', '=', self.product_id.uom_id.category_id.id)]}}

    product_id = fields.Many2one('product.product', domain=[
        ('purchase_ok', '=', True),
        ('qty_available', '>', 0),
        ('type', '=', 'product')
    ], string='Producto', required=True)  # Soló productos almacenables y con stock físico
    name = fields.Text('Descripción')
    product_quantity = fields.Float('Cantidad', digits=dp.get_precision('Product Unit of Measure'), required=True)
    product_uom_id = fields.Many2one('product.uom', string='Unidad de medida', required=True)
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

    def create_picking(self):
        """
        Creamos un picking desde el CMC cómo transferencia interna
        """
        Picking = self.env['stock.picking']
        Move = self.env['stock.move']
        for cmc in self:
            picking_type = cmc.picking_type_id
            location_id = picking_type.default_location_src_id.id
            destination_id = picking_type.default_location_dest_id.id
            moves = Move
            picking_vals = {
                'origin': "CMC/%s-%s" % (cmc.prefix_id.name, cmc.name),
                'date_done': cmc.date,
                'picking_type_id': picking_type.id,
                'company_id': self.env.user.company_id.id,
                'move_type': 'direct',
                'location_id': location_id,
                'location_dest_id': destination_id,
            }
            message = 'Se realizó movimiento de inventario del CMC: %s-%s' % (cmc.prefix_id.name, cmc.name)
            cmc_picking = Picking.create(picking_vals.copy())
            cmc_picking.message_post(body=message)
            for line in cmc.supplies.filtered(lambda l: not float_is_zero(l.product_quantity,
                                                                          precision_rounding=l.product_uom_id.rounding)):
                quant_uom = line.product_id.uom_id
                get_param = self.env['ir.config_parameter'].sudo().get_param
                if line.product_uom_id.id != quant_uom.id and get_param('stock.propagate_uom') != '1':
                    product_qty = line.product_uom_id._compute_quantity(line.product_quantity, quant_uom,
                                                                        rounding_method='HALF-UP')
                else:
                    product_qty = line.product_quantity
                moves |= Move.create({
                    'name': line.name,
                    'product_uom': quant_uom.id,
                    'picking_id': cmc_picking.id,
                    'picking_type_id': picking_type.id,
                    'product_id': line.product_id.id,
                    'product_uom_qty': abs(product_qty),
                    'state': 'draft',
                    'location_id': location_id,
                    'location_dest_id': destination_id,
                })
            # Realizar las operaciones de inventario
            moves._action_confirm()
            moves._action_assign()
            cmc.write({'picking_id': cmc_picking.id})  # Picking creado se asigna a cmc

    def _create_record_overtime(self, employee):
        """
        Creamos los registros de horas extras
        """
        if employee.apply_overtime:
            amount = round(self.extra_hours * employee.additional_hours, 2)
            object_record_overtime = self.env['eliterp.record.overtime']
            object_record_overtime.create({
                'name': employee.id,
                'date': self.date,
                'additional_hours': self.extra_hours,
                'total_additional_hours': amount
            })
        return True

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
        # Creamos líneas de horas extras
        if self.extra_hours > 0:
            self._create_record_overtime(self.operator)
            self._create_record_overtime(self.assistant)
        if self.picking_type_id:
            self.create_picking()  # Función para crear picking si tiene tipo de operación
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
                               required=True, store=True,
                               states={'draft': [('readonly', False)]})
    assistant = fields.Many2one('hr.employee', string='Ayudante', readonly=True,
                                states={'draft': [('readonly', False)]})
    ubication_id = fields.Many2one('eliterp.location', 'Ubicación', required=True, readonly=True,
                                   states={'draft': [('readonly', False)]})
    gang_id = fields.Many2one('eliterp.gang', 'Cuadrilla', required=True, readonly=True,
                              states={'draft': [('readonly', False)]})
    work_id = fields.Many2one('product.product', domain=[
        ('sale_ok', '=', True),
        ('type', '=', 'service')
    ], string='Producto/Servicio', required=True, readonly=True,
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
    supplies = fields.One2many('eliterp.supplies.cmc', 'cmc_id', 'Insumos de CMC', readonly=True,
                               states={'draft': [('readonly', False)]})
    piece_ids = fields.One2many('eliterp.parts.management', 'cmc_id', 'Administración de piezas', readonly=True,
                                states={'draft': [('readonly', False)]})

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
    picking_type_id = fields.Many2one('stock.picking.type', 'Usado para',
                                      domain=[('code', '=', 'internal')], readonly=True,
                                      states={'draft': [('readonly', False)]},
                                      help="Está determinada operación será usada en el uso de insumos para CMC's.")
    picking_id = fields.Many2one('stock.picking', 'Movimiento', readonly=True,
                                 states={'draft': [('readonly', False)]})

    _sql_constraints = [
        ('number_unique', 'unique (prefix_id, name, state)', "El Nº de CMC debe ser único por prefijo.")
    ]
