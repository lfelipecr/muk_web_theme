odoo.define('l10n_cr_municipality_extend.script', function (require) {
    "use strict";
    require('web.dom_ready')
    $(function () {
        $("#option_cedula").click(function(){
            $("#div_patente").attr('style','display:none');
            $("#div_cedula").removeAttr('style');
            $("#txt_patente").val("")
        })

         $("#option_patente").click(function(){
            $("#div_cedula").attr('style','display:none');
            $("#div_patente").removeAttr('style');
            $("#txt_cedula").val("")
        })

        $("#btnRefresh").click(function(){
            window.location.reload();
        })

        let data_result = []

        if ($('input[name="txt_cedula"]') || $('input[name="txt_patente"]')) {
            //$('#table_data').hide();
            $("#btnConsultar").click(function(){

                var opt_cedula = $("#option_cedula");
                var opt_patente = $("#option_patente");

                var cedula_checked = opt_cedula[0].checked;
                var patente_checked = opt_patente[0].checked;

                if ($('#txt_cedula').val() == "" && cedula_checked == true ){
                    alert("Ingrese el número de cédula.")
                }

                 if ($('#txt_patente').val() == "" && patente_checked == true ){
                    alert("Ingrese el número de patente.")
                }

                $.ajax({
                    type: "GET",
                    data: {
                        'cedula_checked': cedula_checked,
                        'patente_checked': patente_checked,
                        'cedula_name': $('#txt_cedula').val(),
                        'patente_name': $('#txt_patente').val(),
                    },
                    url: "/consulta-patentes-pendientes/search",
                    dataType: "json",
                    success: function (response) {
                        $('#div_table').removeAttr('style');
                        let data = response.data;
                        data_result = data;
                        let template ='';
                        $(data).each(function (i,val){
                            template+= '<tr index="'+ i +'">' +
                                            '<td>'+ val.cliente +'</td>' +
                                            '<td>'+ val.pagado_hasta +'</td>' +
                                            '<td class="text-right">₡ '+ val.saldo_factura +'</td>' +
                                            '<td>'+ val.interes_hasta +'</td>' +
                                            '<td class="text-right">₡ '+ val.saldo_interes +'</td>' +
                                            '<td class="text-right" style="background: #fde9e2">₡ '+ val.saldo_total +'</td>' +
                                      '</tr>';
                        })
                        if(template!=''){
                            template= '<tr>'+ template +'</tr>';
                        }else{
                            template= '<tr><td colspan="3">No hay resultados en su búsqueda</td></tr>';
                        }
                        $('#table_data tbody').html(template);
                    }
                });
            })

        }


    })
})
