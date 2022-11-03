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
    _name = "mrp.production.granos.cab.wizard"

    production_cab_id = fields.Many2one('mrp.production.cab', string="Orden de Produccion")
    product_id = fields.Many2one('product.product', 'Producto', check_company=True)
    lot_producing_id = fields.Many2one('stock.production.lot', string='Lot/Serial Number', copy=False,
                                       check_company=True,
                                       domain="[('product_id', '=', product_id), ('company_id', '=', company_id)]")
    # cod_linea_work = fields.Many2one('mrp.workcenter', string='Linea de trabajo')
    date = fields.Date(string="Fecha")
    date_ini = fields.Date(string="Fecha Desde")
    date_end = fields.Date(string="Fecha Hasta")
    product_tod = fields.Char(string="Producto todos")
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

    type = fields.Selection(
        [('xlsx', 'XLSX'),
         ('pdf', 'PDF')],
        string="Tipo de archivo",
        default='pdf')

    def check_report(self):
        if self.type == 'pdf':
            return self.env.ref("py_ctrm_mrp.report_resumen_superalimentos").report_action(self)
        else:
            raise ValidationError('Aun no esta implementado en xlsx ')

    def _print_report(self, data):
        data['form'].update(self.read(['date_ini',
                                       'date_end',
                                       'type'])[0])
        if self.type == 'pdf':
            return self.env.ref(
                'py_ctrm_mrp.'
                'report_resumen_superalimentos').report_action(
                self, data=data)
        else:
            raise ValidationError('Aun no esta implementado en xlsx ')

    def datos(self):
        for record in self:
            orden = 'name asc'
            domain = []
            domain += [('company_id', '=', record.company_id.id),
                       ('state', '=', 'done'),
                       ('date_planned_start', '>=', record.date_ini),
                       ('date_planned_start', '<=', record.date_end),
                       ('tipo_producto', '=', record.tipo_producto),
                       ('tipo_producto','not ilike',"2"),
                       ('tipo_producto','not ilike',"3")]

            if record.cod_proveedor:
                domain += [('cod_proveedor', '=', record.cod_proveedor.id)]

            if record.lot_producing_id:
                domain += [('lot_producing_id', '=', record.lot_producing_id.id)]

            if record.production_cab_id:
                domain += [('production_cab_id', '=', record.production_cab_id.id)]

            if record.product_id:
                domain += [('product_id', '=', record.product_id.id)]

            if record.product_tod:
                domain += [("product_id", "ilike", record.product_tod)]

            # if record.tipo_producto:
            #     domain +=[('tipo_producto','=', )]


            produccion = request.env['mrp.production.cab'].search(domain, order=orden)
            print(produccion)
            return produccion

    def agregar_punto_de_miles(self, numero):
        numero_con_punto = '.'.join([str(int(numero))[::-1][i:i + 3] for i in range(0, len(str(int(numero))), 3)])[::-1]
        num_return = numero_con_punto
        return num_return

    def agregar_decimal(self, numero):
        numero_decimal = '{0:.2f}'.format(numero)
        num_return = numero_decimal
        return num_return

    def compute_reporte(self):
        for rec in self:
            obj = rec.env['mrp.production.cab'].search([("lot_producing_id", "=", rec.lot_producing_id.id)])
            ordenado = obj.sorted(key=lambda r: r.date_planned_start)
            if len(ordenado) == 1:
                rec.update({"bruto_reporte": ordenado[0].product_qty})
                rec.update({"final_reporte": ordenado[len(ordenado) - 1].qty_producing})
                rec.update({"final_porce": ordenado[len(ordenado) - 1].product_final_porce})
                rec.update({"bb_reporte": ordenado[len(ordenado) - 1].bibag_count})
                rec.update({"pureza_reporte": ordenado[len(ordenado) - 1].big_bag_promedio})
                rec.update({"humedad_reporte": ordenado[len(ordenado) - 1].humedad})
                rec.update({"big_bag_promedio_final": ordenado[len(ordenado) - 1].big_bag_promedio_final})
                rec.update({"merma_porce": (ordenado[0].merma / (ordenado[0].product_qty + 1)) * 100})
                print(ordenado[0].merma)
                print("merma")
                print(ordenado[0].product_qty)
            elif len(ordenado) > 1:
                valor_menor2 = ordenado[0].product_qty
                valor_menor = ordenado[0].product_qty / len(ordenado)
                valor_mayor2 = ordenado[len(ordenado) - 1].qty_producing
                valor_mayor = ordenado[len(ordenado) - 1].qty_producing / len(ordenado)
                porce_mayor = ordenado[len(ordenado) - 1].product_final_porce / len(ordenado)
                bigbag_mayor2 = ordenado[len(ordenado) - 1].bibag_count / len(ordenado)
                bigbag_mayor = ordenado[len(ordenado) - 1].bibag_count / len(ordenado)
                pureza_mayor2 = ordenado[len(ordenado) - 1].big_bag_promedio
                pureza_mayor = ordenado[len(ordenado) - 1].big_bag_promedio / len(ordenado)
                humedad_mayor2 = ordenado[len(ordenado) - 1].humedad
                humedad_mayor = ordenado[len(ordenado) - 1].humedad / len(ordenado)
                nota_mayor = ordenado[len(ordenado) - 1].big_bag_promedio_final / len(ordenado)
                mer_por = 0
                cont = 0
                for ll in ordenado:
                    ll.update({"bruto_reporte": valor_menor})
                    ll.update({"final_reporte": valor_mayor})
                    ll.update({"final_porce": porce_mayor})
                    ll.update({"bb_reporte": bigbag_mayor})
                    ll.update({"pureza_reporte": pureza_mayor})
                    ll.update({"humedad_reporte": humedad_mayor})
                    ll.update({"big_bag_promedio_final": nota_mayor})

                    ll.update({"bruto_reporte2": valor_menor2})
                    ll.update({"final_reporte2": valor_mayor2})
                    # ll.update({"final_porce2": porce_mayor2})
                    ll.update({"bb_reporte2": bigbag_mayor2})
                    ll.update({"pureza_reporte2": pureza_mayor2})
                    ll.update({"humedad_reporte2": humedad_mayor2})
                    # ll.update({"big_bag_promedio_final": nota_mayor})
                    print("bruto_reporte2")
                    print(ll.bruto_reporte2)
                    print(ll.tipo_producto)
                    print("codigo producto")
                    if ll.tipo_producto == '1' or ll.tipo_producto == '4':
                        mer_por = mer_por + ordenado[len(ll) - 1].merma
                        print("ciclo")
                        print(ordenado[len(ll) - 1].merma)
                        print(mer_por)
                        cont = cont + 1
                    elif ll.tipo_producto == '2' or ll.tipo_producto == '3':
                        print("no es nuevo producto o reproceso")

                rec.update({"merma_porce": ((mer_por / ordenado[0].product_qty) * 100) / cont})


