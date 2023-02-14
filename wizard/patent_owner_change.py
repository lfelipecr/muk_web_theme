# -*- coding: utf-8 -*-

from datetime import date, datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError,ValidationError
import calendar


class PatentOwnerChangeWizard(models.TransientModel):
    _name = "patent.owner.change.wizard"
    _description = 'Cambiar de propietario en patente'

    def _get_patent(self):
        patent = self.env['l10n_cr.patent'].browse(self.env.context['active_ids'])
        return patent

    def _get_partner(self):
        patent = self.env['l10n_cr.patent'].browse(self.env.context['active_ids'])
        return patent.partner_id

    patent_id = fields.Many2one('l10n_cr.patent',string='Número de pantente', default=_get_patent, readonly=True, store=True)
    partner_old_id = fields.Many2one('res.partner', string='Contribuyente actual', default=_get_partner, readonly=True, store=True)
    partner_new_id = fields.Many2one('res.partner', string='Nuevo contribuyente')


    def process_change(self):
        res = {}
        if self.patent_id:
            sw=0
            for inv in self.patent_id.invoices_ids:
                if inv.state in ('posted','draft') and (inv.payment_state == False or inv.payment_state == 'not_paid') and not inv.reversal_move_id and not inv.reversed_entry_id:
                    sw=1
                    break

            if sw==1:
                raise UserError(_('La patente cuenta con alguna factura sin pagar. Para realizar el cambio de contribuyente, por favor realice el pago de la factura.'))
                # # warning = {
                # #     'title': 'Atención',
                # #     'message': 'La patente cuenta con alguna factura sin pagar. Para realizar el cambio de propietario, por favor realice el pago de la factura.'
                # # }
                # # return {'warning': warning}
                # res['warning'] = {'title': _('Ups'), 'message': _(
                #     'El número de identificación encontrado, no conincide con el número de documento del cliente.')}
                # return res

            self.patent_id.write({
                'partner_id': self.partner_new_id.id,
            })

            mail_message_values = {
                'email_from': self.env.user.partner_id.email,
                'author_id': self.env.user.partner_id.id,
                'model': 'l10n_cr.patent',
                'message_type': 'comment',
                'body': str("Cambio contribuyente:") + str("<br>")
                        +str("Antes: ") + str(self.partner_old_id.name) + str(" -> Ahora: ") + str(self.partner_new_id.name),
                'res_id': self.patent_id.id,
                'subtype_id': self.env.ref('mail.mt_comment').id,
                'record_name': self.patent_id.name,
            }
            self.env['mail.message'].sudo().create(mail_message_values)

            self.env.user.notify_success(message='Cambio realizado de manera exitosa!',title="BIEN! ")



