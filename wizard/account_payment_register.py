# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    source_payment_methods_id = fields.Many2one(comodel_name="payment.methods")
    payment_methods_id = fields.Many2one(comodel_name="payment.methods",string=u'Forma de Pago')

    def _create_payment_vals_from_wizard(self):
        payment_vals = super(AccountPaymentRegister, self)._create_payment_vals_from_wizard()
        payment_vals['payment_methods_id'] = self.payment_methods_id.id
        return payment_vals
