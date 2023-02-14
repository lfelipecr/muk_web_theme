import base64
import logging

from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tests import common, Form
from datetime import datetime, date
import calendar
import logging
_logger = logging.getLogger(__name__)
trimester_to_paid = {
    "t1": 3,
    "t2": 6,
    "t3": 9,
    "t4": 12,
}

trimester_letter_to_number = {
    "t1": 1,
    "t2": 2,
    "t3": 3,
    "t4": 4,
}

trimester_letter = {
    1: 't1',
    2: 't2',
    3: 't3',
    4: 't4',
}

month_to_trimester = {
    1: "t1",
    2: "t1",
    3: "t1",
    4: "t2",
    5: "t2",
    6: "t2",
    7: "t3",
    8: "t3",
    9: "t3",
    10: "t4",
    11: "t4",
    12: "t4",
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
    "10-12": 4,
}

date_gracie = {
    't1': 1,
    't2': 4,
    't3': 7,
    't4': 10,
}

meses_cobrables = {
    1: [2,3],
    2: [5,6],
    3: [8,9],
    4: [11,12],
}

from pytz import timezone
zone = timezone('America/Lima')

class AccountInvoice(models.Model):
    _inherit = "account.move"

    total_discount = fields.Monetary('Total Descuento', compute='_compute_amount',store=True,copy=False)
    total_paid = fields.Monetary('Total Abonado',compute='_compute_amount',store=True,copy=False)
    calulate_interes = fields.Boolean('Calcular interés', default=False)
    def _default_date_cr(self):
        return fields.Date.context_today(self.with_context(tz='America/Costa_Rica'))
    date_interes = fields.Date(string=u'Fecha interés', default=_default_date_cr)

    validate_button = fields.Boolean(default=False) #Nuevo 26-11-2021



    def search_invoices_paids(self,r):
        #sw = self.search_bandera(self.invoice_line_ids,list)
        if r>0:
            raise ValidationError(_('Está tratando de validar un comprobante con un trimestre ya PAGADO:  Trimestre N° '+str(r)+' '))

    @api.model
    def search_validates(self, patent):
        for inv in patent.invoices_ids:
            if inv.state == 'posted' and inv.amount_residual > 0.0 and (not inv.reversal_move_id and not inv.reversed_entry_id):
                r = self._lines_values(inv.invoice_line_ids)
                if r > 0:
                    raise ValidationError(
                        _('Está tratando de validar un comprobante con un trimestre ya VALIDADO:  Trimestre N° ' + str(r) + ' '))


    def _lines_values(self,lines):
        array_names = []

        for line in lines:
            if line.name.find('trimestre') > 0:
                array_names.append(line.name)

        trimester_number = 0
        list, tr, mr = self.calc_number_trimester_month(array_names)
        if list:
            top = max(list)
            if tr == True and top <= 4:
                trimester_number = trimester_to_paid[trimester_letter[top]]
            else:
                trimester_number = top

        return trimester_number

    def calc_number_trimester_month(self, array_names):

        list = []
        numbs = []
        tr = False  # TRIMESTER RETURN
        mr = False  # MES RETURN
        if array_names:
            for y in array_names:
                sp = y.split(" ")
                t = len(sp) - 1
                if sp[t].find('-') >= 0:
                    nums = sp[t].split('-')
                    numbs.append(int(nums[1].strip()))
                    number = max(numbs)
                    mr = True
                else:
                    number = int(sp[3]) if sp[3] else 0
                    tr = True
                list.append(number)

        return list, tr, mr

    # def search_bandera(self,lines,list):
    #     sw = 0
    #     if list:
    #         for line in lines:
    #             if line.name.find('trimestre') > 0:
    #                 name = line.name
    #                 sp = name.split(" ")
    #                 #number = int(sp[3]) if sp[3] else 0
    #                 if sp[3]:
    #                     lx = sp[3].split('-')
    #                     if len(lx) > 1:
    #                         mes = int(lx[1])
    #                         number = trimester_to_number[month_to_trimester[mes]]
    #                     else:
    #                         number = int(sp[3])
    #                 else:
    #                     number = 0
    #                 if number > 0:
    #                     for i in list:
    #                         if number == i:
    #                             sw = number
    #                             break
    #
    #
    #     return sw


    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id')
    def _compute_amount(self):
        super(AccountInvoice, self)._compute_amount()
        for inv in self:
            self.calculate_items(inv)

    @api.model
    def compute_amount_extra(self):
        for inv in self.search([('move_type','!=','entry')]):
            self.calculate_items(inv)

    def calculate_items(self,inv):
        inv.total_discount = 0.0
        total_discount = sum(
            (l.quantity * l.price_unit) * (l.discount / 100) if l.discount > 0 else 0.0 for l in inv.line_ids)
        inv.total_discount = total_discount

        inv.total_paid = 0.0
        total_paid = inv.amount_total - inv.amount_residual
        inv.total_paid = total_paid

    def action_post(self):
        if self.patent_id and self.date_interes:
            self.patent_id.validate_invoices_timbre_licor(self)
            if self.date_interes < date.today() and not self.validate_button:
                return self.patent_id._show_modal(self)
            self.patent_id._caculate_interes_by_move(self, 'assign')
        res = super(AccountInvoice, self).action_post()
        return res

    def button_draft(self):
        res = super(AccountInvoice, self).button_draft()
        for record in self:
            if record.patent_id and record.validate_button:
                record.validate_button = False
        return res


    def _caculate_interes(self):
        date_validate = datetime.now(zone).date()
        trimester_validate = trimester_letter_to_number[month_to_trimester[date_validate.month]]
        for inv in self:
            amount = 0.0
            dict_line = []
            for line in inv.invoice_line_ids:
                trimestre=0
                dias=0
                if line.trimestre > 0:
                    trimestre=line.trimestre
                else:
                    pos, sw = self._search_trimesters_paids(line.name.split(' '))
                    if sw:
                        trimester = trimester_group[str(line.name.split(' ')[pos])]
                        line.trimestre = trimester
                        trimestre = trimester

                #validar el mismo trimestre
                if trimestre == trimester_validate:
                    mes_gracia = date_gracie[month_to_trimester[date_validate.month]]
                    monthRange = calendar.monthrange(datetime.now().year, mes_gracia)
                    last_day = date(datetime.now().year, mes_gracia, monthRange[1])
                    #first_day = date(datetime.now().year, mes_gracia, 1)
                    if date_validate > last_day:
                        dias = (date_validate - last_day).days
                # validar trimestres anteriores
                elif trimestre < trimester_validate and trimestre != 0:
                    array_meses_cobrables = meses_cobrables[trimestre]
                    first_day = date(datetime.now().year, array_meses_cobrables[0], 1)
                    rango_mes = calendar.monthrange(datetime.now().year, array_meses_cobrables[1])
                    last_day = date(datetime.now().year, array_meses_cobrables[1], rango_mes[1])
                    dias = (last_day - first_day).days

                interest_ids = self.default_get_intereses()
                if interest_ids and dias > 0:
                    interes_id = interest_ids.filtered(lambda x: x.date <= date_validate)
                    if interes_id:
                        interes_id = interes_id[0]
                        amount += dias * interes_id.rate


                    else:
                        raise UserError(_('No hay interés definido para fecha'))

            if amount > 0.0:
                _logger.info("Factura %s =>> monto de interes %s " % (inv.name, amount))
                prod_interes = self.env.ref("l10n_cr_municipality_extend.product_intereses")

                sw = 0
                for linea in inv.invoice_line_ids:
                    if linea.product_id.id == prod_interes.id:
                        linea.price_unit = amount
                        sw = 1
                        break

                if sw == 0:
                    move_form = Form(inv)
                    with move_form.invoice_line_ids.new() as new_move:
                        new_move.name = u'Interés por pagar'
                        new_move.product_id = prod_interes
                        new_move.quantity = 1
                        new_move.price_unit = amount
                    move_form.save()


    def _search_trimesters_paids(self, name):
        pos = 0
        sw = 0
        for x in name:
            if x in ('trimestre', 'trimester', 'Trimestre'):
                pos += 1
                sw = 1
                break
            pos += 1
        return pos, sw



class AccountInvoiceLine(models.Model):
    _name = 'account.move.line'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'account.move.line']

    trimestre = fields.Integer('Trimestre', store=True)
    year = fields.Integer(string='Año', store=True, default=2021)
    interes = fields.Monetary()
    dias = fields.Integer()


    #orginal
    product_id = fields.Many2one('product.product', string='Product', ondelete='restrict', tracking=True)
    parent_state = fields.Selection(related='move_id.state', store=True, readonly=True, tracking=True)
    date = fields.Date(related='move_id.date', store=True, readonly=True, index=True, copy=False, group_operator='min', tracking=True)
    ref = fields.Char(related='move_id.ref', store=True, copy=False, index=True, readonly=False, tracking=True)
    price_unit = fields.Float(string='Unit Price', digits='Product Price', tracking=True)
    quantity = fields.Float(string='Quantity',
                            default=1.0, digits='Product Unit of Measure',
                            help="The optional quantity expressed by this line, eg: number of product sold. "
                                 "The quantity is not a legal requirement but is very useful for some reports.",tracking=True)



    @api.model
    def _assign_year(self):
        new_year = date.today().year
        lines = self.env['account.move.line'].sudo().search([('year','in',(0,False))])
        if lines:
            for l in lines:
                l.write({'year': new_year - 1})