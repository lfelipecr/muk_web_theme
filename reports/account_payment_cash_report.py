# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from datetime import date, datetime

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

trimester_group = {
    "1": 1,
    "2": 2,
    "3": 3,
    "4": 4,
    "01-03": 1,
    "04-06": 2,
    "07-09": 3,
    "10-12": 4,
    "1-3": 1,
    "4-6": 2,
    "7-9": 3,
}

month_to_trimester = {
    '1': 1,
    '2': 1,
    '3': 1,
    '4': 2,
    '5': 2,
    '6': 2,
    '7': 3,
    '8': 3,
    '9': 3,
    '10': 4,
    '11': 4,
    '12': 4,
}


class PrintReportCashFinancial(models.AbstractModel):
    _name = 'report.l10n_cr_municipality_extend.report_cash_financial'
    _description = 'Reporte de Caja'

    def _get_report_data(self, data):
        # El campo ocultar permite mostrar o no según sea el caso, el campo TOTAL PAGADO HOY
        ocultar = False
        if data['mode'] == 'date':
            dates = 'Hoy ' + str(data['date_now'])
        else:
            dates = 'Del ' + str(data['date_from']) + ' hasta al ' + str(data['date_to'])

            hasta = datetime.strptime(data['date_to'], '%Y-%m-%d')
            if hasta.date() < date.today():
                ocultar = True

        date_hoy = str(date.today().day) + ' de ' + str(date_month[str(date.today().month)]) + ' del ' + str(date.today().year)

        if len(data['account_payment_ids']) == 1:
            payments_ids = '(' + str(data['account_payment_ids'][0]) + ')'
        else:
            payments_ids = tuple(data['account_payment_ids'])

        response = {
            'pages': 1,
            'fechas': dates,
            'fecha_hoy': date_hoy,
            'total': self._amount_total(payments_ids)['total'],
            'total_pagado_hoy': self._amount_hoy(payments_ids, date.today())['total'],
            'tipos_patentes': self._type_patent_amount_total(payments_ids),
            'trimestres': self._type_patent_amount_trimester(payments_ids),
            # 'formas_pago': self._type_form_paid(payments_ids),
            'ocultar': ocultar,
            'usuario': data['user']
        }
        return response

    @api.model
    def _get_report_values(self, docids, data=None):
        return {'data': self._get_report_data(data)}

    def _type_patent_amount_total(self, payment_ids):
        invoice_ids = self.env['account.payment'].sudo().browse(payment_ids).mapped('reconciled_invoice_ids')
        if len(invoice_ids.ids) == 1:
            invoice_ides = '(' + str(invoice_ids.ids[0]) + ')'
        else:
            invoice_ides = tuple(invoice_ids.ids)

        sql = """
              select
                pat.code as code,
                aml.year,
                pat."name" as tipo_patente,
                SUM(aml.debit - aml.amount_residual) as colones
                from
                l10n_cr_patent pa
                inner join l10n_cr_patent_type pat on pa.type_id = pat.id
                inner join account_move am on pa.id = am.patent_id
                inner join account_move_line aml on am.id = aml.move_id
                where aml.debit > 0  and am.id in {0}                                 
                group by 
                pat.code,
                aml."year",
                pat."name"
                order by 1 desc;

              """.format(invoice_ides)
        print(sql)
        self.env.cr.execute(sql)
        data = self.env.cr.dictfetchall()

        def _group_by_year(name, d):
            if len(amounts[name]) == 0:
                amounts[name].append({'year': d['year'], 'amount': d['colones']})
            else:
                sw = 0
                for p in amounts[name]:
                    if p['year'] == d['year']:
                        p['amount'] += d['colones']
                        sw = 1
                if sw == 0:
                    amounts[name].append({'year': d['year'], 'amount': d['colones']})

        amounts = {
            'rt_amount': 0.0,
            'rt_periods': [],
            'rs_amount': 0.0,
            'rs_periods': [],
            'em_amount': 0.0,
            'em_periods': [],
            'pr_amount': 0.0,
            'pr_periods': [],
            'lc_amount': 0.0,
            'lc_periods': [],
            'tm_amount': 0.0,
            'tm_periods': [],
            'totals': 0.0

        }

        CODES = ['rt', 'rs', 'em', 'pr', 'lc', 'tm']

        for cod in CODES:
            for d in data:
                if cod == d['code'].lower():
                    amounts[cod + '_amount'] += d['colones']
                    _group_by_year(cod + '_periods', d)

        amounts['totals'] = amounts['rt_amount'] + amounts['rs_amount'] + amounts['em_amount'] + amounts['pr_amount'] + amounts['lc_amount'] + amounts['tm_amount']

        return amounts

    def _type_patent_amount_trimester(self, payment_ids):
        print(payment_ids)
        invoice_ids = self.env['account.payment'].sudo().browse(payment_ids).mapped('reconciled_invoice_ids')
        if len(invoice_ids.ids) == 1:
            invoice_ides = '(' + str(invoice_ids.ids[0]) + ')'
        else:
            invoice_ides = tuple(invoice_ids.ids)
        sql = """
                 select
                   aml.move_id,
                   aml."name",
                   aml.year,
                   SUM(aml.credit) 
                     - (
                     (select amount_residual from account_move_line where debit > 0 and move_id = aml.move_id) / 
                     (select count(*) from account_move_line where credit > 0 and move_id = aml.move_id)
                     )
                     as amount
                   from
                   l10n_cr_patent pa
                   inner join l10n_cr_patent_type pat on pa.type_id = pat.id
                   inner join account_move am on pa.id = am.patent_id
                   inner join account_move_line aml on am.id = aml.move_id
                   where aml.credit > 0 and am."state" = 'posted' and am.id in {0}                                 
                   group by 
                   aml.move_id,
                   aml.year,
                   aml."name" 
                   order by 1 desc;

                 """.format(invoice_ides)
        # print(sql)
        self.env.cr.execute(sql)
        data = self.env.cr.dictfetchall()

        t1 = 0.0
        t2 = 0.0
        t3 = 0.0
        t4 = 0.0
        timbre = 0.0
        timbre_licor = 0.0
        total = 0.0

        amounts = {
            't1_amount': 0.0,
            't1_periods': [],
            't2_amount': 0.0,
            't2_periods': [],
            't3_amount': 0.0,
            't3_periods': [],
            't4_amount': 0.0,
            't4_periods': [],
            'timbre': 0.0,
            'timbre_periods': [],
            'timbre_licor': 0.0,
            'timbre_licor_periods': [],
            'totals': []
        }

        def _group_by_year(name, d):
            if len(amounts[name]) == 0:
                amounts[name].append({'year': d['year'], 'amount': d['amount']})
            else:
                sw = 0
                for p in amounts[name]:
                    if p['year'] == d['year']:
                        p['amount'] += d['amount']
                        sw = 1

                if sw == 0:
                    amounts[name].append({'year': d['year'], 'amount': d['amount']})

        for d in data:
            r = self.search_pos_trimester(d['name'].split(' '))
            if r == -1:
                amounts['timbre'] += d['amount']
                _group_by_year('timbre_periods', d)
            elif r == -2:
                amounts['timbre_licor'] += d['amount']
                _group_by_year('timbre_licor_periods', d)
            else:
                print(d['name'])
                trimester = trimester_group[str(d['name'].split(' ')[r])]
                if trimester == 1:
                    amounts['t1_amount'] += d['amount']
                    _group_by_year('t1_periods', d)
                elif trimester == 2:
                    amounts['t2_amount'] += d['amount']
                    _group_by_year('t2_periods', d)
                elif trimester == 3:
                    amounts['t3_amount'] += d['amount']
                    _group_by_year('t3_periods', d)
                else:
                    amounts['t4_amount'] += d['amount']
                    _group_by_year('t4_periods', d)

        amounts['totals'] = amounts['t1_amount'] + amounts['t2_amount'] + amounts['t3_amount'] + amounts['t4_amount'] + amounts['timbre'] + amounts['timbre_licor']
        """Tener en cuenta que t=Trimestre"""

        # trimestres = {
        #     't1': t1,
        #     't2': t2,
        #     't3': t3,
        #     't4': t4,
        #     'timbre': timbre,
        #     'timbre_licor': timbre_licor,
        #     'total': total
        # }
        return amounts

    def search_pos_trimester(self, name):

        if name[0] in ('Timbre', 'Intereses'):
            if len(name) == 3 and name[2] == 'Licores':
                pos = -2
            else:
                pos = -1
        else:
            pos = 0
            for x in name:
                if x in ('trimestre', 'trimester', 'Trimestre'):
                    pos += 1
                    break
                pos += 1

        return pos

    # def _type_form_paid(self,payment_ids):
    #     sql = """
    #             select
    #                 coalesce(pm.id,0) as id,
    #                 coalesce(pm."name",'No definido') as descripcion,
    #                 SUM(ap.amount),
    #                 --SUM(am_paid.amount_total) as usd,
    #                 SUM(am_paid.amount_total_signed) as colones,
    #                 SUM(case when am_paid.amount_total=am_paid.amount_total_signed then 0 else  am_paid.amount_total end) as usd
    #                 from
    #                 account_move am_paid
    #                 inner join account_payment ap on am_paid.id = ap.move_id
    #                 left join payment_methods pm on ap.payment_methods_id = pm.id
    #                 inner join account_move_line aml on am_paid.id = aml.move_id
    #                 where ap.id in {0}
    #                 group by pm.id
    #                 order by pm.id asc;
    #                  """.format(payment_ids)
    #     self.env.cr.execute(sql)
    #     return self.env.cr.dictfetchall()

    def _amount_total(self, payment_ids):
        invoice_ids = self.env['account.payment'].sudo().browse(payment_ids).mapped('reconciled_invoice_ids')
        if len(invoice_ids.ids) == 1:
            invoice_ides = '(' + str(invoice_ids.ids[0]) + ')'
        else:
            invoice_ides = tuple(invoice_ids.ids)
        sql = """
                select               
                SUM(aml.debit - aml.amount_residual) as total
                from
                l10n_cr_patent pa
                inner join l10n_cr_patent_type pat on pa.type_id = pat.id
                inner join account_move am on pa.id = am.patent_id
                inner join account_move_line aml on am.id = aml.move_id
                where aml.debit > 0  and am.id in {0} """.format(invoice_ides)
        self.env.cr.execute(sql)
        return self.env.cr.dictfetchone()

    def _amount_hoy(self, payment_ids, hoy):
        sql = """
              select
              coalesce(SUM(am_paid.amount_total_signed),0) as total
              from
              account_move am_paid 
              inner join account_payment ap on am_paid.id = ap.move_id 
              where ap.id in {0} and am_paid.date = '{1}' """.format(payment_ids, hoy)
        self.env.cr.execute(sql)
        return self.env.cr.dictfetchone()