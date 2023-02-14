odoo.define('l10n_cr_municipality_extend.wizard', function (require) {
    "use strict";
    require('web.dom_ready')
    let args = {
        "wz_nav_style": "dots",
    };

    const wizard = new Wizard(args);

    wizard.init();


    function validaciones(){
          if( $("#combo_tipo_persona").val() == ""){
            swal('Nota!','Seleccione el tipo de persona','info');
            return false;
          }

          if( $("#m_tipo_identificacion").val() == ""){
            swal('Nota!','Seleccione el tipo de identificación','info');
            return false;
          }

          if( $("#m_identificacion").val() == ""){
            swal('Nota!','Ingrese el número de indentificación','info');
            return false;
          }


          if( $("#m_provincia").val() == ""){
            swal('Nota!','Selecione la provincia','info');
            return false;
          }

          if( $("#m_canton").val() == ""){
            swal('Nota!','Selecione el cantón','info');
            return false;
          }

          if( $("#m_distrito").val() == ""){
            swal('Nota!','Selecione el distrito','info');
            return false;
          }

           if( $("#m_uso_patente").val() == ""){
            swal('Nota!','Selecione el uso de la patente','info');
            return false;
          }

          if( $("#m_area_local").val() == ""){
            swal('Nota!','Ingrese el área del local comercial','info');
            return false;
          }

          if( $("#m_distrito_local").val() == ""){
            swal('Nota!','Seleccione el distrito del local','info');
            return false;
          }


          return true;
    }

    document.addEventListener("submitWizard", function (e) {
           var res = validaciones();

           if (res){
                let jsn = {
                    'combo_tipo_persona': $("#combo_tipo_persona").val(),
                    'm_cedula_juridica': $("#m_cedula_juridica").val(),
                    'm_nombre_persona_juridica': $("#m_nombre_persona_juridica").val(),
                    'm_nombres': $("#m_nombres").val(),
                    'm_apellidos': $("#m_apellidos").val(),
                    'm_tipo_identificacion': $("#m_tipo_identificacion").val(),
                    'm_identificacion': $("#m_identificacion").val(),
                    'm_provincia': $("#m_provincia").val(),
                    'm_canton': $("#m_canton").val(),
                    'm_distrito': $("#m_distrito").val(),
                    'm_direccion': $("#m_direccion").val(),
                    'm_telefono': $("#m_telefono").val(),
                    'm_celular': $("#m_celular").val(),
                    'm_mail': $("#m_mail").val(),
                    'm_uso_patente': $("#m_uso_patente").val(),
                    'm_nombre_fantasia': $("#m_nombre_fantasia").val(),
                    'm_actividad_comercial': $("#m_actividad_comercial").val(),
                    'm_uso_suelo': $("#m_uso_suelo").val(),
                    'm_distrito_local': $("#m_distrito_local").val(),
                    'm_direccion_local': $("#m_direccion_local").val(),
                    'm_area_local': $("#m_area_local").val(),
                    'm_dimensiones_local': $("#m_dimensiones_local").val(),
                };
                let json = JSON.stringify(jsn);
                let files_data = $("#files").prop('files');
                let formData = new FormData($("#form_data")[0]);
                let sw = 0;
                let images_list = [];
                $.each(files_data, function(i, a) {
                formData.append('files[]', a);
                });

                formData.append('json', json);

                $.ajax({
                    type: "post",
                    url: '/patent/request/new',
                    contentType: false,
                    processData: false,
                    cache: false,
                    data: formData,
                    beforeSend: function() {
                        $(".js_loader").addClass("show");
                    },
                    success: function(resultado) {
                        console.log(resultado);
                        var data = JSON.parse(resultado);
                        console.log(data);
                        if (data.estado == 200) {
                            $(".js_loader").removeClass("show");
                            swal('Genial!',data.mensaje, 'success');
                            setTimeout(function() {
                                window.location.reload(true);
                            }, 2e3)
                        } else {
                            $(".js_loader").removeClass("show");
                            swal('Ups!', data.mensaje, 'warning');
                            return 0;
                        }
                    },
                    error: function(error) {
                        $(".js_loader").removeClass("show");
                        console.log(error);
                        swal("Error", error.mensaje, "error");
                    }
                });

           }
    });

     $(function () {

        $("#m_provincia").change(function() {
            let state_id = $("#m_provincia").val();
            $.ajax({
                type: "GET",
                url: "/state/county_id/" + state_id,
                dataType: "json",
                success: function (response) {
                    //var data = JSON.parse(response);
                    var t = '<option value="">-- Seleccione --</option>';
                    $(response).each(function (i, v) {
                        t += '<option value="' + v.id + '">' + v.name + '</option>';
                    })
                    $('#m_canton').empty();
                    $('#m_canton').html(t);
                }
            });

        });

         $("#m_canton").change(function() {
            let county_id = $("#m_canton").val();
            $.ajax({
                type: "GET",
                url: "/county/district_id/" + county_id,
                dataType: "json",
                success: function (response) {
                    //var data = JSON.parse(response);
                    var t = '<option value="">-- Seleccione --</option>';
                    $(response).each(function (i, v) {
                        t += '<option value="' + v.id + '">' + v.name + '</option>';
                    })
                    $('#m_distrito').empty();
                    $('#m_distrito').html(t);
                }
            });

        });


        $("#combo_tipo_persona").change(function() {
            var valor = $("#combo_tipo_persona").val();
            if(valor == '#pj'){
                $("#div_juridica").removeAttr('style');
            }else{
                $("#div_juridica").attr('style','display:none')
            }
        });

        $("#check_uso_suelo").change(function() {
            var check = $("#check_uso_suelo").is(':checked');
            if(check){
                $("#div_uso_suelo").removeAttr('style');
            }else{
                $("#div_uso_suelo").attr('style','display:none')
                $("#m_uso_suelo").val("");
            }
        });


     });





});
