# -*- coding: utf-8 -*-

from datetime import date, datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
import calendar

traslation = {
    "suspended": "Suspendida",
    "retired": "Retirada",
    "canceled": "Cancelada"
}

STATES_TO_CHANGE = [
    ("suspended", "Suspendida"),
    ("retired", "Retirada"),
    ("canceled", "Cancelada"),
]


class PatentStateChangeWizard(models.TransientModel):
    _name = "patent.states.change.wizard"
    _description = 'Cambiar estados en patente'

    def _get_patent(self):
        patent = self.env['l10n_cr.patent'].browse(self.env.context['active_ids'])
        return patent

    def _get_state(self):
        patent = self.env['l10n_cr.patent'].browse(self.env.context['active_ids'])
        return patent.state

    patent_id = fields.Many2one('l10n_cr.patent', string='Número de patente', default=_get_patent, readonly=True,
                                store=True)
    state_old = fields.Selection([
        ("requested", "Solicitada"),
        ("in_progress", "En proceso"),
        ("approved", "Aprobada"),
        ("rejected", "Rechazada"),
        ("suspended", "Suspendida"),
        ("retired", "Retirada"),
        ("canceled", "Cancelada"),
    ], string='Estado actual', default=_get_state, readonly=True)
    state = fields.Selection(string="Nuevo estado", selection=STATES_TO_CHANGE, required=True, tracking=True,
                             copy=False)
    motivo = fields.Text(string='Motivo', required=True)

    def _validations(self):
        if not self.state:
            raise UserError(
                _('Seleccione el estado al cual desea cambiar'))

        if self.state_old == 'in_progress' and self.state != 'canceled':
            raise UserError(_('Solo una patente ARPOBADA puede pasar a : suspendida o retirada. '))

        elif self.state_old == 'approved' and self.state not in ('suspended', 'retired'):

            raise UserError(
                _('Solo puede cancelar una patente que se encuentra EN PROGRESO. '))
        sw = 0
        for inv in self.patent_id.invoices_ids:
            if inv.state in ('posted', 'draft') and (
                inv.payment_state == False or inv.payment_state == 'not_paid') and not inv.reversal_move_id and not inv.reversed_entry_id:
                sw = 1
                break

        if sw == 1:
            raise UserError(
                _('La patente cuenta con alguna factura sin pagar. Para realizar el cambio de estado, por favor realice el pago de la factura.'))

    def process_update(self):

        self._validations()

        self.patent_id.write({
            'state': self.state,
            'reject_motive': self.motivo,
        })

        mail_message_values = {
            'email_from': self.env.user.partner_id.email,
            'author_id': self.env.user.partner_id.id,
            'model': 'l10n_cr.patent',
            'message_type': 'comment',
            'body': str("La Patente :") + str(self.patent_id.name) + ','
                    + str("<br>")
                    + str("fue ") + str(traslation[self.state]) + str(" por el siguiente motivo:")
                    + str("<br>")
                    + str(self.motivo),
            'res_id': self.patent_id.id,
            'subtype_id': self.env.ref('mail.mt_comment').id,
            'record_name': self.patent_id.name,
        }
        self.env['mail.message'].sudo().create(mail_message_values)

        self.env.user.notify_success(message='Cambio realizado de manera exitosa!', title="BIEN! ")
