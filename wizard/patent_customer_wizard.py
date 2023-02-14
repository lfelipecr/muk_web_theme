# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from io import BytesIO
import base64
from datetime import datetime
import xlsxwriter
from odoo import models, fields, api, _


class PatentCustomerWizard(models.TransientModel):
    _name = "patent.customer.wizard"

    xls_filename = fields.Char(u'Nombre de fichero')
    xls_file = fields.Binary(u'Descargar reporte', readonly=True)

    def process(self):
        excel = BytesIO()
        workbook = xlsxwriter.Workbook(excel, {'in_memory': True})

        header = workbook.add_format({
            'font_name': 'DejaVu Sans',
            'font_size': 10,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#1F497D',
            'font_color': 'white',
            'border': 0
        })

        header_detalle = workbook.add_format({
            'font_name': 'DejaVu Sans',
            'font_size': 9.5,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#efefef',
            'border': 0
        })
        body = workbook.add_format({
            'font_name': 'DejaVu Sans',
            'font_size': 8,
            'align': 'left',
            'valign': 'vcenter',
            'bg_color': '#ffffff',
            'font_color': '#003a92',
            'border': 0
        })

        name = workbook.add_format({
            'font_name': 'DejaVu Sans',
            'font_size': 8,
            'align': 'left',
            'valign': 'vcenter',
            'bg_color': '#ffffff',
            'font_color': '#003a92',
            'border': 0,
            'bold':1
        })

        number = workbook.add_format({ 'font_name': 'DejaVu Sans',
            'font_size': 8,
            'align': 'right',
            'valign': 'vcenter',
            'bg_color': '#ffffff',
            'font_color': '#003a92',
            'border': 0,
            'num_format': '#,###,##0.00'})

        sheet = workbook.add_worksheet(u'Lista de patentados')

        # Especificamos cabecera
        sheet.merge_range('A1:AD1', u'Patentados en la Municipalidad de Rio Cuarto', header)

        sheet.set_column('A:A', 15)
        sheet.set_column('B:B', 39)
        sheet.set_column('C:C', 25)
        sheet.set_column('D:D', 25)
        sheet.set_column('E:E', 25)
        sheet.set_column('F:F', 25)
        sheet.set_column('G:G', 25)
        sheet.set_column('H:H', 25)
        sheet.set_column('I:I', 25)
        sheet.set_column('J:J', 29)
        sheet.set_column('K:K', 80)
        sheet.set_column('L:L', 25)
        sheet.set_column('M:M', 25)
        sheet.set_column('N:N', 25)
        sheet.set_column('O:O', 25)
        sheet.set_column('P:P', 25)
        sheet.set_column('Q:Q', 25)
        sheet.set_column('R:R', 25)
        sheet.set_column('S:S', 25)
        sheet.set_column('T:T', 25)
        sheet.set_column('U:U', 25)
        sheet.set_column('V:V', 25)
        sheet.set_column('W:W', 25)
        sheet.set_column('X:X', 25)
        sheet.set_column('Y:Y', 80)
        sheet.set_column('Z:Z', 25)
        sheet.set_column('AA:AA', 25)
        sheet.set_column('AB:AB', 25)
        sheet.set_column('AC:AC', 13)
        sheet.set_column('AD:AD', 10)
        #sheet.set_column('AE:AE', 25)
        #sheet.set_column('AF:AF', 25)
        #sheet.set_column('AG:AG', 25)

        sheet.write('A2', 'Sol.Identificación', header_detalle)
        sheet.write('B2', 'Solicitante', header_detalle)
        sheet.write('C2', 'Representante Legal', header_detalle)
        sheet.write('D2', 'N° Identificación', header_detalle)
        sheet.write('E2', 'Sol.Tipo Identificación', header_detalle)
        sheet.write('F2', 'Sol.Celular', header_detalle)
        sheet.write('G2', 'Sol.Tél.Fijo', header_detalle)
        sheet.write('H2', 'Sol.Correo Electrónico', header_detalle)
        sheet.write('I2', 'Sol.Actividad Económica', header_detalle)
        sheet.write('J2', 'Nombre comercial o de fantasía', header_detalle)
        sheet.write('K2', 'Dirección', header_detalle)
        sheet.write('L2', 'Prop.Identificación', header_detalle)
        sheet.write('M2', 'Propietario', header_detalle)
        sheet.write('N2', 'Prop.Tipo Identificación', header_detalle)
        sheet.write('O2', 'Prop.Celular', header_detalle)
        sheet.write('P2', 'Prop.Tél.Fijo', header_detalle)
        sheet.write('Q2', 'Prop.Correo Electrónico', header_detalle)
        #sheet.write('R2', 'Prop.Actividad Económica', header_detalle)
        sheet.write('R2', 'N° Finca', header_detalle)
        sheet.write('S2', 'Duplicado', header_detalle)
        sheet.write('T2', 'Horizontal', header_detalle)
        sheet.write('U2', 'Derecho', header_detalle)
        sheet.write('V2', 'Provincia', header_detalle)
        sheet.write('W2', 'Cantón', header_detalle)
        sheet.write('X2', 'Distrito', header_detalle)
        sheet.write('Y2', 'Dirección física', header_detalle)
        sheet.write('Z2', 'N° Patente', header_detalle)
        sheet.write('AA2', 'Tipo Patente', header_detalle)
        #sheet.write('AC2', 'Tipo Temporalidad', header_detalle)
        sheet.write('AB2', 'Monto Impuesto(trimestral)', header_detalle)
        sheet.write('AC2', 'Fecha Aprobación', header_detalle)
        #sheet.write('AF2', 'Fecha Cierre', header_detalle)
        sheet.write('AD2', 'Estado', header_detalle)

        patents = self._get_data()

        if patents:
            i = 2
            for data in patents:
                direccion = (data.partner_id.street or '') + ' / ' + \
                            (data.partner_id.state_id.name or '') + ' / ' + \
                            (data.partner_id.county_id.name or '') + ' / ' + \
                            (data.partner_id.district_id.name or '') + ' / ' + \
                            (data.partner_id.neighborhood_id.name or '') + ' / ' + \
                            (data.partner_id.country_id.name or '')

                sheet.write(i, 0, data.partner_id.vat, name)
                sheet.write(i, 1, data.partner_id.name, name)
                sheet.write(i, 2, data.partner_id.representante_name, body)
                sheet.write(i, 3, data.partner_id.representante_identity, body)
                sheet.write(i, 4, data.partner_id.identification_id.name, body)
                sheet.write(i, 5, data.partner_id.mobile or '', body)
                sheet.write(i, 6, data.partner_id.phone or '', body)
                sheet.write(i, 7, data.partner_id.email or  '', body)
                sheet.write(i, 8, data.commercial_activity, body) #Actividad económica
                sheet.write(i, 9, data.fantasy_name, body)
                sheet.write(i, 10, direccion, body)
                sheet.write(i, 11, data.land_id.partner_id.vat, body)
                sheet.write(i, 12, data.land_id.partner_id.name, body)
                sheet.write(i, 13, data.land_id.partner_id.identification_id.name, body)
                sheet.write(i, 14, data.land_id.partner_id.mobile or '', body)
                sheet.write(i, 15, data.land_id.partner_id.phone or '', body)
                sheet.write(i, 16, data.land_id.partner_id.email or '', body)
                #sheet.write(i, 17, '', body) #Actividad económica
                sheet.write(i, 17, data.land_id.land_number, body)
                sheet.write(i, 18, data.land_id.duplicate or '', body)
                sheet.write(i, 19, data.land_id.horizontal or '', body)
                sheet.write(i, 20, data.land_id.rights_qty or '', body)
                sheet.write(i, 21,  data.district_id.county_id.state_id.name or '', body)
                sheet.write(i, 22, data.district_id.county_id.name or '', body)
                sheet.write(i, 23, data.district_id.name or '', body)
                sheet.write(i, 24, data.address or '', body)
                sheet.write(i, 25, data.name, body)
                sheet.write(i, 26, data.type_id.name, body)
                #sheet.write(i, 28, '', body) #Temporalidad
                sheet.write(i, 27, data.trimester_payment, number)
                if data.date_approved:
                    fecha = datetime.strftime(data.date_approved,'%Y-%m-%d')
                else:
                    fecha = 'Sin fecha'
                sheet.write(i, 28, fecha,  body)
                #sheet.write(i, 31, '', number) #Fecha de cierre
                sheet.write(i, 29, data.state, body)
                i+=1

        workbook.close()
        excel.seek(0)
        return excel.getvalue()


    def excel_report(self):
        for rpt in self:
            name = datetime.now().strftime("%Y%m%d%H%M%S")
            rpt.write(dict(
                xls_filename='patentados' + name + '.xlsx',
                xls_file=base64.b64encode(self.process()),
            ))
            return {
                u'name': u'Reporte de Patentados',
                u'type': u'ir.actions.act_window',
                u'view_type': u'form',
                u'view_mode': u'form',
                u'target': u'new',
                u'res_model': u'patent.customer.wizard',
                u'res_id': rpt.id
            }


    def _get_data(self):
        return self.env['l10n_cr.patent'].sudo().search([])

    def view_list(self):
        sql = """delete from l10ncr_patent_customer_report"""
        self.env.cr.execute(sql)

        patents = self._get_data()
        if patents:
            array = []
            for data in patents:
                direccion = (data.partner_id.street or '') + ' / ' + \
                            (data.partner_id.state_id.name or '') + ' / ' + \
                            (data.partner_id.county_id.name or '') + ' / ' + \
                            (data.partner_id.district_id.name or '') + ' / ' + \
                            (data.partner_id.neighborhood_id.name or '') + ' / ' + \
                            (data.partner_id.country_id.name or '')

                data = {
                    'patent_id': data.id,
                    't_identificacion': data.partner_id.vat,
                    'titular': data.partner_id.name,
                    'r_legal': data.partner_id.representante_name or '-',
                    'r_identificacion': data.partner_id.representante_identity or '-',
                    't_tipo_i': data.partner_id.identification_id.name,
                    't_celular': data.partner_id.mobile,
                    't_fono': data.partner_id.phone,
                    't_mail': data.partner_id.email,
                    't_actividad': data.commercial_activity,
                    'direccion': direccion,
                    'p_identificacion': data.land_id.partner_id.vat,
                    'p_name': data.land_id.partner_id.name,
                    'p_tipo_i': data.land_id.partner_id.identification_id.name,
                    'p_celular': data.land_id.partner_id.mobile,
                    'p_fono': data.land_id.partner_id.phone,
                    'p_mail': data.land_id.partner_id.email,
                    #'p_actividad': data.commercial_activity,
                    'finca': data.land_id.land_number,
                    'duplicado': data.land_id.duplicate,
                    'horizontal': data.land_id.horizontal,
                    'derecho': data.land_id.rights_qty,
                    'provincia': data.district_id.county_id.state_id.name,
                    'canton':  data.district_id.county_id.name,
                    'distrito': data.district_id.name,
                    'direccion_f': data.address,
                    'patente_tipo': data.type_id.name,
                    #'patente_temporalidad':'',
                    'costo_trimestral': data.trimester_payment,
                    'aprobacion': data.date_approved or False,
                    #'cierre': False,
                    'state': data.state,
                }

                array.append(data)


        self.env['l10ncr.patent.customer.report'].sudo().create(array)


        view_id = self.env.ref('l10n_cr_municipality_extend.l10n_cr_patent_customers_view_tree').id

        return {
            'type': 'ir.actions.act_window',
            'name': _('Lista de Patentados'),
            'res_model': 'l10ncr.patent.customer.report',
            'view_mode': 'tree',
            'limit': 99999999,
            'views': [[view_id, 'list']],
        }
