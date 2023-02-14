from datetime import date, datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError,ValidationError
import calendar


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
trimester_to_paid = {
    "t1": 3,
    "t2": 6,
    "t3": 9,
    "t4": 12,
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

trimester_to_number = {
    "t1": 1,
    "t2": 2,
    "t3": 3,
    "t4": 4,
}

trimester_names = {
    1: '(Enero,Febrero,Marzo)',
    2: '(Abril,Mayo,Junio)',
    3: '(Julio,Agosto,Setiembre)',
    4: '(Octubre,Noviembre,Diciembre)',
}


timbre = 0.02 #TIMBRE 2 POR CIENTO
timbre_licor = 5000 #TIMBRE PARA LICORES 5000 COLONES

class PatentApproveWizard(models.TransientModel):
    _inherit = "l10n_cr.patent.approve_wizard"


    def _get_year_month(self):
        year = datetime.today().year
        month = datetime.today().month
        patent_id = self.env["l10n_cr.patent"].browse(self.env.context["default_patent_id"])[0]
        if patent_id.pay_to:
            if patent_id.pay_to.year == int(self.company_id.period):
                year = patent_id.pay_to.year
                month = month + 3
            else:
                if patent_id.pay_to.month == 12:
                    year = patent_id.pay_to.year + 1
                    month = month
                else:
                    year = patent_id.pay_to.year
                    month = patent_id.pay_to.month + 3

        return year, month

    company_id = fields.Many2one('res.company', required=True, readonly=True, default=lambda self: self.env.company)

    @api.model
    def _default_trimester_now(self):
        t_actual = trimester_to_number[month_to_trimester[str(datetime.now().month)]]
        return t_actual

    active_mensaje = fields.Integer(default=0)
    trimestre_now = fields.Integer(default=_default_trimester_now)
    trimestre_selected = fields.Integer()
    show_mensaje = fields.Text()

    @api.model
    def _default_trimester_paid(self):
        year, month = self._get_year_month()
        t_paid = trimester_to_number[month_to_trimester[str(month)]]
        return t_paid

    @api.model
    def _default_trimester(self):
        year, month = self._get_year_month()
        month = month_to_trimester[str(month)]

        return month

    trimester = fields.Selection(
        selection=[
            ("t1", "Primer Trimestre"),
            ("t2", "Segundo Trimestre"),
            ("t3", "Tercer Trimestre"),
            ("t4", "Cuarto Trimestre"),
        ],
        string="Trimestre",
        required=True,
        default=_default_trimester,
    )

    trimester_paid = fields.Integer(default=_default_trimester_paid)

    @api.model
    def _default_year_paid(self):
        year, month = self._get_year_month()
        return year

    year_paid = fields.Char(default=_default_year_paid)

    def mensajes_a_mostrar(self,select,actual):
        mensaje = ''
        if select<actual and not self.patent_id.pay_to:
            mensaje = 'Leer mensaje en la parte inferior.'
            self.active_mensaje=1
            #mensaje = 'Generará comprobante para trimestre ' + str(select) + trimester_names[select] + '.'
            #self.active_mensaje=0
        elif select==actual:
            self.active_mensaje = 0
            mensaje = 'Generará comprobante para trimestre ' + str(select) + trimester_names[select] + '.'
        elif select > actual:
            self.active_mensaje = 0
            mensaje += 'Generará comprobante para '
            for i in range(actual, select+1):
                if i==select:
                    final = '.'
                else:
                    final = ', '
                mensaje+='trimestre ' + str(i) + trimester_names[i] + final
        else:
            mensaje = 'Leer mensaje en la parte inferior.'

        self.show_mensaje = mensaje

    @api.onchange("trimester")
    def _change_trimester(self):
        super(PatentApproveWizard, self)._change_trimester()
        r = self.evalue_month_selected('test_message')
        if r==-1:
            self.active_mensaje = 1
        else:
            self.active_mensaje = 0

        t_selected = trimester_to_number[self.trimester]
        self.trimestre_selected = t_selected
        self.mensajes_a_mostrar(t_selected,self.trimester_paid)

    def create_invoice(self):
        lines,paid_timbre_licor = self._get_sale_lines()
        #date_inv = self.patent_id.pay_to + timedelta(days=1) if self.patent_id.pay_to else pay_to
        date_inv = datetime.now().date()
        data = {
            "partner_id": self.patent_id.partner_id.id,
            "patent_id": self.patent_id.id,
            "invoice_line_ids": lines,
            'state': 'draft',
            'move_type': 'out_invoice',
            'invoice_date': date_inv,
            'name': None or False
        }

        #MODELO MOVE ODOO
        move_inv = self.env["account.move"]

        """TODO ESTO SE APLICA SIEMPRE Y CUANDO SEA BORRADOR"""
        #buscamos la última factura relacionada a la patente
        inv_old = move_inv.search([('patent_id','=',self.patent_id.id),('state','=','draft')], order='id desc',limit=1)
        if inv_old:
            #en caso haya alguna, se eliminan los apuntes y se crean nuevos, actualizando los datos
            inv_old.line_ids.unlink()
            inv_old.write(data)
            invoice = inv_old
        else:
            #si en casi no hay, se crea la factura
            invoice = move_inv.create(data)
        return invoice,paid_timbre_licor

    def _get_percentage_by_trimester(self, fecha):

        last_month = trimester_to_paid[month_to_trimester[str(fecha.month)]]
        monthRange = calendar.monthrange(datetime.now().year, last_month)
        first_day = date(datetime.now().year,last_month-2,1)
        last_day = date(datetime.now().year, last_month, monthRange[1])
        total_day = (last_day - first_day).days
        days_to_end = (last_day - fecha).days
        return days_to_end / total_day



    def _get_paid_to(self, today):
        """ULTIMO DÍA DE PAGO"""
        month_to_paid = trimester_to_paid[self.trimester]
        monthRange = calendar.monthrange(today.year, month_to_paid)
        last_day = date(today.year, month_to_paid, monthRange[1])
        return last_day


    def approve(self):
        today = fields.Date.today()
        pay_to = self._get_paid_to(today)

        for wizard in self:
            r = wizard.evalue_month_selected('execute')
            #r = 1
            if r:
                invoice,paid_timbre_licor = wizard.create_invoice()
                wizard.patent_id.invoices_ids += invoice
                invoice.patent_id = wizard.patent_id
                wizard.patent_id.state = "approved"
                wizard.patent_id.resolution_date = fields.Date.today()
                if paid_timbre_licor:
                    wizard.patent_id.pago_timbre_licor = 'in_process'

                #Todo: Asignar fecha de aprobación
                if not wizard.patent_id.date_approved:
                    wizard.patent_id.date_approved = fields.Date.today()


                #wizard.patent_id.pay_to = pay_to

                if len(self) == 1:
                    return {
                        'name': _('Factura de cliente'),
                        'view_mode': 'form',
                        'view_id': self.env.ref('account.view_move_form').id,
                        'res_model': 'account.move',
                        'context': "{'move_type':'out_invoice'}",
                        'type': 'ir.actions.act_window',
                        'res_id': invoice.id,
                    }
        return {}


    def evalue_month_selected(self, mod):
        year, month = self._get_year_month
    # def evalue_month_selected(self, mod):
    #     for pat in self:
    #         if pat.patent_id.pay_to:
    #             period = int(self.company_id.period)
    #             year_paid = pat.patent_id.pay_to.year #Año último pagado
    #             month_paid = pat.patent_id.pay_to.month #Mes último pagado
    #             month_t = trimester_to_number[month_to_trimester[str(month_paid)]] #Número de trimestre
    #             month_to_paid = trimester_to_number[self.trimester] #Mes a pagar(OK)
    #             if month_to_paid == month_t:
    #                 if month_paid==12:
    #                     raise ValidationError(_("Este patente está pagado por todo el año. No puede generar más comprobantes."))
    #                 else:
    #                     return -1
    #
    #             elif month_to_paid < month_t:
    #                 if mod == 'execute':
    #                     raise UserError(_("No puede generar un comprobante con un trimestre menor al último generado."))
    #                 else:
    #                     return -1
    #             else:
    #                 return 1
    #         else:
    #             return 1


    def _get_sale_lines(self):
        trimesters = self._get_trimesters()

        lines = []
        for trimester in trimesters:
            product = self.patent_id.type_id.product_id
            plus = 1
            if trimester["advance"]:
                product = self.patent_id.type_id.product_advance_id
            if trimester['percentage'] != 1:
                plus = trimester['percentage']

            data = {
                "product_id": product.id,
                "name": trimester["name"],
                "price_unit": self.patent_id.trimester_payment * plus,
                "discount": trimester["discount"],
                "trimestre": trimester['number']
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
        if self.patent_id.pago_timbre_licor in ('not_paid','nn') and self.patent_id.type_id.code == 'LC':
            lines.append({
                'product_id': self.env.ref("l10n_cr_municipality.product_timbre_licores").id,
                'price_unit': timbre_licor
            })
            paid_timbre_licor = True

        return [(0, None, line) for line in lines],paid_timbre_licor


    def _get_trimesters(self):
        actual_month = str(datetime.now().date().month)
        actual_trimester_number = trimester_to_number[month_to_trimester[actual_month]] #numero trimestre actua: 1,2,3,4

        if self.patent_id.date_approved:
            fecha_aprobacion = self.patent_id.date_approved
            mes_aprobacion = self.patent_id.date_approved.month
        else:
            fecha_aprobacion = date.today()
            mes_aprobacion = date.today().month

        trimestre_de_aprobacion = trimester_to_number[month_to_trimester[str(mes_aprobacion)]]

        trimestre_paids = self._evalue_invoice()

        discount = float(
            self.env["ir.config_parameter"].sudo().get_param("l10n_cr.payment_in_advance_discount")
        )
        trimesters = []
        t_last = self.trimestre_selected
        if not trimestre_paids:
            t_init = self.trimestre_selected
        else:
            t_init = 1
        for t in range(t_init, t_last+1):
            percentage = 1
            not_save = False #tomar en cuenta o no el trimestre
            for tp in trimestre_paids: #trimestres en otras facturas a no tomar en cuenta
                if tp >= t:
                    not_save = True #trimestre a no tomar en cuenta

            if not not_save:
                if t < trimestre_de_aprobacion: #trimestres antes del trimestre de aprobacion
                    not_save = False
                elif t == trimestre_de_aprobacion: #si es igual al trimestre de aprobacion, sacar porcentaje
                    percentage = self._get_percentage_by_trimester(fecha_aprobacion)
                elif t == actual_trimester_number:
                    not_save = False

                if not not_save:

                    data = {
                        "name": _(f"Patente {self.patent_id.name} trimestre {t}"),
                        "discount": discount if self.apply_discount else 0,
                        "account_id": self.patent_id.company_id.advance_account_id.id if t > 0 else [],
                        "advance": t > actual_trimester_number,
                        "percentage": percentage,
                        "number": t
                    }
                    trimesters.append(data)
        return trimesters

    def _evalue_invoice(self):
        trimestre_number = []
        for inv in self.patent_id.invoices_ids:
            if inv.state == 'posted' and not (inv.payment_state == False or inv.payment_state == 'not_paid') and not inv.reversal_move_id and not inv.reversed_entry_id:
                for line in inv.invoice_line_ids:
                    if line.trimestre > 0:
                        trimester = line.trimestre
                        trimestre_number.append(trimester)
                    else:
                        pos, sw = self.patent_id._search_trimesters_paids(line.name.split(' '))
                        if sw:
                            trimester = trimester_group[str(line.name.split(' ')[pos])]
                            trimestre_number.append(trimester)
                            # line.write({'trimestre': trimester})

        return trimestre_number
