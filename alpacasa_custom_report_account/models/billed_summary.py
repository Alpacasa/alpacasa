# -*- coding: utf-8 -*-
from odoo import fields, models, exceptions, api
import time, collections
import io, datetime
from odoo.exceptions import ValidationError
import xlsxwriter
import logging
from datetime import datetime
from datetime import date
import base64
import xlwt
import base64
import xlsxwriter
from io import StringIO
from odoo import http, _
from odoo.http import request
from odoo.addons.web.controllers.main import serialize_exception, content_disposition

_logger = logging.getLogger(__name__)
import werkzeug


class WizardBilledSummary(models.TransientModel):
    _name = "billed.summary.report"
    _description = "Informe de Cobranza Resumido"

    def _get_this_month(self):
        today = datetime.now()
        month = str(today.month)
        return '0' + month if len(month) == 1 else month

    type = fields.Selection([('xlsx', 'XLSX'), ('pdf', 'PDF')], string="Tipo de archivo", default='pdf')
    today_date = fields.Datetime(string='Fecha de hoy', default=lambda self: fields.datetime.now())
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True,
                                 default=lambda self: self.env.company)

    date_ini = fields.Date(string="Fecha desde")
    date_end = fields.Date(string="Fecha hasta")

    cliente = fields.Many2one('res.partner', string='Cliente')
    cobrador = fields.Many2one('sales.team.asig', string='Cobrador')


    margen_desde = fields.Float(string='% Margen Desde', default='1')
    margen_hasta = fields.Float(string='% Margen Hasta', default='100')
    comision_id = fields.Many2one('range.comisiones', string='Comisiones', tracking=True)

# en este sector se ingresa para la parte de tipo de orden de impresion
    orden = fields.Selection(
        [('rango', 'Rango Comisión'),
         ('margen', 'Margen')],
        default='margen'
    )
    type_report = fields.Selection([('detallado', 'Detallado'),
                                    ('resumido', 'Resumido'),
                                    ('detallado_rango', 'Detallado por Rango de Comisión'),
                                    ('resumido_rango', 'Resumido por Rango de Comisión')], string="Tipo de Reporte",default='detallado')

    @api.model
    def _get_default_company(self):
        return self.env.user.company_id.id


    def check_report(self):
        if self.type == 'pdf':
            if self.type_report=='detallado':
                return self.env.ref("py_ctrm_account_report.report_billed_summary").report_action(self)
            else:
                if self.type_report == 'resumido':
                    return self.env.ref("py_ctrm_account_report.report_billed_summary_resu").report_action(self)
                else:
                    if self.type_report == 'detallado_rango':
                         return self.env.ref("py_ctrm_account_report.report_billed_summary_cate").report_action(self)
                    else:
                        if self.type_report == 'resumido_rango':
                            return self.env.ref("py_ctrm_account_report.report_billed_summary_resu_cate").report_action(self)
        else:
            if self.type == 'xlsx':
                return {
                    'type': 'ir.actions.act_url',
                    'url': '/getBilledSummaryRoute/' + str(self.id),
                    'target': 'current'
                }

    def _print_report(self, data):
        data['form'].update(self.read(['date_ini',
                                       'date_end',
                                       'margen_desde',
                                       'margen_hasta',
                                       'type'])[0])
        if self.type == 'pdf':
            return self.env.ref(
                'py_ctrm_account_report.'
                'report_billed_summary').report_action(
                self, data=data)
        else:
            return {
                'type': 'ir.actions.act_url',
                'url': '/getBilledSummaryRoute/' + str(self.id),
                'target': 'current'
            }

    def datos(self):
        for record in self:
            orden = 'name asc'
            domain = []
            domain += [('company_id', '=', record.company_id.id),
                       ('partner_type', '=', 'customer'),
                       ('state', '=', 'posted'),
                       # ('payment_state', '=', 'paid'),
                       ('payment_date', '>=', record.date_ini),
                       ('payment_date', '<=', record.date_end)]

            if record.cliente:
                domain += [('partner_id', '=', record.cliente.id)]

            if record.cobrador:
                domain += [('invoice_vendedor', '=', record.cobrador.id)]


            recibos = request.env['account.payment.group'].search(domain, order=orden)
            print(recibos)
            return recibos


    def agregar_punto_de_miles(self, numero):
        numero_con_punto = '.'.join([str(int(numero))[::-1][i:i + 3] for i in range(0, len(str(int(numero))), 3)])[::-1]
        num_return = numero_con_punto
        return num_return

    def agregar_decimal(self, numero):
        numero_decimal = '{0:.2f}'.format(numero)
        num_return = numero_decimal
        return num_return



class DownloadXLS(http.Controller):
    @http.route('/getBilledSummaryRoute/<int:id>', auth='public')
    def generarXLSX(self, id=None, **kw):
        record = request.env['billed.summary.report'].browse(id)
        i = 2
        fp = io.BytesIO()
        workbook = xlsxwriter.Workbook(fp, {'in_memory': True})
        domain = []
        domain += [('company_id', '=', record.company_id.id),
                   ('partner_type', '=', 'customer'),
                   ('state', '=', 'posted'),
                   # ('payment_state', '=', 'paid'),
                   ('payment_date', '>=', record.date_ini),
                   ('payment_date', '<=', record.date_end)]

        if record.cliente:
            domain += [('partner_id', '=', record.cliente.id)]

        if record.cobrador:
            domain += [('invoice_vendedor', '=', record.cobrador.id)]

        orden = 'name asc'
        recibos = request.env['account.payment.group'].search(domain, order=orden)

        costo = request.env['product.template']
        sheet = workbook.add_worksheet("Facturas Cobradas")
        bold = workbook.add_format({'bold': True, 'fg_color': 'white', 'align': 'left', 'border': 1})
        number_format2 = workbook.add_format({'num_format': '#,##0'})
        currency_format = workbook.add_format({'num_format': '#,##0.00'})
        merge_format1 = workbook.add_format({'align': 'left', 'valign': 'vleft', 'font_color': 'black'})


        sheet.set_column('A:D', 30)
        sheet.write(1, 0, 'Cliente', bold)
        sheet.write(1, 1, 'Factura', bold)
        write = sheet.write(1, 2, 'Fecha Recibo', bold)
        sheet.write(1, 3, 'Cobrador', bold)
        sheet.write(1, 4, 'Monto', bold)
        sheet.write(1, 5, 'Producto', bold)
        sheet.write(1, 6, 'Cantidad', bold)
        sheet.write(1, 7, 'Precio Unit', bold)
        sheet.write(1, 8, 'Costo', bold),
        sheet.write(1, 9, 'Total libre de impuestos', bold)
        sheet.write(1, 10, 'Total Monto', bold)
        sheet.write(1, 11, 'Margen', bold)
        sheet.write(1, 12, '% Margen', bold)


        if record.margen_desde and record.margen_hasta:
            for h in recibos:
                for u in h.matched_move_line_ids:
                    if u.journal_id.type == 'sale':
                        merge_format1 = workbook.add_format({'align': 'left', 'valign': 'vleft', 'font_color': 'black'})
                        diferencia_fecha = ""
                        # i = i + 1
                        bandera = 0
                        for linea in u.move_id.invoice_line_ids:
                            if linea.percent_margin >= record.margen_desde and linea.percent_margin <= record.margen_hasta:
                                bandera = 1
                                break
                        if bandera == 1:
                            i = i + 1
                            if u.move_id.partner_id:
                                sheet.write(i, 0, u.move_id.partner_id.name, merge_format1)
                                pass
                            sheet.write(i, 1, u.move_id.name, merge_format1)
                            sheet.write(i, 2, h.invoice_vendedor.name, merge_format1)
                            sheet.write(i, 3, h.payment_date.strftime('%d-%m-%Y'), merge_format1)

                            merge_format1 = workbook.add_format({'align': 'left', 'valign': 'vleft', 'font_color': 'black'})
                            sheet.write(i, 4, u.payment_group_matched_amount_store)

                    for x in h.matched_move_line_ids:
                        if x.journal_id.type == 'sale':
                            if x.move_id.invoice_line_ids:
                                for xx in x.move_id.invoice_line_ids:
                                    if xx.percent_margin >= record.margen_desde and xx.percent_margin <= record.margen_hasta:
                                        pivo = costo.search([('id', '=', xx.product_id.product_tmpl_id.id)])
                                        sheet.write(i, 5, xx.product_id.name, merge_format1)
                                        sheet.write(i, 6, xx.quantity)
                                        sheet.write(i, 7, xx.price_unit, number_format2)
                                        sheet.write(i, 8, pivo.standard_price, number_format2)
                                        sheet.write(i, 9, xx.price_subtotal, number_format2)
                                        sheet.write(i, 10, xx.price_total, number_format2)
                                        sheet.write(i, 11, xx.costs_margin_pyg, number_format2)
                                        sheet.write(i, 12, xx.percent_margin, currency_format)
                                        i = i + 1
        else:
            for h in recibos:
                for u in h.matched_move_line_ids:
                    if u.journal_id.type == 'sale':
                        merge_format1 = workbook.add_format({'align': 'left', 'valign': 'vleft', 'font_color': 'black'})
                        diferencia_fecha = ""
                        i = i + 1
                        if u.move_id.partner_id:
                            sheet.write(i, 0, u.move_id.partner_id.name, merge_format1)
                            pass
                        sheet.write(i, 1, u.move_id.name, merge_format1)
                        sheet.write(i, 2, h.invoice_vendedor.name, merge_format1)

                        merge_format1 = workbook.add_format({'align': 'left', 'valign': 'vleft', 'font_color': 'black'})
                        sheet.write(i, 3, h.payment_date.strftime('%d-%m-%Y'), merge_format1)
                        sheet.write(i, 4, u.payment_group_matched_amount_store)
                        i = i + 1

                    for x in h.matched_move_line_ids:
                        if x.journal_id.type == 'sale':
                            if x.move_id.invoice_line_ids:
                                for xx in x.move_id.invoice_line_ids:
                                    pivo = costo.search([('id', '=', xx.product_id.product_tmpl_id.id)])
                                    sheet.write(i, 5, xx.product_id.name, merge_format1)
                                    sheet.write(i, 6, xx.quantity)
                                    sheet.write(i, 7, xx.price_unit)
                                    sheet.write(i, 8, pivo.standard_price)
                                    sheet.write(i, 9, xx.price_subtotal)
                                    sheet.write(i, 10, xx.price_total)
                                    sheet.write(i, 11, xx.costs_margin_pyg)
                                    sheet.write(i, 12, xx.percent_margin)
                                    i = i + 1
        workbook.close()
        fp.seek(0)
        return request.make_response(fp.read(),
                                     [('Content-Type',
                                       'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                                      ('Content-Disposition', content_disposition('recibos.xlsx'))])