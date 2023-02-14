# -*- coding: utf-8 -*-
import binascii

import pytz
from werkzeug.exceptions import Forbidden
from odoo import http
from odoo.exceptions import UserError, AccessError, MissingError
from odoo.http import request, Response
import logging
import base64
import json
from odoo import fields, http, SUPERUSER_ID, tools, _
import datetime
from odoo.osv.expression import expression

_logger = logging.getLogger(__name__)


class WebSite(http.Controller):
    @http.route('/consulta-de-patentes-pendientes', type='http', auth='public', website=True)
    def show_custom_webpage(self, **kw):
        return http.request.render('l10n_cr_municipality_extend.patentes_pendientes', {})

    @http.route('/patentes-solicitud', type='http', auth='public', website=True)
    def show_patentes_pendientes(self, **kw):
        cr_id = request.env['res.country'].sudo().search([('code', '=', 'CR')])
        provincia = request.env['res.country.state'].sudo().search([('country_id', '=', cr_id.id)])
        identificacion = request.env['l10n_cr.identification'].sudo().search([])
        distritos = request.env['res.country.district'].sudo().search([])
        return http.request.render('l10n_cr_municipality_extend.solicitud_patentes', {'provincias': provincia, 'identificacion': identificacion, 'distritos': distritos})

    @http.route(['/consulta-patentes-pendientes/search'], type='http', auth="public", methods=['GET'], website=True, csrf=False)
    def search_partner_shop(self, cedula_checked='', patente_checked='', cedula_name='', patente_name='', **kw):

        patent_model = request.env['l10n_cr.patent'].sudo()
        patents = False

        if cedula_checked == 'false' and patente_checked == 'false':
            raise UserError(_("Seleccione la forma de búsqueda."))

        if cedula_name == "" and patente_name == "":
            raise UserError(_("Debe ingresar el número de cédula o número de patente."))

        if cedula_checked == 'true' and cedula_name:
            patents = patent_model.search([('state', '=', 'approved'), ('partner_id.vat', '=', cedula_name)])
        elif patente_checked == 'true' and patente_name:
            patents = patent_model.search([('state', '=', 'approved'), ('name', '=', patente_name)])

        patent_list = []

        if not patents:
            return json.dumps({'data': []})

        if patents:
            for patent in patents:

                def _get_interes(inv, fecha):
                    inv.patent_id._caculate_interes_by_move(inv, 'not_assign', fecha)
                    inv_lines = inv.invoice_line_ids.filtered(lambda l: l.trimestre > 0)
                    t = sum(line.interes for line in inv_lines)
                    return inv.currency_id.round(t)

                product_interes_id = patent.env.ref('l10n_cr_municipality_extend.product_intereses').id
                total_intereses = 0.0
                total_residual = 0.0
                if patent.invoices_ids:
                    for inv in patent.invoices_ids:
                        if inv.state == 'draft' and inv.payment_state != 'paid':
                            line = inv.invoice_line_ids.filtered(lambda l: l.product_id.id == product_interes_id)
                            total_residual += (inv.amount_total - line.price_subtotal)
                            date_interes = fields.Date.context_today(patent.with_context(tz='America/Costa_Rica'))
                            total_intereses += round(_get_interes(inv, date_interes), 2)

                        if inv.state == 'posted' and inv.payment_state != 'paid':
                            line_posted = inv.invoice_line_ids.filtered(lambda l: l.product_id.id == product_interes_id)
                            total_residual += (inv.amount_residual - line_posted.price_subtotal)
                            date_interes = inv.date_interes
                            if not date_interes:
                                date_interes = fields.Date.context_today(patent.with_context(tz='America/Costa_Rica'))
                            total_intereses += round(_get_interes(inv, date_interes), 2)

                interes_hasta = '-'
                if total_intereses > 0.0:
                    interes_hasta = str(date_interes)

                dict_p = {
                    'cliente': patent.partner_id.name,
                    'pagado_hasta': str(patent.pay_to) if patent.pay_to else 'Aun no ha pagado',
                    'interes_hasta': interes_hasta,
                    'saldo_factura': total_residual,
                    'saldo_interes': total_intereses,
                    'saldo_total': total_residual + total_intereses
                }

                print(dict_p)

                patent_list.append(dict_p)

        return json.dumps({'data': patent_list})

    @http.route(['/state/county_id/<int:state_id>'], type='http', auth="public", methods=['GET'], website=True, csrf=False)
    def get_county_all(self, state_id=0):
        canton = request.env['res.country.county'].sudo().search([('state_id', '=', state_id)])
        d = []
        for c in canton:
            d.append({
                'id': c.id,
                'name': c.name
            })

        return json.dumps(d)

    @http.route(['/county/district_id/<int:county_id>'], type='http', auth="public", methods=['GET'], website=True, csrf=False)
    def get_district_all(self, county_id=0):
        distrito = request.env['res.country.district'].sudo().search([('county_id', '=', county_id)])
        da = []
        for d in distrito:
            da.append({
                'id': d.id,
                'name': d.name
            })

        return json.dumps(da)

    @http.route('/patent/request/new', type='http', auth="public", website=True, methods=['POST'], csrf=False)
    def restore(self, **post):
        mensaje = ""
        files = request.httprequest.files.getlist('files[]')
        files_list = []

        data = self._get_params(json.loads(post.get('json')))
        company_id = request.env['res.company'].sudo().search([])
        partner_id = self._get_partner(data, company_id)
        # partner_manager_id = company_id.patent_manager_id

        sol_patente = request.env['l10n_cr.patent'].create({
            # 'name':,
            'partner_id': partner_id.id,
            'is_web': True,
            'change_name': True,
            'solicitation_date': datetime.date.today(),
            'type_id': request.env.ref('l10n_cr_municipality_extend.patent_type_other').id
        })
        sol_patente.write({'name': request.env.ref('l10n_cr_municipality_extend.ir_sequence_solicitud_patente').sudo().next_by_id()})
        if not sol_patente:
            pass  # error

        body = self._body_html(data, sol_patente, company_id)
        body_user = self._body_html_user(data, sol_patente, company_id)

        message_body = body_user
        odoobot = request.env.ref('base.partner_root')
        sol_patente.sudo().message_post(body=message_body, message_type='comment', subtype_xmlid='mail.mt_note', author_id=company_id.partner_id.id,
                                        email_from=company_id.partner_id.email)

        for attachment in files:
            json_attachment = {
                'res_name': attachment.filename,
                'res_model': 'l10n_cr.patent',
                'res_id': sol_patente.id,
                'datas': base64.encodebytes(attachment.read()),
                'type': 'binary',
                # 'datas_fname': attachment.filename,
                'name': attachment.filename,
            }
            files_list.append(json_attachment)

        attachs = http.request.env['ir.attachment'].sudo().create(files_list)
        template_customer = http.request.env.ref('l10n_cr_municipality_extend.email_template_solicitud_patente_customer')
        template_user = http.request.env.ref('l10n_cr_municipality_extend.email_template_solicitud_patente_user')
        if template_customer and template_user:
            email_values = {}
            email_values['attachment_ids'] = attachs
            template_customer.sudo().write({'body_html': body})
            template_user.sudo().write({'body_html': body_user})
            # template.sudo().send_mail(sol_patente.id, force_send=True, email_values=email_values, notif_layout='mail.mail_notification_light')
            template_customer.sudo().send_mail(sol_patente.id, force_send=True, email_values=email_values)
            template_user.sudo().send_mail(sol_patente.id, force_send=True, email_values=email_values)

        mensaje += 'Solicitud procesada.'
        return json.dumps({'estado': 200, 'mensaje': mensaje})

    def _get_partner(self, data, company_id):

        # Creacion de partner
        domain = []
        domain.append(('active', '=', True))
        pronvincia = request.env['res.country.state'].sudo().browse(int(data.get('m_provincia')))
        canton = request.env['res.country.state'].sudo().browse(int(data.get('m_canton')))
        distrito = request.env['res.country.state'].sudo().browse(int(data.get('m_distrito')))

        if data['combo_tipo_persona'] == '#pf':
            domain.append(('vat', '=', data.get('m_identificacion')))
            js_partner = {
                'company_type': 'person',
                'vat': data.get('m_identificacion'),
                'name': data.get('m_apellidos') + ' ' + data.get('m_nombres'),
                'state_id': pronvincia.id,
                'county_id': canton.id,
                'district_id': distrito.id,
                'phone': data.get('m_telefono'),
                'mobile': data.get('m_celular'),
                'email': data.get('m_mail'),
                'company_id': company_id.id

            }
        else:
            domain.append(('vat', '=', data.get('m_cedula_juridica')))
            js_partner = {
                'company_type': 'company',
                'vat': data.get('m_cedula_juridica'),
                'name': data.get('m_nombre_persona_juridica'),
                'state_id': pronvincia.id,
                'county_id': canton.id,
                'district_id': distrito.id,
                'phone': data.get('m_telefono'),
                'mobile': data.get('m_celular'),
                'email': data.get('m_mail'),
                'representante_name': data.get('m_apellidos') + ' ' + data.get('m_nombres'),
                'representante_identity': data.get('m_identificacion'),
                'company_id': company_id.id
            }

        partner_id = request.env['res.partner'].sudo().search(domain, limit=1)
        if not partner_id:
            partner_id = request.env['res.partner'].sudo().create(js_partner)

        else:
            partner_id.sudo().write(js_partner)

        return partner_id

    def _get_params(self, params):

        return {
            'combo_tipo_persona': params.get('combo_tipo_persona'),
            'm_cedula_juridica': params.get('m_cedula_juridica'),
            'm_nombre_persona_juridica': params.get('m_nombre_persona_juridica'),
            'm_nombres': params.get('m_nombres'),
            'm_apellidos': params.get('m_apellidos'),
            'm_tipo_identificacion': params.get('m_tipo_identificacion'),
            'm_identificacion': params.get('m_identificacion'),
            'm_provincia': params.get('m_provincia'),
            'm_canton': params.get('m_canton'),
            'm_distrito': params.get('m_distrito'),
            'm_direccion': params.get('m_direccion'),
            'm_telefono': params.get('m_telefono'),
            'm_celular': params.get('m_celular'),
            'm_mail': params.get('m_mail'),
            'm_uso_patente': params.get('m_uso_patente'),
            'm_nombre_fantasia': params.get('m_nombre_fantasia'),
            'm_actividad_comercial': params.get('m_actividad_comercial'),
            'm_uso_suelo': params.get('m_uso_suelo'),
            'm_distrito_local': params.get('m_distrito_local'),
            'm_direccion_local': params.get('m_direccion_local'),
            'm_area_local': params.get('m_area_local'),
            'm_dimensiones_local': params.get('m_dimensiones_local'),

        }

    def _body_html(self, params, sol_patente, company_id):
        # wizard.body_html = _('Hello,<br><br>There are some amazing job offers in my company! Have a look, they  can be interesting for you<br><a href="%s">See Job Offers</a>') % (wizard.url)
        identificacion = params.get('m_identificacion')
        if params.get('combo_tipo_persona') == '#pf':
            tipo_persona = 'Persona Física'
        else:
            tipo_persona = 'Persona Jurídica'

        if params.get('m_cedula_juridica'):
            cedula_juridica = params.get('m_cedula_juridica')
        else:
            cedula_juridica = '-'

        if params.get('m_nombre_persona_juridica'):
            nombre_juridico = params.get('m_nombre_persona_juridica')
        else:
            nombre_juridico = '-'

        if params.get('m_uso_patente') == 'uso_comer':
            uso_patente = 'Comercial'
        else:
            uso_patente = 'Transporte'

        tipo_identificacion = request.env['l10n_cr.identification'].sudo().browse(int(params.get('m_tipo_identificacion')))
        distrito_local = request.env['res.country.district'].sudo().browse(int(params.get('m_distrito_local')))

        body = """<table border="0" cellpadding="0" cellspacing="0" style="padding-top: 16px; background-color: #F1F1F1; font-family:Verdana, Arial,sans-serif; color: #454748; width: 100%; border-collapse:separate;"><tr><td align="center">
            <table border="0" cellpadding="0" cellspacing="0" width="590" style="padding: 16px; background-color: white; color: #454748; border-collapse:separate;">
            <tbody>
                <!-- HEADER -->
                <tr>
                    <td align="center" style="min-width: 590px;">
                        <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
                            <tr><td valign="middle">
                                <span style="font-size: 10px;">Solicitud</span><br/>
                                <span style="font-size: 20px; font-weight: bold;">
                                    {0}
                                </span>
                            </td><td valign="middle" align="right">
                                <img src="/logo.png?company={1}" style="padding: 0px; margin: 0px; height: auto; width: 80px;" alt="{2}"/>
                            </td></tr>
                            <tr><td colspan="2" style="text-align:center;">
                              <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 16px 0px;"/>
                            </td></tr>
                        </table>
                    </td>
                </tr>
                <!-- CONTENT -->
                <tr>
                    <td align="center" style="min-width: 590px;">
                        <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
                            <tr>
                                <td valign="top" style="font-size: 13px;">
                                    <div>                                        

                                        Estimado {3},<br/><br/>
                                        Su solicitud de patente está siendo procesada.
                                        Se recolectaron los siguientes datos: 

                                        <table width="100%">
                                            <body>
                                                <tr><td width="40%"><b>Tipo de persona: </b></td style="color: #002974"><td>{4}</td></tr>
                                                <tr><td width="40%"><b>Cédula jurídica: </b></td style="color: #002974"><td>{5}</td></tr>
                                                <tr><td width="40%"><b>Nombre de persona jurídica: </b></td style="color: #002974"><td>{6}</td></tr>
                                                <tr><td width="40%"><b>Tipo identificación: </b></td style="color: #002974"><td>{7}</td></tr>
                                                <tr><td width="40%"><b>Identificación: </b></td style="color: #002974"><td>{8}</td></tr>
                                                <tr><td width="40%"><b>Teléfono: </b></td style="color: #002974"><td>{13}</td></tr>
                                                <tr><td width="40%"><b>Celular: </b></td style="color: #002974"><td>{14}</td></tr>
                                                <tr><td width="40%"><b>Mail: </b></td style="color: #002974"><td>{15}</td></tr>
                                                <tr><td width="40%"><b>Uso Patente: </b></td style="color: #002974"><td>{16}</td></tr>
                                                <tr><td width="40%"><b>Nombre Fantasía: </b></td style="color: #002974"><td>{17}</td></tr>
                                                <tr><td width="40%"><b>Actividad Comercial: </b></td style="color: #002974"><td>{18}</td></tr>
                                                <tr><td width="40%"><b>Uso Suelo: </b></td style="color: #002974"><td>{19}</td></tr>
                                                <tr><td width="40%"><b>Distrito Local: </b></td style="color: #002974"><td>{23}</td></tr>
                                                <tr><td width="40%"><b>Dirección Local: </b></td style="color: #002974"><td>{20}</td></tr>
                                                <tr><td width="40%"><b>Area Local: </b></td style="color: #002974"><td>{21}</td></tr>
                                                <tr><td width="40%"><b>Dimensiones Local: </b></td style="color: #002974"><td>{22}</td></tr>                                                
                                            </body>
                                        </table>                                                                                                                                             
                                        <br/>
                                        <br/>                      
                                        Gracias,                                       
                                    </div>
                                </td>
                            </tr>
                            <tr>
                                <td style="text-align:center;">
                                    <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 16px 0px;"/>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
                <!-- FOOTER -->
                <tr>
                    <td align="center" style="min-width: 590px;">
                        <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; font-size: 11px; padding: 0px 8px 0px 8px; border-collapse:separate;">
                            <tr><td valign="middle" align="left">
                                {2}
                            </td></tr>
                            <tr><td valign="middle" align="left" style="opacity: 0.7;">
                                {12}
                                | <a href="'mailto:{9}'" style="text-decoration:none; color: #454748;">{10}</a>
                                | <a href="{11}" style="text-decoration:none; color: #454748;">{11}
                            </td></tr>
                        </table>
                    </td>
                </tr>
            </tbody>
            </table>
            </td></tr>
            <!-- POWERED BY -->
            <tr><td align="center" style="min-width: 590px;">
                <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: #F1F1F1; color: #454748; padding: 8px; border-collapse:separate;">
                  <tr><td style="text-align: center; font-size: 13px;">
                    Powered by <a target="_blank" href="https://www.odoo.com?utm_source=db&amp;utm_medium=auth" style="color: #875A7B;">Odoo</a>
                  </td></tr>
                </table>
            </td></tr>
            </table>""".format(sol_patente.name,
                               company_id.id,
                               company_id.name,
                               sol_patente.partner_id.name,
                               tipo_persona,
                               cedula_juridica,
                               nombre_juridico,
                               tipo_identificacion.name,
                               identificacion,
                               company_id.email,
                               company_id.email,
                               company_id.website,
                               company_id.phone,
                               sol_patente.partner_id.phone,
                               sol_patente.partner_id.mobile,
                               sol_patente.partner_id.email,
                               uso_patente,
                               params.get('m_nombre_fantasia'),
                               params.get('m_actividad_comercial'),
                               params.get('m_uso_suelo'),
                               params.get('m_direccion_local'),
                               params.get('m_area_local'),
                               params.get('m_dimensiones_local'),
                               distrito_local.name,
                               )

        return body

    def _body_html_user(self, params, sol_patente, company_id):
        # wizard.body_html = _('Hello,<br><br>There are some amazing job offers in my company! Have a look, they  can be interesting for you<br><a href="%s">See Job Offers</a>') % (wizard.url)
        identificacion = params.get('m_identificacion')
        if params.get('combo_tipo_persona') == '#pf':
            tipo_persona = 'Persona Física'
        else:
            tipo_persona = 'Persona Jurídica'

        if params.get('m_cedula_juridica'):
            cedula_juridica = params.get('m_cedula_juridica')
        else:
            cedula_juridica = '-'

        if params.get('m_nombre_persona_juridica'):
            nombre_juridico = params.get('m_nombre_persona_juridica')
        else:
            nombre_juridico = '-'

        if params.get('m_uso_patente') == 'uso_comer':
            uso_patente = 'Comercial'
        else:
            uso_patente = 'Transporte'

        tipo_identificacion = request.env['l10n_cr.identification'].sudo().browse(int(params.get('m_tipo_identificacion')))
        distrito_local = request.env['res.country.district'].sudo().browse(int(params.get('m_distrito_local')))

        body = """<table border="0" cellpadding="0" cellspacing="0" style="padding-top: 16px; background-color: #F1F1F1; font-family:Verdana, Arial,sans-serif; color: #454748; width: 100%; border-collapse:separate;"><tr><td align="center">
            <table border="0" cellpadding="0" cellspacing="0" width="590" style="padding: 16px; background-color: white; color: #454748; border-collapse:separate;">
            <tbody>
                <!-- HEADER -->
                <tr>
                    <td align="center" style="min-width: 590px;">
                        <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
                            <tr><td valign="middle">
                                <span style="font-size: 10px;">Solicitud</span><br/>
                                <span style="font-size: 20px; font-weight: bold;">
                                    {0}
                                </span>
                            </td><td valign="middle" align="right">
                                <img src="/logo.png?company={1}" style="padding: 0px; margin: 0px; height: auto; width: 80px;" alt="{2}"/>
                            </td></tr>
                            <tr><td colspan="2" style="text-align:center;">
                              <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 16px 0px;"/>
                            </td></tr>
                        </table>
                    </td>
                </tr>
                <!-- CONTENT -->
                <tr>
                    <td align="center" style="min-width: 590px;">
                        <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
                            <tr>
                                <td valign="top" style="font-size: 13px;">
                                    <div>                                        
                                        Le notificamos que se ha solicitado una nueva Patente.
                                        Se recolectaron los siguientes datos: 

                                        <table width="100%">
                                            <body>
                                                <tr><td width="40%"><b>Solicitada por: </b></td style="color: #002974"><td>{3}</td></tr>
                                                <tr><td width="40%"><b>Tipo de persona: </b></td style="color: #002974"><td>{4}</td></tr>
                                                <tr><td width="40%"><b>Cédula jurídica: </b></td style="color: #002974"><td>{5}</td></tr>
                                                <tr><td width="40%"><b>Nombre de persona jurídica: </b></td style="color: #002974"><td>{6}</td></tr>
                                                <tr><td width="40%"><b>Tipo identificación: </b></td style="color: #002974"><td>{7}</td></tr>
                                                <tr><td width="40%"><b>Identificación: </b></td style="color: #002974"><td>{8}</td></tr>
                                                <tr><td width="40%"><b>Teléfono: </b></td style="color: #002974"><td>{13}</td></tr>
                                                <tr><td width="40%"><b>Celular: </b></td style="color: #002974"><td>{14}</td></tr>
                                                <tr><td width="40%"><b>Mail: </b></td style="color: #002974"><td>{15}</td></tr>
                                                <tr><td width="40%"><b>Uso Patente: </b></td style="color: #002974"><td>{16}</td></tr>
                                                <tr><td width="40%"><b>Nombre Fantasía: </b></td style="color: #002974"><td>{17}</td></tr>
                                                <tr><td width="40%"><b>Actividad Comercial: </b></td style="color: #002974"><td>{18}</td></tr>
                                                <tr><td width="40%"><b>Uso Suelo: </b></td style="color: #002974"><td>{19}</td></tr>
                                                <tr><td width="40%"><b>Distrito Local: </b></td style="color: #002974"><td>{23}</td></tr>
                                                <tr><td width="40%"><b>Dirección Local: </b></td style="color: #002974"><td>{20}</td></tr>
                                                <tr><td width="40%"><b>Area Local: </b></td style="color: #002974"><td>{21}</td></tr>
                                                <tr><td width="40%"><b>Dimensiones Local: </b></td style="color: #002974"><td>{22}</td></tr>                                                
                                            </body>
                                        </table>                                                                                                                                             
                                        <br/>
                                        <br/>
                                        Gracias,                                       
                                    </div>
                                </td>
                            </tr>
                            <tr>
                                <td style="text-align:center;">
                                    <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 16px 0px;"/>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
                <!-- FOOTER -->
                <tr>
                    <td align="center" style="min-width: 590px;">
                        <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; font-size: 11px; padding: 0px 8px 0px 8px; border-collapse:separate;">
                            <tr><td valign="middle" align="left">
                                {2}
                            </td></tr>
                            <tr><td valign="middle" align="left" style="opacity: 0.7;">
                                {12}
                                | <a href="'mailto:{9}'" style="text-decoration:none; color: #454748;">{10}</a>
                                | <a href="{11}" style="text-decoration:none; color: #454748;">{11}
                            </td></tr>
                        </table>
                    </td>
                </tr>
            </tbody>
            </table>
            </td></tr>
            <!-- POWERED BY -->
            <tr><td align="center" style="min-width: 590px;">
                <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: #F1F1F1; color: #454748; padding: 8px; border-collapse:separate;">
                  <tr><td style="text-align: center; font-size: 13px;">
                    Powered by <a target="_blank" href="https://www.odoo.com?utm_source=db&amp;utm_medium=auth" style="color: #875A7B;">Odoo</a>
                  </td></tr>
                </table>
            </td></tr>
            </table>""".format(sol_patente.name,
                               company_id.id,
                               company_id.name,
                               sol_patente.partner_id.name,
                               tipo_persona,
                               cedula_juridica,
                               nombre_juridico,
                               tipo_identificacion.name,
                               identificacion,
                               company_id.email,
                               company_id.email,
                               company_id.website,
                               company_id.phone,
                               sol_patente.partner_id.phone,
                               sol_patente.partner_id.mobile,
                               sol_patente.partner_id.email,
                               uso_patente,
                               params.get('m_nombre_fantasia'),
                               params.get('m_actividad_comercial'),
                               params.get('m_uso_suelo'),
                               params.get('m_direccion_local'),
                               params.get('m_area_local'),
                               params.get('m_dimensiones_local'),
                               distrito_local.name
                               )

        return body