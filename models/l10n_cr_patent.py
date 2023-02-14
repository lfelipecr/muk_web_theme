from dateutil.parser import parser

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
import calendar
from datetime import date, datetime, timedelta
from odoo.tests import common, Form

import logging
_logger = logging.getLogger(__name__)
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
    "10-12": 4,
}

month_to_trimester = {
    "1": "t1",
    "2": "t1",
    "3": "t1",
    "4": "t2",
    "5": "t2",
    "6": "t2",
    "7": "t3",
    "8": "t3",
    "9": "t3",
    "10": "t4",
    "11": "t4",
    "12": "t4",
}

trimester_to_paid = {
    "t1": 3,
    "t2": 6,
    "t3": 9,
    "t4": 12,
}

trimester_letter = {
    1: 't1',
    2: 't2',
    3: 't3',
    4: 't4',
}

trimester_to_number = {
    "t1": 1,
    "t2": 2,
    "t3": 3,
    "t4": 4,
}


DESCRIPTION = {
    1: 'Enero a Marzo',
    2: 'Abril a Junio',
    3: 'Julio a Setiembre',
    4: 'Octubre a Diciembre',
}

month_range = {
    '1': [1,2,3],
    '2': [4,5,6],
    '3': [7,8,9],
    '4': [10,11,12],
}

timbre = 0.02 #TIMBRE 2 POR CIENTO
timbre_licor = 5000 #TIMBRE PARA LICORES 5000 COLONES

TYPE_TIMBRE = [
               ('nn','No aplica'),
               ('not_paid','Timbre Licor NO PAGADO'),
               ('in_process','Timbre Licor en una factura AUN NO PAGADA'),
               ('paid','Timbre Licor PAGADA')]


PERIOD = [
    ('2021','2021'),
    ('2022','2022'),
    ('2023','2023'),
    ('2024','2024'),
    ('2025','2025'),
]

class Patent(models.Model):
    _name = "l10n_cr.patent"
    _inherit = "l10n_cr.patent"
    _order = 'id desc'

    invoices_ids = fields.Many2many('account.move', string='Facturas relacionadas',readonly=True, copy=False)
    invoice_count = fields.Integer(string='Invoice Count', compute='_get_invoiced',readonly=True, copy=False)

    pay_to = fields.Date(string="Pagado A",store=True,copy=False,compute='_get_invoiced')
    month = fields.Integer(compute='_get_month_paid', defaut=0, copy=False, store=True)
    year = fields.Integer(compute='_get_month_paid', defaut=0, copy=False, store=True)

    pay_next = fields.Date(string='Posible "Pagado hasta el"',store=True,copy=False,compute='_get_invoiced')

    pay_next_visible = fields.Boolean(compute='_pay_next_visible')

    pago_timbre_licor = fields.Selection(TYPE_TIMBRE,default='not_paid',compute='_get_compute_state',store=True,
                                         string='Timbre Licor')

    patents_lines = fields.One2many('l10n_cr.patent.lines', 'patent_id')

    period = fields.Selection(PERIOD, related='company_id.period', readonly=True)
    generate_inv = fields.Boolean(compute='_get_month_paid', copy=False, store=True)
    #state = fields.Selection(selection_add=[('prevention', u'Prevenida')], ondelete={'prevention': 'cascade'})

    def write(self, vals):
        #Nuevo.
        if self.is_web and self.change_name:
            if 'type_id' in vals and 'district_id' in vals:
                patent_type = self.env['l10n_cr.patent.type'].sudo().browse(vals['type_id'])
                district = self.env['res.country.district'].sudo().browse(vals['district_id'])
                sequence = patent_type.sequence_id
                vals['name'] = (f"{patent_type.code}-{district.code}-{sequence.next_by_id()}")  # TODO district.code
                vals['change_name'] = False

        res = super(Patent, self).write(vals)
        return res



    @api.depends('pay_to', 'pay_next', 'invoices_ids.state')
    def _pay_next_visible(self):
        for pat in self:
            list_trimester = self.search_posted(pat)
            if list_trimester:
                year = int(list_trimester[0])
                month = list_trimester[1]
                mes = month_range[str(month)][2]
                monthRange = calendar.monthrange(year, mes)
                dia_tentativo = date(year, mes, monthRange[1])

                pat.pay_next = dia_tentativo
            else:
                pat.pay_next = False

            if pat.pay_next and pat.pay_to:
                if pat.pay_next == pat.pay_to:
                    pat.pay_next_visible = True
                else:
                    pat.pay_next_visible = False
            elif not pat.pay_next:
                pat.pay_next_visible = True
            else:
                pat.pay_next_visible = False

    @api.depends('invoices_ids','invoices_ids.state','invoices_ids.amount_residual','pay_to','invoices_ids.payment_state')
    def _get_compute_state(self):
        p_id = self.env.ref("l10n_cr_municipality.product_timbre_licores").id
        for patent in self:
            invs = patent.invoices_ids.filtered(lambda inv: inv.state == 'posted' and inv.amount_residual >= 0.0 and (not inv.reversal_move_id and not inv.reversed_entry_id))
            if patent.type_code=='LC' and patent.state=='approved' and len(invs)>0:
                if patent.pago_timbre_licor != False:
                    sw=0
                    for inv in invs:
                        for line in inv.invoice_line_ids:
                            if line.product_id.id == p_id:
                                if inv.amount_residual == 0.0:
                                    sw=2
                                else:
                                    sw=1
                                break
                        if sw>0:
                            break

                    if sw==2:
                        patent.pago_timbre_licor='paid'
                    elif sw==1:
                        patent.pago_timbre_licor='in_process'
                    else:
                        patent.pago_timbre_licor = 'not_paid'

            else:
                patent.pago_timbre_licor = 'nn'

    def validate_invoices_timbre_licor(self, factura):
        p_id = self.env.ref("l10n_cr_municipality.product_timbre_licores").id
        for record in self:
            if record.invoices_ids:
                for inv in record.invoices_ids:
                    sw = 0
                    if inv.state == 'posted' and inv.payment_state == 'paid':
                        p_p_licor = inv.invoice_line_ids.filtered(lambda l: l.product_id.id == p_id and l.year == int(inv.company_id.period))  # buscando producto patente de licor
                        if p_p_licor:
                            record.pago_timbre_licor = 'paid'
                            exist_product_licor = factura.invoice_line_ids.filtered(lambda l: l.product_id.id == p_id)
                            if exist_product_licor:
                                sw = 1
                                break
            if sw == 1:
                raise ValidationError(_("Ya se encuentra pagado el producto Timbre Patente Licores para la patente %s en la factura %s .Edite el comprobante y elimine "
                                        "esa línea en la factura." % (record.name, inv.name)))

    def action_view_invoices(self):
        compose_tree = self.env.ref('account.view_invoice_tree')
        compose_form = self.env.ref('account.view_move_form')

        return {
            'name': _('Lista de Facturas'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            #'views': [(compose_form.id, 'tree')],
            'views': [(compose_tree.id, 'tree'), (compose_form.id, 'form')],
            'target': 'current',
            'context': {},
            'domain': [('id', '=', self.invoices_ids.ids)],
        }

    @api.model
    def search_posted(self,patent):
        trimestre_year = []
        #date_last_paid = self._ultima_fecha_pago(patent.invoices_ids)
        for inv in patent.invoices_ids:
            if inv:
                for line in inv.invoice_line_ids:
                    pos, sw = self._search_trimesters_paids(line.name.split(' '))
                    if sw:
                        trimester = trimester_group[str(line.name.split(' ')[pos])]
                        if trimester > 0:
                            line.write({'trimestre': trimester})

            if inv.state == 'posted' and (inv.payment_state == False or inv.payment_state == 'not_paid') and not inv.reversal_move_id \
                    and not inv.reversed_entry_id:

                for line in inv.invoice_line_ids:
                    if line.trimestre > 0:
                        trimester = line.trimestre
                        trimestre_year.append([line.year, trimester])
                    else:
                        pos, sw = self._search_trimesters_paids(line.name.split(' '))
                        if sw:
                            trimester = trimester_group[str(line.name.split(' ')[pos])]
                            trimestre_year.append([line.year, trimester])
                            #line.write({'trimestre': trimester})
        if not trimestre_year:
            return trimestre_year
        return max(trimestre_year)

    def _ultima_fecha_pago(self, invoices_ids):
        date_last_paid = []
        for inv in invoices_ids:
            paids = self.env['account.payment'].sudo().search([('ref', '=', inv.name)])
            fechas = paids.mapped('date')
            print(inv.name)
            if fechas:
                date_last_paid.append(max(fechas))
            else:
                date_last_paid.append(inv.invoice_date)
        if date_last_paid:
            return max(date_last_paid)
        return date_last_paid
    @api.model
    def search_paids(self,patent):
        trimestre_and_pago = []
        trimestre_year = []
        #date_last_paid = False
        #date_last_paid = self._ultima_fecha_pago(patent.invoices_ids)
        for inv in patent.invoices_ids:
            if inv.payment_state in ('paid') and not inv.reversal_move_id and not inv.reversed_entry_id:
                for line in inv.invoice_line_ids:
                    if line.trimestre > 0:
                        trimester = line.trimestre
                        trimestre_year.append([line.year,trimester])
                        trimestre_and_pago.append({'trimestre': trimester, 'monto': line.price_subtotal, 'factura': inv, 'active': True ,
                                                   'product_id': line.product_id.id, 'year': line.year})
                    else:
                        pos, sw = self._search_trimesters_paids(line.name.split(' '))
                        if sw:
                            trimester = trimester_group[str(line.name.split(' ')[pos])]
                            trimestre_year.append([line.year,trimester])
                            line.write({'trimestre': trimester})
                            trimestre_and_pago.append({'trimestre': trimester, 'monto': line.price_subtotal, 'factura': inv, 'active': True,
                                                       'product_id': line.product_id.id, 'year': line.year})
        if trimestre_year:
            trimestre_year = max(trimestre_year)
        return trimestre_year, trimestre_and_pago

    @api.depends('invoices_ids', 'invoices_ids.state','invoices_ids.payment_state')
    def _get_invoiced(self):
        self._get_topaid()

    def _search_trimesters_paids(self, name):
        pos = 0
        sw=0
        for x in name:
            if x in ('trimestre', 'trimester', 'Trimestre'):
                pos += 1
                sw=1
                break
            pos += 1
        return pos, sw


    @api.model
    def _get_topaid(self):
        if not self:
            self = self.search([('state','=','approved')])
        for patent in self:

            #AÑADIR FACTURAS ANTIGUAS A LAS RELACIONES DE FACTURAS
            invoices_add = self.env['account.move'].search([('patent_id', '=', patent.id)], order='id asc')
            if len(invoices_add) > 0:
                if patent.invoice_count == 0:
                    patent.invoice_count = len(invoices_add)
                    # patent.invoice_count = patent.invoice_count + len(invoices_add)
                patent.invoices_ids = patent.invoices_ids + invoices_add

            invoices = patent.invoices_ids
            patent.invoice_count = len(invoices.ids)
            #PROCESO PARA PAGADAS
            list_trimestres_years, trimestre_and_pago = self.search_paids(patent)

            if list_trimestres_years:
                anio = int(list_trimestres_years[0])
                if not anio or anio == 0:
                    anio = date.today().year - 1 #año pasado
                mes = list_trimestres_years[1]
                month = month_range[str(mes)][2]
                monthRange = calendar.monthrange(anio, month)
                last_day = date(anio, month, monthRange[1])
                patent.pay_to = last_day
            else:
                patent.pay_to = False

            # PROCESO PARA PUBLICADAS
            list_trimester = self.search_posted(patent)
            if list_trimester:
                anio_1 = int(list_trimester[0])
                if not anio_1 or anio_1 == 0:
                    anio_1 = date.today().year - 1  # año pasado
                mes_1 = list_trimester[1]
                month_1 = month_range[str(mes_1)][2]
                monthRange = calendar.monthrange(anio_1, month_1)
                dia_tentativo = date(anio_1, month_1, monthRange[1])
                patent.pay_next = dia_tentativo
            else:
                patent.pay_next = False

            # patent_id = fields.Many2one('l10n_cr.patent')
            #
            # trimestre = fields.Integer(string='Número de trimestre')
            # description = fields.Char(string=u'Descripción')
            # factura_id = fields.Many2one('account.move', string='Factura')
            # currency_id = fields.Many2one('res.currency', string='Moneda', related='payment_id.currency_id', store=True,
            #                               related_sudo=False)
            # amount = fields.Monetary(string='Monto')

            #TODO Lista de trimestres pagados
            if trimestre_and_pago:
                #self._create_lines_trimester_paids(trimestre_and_pago, patent)
                self._create_other_paids(patent)


    def _create_other_paids(self, patent):
        if patent:
            patent_lines = []
            if patent.invoices_ids:
                if patent.name == 'EM-01-0089':
                    sw=1
                for inv in patent.invoices_ids:
                    if inv.state == 'posted' and inv.payment_state == 'paid':
                        for line in inv.invoice_line_ids:

                            p_line = patent.patents_lines.filtered(lambda l: l.year in [0,False,'2021'] and line.trimestre == l.trimestre and l.factura_id.id == line.move_id.id)
                            if p_line:
                                p_line.write({'year': str(date.today().year - 1), 'product_id': line.product_id.id})
                            else:
                                p_line = patent.patents_lines.filtered(lambda l: int(l.year) == line.year and l.product_id.id == line.product_id.id and
                                                                                 line.trimestre == l.trimestre and l.factura_id.id == line.move_id.id)
                                if not p_line:
                                    data = {
                                        'patent_id': patent.id,
                                        'product_id': line.product_id.id,
                                        'trimestre': line.trimestre,
                                        'year': str(date.today().year - 1) if line.year == 0 else str(line.year),
                                        'description': line.product_id.name,
                                        'factura_id': inv.id,
                                        'state_paid': inv.payment_state,
                                        'currency_id': inv.currency_id.id,
                                        'amount': line.price_subtotal,
                                        'active': True
                                    }
                                    patent_lines.append(data)

            if patent_lines:
                self.env['l10n_cr.patent.lines'].sudo().create(patent_lines)


    def _create_lines_trimester_paids(self, trimestre_and_pago, patent):
        lines = self.env['l10n_cr.patent.lines']
        patent_lines = []
        for t in trimestre_and_pago:
            sw = patent.patents_lines.filtered(
                lambda linea: linea.trimestre == t['trimestre'] and linea.patent_id.id == patent.id)
            if not sw:
                data = {
                    'patent_id': patent.id,
                    'product_id': t['product_id'],
                    'trimestre': t['trimestre'],
                    'year': int(self.company_id.period),
                    'description': DESCRIPTION[t['trimestre']] + ' del ' + str(patent.solicitation_date.year),
                    'factura_id': t['factura'].id,
                    'state_paid': False,
                    'currency_id': t['factura'].currency_id.id,
                    'amount': t['monto'],
                    'active': t['active']
                }
                patent_lines.append(data)

        if len(patent_lines) > 0:
            lines.create(patent_lines)

    @api.depends('pay_to')
    def _get_month_paid(self):
        for patent in self:
            patent.month = patent.pay_to.month if patent.pay_to else 0
            patent.year = patent.pay_to.year if patent.pay_to else 0
            if patent.month == 12 and patent.year == int(patent.company_id.period):
                patent.generate_inv = False
            else:
                patent.generate_inv = True

    def new_invoice(self):
        ctx = {'default_patent_id': self.id}
        return {
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
            "res_model": "l10n_cr.patent.approve_wizard",
            "context": ctx,
            "target": "new",
        }


    def _evalue_date(self,patent):
        if patent.pay_to and patent.pay_next:
            if patent.pay_next > patent.pay_to:
                return patent.pay_next, 0
            else:
                return patent.pay_to, 0
        elif patent.pay_to and not patent.pay_next:
            return patent.pay_to, 0
        elif not patent.pay_to and patent.pay_next:
            return patent.pay_next, 0
        else:
            return patent.solicitation_date, 1

    #TODO: CRON PARA GENERAR FACTURAS A TRAVÉS DE PATENTES
    @api.model
    def patents_to_invoice(self,date=None):
        cron = self.env.ref("l10n_cr_municipality_extend.ir_cron_patent_invoices")
        nextcall = cron.nextcall
        nextcall_date = date
        if date == None:
            nextcall_date = nextcall.date()
        patents = self.env['l10n_cr.patent'].search([('state','=','approved')],order='id desc')
        if patents:
            for patent in patents:
                #date_paid = patent.pay_to
                #next_paid = patent.pay_next

                last_date, atraso = self._evalue_date(patent)

                month_now = nextcall_date.month
                if month_now > last_date.month:
                    trimestre_pagado = month_to_trimester[str(last_date.month)]
                    trimestre_a_pagar = month_to_trimester[str(month_now)]
                    invoice, paid_timbre_licor = self.create_invoice(patent, trimestre_pagado, trimestre_a_pagar, nextcall_date, atraso)
                    if paid_timbre_licor:
                        patent.pago_timbre_licor = 'in_process'


    def create_invoice(self,patent,trimestre_pagado, trimestre_a_pagar, nextcall_date, atraso):

        lines, paid_timbre_licor = self._get_sale_lines(patent,trimestre_pagado, trimestre_a_pagar, atraso)
        # date_inv = self.patent_id.pay_to + timedelta(days=1) if self.patent_id.pay_to else pay_to
        date_inv = nextcall_date

        monthRange = calendar.monthrange(datetime.now().year, nextcall_date.month)

        data = {
            "partner_id": patent.partner_id.id,
            "patent_id": patent.id,
            "invoice_line_ids": lines,
            'state': 'draft',
            'move_type': 'out_invoice',
            'date': date_inv,
            'invoice_date_due':  date(datetime.now().year, nextcall_date.month, monthRange[1]),
            'invoice_date': date_inv,
            #"'invoice_payment_term_id': patent.partner_id.property_payment_term_id.id,
            'name': None or False
        }

        # MODELO MOVE ODOO
        move_inv = self.env["account.move"]

        """TODO ESTO SE APLICA SIEMPRE Y CUANDO SEA BORRADOR"""
        # buscamos la última factura relacionada a la patente
        inv_old = move_inv.search([('patent_id', '=', patent.id), ('state', '=', 'draft')],order='id desc', limit=1)
        if inv_old:
            # en caso haya alguna, se eliminan los apuntes y se crean nuevos, actualizando los datos
            inv_old.line_ids.unlink()
            inv_old.write(data)
            invoice = inv_old
        else:
            # si en casi no hay, se crea la factura
            invoice = move_inv.create(data)
        return invoice, paid_timbre_licor

    def _get_sale_lines(self, patent,trimestre_pagado, trimestre_a_pagar, atraso):
        trimesters = self._get_trimesters(patent,trimestre_pagado, trimestre_a_pagar, atraso)
        lines = []
        for trimester in trimesters:
            if not trimester["atrasado"]:
                plus = 1
            else:
                plus = self._get_trimester_percentage(patent)
            product = patent.type_id.product_id
            data = {
                "product_id": product.id,
                "name": trimester["name"],
                "price_unit": patent.trimester_payment * plus,
                "discount": trimester["discount"],
                "trimestre": trimester["trimestre"],
            }
            lines.append(data)

        sum_timbre = 0
        for l in lines:
            a_pagar = float(l['price_unit'])
            sum_timbre += a_pagar*timbre
        if sum_timbre>0:
            lines.append({
                'product_id': self.env.ref("l10n_cr_municipality.product_timbre").id,
                'price_unit': sum_timbre
            })

        #TIMBRE PARA PAGO DE LICORES POR UNICA VEZ
        paid_timbre_licor=False
        if patent.pago_timbre_licor in ('not_paid','nn') and patent.type_id.code == 'LC':
            lines.append({
                'product_id': self.env.ref("l10n_cr_municipality.product_timbre_licores").id,
                'price_unit': timbre_licor
            })
            paid_timbre_licor = True

        return [(0, None, line) for line in lines],paid_timbre_licor



    def _get_trimesters(self, patent, trimestre_pagado, trimestre_a_pagar, atraso):
        number_trimestre_pagado = trimester_to_number[trimestre_pagado]
        number_trimestre_a_pagar = trimester_to_number[trimestre_a_pagar]

        bandera = 0
        if atraso:
            bandera = 1
            number_trimestre_pagado = number_trimestre_pagado - 1

        trimesters = []
        for t in range(number_trimestre_pagado, number_trimestre_a_pagar):
            if bandera==1:
                atrasado=True
                bandera = 0
            else:
                atrasado = False

            data = {
                "name": _(f"Patente {patent.name} trimestre {t+1}"),
                "discount": 0,
                "account_id": patent.company_id.advance_account_id.id if t > 0 else [],
                "atrasado": atrasado,
                "trimestre": t+1
            }
            trimesters.append(data)
        return trimesters

    def _get_trimester_percentage(self, patent):
        """PERMITE CALCULO PRORRATA """

        #A diferencia del wizard el mes a tomar en cuenta es la fecha de solicitud de la factura
        if patent.date_approved:
            fecha = patent.date_approved
        else:
            fecha = date.today()
        last_month = trimester_to_paid[month_to_trimester[str(fecha.month)]]
        monthRange = calendar.monthrange(datetime.now().year, last_month)
        first_day = date(datetime.now().year, last_month - 2, 1)
        last_day = date(datetime.now().year, last_month, monthRange[1])
        total_day = (last_day - first_day).days
        days_to_end = (last_day - fecha).days
        return days_to_end / total_day

    def action_view_trimesters_paids(self):

        compose_tree = self.env.ref('l10n_cr_municipality_extend.l10n_cr_patent_lines_view_tree')
        return {
            'name': _('Trimestres pagados'),
            'type': 'ir.actions.act_window',
            'res_model': 'l10n_cr.patent.lines',
            'views': [(compose_tree.id, 'tree')],
            'target': 'current',
            'context': {},
            'domain': [('id', 'in', self.patents_lines.ids)],
        }


    def _auto_init(self):
        all_patents = self.env['l10n_cr.patent'].sudo().search([('state','=','approved')])
        for p in all_patents:
            messages = self.env['mail.message'].search([('model','=','l10n_cr.patent'),('res_id','=',p.id)])
            for m in messages:
                if m.tracking_value_ids:
                    for val in m.tracking_value_ids:
                        if val.field_desc =='Estado' and val.new_value_char == 'Aprobada':
                            p.date_approved = val.write_date.date()
                            p.resolution_date = val.write_date.date()
                            usuario_id = val.create_uid
                            if usuario_id.employee_id:
                                p.user_approved = usuario_id.employee_id
        #self.patents_to_invoice(date.today())

    def _get_date_approved(self):
        date = False
        messages = self.env['mail.message'].search([('model', '=', 'l10n_cr.patent'), ('res_id', '=', self.id)])
        for m in messages:
            if m.tracking_value_ids:
                for val in m.tracking_value_ids:
                    if val.field_desc == 'Estado' and val.new_value_char == 'Aprobada':
                        date = val.write_date.date()

        return date

    def _show_modal(self, inv):
        title = u'Proceso de validación de factura con interés'
        message = '1. VALIDAR CON FECHA HOY: Se procederá a validar la factura tomando como fecha de interés hasta el día de hoy. \n' \
                  '2. VALIDAR CON FECHA EN FACTURA: Se procederá a validar la factura tomando en cuenta la fecha de interés que refleja en la misma. \n' \
                  '3. Si quiere obviar el proceso de validación de la Factura, click en CANCELAR. '
        model_name = 'account.move'
        model_id = inv.id
        model_action = 'button_confirm()'
        t = inv.env['swal.message'].sudo().info(title=title,
                                                message=message,
                                                model_name=model_name,
                                                model_id=model_id,
                                                model_action=model_action,
                                                )
        return t

    # TODO: CÁLCULO DE INTERÉS
    def _caculate_interes_by_move(self, move, param, date_interes_by_wizard=None):
        array_line = []
        date_approve = self.date_approved
        _logger.info('MOVE ID {0}'.format(move.id))
        # if move.id == 888:
        #     a = 1
        if not date_interes_by_wizard:
            date_interes = move.date_interes
        else:
            date_interes = date_interes_by_wizard
        if not date_approve:
            date_approve = self._get_date_approved()
        trimester_approved = trimester_to_number[month_to_trimester[str(date_approve.month)]]
        trimester_now = trimester_to_number[month_to_trimester[str(date.today().month)]]
        # vemos si está atrasado o no
        patent_atrasada = False
        total_interes = 0
        for l in move.invoice_line_ids:
            trimester = 0
            if l.trimestre > 0:
                trimester = l.trimestre
            else:
                pos, sw = self._search_trimesters_paids(l.name.split(' '))
                if sw:
                    trimester = trimester_group[str(l.name.split(' ')[pos])]

            if trimester < trimester_now and trimester != 0:
                patent_atrasada = True
            l.write({'trimestre': trimester, 'interes': 0, 'dias': 0})

        def _f_days_to_calculate(t_from, gracie=False, year_behind=True):
            t_from = line.trimestre
            dias_a_calcular = 0
            first_day = False
            # ----year_behind => Año atrasado: El año del comprobante es menor al actual
            if year_behind == False:
                range_t_from = month_range[str(t_from)]
                fecha_pago = self.pay_to
                if not fecha_pago:
                    fecha_aprobacion = self.date_approved if self.date_approved else date.today()
                    trimestre_de_aprobacion = trimester_to_number[month_to_trimester[str(fecha_aprobacion.month)]]
                    if t_from == trimestre_de_aprobacion and t_from < trimester_now:
                        mes = month_range[str(t_from + 1)][0]
                    elif t_from > trimestre_de_aprobacion and t_from < trimester_now:
                        mes = month_range[str(t_from)][0]
                    elif t_from == trimester_now:
                        mes = False
                elif fecha_pago and fecha_pago.year == line.year:  # cuando la fecha de pago última es igual a este año
                    trimestre_de_pago = trimester_to_number[month_to_trimester[str(fecha_pago.month)]]  # consideremos el trimestre que tiene mes de gracia
                    trimestres_que_pasaron = t_from - trimestre_de_pago
                    if trimestres_que_pasaron == 1:
                        mes = range_t_from[1]
                    elif t_from == trimester_now:
                        mes = False
                    else:
                        mes = range_t_from[0]

                elif fecha_pago and fecha_pago.year != line.year:  # cuando la fecha de pago última es diferente a este año
                    mes = range_t_from[1]  # Pasando al segundo mes del trimestre a pagar, dando ventaja de 1 mes

                if mes != False:
                    first_day = date(datetime.now().year, mes, 1)
                    last_day = date_interes
                    dias_a_calcular = (last_day - first_day).days

            else:
                range_t_from = month_range[str(t_from)]
                fecha_pago = self.pay_to
                if fecha_pago:
                    ultimo_trimestre_de_pago = trimester_to_number[month_to_trimester[str(fecha_pago.month)]]  # consideremos el trimestre que tiene mes de gracia
                    trimestres_que_pasaron = t_from - ultimo_trimestre_de_pago
                    if trimestres_que_pasaron == 1:
                        mes = range_t_from[1]
                    elif t_from == trimester_now:
                        mes = False
                    else:
                        mes = range_t_from[0]

                    if mes != False:
                        first_day = date(datetime.now().year - 1, mes, 1)
                        last_day = date_interes
                        dias_a_calcular = (last_day - first_day).days

            dias_a_calcular = dias_a_calcular + 1 #PEDIDO POR FELIPE
            return dias_a_calcular, first_day

        for line in move.invoice_line_ids:
            # evaluamos si el trimestre existe o si pertenece a alguno numericamente

            if line.trimestre > 0:
                # days_by_trimester = _f_days_by_trimester(line.trimestre)
                amount = line.price_unit
                # si mi trimestre de la linea es menor al de ahora, entonces voy a validar un trimestre atrasado
                # if line.trimestre < trimester_now:
                if line.year == int(line.company_id.period):
                    if line.trimestre < trimester_now:
                        days_to_calculate, date_from_interes = _f_days_to_calculate(line, gracie=True, year_behind=False)  # días adeudados
                        if days_to_calculate > 0:
                            interes_by_day = self._get_interes(date_from_interes, amount)
                            interes = (interes_by_day * days_to_calculate)
                            total_interes += interes
                            array_line.append({
                                'id': line.id,
                                'interes': interes,
                                'dias': days_to_calculate,
                            })
                    elif line.trimestre == trimester_now and patent_atrasada:
                        days_to_calculate, date_from_interes = _f_days_to_calculate(line, gracie=True, year_behind=False)  # días adeudados
                        if days_to_calculate > 0:
                            interes_by_day = self._get_interes(date_from_interes, amount)
                            interes = (interes_by_day * days_to_calculate)
                            total_interes += interes
                            array_line.append({
                                'id': line.id,
                                'interes': interes,
                                'dias': days_to_calculate,
                            })
                    elif trimester == trimester_now and not patent_atrasada:
                        total_interes = 0
                    else:
                        pass

                elif line.year < int(line.company_id.period):
                    days_to_calculate, date_from_interes = _f_days_to_calculate(line.trimestre, gracie=True, year_behind=True)  # días adeudados
                    if days_to_calculate > 0:
                        interes_by_day = self._get_interes(date_from_interes, amount)
                        interes = (interes_by_day * days_to_calculate)
                        total_interes += interes
                        array_line.append({
                            'id': line.id,
                            'interes': interes,
                            'dias': days_to_calculate,
                        })

        if total_interes > 0:
            prod_interes = self.env.ref("l10n_cr_municipality_extend.product_intereses")
            sw = 0
            if param == 'assign':
                for linea in move.invoice_line_ids:
                    if linea.product_id.id == prod_interes.id:
                        linea.price_unit = total_interes
                        sw = 1
                        break

            if sw == 0 and param == 'assign':
                move_form = Form(move)
                with move_form.invoice_line_ids.new() as new_move:
                    new_move.name = u'Interés por pagar'
                    new_move.product_id = prod_interes
                    new_move.quantity = 1
                    new_move.price_unit = total_interes
                move_form.save()

            # Recálculo
            for a in array_line:
                move.invoice_line_ids.filtered(lambda ml: ml.id == a['id']).write({'interes': a['interes'], 'dias': a['dias']})



    def _get_interes(self,fecha,monto):
        list_interes = self._get_intereses_by_database()
        interes_por_dia = 0.0
        if list_interes:
            interes_capt = False
            for i in list_interes:
                if i.date <= fecha:
                    interes_capt = i

            if interes_capt:
                interes_por_dia = (monto * interes_capt.rate) / 100

        return interes_por_dia


    def _get_intereses_by_database(self):
        interes_ids = False
        if self.env.company.interest_rate_ids:
            interes_ids = self.env.company.interest_rate_ids

        return interes_ids
    # def _get_intereses_by_database(self):
    #     interes_ids = False
    #     self._cr.execute('''select id from res_config_settings order by 1 desc limit 1''')
    #     res = self._cr.fetchone()
    #     if res:
    #         self._cr.execute('''select * from l10n_cr_interes_res_config_settings_rel where res_config_settings_id = {0} '''.format(res[0]))
    #         query_res = self._cr.fetchall()
    #         if query_res:
    #             ids = []
    #             for i in query_res:
    #                 ids.append(i[1])
    #             all_intereses = self.env['l10n_cr.interes'].sudo().search([('id', 'in', ids)], order="date asc")
    #             if all_intereses:
    #                 interes_ids = all_intereses
    #
    #     return interes_ids
    @api.model
    def _create_patent_lines(self):
        patent_ids = self.env['l10n_cr.patent'].sudo().search([('state', '=', 'approved')])
        patent_lines = []
        for patent in patent_ids:
            self._create_other_paids(patent)


class PatentsPaidLine(models.Model):
    _name = "l10n_cr.patent.lines"
    _description = "Detalle de patentes pagadas"

    patent_id = fields.Many2one('l10n_cr.patent')
    product_id = fields.Many2one('product.product', string=u'Producto')
    year = fields.Char(string='Año', default='2021')
    trimestre = fields.Integer(string='Número de trimestre')
    description = fields.Char(string=u'Descripción')
    factura_id = fields.Many2one('account.move',string='Factura')
    state_paid = fields.Selection(selection=[
        ('not_paid', 'No pagado'),
        ('in_payment', 'En pago'),
        ('paid', 'Pagado'),
        ('partial', 'Parcialmente pagado'),
        ('reversed', 'Revertido'),
        ('invoicing_legacy', 'Invoicing App Legacy')], related='factura_id.payment_state', store=True, string='Estado de Pago')
    currency_id = fields.Many2one('res.currency',string='Moneda',related='factura_id.currency_id', store=True, related_sudo=False)
    amount = fields.Monetary(string='Monto')
    active = fields.Boolean(default=False)





