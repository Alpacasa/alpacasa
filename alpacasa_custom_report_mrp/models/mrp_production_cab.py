import json
import datetime
import base64
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_compare, float_round, float_is_zero, format_datetime
from odoo.modules.module import get_module_resource

from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES


class MrpProduccionAlpa(models.Model):
    _name = 'mrp.production.cab'
    _description = 'Orden de Producción Alpacasa'
    _order = 'date_planned_start desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'stock.valuation.layer', 'stock.quant']



    date_ini = fields.Date(string="Fecha desde")
    date_end = fields.Date(string="Fecha hasta")
    merma = fields.Float('merma', compute="_compute_merma", store=True)
    merma2 = fields.Float('merma*', compute="_compute_merma", store=True)
    cant_bb = fields.Float('cant_bb')
    humedad = fields.Float('humedad', compute="_compute_check_bigbag", store=True)
    nota_prom = fields.Integer('notaprom', compute='_compute_check_bigbag', store=True)
    costototal = fields.Float('costototal')
    costo_kg = fields.Float('costokilo')
    costo_final = fields.Float('costofinal')
    Pureza = fields.Float('pureza', compute="_compute_check_bigbag", store=True)
    bruto_reporte = fields.Float('Peso en bruto', compute="compute_reporte", store=True)
    bruto_reporte2 = fields.Float('Peso en bruto*', compute="compute_reporte", store=True)
    final_reporte = fields.Float('Peso Final', compute="compute_reporte", store=True)
    final_reporte2 = fields.Float('Peso Final*', compute="compute_reporte", store=True)
    bb_reporte = fields.Float('Cantidad de BigBags', compute="compute_reporte", store=True)
    bb_reporte2 = fields.Float('Cantidad de BigBags*', compute="compute_reporte", store=True)
    final_porce = fields.Float('Producto Final%', compute="compute_reporte", store=True)
    final_porce2 = fields.Float('Producto Final%*', compute="compute_reporte", store=True)
    humedad_reporte = fields.Float('Humedad', compute="compute_reporte", store=True)
    humedad_reporte2 = fields.Float('Humedad*', compute="compute_reporte", store=True)
    pureza_reporte = fields.Float('Purezas', compute="_compute_check_bigbag", store=True)
    pureza_reporte2 = fields.Float('Pureza*', compute="_compute_check_bigbag", store=True)
    costototal_reporte = fields.Float('Costo Total', compute= "compute_reporte", store=True)
    costototal_reporte2 = fields.Float('Costo Total*', compute= "compute_reporte", store=True)
    costo_kg_reporte = fields.Float('Costo Por Kilo', compute= "compute_reporte", store=True)
    costo_kg_reporte2 = fields.Float('Costo Por Kilo*', compute= "compute_reporte", store=True)
    costo_final_reporte = fields.Float('Costo Final', compute= "compute_reporte", store=True)
    costo_final_reporte2 = fields.Float('Costo Final*', compute= "compute_reporte", store=True)
    merma_porce = fields.Float('Descuento %', compute="compute_reporte", store=True)
    merma_porce2 = fields.Float('Descuento %*', compute="compute_reporte", store=True)
    horas_reporte = fields.Float('Cantidad de horas',compute="compute_reporte",store=True)
    # proveedor_reporte = fields.Char('Proveedor', compute="compute_reporte", store=True)
    # todos los campos con "_reporte" son para realizar la nueva linea la cual se mostrara en la parte inicial de la vista tipo pivot
    # final



    big_bag_promedio_final = fields.Float('Promedio nota', compute='compute_reporte', store=True)
    nota = fields.Char('Nota Promedio', compute='compute_reporte', store=True)



    @api.depends('state', 'qty_producing', 'product_qty')
    def _compute_merma(self):
        for line in self:
            if line.state == 'progress':
                line.merma = line.product_qty - line.qty_producing
                line.update({
                    'merma': line.merma,
                    'merma2': line.merma
                })
            elif line.state == 'done':
                line.merma = line.product_qty - line.qty_producing
                line.update({
                    'merma': line.merma,
                    'merma2': line.merma
                })

    def _compute_check_bigbag(self):
        # traemos la lista de las ordenes de produccion
        # lista_produccion = self.env['']
        for production_cab in self:
            check_ids = self.env['quality.check'].search(
                [('company_id', '=', self.company_id.id),
                 ('production_cab_id', '=', production_cab.id)])

            cont = 0
            cont_cat_a = 0
            cont_cat_b = 0
            cont_cat_c = 0
            cont_cat_d = 0
            cont_fail = 0
            cont_cat_prom = 0
            promedio = 0
            prom_hum = 0
            humedad = 0
            for check in check_ids:
                humedad = check.humedad
                prom_hum = prom_hum + humedad
                if check.big_bag and check.quality_cat == 'A':
                    cont = cont + 1
                    cont_cat_a = cont_cat_a + 1
                    promedio = promedio + check.pureza
                    cont_cat_prom = cont_cat_prom + 1
                elif check.big_bag and check.quality_cat == 'B':
                    cont = cont + 1
                    cont_cat_b = cont_cat_b + 1
                    promedio = promedio + check.pureza
                    cont_cat_prom = cont_cat_prom + 2
                elif check.big_bag and check.quality_cat == 'C':
                    cont = cont + 1
                    cont_cat_c = cont_cat_c + 1
                    promedio = promedio + check.pureza
                    cont_cat_prom = cont_cat_prom + 3
                elif check.big_bag and check.quality_cat == 'D':
                    cont = cont + 1
                    cont_cat_d = cont_cat_d + 1
                    promedio = promedio + check.pureza
                    cont_cat_prom = cont_cat_prom + 4


                if check.quality_state == 'fail':
                    if check.big_bag:
                        cont_fail = cont_fail + 1
            production_cab.bibag_count = cont
            production_cab.bibag_count_fail = cont_fail
            production_cab.bigbag_a = cont_cat_a
            production_cab.bigbag_b = cont_cat_b
            production_cab.bigbag_c = cont_cat_c
            production_cab.bigbag_d = cont_cat_d
            if cont > 0:
                # for n in self:
                production_cab.update({'big_bag_promedio_final': round(cont_cat_prom / cont)})
                production_cab.update({'big_bag_promedio': (promedio / cont)})
                production_cab.update({'humedad': prom_hum / cont})
                if production_cab.big_bag_promedio_final == 1.0:
                    production_cab.nota = "A"
                elif production_cab.big_bag_promedio_final == 2.0:
                    production_cab.nota = "B"
                elif production_cab.big_bag_promedio_final == 3.0:
                    production_cab.nota = "C"
                elif production_cab.big_bag_promedio_final == 4.0:
                    production_cab.nota = "D"
            else:
                production_cab.update({'big_bag_promedio_final': 0})
        production_cab.compute_reporte()


    def compute_reporte(self):
        for rec in self:
            obj = rec.env['mrp.production.cab'].search([("lot_producing_id", "=", rec.lot_producing_id.id)])
            ordenado = obj.sorted(key=lambda r: r.date_planned_start)
            pivo_id = 0
            nom_lot = obj.lot_producing_id.name
            lista_mat = obj.bom_id.bom_line_ids.product_id.id
            nom_brut = rec.env['stock.production.lot'].search([("product_id", "=", lista_mat)])
            for x in nom_brut:
                if x.name == nom_lot:
                    pivo_id = x.id

            if nom_lot == "AL-CH 06/22":
                pivo_id = 1016
            if nom_lot == "AL-CH-BIO 16/22":
                pivo_id = 1044

            lot = rec.env['stock.move.line'].search([("lot_id", "=", pivo_id)])
            print("xdxdxdxdxd")
            tot_cost = 0
            for x in lot.picking_id:
                tot_cost += x.update_costs
                print(x.partner_id.name)
                rec.update({"cod_proveedor": x.partner_id})
            cos_kg = tot_cost / ordenado[0].product_qty
            cos_fin = tot_cost / ordenado[len(ordenado)-1].qty_producing
            rec.update({"costototal_reporte": tot_cost})
            rec.update({"costo_kg_reporte": cos_kg})
            rec.update({"costo_final_reporte": cos_fin})

            print(rec.cod_proveedor)
            print(rec.costototal_reporte)


            # cos = rec.env['stock.picking'].search([("id", "=", rec.lot_producing_id.id)])
            # ordenado3 = cos.sorted(key=lambda r: r.date_done)


            pivo = rec.env['mrp.routing.workcenter.cab'].search([('id', '=', self.production_cab_id.id)])
            rec.horas_reporte = pivo.duration

            for x in pivo:
                if x.workcenter_cab_ids:
                    rec.cod_linea_work = x.workcenter_cab_ids.cod_linea_work.id

            prov = self.env['mrp.production.cab'].search(
                [('company_id', '=', self.company_id.id), ("lot_producing_id", "=", rec.lot_producing_id.id)])
            self.cod_proveedor = prov.cod_proveedor.id
            print("nombre de proveedor")
            print(self.cod_proveedor)
            print(prov.cod_proveedor)
            print(prov.cod_proveedor.id)


            if len(ordenado) == 1:
                print("cantidad de horas")
                print(ordenado[0].horas_reporte)
                for x in self:
                    pivot = x.env['mrp.routing.workcenter.cab'].search(
                        [('company_id', '=', self.company_id.id), ('production_cab_id', '=', x.id)])
                    if pivot.duration:
                        dato = pivot.duration
                        calculo = dato / 60
                        print(pivot.hora_convertido)
                        self.update({"horas_reporte": pivot.hora_convertido})
                        print(self.horas_reporte)
                rec.update({"bruto_reporte": ordenado[0].product_qty})
                rec.update({"bruto_reporte2": ordenado[0].product_qty})
                rec.update({"final_reporte": ordenado[len(ordenado)-1].qty_producing})
                rec.update({"final_reporte2": ordenado[len(ordenado) - 1].qty_producing})
                rec.update({"final_porce": ordenado[len(ordenado) - 1].product_final_porce})
                rec.update({"final_porce2": ordenado[len(ordenado) - 1].product_final_porce})
                rec.update({"bb_reporte": ordenado[len(ordenado) - 1].bibag_count})
                rec.update({"bb_reporte2": ordenado[len(ordenado) - 1].bibag_count})
                rec.update({"pureza_reporte": ordenado[len(ordenado) - 1].big_bag_promedio})
                rec.update({"pureza_reporte2": ordenado[len(ordenado) - 1].big_bag_promedio})
                rec.update({"humedad_reporte": ordenado[len(ordenado) - 1].humedad})
                rec.update({"humedad_reporte2": ordenado[len(ordenado) - 1].humedad})
                rec.update({"big_bag_promedio_final": ordenado[len(ordenado)-1].big_bag_promedio_final})
                rec.update({"merma": ordenado[0].product_qty - ordenado[len(ordenado) - 1].qty_producing})
                rec.update({"merma_porce": (ordenado[len(ordenado) - 1].merma/(ordenado[0].product_qty))*100})
                rec.update({"merma_porce2":(ordenado[0].merma/(ordenado[0].product_qty))*100})
                rec.update({"horas_reporte": calculo})

                # if len(ordenado3) == 1:
                #     rec.update({"costototal_reporte": ordenado3[0].update_costs})
                #     rec.update({"costo_kg_reporte": ordenado3[0].update_costs/ordenado[0].product_qty})
                #     rec.update({"costo_final_reporte": ordenado3[0].update_costs / ordenado[len(ordenado)-1].qty_producing})



                if ordenado[0].merma == ordenado[0].product_qty:
                    ordenado[0].merma = 0


            elif len(ordenado) > 1:
                mer_por = 0
                cont = 0
                dato = 0
                for ll in ordenado:
                    if ll.tipo_producto == '1' or ll.tipo_producto == '4':
                        cont = cont + 1

                        pivot = ll.env['mrp.routing.workcenter.cab'].search([('company_id', '=', self.company_id.id), ('production_cab_id', '=', ll.id)])
                        if pivot.duration:
                            dato = dato + pivot.duration
                            print(dato)
                    elif ll.tipo_producto == '2' or ll.tipo_producto == '3':
                        print("no es nuevo producto o reproceso")
                calculo = dato / 60

                print(calculo)

                print(self.horas_reporte)
                valor_menor2 = ordenado[0].product_qty
                valor_menor = ordenado[0].product_qty / cont
                valor_mayor2 = ordenado[len(ordenado) - 1].qty_producing
                valor_mayor = ordenado[len(ordenado)-1].qty_producing / cont
                porce_mayor = ordenado[len(ordenado)-1].product_final_porce / cont
                bigbag_mayor2 = ordenado[len(ordenado) - 1].bibag_count
                bigbag_mayor = ordenado[len(ordenado)-1].bibag_count / cont
                pureza_mayor2 = ordenado[len(ordenado) - 1].big_bag_promedio
                pureza_mayor = ordenado[len(ordenado)-1].big_bag_promedio / cont
                humedad_mayor2 = ordenado[len(ordenado) - 1].humedad
                humedad_mayor = ordenado[len(ordenado) - 1].humedad / cont
                nota_mayor = ordenado[len(ordenado)-1].big_bag_promedio_final / cont

                # if len(ordenado3) > 1:
                #     costo_mayor = ordenado3[0].update_costs / cont
                #     costo_mayor2 = ordenado3[0].update_costs
                #     costo_kg = ordenado3[0].update_costs / ordenado[0].product_qty / cont
                #     costo_kg2 = ordenado3[0].update_costs / ordenado[0].product_qty / cont
                #     costo_final = ordenado3[0].update_costs / ordenado[len(ordenado) - 1].qty_producing / cont
                #     costo_final2 = ordenado3[0].update_costs / ordenado[len(ordenado) - 1].qty_producing
                #     ll.update({"costototal_reporte": costo_mayor})
                #     ll.update({"costo_kg_reporte": costo_kg})
                #     ll.update({"costo_final_reporte": costo_final})
                #     ll.update({"costototal_reporte2": costo_mayor2})
                #     ll.update({"costo_kg_reporte2": costo_kg2})
                #     ll.update({"costo_final_reporte2": costo_final2})



                for ll in ordenado:
                    ll.update({"bruto_reporte":valor_menor})
                    ll.update({"final_reporte":valor_mayor})
                    ll.update({"final_porce":porce_mayor})
                    ll.update({"bb_reporte":bigbag_mayor})
                    ll.update({"pureza_reporte": pureza_mayor})
                    ll.update({"humedad_reporte": humedad_mayor})
                    ll.update({"big_bag_promedio_final": nota_mayor})
                    ll.update({"horas_reporte": round(calculo)})

                    ll.update({"bruto_reporte2": valor_menor2})
                    ll.update({"final_reporte2": valor_mayor2})
                    # ll.update({"final_porce2": porce_mayor2})
                    ll.update({"bb_reporte2": bigbag_mayor2})
                    ll.update({"pureza_reporte2": pureza_mayor2})
                    ll.update({"humedad_reporte2": humedad_mayor2})
                    ll.update({"big_bag_promedio_final": nota_mayor})



                    if ll.tipo_producto == '1' or ll.tipo_producto == '4':
                        mer_por = mer_por + ll.merma
                        cont = cont+1
                    elif ll.tipo_producto == '2' or ll.tipo_producto == '3':
                        print("no es nuevo producto o reproceso")


                rec.update({"merma_porce": ((mer_por / ordenado[0].product_qty)*100)/cont})
                rec.update({"merma_porce2": ((mer_por / ordenado[0].product_qty) * 100)})
                rec.update({"merma2": mer_por})