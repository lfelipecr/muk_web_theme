# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import ValidationError, Warning
from datetime import date
WARNING_TYPES = [('warning', 'Warning'), ('info', 'Information'), ('error', 'Error')]


class swalMessage(models.TransientModel):
    _name = 'swal.message'
    _description = 'Swal Warning'
    _req_name = 'title'

    my_type = fields.Selection(WARNING_TYPES, string='Type', readonly=True)
    title = fields.Char(string=u"Título", size=100, readonly=True)
    my_message = fields.Text(string="Mensaje:", readonly=True)
    model_name = fields.Char('Model Nombre')
    model_id = fields.Integer('Model ID')
    model_action = fields.Char('Model Action')

    def message(self, id, context):
        message = self.browse(id)
        message_type = [t[1] for t in WARNING_TYPES if message.id.my_type == t[0]][0]
        res = {
            'name': '%s: %s' % (_(message_type), _(message.id.title)),
            'view_mode': 'form',
            'view_id': False,
            'res_model': 'swal.message',
            'domain': [],
            'context': context,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': message.id.id
        }
        return res

    def warning(self, title, message, context=None):
        id = self.create({'title': title, 'my_message': message, 'my_type': 'warning'})
        res = self.message(id, context)
        return res

    @api.model
    def info(self, title, message, model_name, model_id, model_action, context=None):
        id = self.create({'title': title,
                          'my_message': message,
                          'model_name': model_name,
                          'model_id': model_id,
                          'model_action': model_action,
                          'my_type': 'info'})
        res = self.message(id, context)
        return res

    def error(self, title, message, context=None):
        id = self.create({'title': title, 'my_message': message, 'my_type': 'error'})
        res = self.message(id, context)
        return res


    def confirm(self):
        self.ensure_one()
        model_name = self.model_name
        model_id = self.model_id
        invoice = self.env[model_name].browse(model_id)
        if invoice.exists():
            invoice.sudo().write({'date_interes': date.today()})
            invoice.sudo().write({'validate_button': True})
            invoice.sudo().action_post()
        else:
            raise ValidationError(f'No existe la factura!')

    def cancel(self):
        model_name = self.model_name
        model_id = self.model_id
        invoice = self.env[model_name].browse(model_id)
        if invoice.exists():
            invoice.sudo().write({'validate_button': True})
            #invoice.write({'date_interes': date.today()}) //QUEDA LA FECHA DE INTERÉS TAL CUAL
            invoice.sudo().action_post()
        else:
            raise ValidationError(f'No existe la factura!')
