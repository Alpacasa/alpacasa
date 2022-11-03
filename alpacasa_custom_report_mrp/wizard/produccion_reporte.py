import copy
from datetime import datetime, timedelta, time, date
import time
import babel.dates
from odoo import api, fields, models, tools, _
from functools import reduce
from odoo.exceptions import ValidationError, UserError
import logging
import xlsxwriter
from odoo import http, _
from odoo.http import request
from odoo.addons.web.controllers.main import serialize_exception, \
    content_disposition
import operator

_logger = logging.getLogger(__name__)


class WizardReportControl(models.TransientModel):
    _name = "mrp.production.cab.reporte"

    date_ini = fields.Date(string="Fecha desde")
    date_end = fields.Date(string="Fecha hasta")

    production_cab_id = fields.Many2one('mrp.production.cab', string="Orden de Produccion")
    product_id = fields.Many2one('product.product', 'Producto', check_company=True)
    lot_producing_id = fields.Many2one('stock.production.lot', string='Lot/Serial Number', copy=False,
                                       check_company=True,
                                       domain="[('product_id', '=', product_id), ('company_id', '=', company_id)]")
    cod_linea_work = fields.Many2one('mrp.workcenter', string='Linea de trabajo')
    date = fields.Date(string="Fecha")
    cod_proveedor = fields.Many2one('res.partner', string='Provedoor')
    user_id = fields.Many2one('res.users', 'Operador', default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', 'Empresa', default=lambda self: self.env.company, index=True,
                                 required=True)
    tipo_producto = fields.Selection([('1', 'Nuevo Producto'),
                                      ('4', 'Reproceso')],
                                     string='Tipo de Proceso',
                                     default='1')
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmado'),
        ('progress', 'En Proceso'),
        ('done', 'Finalizado'),
        ('cancel', 'Cancelado')],
        string='State',
        default='confirmed')

    tipo = fields.Selection(
        [('xlsx', 'XLSX'),
         ('pdf', 'PDF')],
        string="Tipo de archivo",
        default='pdf')

    @api.onchange('production_cab_id')
    def onchange_production_cab_id(self):
        if self.production_cab_id:
            pivo = self.env['mrp.production.cab'].search(
                [('company_id', '=', self.company_id.id), ('id', '=', self.production_cab_id.id)])
            self.product_id = pivo.product_id.id
            self.lot_producing_id = pivo.lot_producing_id.id
            self.tipo_producto = pivo.tipo_producto
            self.state = pivo.state
            self.cod_proveedor = pivo.cod_proveedor.id
            for x in pivo:
                if x.workcenter_cab_ids:
                    self.cod_linea_work = x.workcenter_cab_ids.cod_linea_work.id

    def check_report(self):
        data = {}
        data['form'] = self.read(['product_id',
                                  'production_cab_id',
                                  'lot_producing_id',
                                  'tipo_producto'])[0]
        return self._print_report(data)

    def _print_report(self, data):
        data['form'].update(self.read(['product_id',
                                       'production_cab_id',
                                       'lot_producing_id',
                                       'tipo_producto'])[0])
        return self.env.ref('py_ctrm_mrp.report_mrp_menu_cab_2').report_action(self, data=data)


class ReportDailyBook(models.AbstractModel):
    _name = 'report.py_ctrm_mrp.report_resumen_orden_produccion_cab_dos'

    def _get_report_values(self, docids, data=None):
        Model = self.env.context.get('active_model')
        docs = self.env[Model].browse(self.env.context.get('active_id'))

        company = self.env.company.id
        product = docs.product_id.id
        production = docs.production_cab_id.id
        lote = docs.lot_producing_id.id

        if product == False:
            product = 0

        if production == False:
            production = 0

        if lote == False:
            lote = 0

        cr = self.env.cr
        query = """
                    select
                        q.company_id,
                        q.big_bag,
                        to_char(q.control_date, 'dd/mm') as fecha,
                        to_char(q.control_date, 'HH24:MI')as hora,
                        case when q.peso_ini = 0 then 0
                             when q.peso_ini > 0 then q.peso_ini
                        end as peso_ini, 
                        case when q.impurezas is null then 0
                            when q.impurezas > 0 then q.impurezas
                        end as impurezas,
                        case when q.impurezas_porce is null then 0
                            when q.impurezas_porce > 0 then q.impurezas_porce
                        end as impurezas_porce,
                        case when q.excretas_gr is null then 0
                            when q.excretas_gr > 0 then q.excretas_gr
                            end as excretas_gra,
                        case when q.excretas_porce is null then 0
                            when q.excretas_porce > 0 then q.excretas_porce
                            end as excretas_porce,
                        case when q.excretas_uni is null then 0
                            when q.excretas_uni > 0 then q.excretas_uni
                            end as excretas_uni,
                        case when q.seeds_1 is null then 0
                            when q.seeds_1 > 0 then q.seeds_1
                            end as seeds_1,
                        case when q.seeds_1_porce is null then 0
                            when q.seeds_1_porce > 0 then q.seeds_1_porce
                            end as seeds_1_porce,
                        case when q.seeds_1_comment is null then ''
                            when q.seeds_1_comment > '0' then q.seeds_1_comment
                            end as seeds_1_comment,
                        case when q.seeds_2 is null then 0
                            when q.seeds_2 > 0 then q.seeds_2
                            end as seeds_2,
                        case when q.seeds_2_porce is null then 0
                            when q.seeds_2_porce > 0 then q.seeds_2_porce
                            end as seeds_2_porce,
                        case when q.seeds_2_comment is null then ''
                            when q.seeds_2_comment > '0' then q.seeds_2_comment
                            end as seeds_2_comment,
                        case when q.pureza is null then 0
                            when q.pureza > 0 then q.pureza
                            end as pureza,
                        case when q.humedad is null then 0
                            when q.humedad > 0 then q.humedad
                            end as humedad,
                        case when q.temperatura is null then 0
                            when q.temperatura > 0 then q.temperatura
                            end as temperatura,
                        case when q.metales is null then 0
                            when q.metales > 0 then q.metales
                            end as metales,
                        q.insec_res,
                        q.aprobacion,
                        pp.name as operador

                        from quality_check as q
                        inner join mrp_production_cab as c on c.id = q.production_cab_id
                        left join mrp_routing_workcenter_cab as t on t.production_cab_id = q.production_cab_id
                        inner join res_users as r on r.id = q.user_id
                        inner join res_partner as pp on pp.id = r.partner_id
                        where q.company_id = """ + str(company) + """
                        and case when """ + str(production) + """ = '0' then q.production_cab_id 
                                 when """ + str(production) + """ is not null then """ + str(production) + """
                            end = q.production_cab_id 
                        and case when """ + str(product) + """ = '0' then q.product_id
                                 when """ + str(product) + """ is not null then """ + str(product) + """
                            end = q.product_id
                        and case when """ + str(lote) + """ = '0' then q.lot_id
                                 when """ + str(lote) + """ is not null then """ + str(lote) + """
                            end = q.lot_id
                        and q.picking_id is null
                        and q.quality_state = 'pass'
                        and q.check_reprocesado = 'False'
                        order by q.big_bag asc
               """
        cr.execute(query)
        calidad = cr.fetchall()

        docargs = {
            'doc_ids': self.ids,
            'doc_model': Model,
            'docs': docs,
            'time': time,
            'lineas': calidad
        }
        return docargs
