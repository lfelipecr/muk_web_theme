# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from datetime import date, datetime
import logging
logger = logging.getLogger(__name__)

PAY_LINES_PER_PAGE = 20
date_month = {
    '1': 'Enero',
    '2': 'Febrero',
    '3': 'Marzo',
    '4': 'Abril',
    '5': 'Mayo',
    '6': 'Junio',
    '7': 'Julio',
    '8': 'Agosto',
    '9': 'Setiembre',
    '10': 'Octubre',
    '11': 'Noviembre',
    '12': 'Diciembre',
}
trimester_month_final = {
    "t1": 3,
    "t2": 6,
    "t3": 9,
    "t4": 12,
}
class PrintReportPatentsDefaulterFinancial(models.AbstractModel):
    _name = 'report.l10n_cr_municipality_extend.report_defaulter_financial'
    _description = 'Reporte de Patentes Morosas'


    def _get_report_data(self, data):

        if data['mode'] == 'all':
            dates = 'hasta hoy'
        else:
            dates = 'hasta el ' + str(data['date'])

        date_hoy = str(date.today().day)+' de ' + str(date_month[str(date.today().month)]) + ' del ' + str(date.today().year)

        title = 'Morosidad ' + dates

        response = {
            'pages': 1,
            'fechas': dates,
            'fecha_hoy': date_hoy,
            'datas': self._process_data(data),
            'usuario': data['user'],
            'title': title
        }
        return response


    @api.model
    def _get_report_values(self, docids, data=None):
        return {'data': self._get_report_data(data)}

    def _process_data(self,data):
        datos = self._response_sql(data)
        array_datos = []
        for d in datos:
            balance = 0.0
            balance = self._balance(d, data)

            array_datos.append({
                'numero': d['numero'],
                'patentado': d['patentado'],
                'telefono': d['telefono'],
                'email': d['email'],
                'negocio': d['negocio'],
                'distrito': d['distrito'],
                'fecha_solicitud': d['fecha_solicitud'],
                'pay_to': d['pay_to'],
                'pago_trimestral': balance,
            })


        return array_datos



    def _balance(self, dato, data): #where data is json from wizard

        balance = 0.0
        product_interes_id = self.env.ref('l10n_cr_municipality_extend.product_intereses').id

        patent = self.env['l10n_cr.patent'].sudo().browse(int(dato['id']))

        logger.info('Patente: %s' % (patent.name))

        if data['mode'] == 'all':
            fecha = date.today()
        else:
            fecha = data['date']

        if patent:
            # if patent.name == 'RT-01-0031':
            #     a=1
            invs_braft = patent.invoices_ids.filtered(lambda i: i.state == 'draft')
            invs_residual = patent.invoices_ids.filtered(lambda i: i.state == 'posted' and i.amount_residual > 0)

            sum_price_subtotal = 0.0
            sum_interes = 0.0
            for inv_d in invs_braft:
                #print(inv_d.name)
                sum_price_subtotal += sum(inv_d.invoice_line_ids.filtered(lambda l: l.product_id.id != product_interes_id).mapped('price_subtotal'))
                patent._caculate_interes_by_move(inv_d, 'not_assign', fecha)
                sum_interes += sum(line.interes for line in inv_d.invoice_line_ids)

            for inv_r in invs_residual:
                #print(inv_r.name)
                sum_price_subtotal += inv_r.amount_residual

            total = sum_price_subtotal + sum_interes


        logger.info('Interes: %s / Subtotales: %s / BALANCE: %s' % (str(sum_interes), str(sum_price_subtotal), str(total)) )

        balance += total

        return balance


    def _response_sql(self, data):

        if data['mode'] == 'all':
            fecha = date.today()
        else:
            fecha = data['date']

        sql = """
                select
                    p.id,
                    p."name" as numero,
                    p.resolution_date as fecha_solicitud,
                    p.pay_to,
                    rp."name" as patentado,
                    rp.phone as telefono,
                    rp.email,
                    p.fantasy_name as negocio,
                    (case when p.regimen='traditional' then 'Tradicional' else 'Simplificado' end) as regimen,
                    coalesce(rcd."name",'No especificado') as distrito,
                    extract(month from p.pay_to) as ultimo_mes_pagado,
                    extract(month from current_date) as mes_hoy,
                    round((p.yearly_payment/4),2) as pago_trimestral
                    from l10n_cr_patent p
                    inner join l10n_cr_patent_type pt on p.type_id = pt.id
                    inner join res_partner rp on p.partner_id = rp.id
                    left join res_country_district rcd on p.district_id = rcd.id
                    --inner join l10n_cr_ciiu_l10n_cr_patent_rel rel on rel.l10n_cr_patent_id = p.id
                    where p.state = 'approved'
                    and p.pay_to < '{0}'
                    --and extract(month from p.pay_to) < extract(month from current_date)
                    order by 1 asc
              """.format(fecha)
        self.env.cr.execute(sql)
        response = self.env.cr.dictfetchall()
        return response

