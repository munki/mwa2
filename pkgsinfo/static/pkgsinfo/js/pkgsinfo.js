function do_resize() {
    $('#item_editor').height($(window).height() - 180);
    //ace editor is dumb and needs the height specifically as well
    $('#plist').height($(window).height() - 180);
    $('#item_list').height($(window).height() - 100);
    $('.dataTables_scrollBody').height($(window).height() - 180);
}

$(window).resize(do_resize);

$(document).ready(function() {
    initPkginfoTable();
    hash = window.location.hash;
    if (hash.length > 1) {
        getPkginfoItem(hash.slice(1));
    }
    //getCatalogNames();
    getCatalogData();
    $('#listSearchField').focus();
    do_resize();
    // register an event handler to trigger when we get our catalog data
    $('#catalog_dropdown_list').on('custom.update', function () {
        update_catalog_dropdown_list();
    })
    $('#mass_delete').on('click', confirmMassDelete);
    $('#massaction_dropdown').on('click', enableMassActionMenuItems);
    $('#mass_edit_catalogs').on('click', openMassEditModal);
    $(".chosen-select").chosen({width: "100%"});
    
    $(window).on('hashchange', function() {
        hash = window.location.hash;
        if (hash.length > 1) {
            //getPkginfoItem(hash.slice(1));
        }
    });
    
} );


function select_catalog(name) {
    $('#catalog_dropdown').html(name + ' <span class="caret"></span>');
    $('#catalog_dropdown').data('value', name);
    var dt = $('#list_items').DataTable();
    dt.rows().invalidate();
    dt.draw();
}


function update_catalog_dropdown_list() {
    var catalog_list = getValidCatalogNames();
    var list_html = '<li><a href="#" onClick="select_catalog(\'all\')">all</a></li>\n';
    for (var i=0; i < catalog_list.length; i++) {
        list_html += '<li><a href="#" onClick="select_catalog(\''+ catalog_list[i] + '\')">' + catalog_list[i] + '</a></li>\n';
    }
    $('#catalog_dropdown_list').html(list_html);
}


function update_catalog_edit_list() {
    var catalog_list = getValidCatalogNames();
    $('#catalogs_to_add').empty();
    $('#catalogs_to_delete').empty();
    for (var i=0; i < catalog_list.length; i++) {
        var option = $('<option/>').attr("value", catalog_list[i]).text(catalog_list[i]);
        $('#catalogs_to_add').append(option);
        $('#catalogs_to_delete').append(option.clone());
    }
    $('#catalogs_to_add').trigger("chosen:updated");
    $('#catalogs_to_delete').trigger("chosen:updated");
}


function getValidCatalogNames() {
    // return a list of valid catalog names, which are the keys to the
    // catalog_data object minus those keys that start with "._"
    var data = $('#data_storage').data('catalog_data');
    if (data) {
        var raw_names = Object.keys(data);
        // in Python this would be
        // return [item for item in raw_names if not item.startswith('._')]
        return raw_names.filter(function(x){return (x.substring(0, 2) != "._")})
    }
    return [];
}

function getValidInstallItems() {
    // return a list of valid install item names
    var data = $('#data_storage').data('catalog_data');
    if (data) {
        var catalog_list = Object.keys(data);
        var suggested = [];
        for (var i=0, l=catalog_list.length; i<l; i++) {
            var catalog_name = catalog_list[i];
            if ( data.hasOwnProperty(catalog_name) ) {
                Array.prototype.push.apply(suggested, data[catalog_name]['suggested']);
                Array.prototype.push.apply(suggested, data[catalog_name]['updates']);
                Array.prototype.push.apply(suggested, data[catalog_name]['with_version']);
            }
        }
        return uniques(suggested);
    } else {
        return [];
    }
}


$.fn.dataTable.ext.search.push(
    function( settings, searchData, index, rowData, counter ) {
        // custom search filter to filter out rows that have no versions
        // in the current catalog
        var catalog = $('#catalog_dropdown').data('value'),
            column = rowData[1];
        for(var i = 0; i < column.length; i++) {
            if (catalog == 'all' || column[i][1].indexOf(catalog) != -1) {
                // found our catalog
                return true;
            }
        }
        // didn't find the catalog, so filter this row out
        return false;
    }
);


function get_checked_items() {
    var selected_items = [];
    $('.pkginfo_items').each(function(){
        if ($(this).children('input').is(':checked')) {
            selected_items.push($(this).data('path'));
        }
    })
    return selected_items;
}


var enableMassActionMenuItems = function() {
    if (get_checked_items().length == 0) {
        $('#massaction_dropdown_list').children('li').addClass('disabled');
    } else {
        $('#massaction_dropdown_list').children('li').removeClass('disabled');
    }
}


var confirmMassDelete = function() {
    var selected_items = get_checked_items()
    var selected_item_count = selected_items.length
    if (selected_item_count > 0) {
        if (selected_item_count == 1) {
            $('#massDeleteConfirmationModalBodyText').text('Really delete ' + selected_items[0] + '?');
        } else {
            $('#massDeleteConfirmationModalBodyText').text('Really delete the ' + selected_item_count.toString() + ' selected pkginfo items?');
        }
        // show the deletion confirmation dialog
        $("#massDeleteConfirmationModal").modal("show");
    }
}


var openMassEditModal = function() {
    var selected_items = get_checked_items()
    var selected_item_count = selected_items.length
    if (selected_item_count > 0) {
        if (selected_item_count == 1) {
            $('#massEditModalBodyText').text('Edit catalogs for ' + selected_items[0] + ':');
        } else {
            $('#massEditModalBodyText').text('Edit catalogs for the ' + selected_item_count.toString() + ' selected pkginfo items:');
        }
        update_catalog_edit_list();
        // show the deletion confirmation dialog
        $("#massEditModal").modal("show");
    }
}


var render_versions = function(data, type, row, meta) {
    var html = '<ul class="list">\n';
    var catalog_filter = $('#catalog_dropdown').data('value');
    for(var i = 0; i < data.length; i++) {
        if (catalog_filter == 'all' || data[i][1].indexOf(catalog_filter) != -1) {
            html += '<li class="pkginfo_items" data-path=\'' + data[i][2] + '\'>'
            html += '<a href="#' + data[i][2] 
            html += '" onClick="getPkginfoItem(\'' + data[i][2] + '\')">' 
            html += data[i][0] + '</a>'
            html += '<input type="checkbox" class="pull-right"/></li>\n';
        }
    }
    html += '</ul>\n';
    return html
}


var render_name = function(data, type, row, meta) {
    data = data.replace(".", "<wbr/>.");
    data = data.replace("_", "<wbr/>_");
    return data;
}


function initPkginfoTable() {
    $('#list_items').dataTable({
        ajax: {
            url: "/pkgsinfo/_json",
            cache: false,
            dataSrc: "",
            complete: function(jqXHR, textStatus){
                  window.clearInterval(poll_loop);
                  $('#process_progress').modal('hide');
                },
            global: false,
        },
        columnDefs: [
         { "targets": 0,
            //"width": "60%",
            "render": render_name,
         },
         {
            "targets": 1,
            "render": render_versions,
            "searchable": false,
            "orderable": false,
          },],
         "sDom": "<t>",
         "bPaginate": false,
         "scrollY": "80vh",
         "bInfo": false,
         "bFilter": true,
         "bStateSave": false,
         "aaSorting": [[0,'asc']]
     });
     // start our monitoring timer loop
     monitor_pkgsinfo_list();
     // tie our search field to the table
     var thisTable = $('#list_items').DataTable(),
         searchField = $('#listSearchField');
     searchField.keyup(function(){
         thisTable.search($(this).val()).draw();
     });
     //searchField.trigger('keyup');
}


function cancelEdit() {
    //$('#cancelEditConfirmationModal').modal('hide');
    $('.modal-backdrop').remove();
    hideSaveOrCancelBtns();
    getPkginfoItem(current_pathname);
}


function setupView(viewName) {
    selected_tab_viewname = viewName;
    if (viewName == '#basicstab') {
        constructBasics();
    } else if (viewName == '#detailtab') {
        constructDetail();
    } else if (viewName == '#plisttab') {
        editor.focus();
        editor.resize(true);
    }
}

function constructBasics() {
    if (js_obj != null) {
        $('#basics').html('')
        $('#basics').plistEditor(js_obj,
            { change: updatePlistAndDetail,
              keylist: key_list,
              keytypes: keys_and_types,
              validator: validator});
    } else {
        $('#basics').html('<br/>Invalid plist.')
    }
    setupTypeahead();
}


function constructDetail() {
    if (js_obj != null) {
        $('#detail').html('')
        $('#detail').plistEditor(js_obj, 
            { change: updatePlistAndBasics,
              keytypes: keys_and_types,
              validator: validator});
    } else {
        $('#detail').html('<br/>Invalid plist.')
    }
   setupTypeahead();
}


function updatePlist() {
    if (js_obj != null) {
        editor.setValue(PlistParser.toPlist(js_obj, true));
        editor.selection.clearSelection();
        editor.selection.moveCursorToPosition({row: 0, column: 0});
        editor.selection.selectFileStart();
    }
}


function updatePlistAndBasics(data) {
    js_obj = data;
    showSaveOrCancelBtns();
    updatePlist();
    setupTypeahead();
}


function updatePlistAndDetail(data) {
    js_obj = data;
    showSaveOrCancelBtns();
    updatePlist();
    setupTypeahead();
}


function plistChanged() {
    showSaveOrCancelBtns();
    var val = editor.getValue();
    if (val) {
        try { js_obj = PlistParser.parse(val); }
        catch (e) { 
            //alert('Error in parsing plist. ' + e);
            js_obj = null;
        }
    } else {
        js_obj = {};
    }
}


var current_pathname = "";
var requested_pathname = "";
var editor = null;

function getPkginfoItem(pathname) {
    //event.preventDefault();
    if ($('#save_and_cancel').length && !$('#save_and_cancel').hasClass('hidden')) {
        /*if (! confirm('Discard current changes?')) {
            event.preventDefault();
            return;
        }*/
        requested_pathname = pathname;
        $("#saveOrCancelConfirmationModal").modal("show");
        event.preventDefault();
        return;
    }
    var pkginfoItemURL = '/pkgsinfo/' + pathname;
    $.ajax({
      type: 'GET',
      url: pkginfoItemURL,
      timeout: 10000,
      cache: false,
      success: function(data) {
          $('#pkginfo_item_detail').html(data);
          val = $('#plist').text();
          try { js_obj = PlistParser.parse(val); }
          catch (e) { 
                //alert('Error in parsing plist. ' + e);
                js_obj = null;
          }
          $('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
              //e.target // newly activated tab
              //e.relatedTarget // previous active tab
              setupView(e.target.hash);
          })
          editor = initializeAceEditor('plist', plistChanged);
          hideSaveOrCancelBtns();
          detectUnsavedChanges();
          current_pathname = pathname;
          requested_pathname = "";
          $('#editortabs a[href="' + selected_tab_viewname + '"]').tab('show');
          setupView(selected_tab_viewname);
          do_resize();
      },
      error: function(jqXHR, textStatus, errorThrown) {
        alert("ERROR: " + textStatus + "\n" + errorThrown);
        $('#pkginfo_item_detail').html("")
        current_pathname = "";
      },
      dataType: 'html'
    });
}

function discardChangesAndLoadNext() {
    //$('#saveOrCancelConfirmationModal').modal('hide');
    $('.modal-backdrop').remove();
    hideSaveOrCancelBtns();
    getPkginfoItem(requested_pathname);
}


function saveChangesAndLoadNext() {
    savePkginfoItem();
    //$('#saveOrCancelConfirmationModal').modal('hide');
    $('.modal-backdrop').remove();
}


var js_obj = {};

var selected_tab_viewname = "#basicstab";

// these should be moved into their own file maybe so they can be edited
// seperately
var key_list = {'name': 'Name', 
                'version': 'Version', 
                'display_name': 'Display name', 
                'description': 'Description', 
                'catalogs': 'Catalogs',
                'category': 'Category',
                'developer': 'Developer',
                'unattended_install': 'Unattended install',
                'unattended_uninstall': 'Unattended uninstall'};

// these should be moved into their own file maybe so they can be edited
// seperately
var keys_and_types = {'apple_item': true,
                      'autoremove': true,
                      'blocking_applications': ['appname'],
                      'catalogs': [''],
                      'description': '',
                      'display_name': '',
                      'force_install_after_date': new Date(),
                      'icon_name': '',
                      'installable_condition': '',
                      'installed_size': 0,
                      'installer_choices_xml': '',
                      'installer_environment': {'USER': 'CURRENT_CONSOLE_USER'},
                      'installer_item_hash': '',
                      'installer_item_location': '',
                      'installer_type': '',
                      'installs': [{'type': 'file',
                                    'path': ''}],
                      'items_to_copy': [{'destination_path': '',
                                         'source_item': '',
                                         'user': 'root',
                                         'group': 'admin',
                                         'mode': 'o-w'}],
                      'minimum_munki_version': '2.3.0',
                      'minimum_os_version': '10.6.',
                      'maximum_os_version': '10.11',
                      'name': '',
                      'notes': '',
                      'OnDemand': true,
                      'PackageCompleteURL': '',
                      'PackageURL': '',
                      'package_path': '',
                      'installcheck_script': '',
                      'uninstallcheck_script': '',
                      'postinstall_script': '#!/bin/sh\nexit 0',
                      'postuninstall_script': '#!/bin/sh\nexit 0',
                      'preinstall_alert': {'alert_title': 'Preinstall Alert', 
                                           'alert_detail': 'Some important information',
                                           'ok_label': 'Install',
                                           'cancel_label': 'Cancel'},
                      'preuninstall_alert': {'alert_title': 'Preuninstall Alert', 
                                             'alert_detail': 'Some important information',
                                             'ok_label': 'Uninstall',
                                             'cancel_label': 'Cancel'},
                      'preupgrade_alert': {'alert_title': 'Preupgrade Alert', 
                                           'alert_detail': 'Some important information',
                                           'ok_label': 'Install',
                                           'cancel_label': 'Cancel'},
                      'preinstall_script': '#!/bin/sh\nexit 0',
                      'preuninstall_script': '#!/bin/sh\nexit 0',
                      'requires': ['itemname'],
                      'RestartAction': 'RequireRestart',
                      'supported_architectures': [''],
                      'unattended_install': true,
                      'unattended_uninstall': true,
                      'uninstall_method': '',
                      'uninstall_script': '',
                      'uninstaller_item_location': '',
                      'uninstallable': true,
                      'update_for': ['itemname'],
                      'version': '1.0'};


var validator = function(path, val) {
    var path_items = path.split('.');
    if (path_items.indexOf('requires') != -1 ||
        path_items.indexOf('update_for') != -1) {
            //check val against valid install items
            var valid_names = getValidInstallItems();
            if (valid_names.length && valid_names.indexOf(val) == -1) {
                return 'danger';
        }
    }
    return null;
};


function setupTypeahead() {
    // typeahead/autocomplete for pkginfo keys
    // suggest keys that are not already in use
    if (js_obj == null) return;
    var keys_in_use = Object.keys(js_obj),
        suggested_keys = Object.keys(keys_and_types),
        keys_to_suggest = suggested_keys.filter(function(value, index, arr){
            return (keys_in_use.indexOf(value) == -1)
        });
    $('div.plist-editor input.property').typeahead({source: keys_to_suggest});
    $('tr[data-path="catalogs"] textarea.value.form-control').typeahead({source: function(query, process) {
            return process(getValidCatalogNames());
        }
    });
    $('tr[data-path="requires"] textarea.value.form-control').typeahead({source: function(query, process) {
            return process(getValidInstallItems());
        }
    });
    $('tr[data-path="update_for"] textarea.value.form-control').typeahead({source: function(query, process) {
            return process(getValidInstallItems());
        }
    });
    $('tr[data-path="category"] textarea.value.form-control').typeahead({source: function(query, process) {
            return process(getCategories());
        }
    });
    $('tr[data-path="developer"] textarea.value.form-control').typeahead({source: function(query, process) {
            return process(getDevelopers());
        }
    });
}


function getCategories() {
    var data = $('#data_storage').data('catalog_data');
    if (data) {
        if (data.hasOwnProperty('._categories')) return data['._categories'];
    }
    return [];
}


function getDevelopers() {
    var data = $('#data_storage').data('catalog_data');
    if (data) {
        if (data.hasOwnProperty('._developers')) return data['._developers'];
    }
    return [];
}


function rebuildCatalogs() {
    $('#process_progress_title_text').text('Rebuilding catalogs...')
    $('#process_progress_status_text').text('Processing...')
    $('#process_progress').modal('show');
    poll_loop = setInterval(function() {
            update_status('/makecatalogs/status');
        }, 1000);
    $.ajax({
        type: 'POST',
        url: '/makecatalogs/run',
        data: '',
        dataType: 'json',
        global: false,
        complete: function(jqXHR, textStatus){
            window.clearInterval(poll_loop);
            $('#process_progress').modal('hide');
            $('#list_items').DataTable().ajax.reload();
        },
    });
}


function monitor_pkgsinfo_list() {
    $('#process_progress_title_text').text('Getting pkgsinfo data...')
    $('#process_progress_status_text').text('Processing...')
    poll_loop = setInterval(function() {
            update_status('/pkgsinfo/__get_process_status');
        }, 1000);
}


function savePkginfoItem() {
    // save pkginfo item back to the repo
    $('.modal-backdrop').remove();
    var plist_data = editor.getValue();
    //var postdata = JSON.stringify({'plist_data': plist_data});
    var pkginfoItemURL = '/api/pkgsinfo/' + current_pathname;
    $.ajax({
        type: 'POST',
        url: pkginfoItemURL,
        headers: {'X_METHODOVERRIDE': 'PUT',
                  'Content-Type': 'application/xml',
                  'Accept': 'application/xml'},
        data: plist_data,
        timeout: 10000,
        success: function(data) {
            hideSaveOrCancelBtns();
            rebuildCatalogs();
            if (requested_pathname.length) {
                getPkginfoItem(requested_pathname);
            }
        },
        error: function(jqXHR, textStatus, errorThrown) {
              try {
                  var json_data = $.parseJSON(jqXHR.responseText)
                  if (json_data['result'] == 'failed') {
                      $("#errorModalTitleText").text("Pkginfo write error");
                      $("#errorModalDetailText").text(json_data['detail']);
                      $("#errorModal").modal("show");
                      return;
                  }
              } catch(err) {
                  // do nothing
              }
              //alert("ERROR: " + textStatus + "\n" + errorThrown);
              $("#errorModalTitleText").text("Pkginfo write error");
              $("#errorModalDetailText").text(textStatus);
              $("#errorModal").modal("show");
              return;
          },
    });
}


function showDeleteConfirmationModal() {
    var installer_item_path = $('#pathname').data('installer-item-path');
    if (installer_item_path) {
        // we need to check to see how many pkginfo items reference this
        // installer item path; if more than one we should not offer to
        // delete the installer_item as well
        // most items should have a single reference, so we'll start 
        // with the checkbox visible, but disabled
        // (checkbox is hidden by default so it's not shown when an item
        //  doesn't have an associated installer_item, like
        //  apple_update_metadata or nopkg items)
        // TO-DO: offer to remove associated uninstaller items
        $('#deleteConfirmationModalInstallerItem').removeClass('hidden');
        $('#delete_pkg').attr('disabled', true);
        // ask the server for the count of references for the installer item
        $.ajax({
          type: 'GET',
          url: '/catalogs/get_pkg_ref_count/' + installer_item_path,
          timeout: 10000,
          cache: false,
          success: function(data) {
              if (data == 1) {
                  // a single reference! we can enable the checkbox
                  $('#delete_pkg').removeAttr("disabled");
              } else {
                  // multiple references! hide the checkbox
                  $('#deleteConfirmationModalInstallerItem').addClass('hidden');
              }
          },
          error: function(jqXHR, textStatus, errorThrown) {
            // do nothing currently, which leaves the checkbox
            // visible but disabled. Better safe than sorry
          },
          dataType: 'json'
        });
    }
    // show the deletion confirmation dialog
    $("#deleteConfirmationModal").modal("show");
}


function massEditCatalogs() {
    var pkginfo_list = get_checked_items();
    var catalogs_to_add = ($("#catalogs_to_add").val() || []);
    var catalogs_to_delete = ($("#catalogs_to_delete").val() || []);
    //alert(catalogs_to_add);
    //alert(catalogs_to_delete);
    //return;
    $.ajax({
      type: 'POST',
      url: '/pkgsinfo/',
      data: JSON.stringify({'pkginfo_list': pkginfo_list,
                            'catalogs_to_add': catalogs_to_add,
                            'catalogs_to_delete': catalogs_to_delete}),
      success: function(data) {
          rebuildCatalogs();
          window.location.hash = '';
          $('#pkginfo_item_detail').html('');
      },
      error: function(jqXHR, textStatus, errorThrown) {
         try {
              var json_data = $.parseJSON(jqXHR.responseText)
              if (json_data['result'] == 'failed') {
                  $("#errorModalTitleText").text("Mass edit error");
                  $("#errorModalDetailText").text(json_data['detail']);
                  $("#errorModal").modal("show");
                  return;
              }
          } catch(err) {
              // do nothing
          }
          //alert("ERROR: " + textStatus + "\n" + errorThrown);
          $("#errorModalTitleText").text("Mass edit error");
          $("#errorModalDetailText").text(textStatus);
          $("#errorModal").modal("show");
          return;
      },
      dataType: 'json'
    });
}


function deletePkginfoList() {
    var pkginfo_list = get_checked_items();
    var deletePkg = $('#mass_delete_pkg').is(':checked');
    $.ajax({
      type: 'POST',
      url: '/pkgsinfo/',
      data: JSON.stringify({'pkginfo_list': pkginfo_list,
                            'deletePkg': deletePkg}),
      headers: {'X_METHODOVERRIDE': 'DELETE'},
      success: function(data) {
          rebuildCatalogs();
          window.location.hash = '';
          $('#pkginfo_item_detail').html('');
      },
      error: function(jqXHR, textStatus, errorThrown) {
          try {
              var json_data = $.parseJSON(jqXHR.responseText)
              if (json_data['result'] == 'failed') {
                  $("#errorModalTitleText").text("Mass delete error");
                  $("#errorModalDetailText").text(json_data['detail']);
                  $("#errorModal").modal("show");
                  return;
              }
          } catch(err) {
              // do nothing
          }
          //alert("ERROR: " + textStatus + "\n" + errorThrown);
          $("#errorModalTitleText").text("Mass delete error");
          $("#errorModalDetailText").text(textStatus);
          $("#errorModal").modal("show");
          return;
      },
      dataType: 'json'
    });
}


function deleteInstallerItem(installer_item_path) {
    if (installer_item_path) {
        the_url = "/api/pkgs/" + installer_item_path
        $.ajax({
            type: 'POST',
            url: the_url,
            headers: {'X_METHODOVERRIDE': 'DELETE'},
            success: function(data) {
                // do nothing
            },
            error: function(jqXHR, textStatus, errorThrown) {
                try {
                    var json_data = $.parseJSON(jqXHR.responseText)
                    if (json_data['result'] == 'failed') {
                        $("#errorModalTitleText").text("Package delete error");
                        $("#errorModalDetailText").text(json_data['detail']);
                        $("#errorModal").modal("show");
                        return;
                    }
                } catch(err) {
                    // do nothing
                }
                //alert("ERROR: " + textStatus + "\n" + errorThrown);
                $("#errorModalTitleText").text("Package delete error");
                $("#errorModalDetailText").text(textStatus);
                $("#errorModal").modal("show");
                return;
            },
        });
    }
}


function deletePkginfoItem() {
    // do the actual pkginfo item deletion
    $('.modal-backdrop').remove();
    var pkginfoItemURL = '/api/pkgsinfo/' + current_pathname;
    var delete_pkg = $('#delete_pkg').is(':checked');
    var installer_item_path = $('#pathname').data('installer-item-path');
    $.ajax({
        type: 'POST',
        url: pkginfoItemURL,
        headers: {'X_METHODOVERRIDE': 'DELETE'},
        success: function(data) {
            if (delete_pkg) {
                deleteInstallerItem(installer_item_path);
            }
            rebuildCatalogs();
            window.location.hash = '';
            $('#pkginfo_item_detail').html('');
        },
        error: function(jqXHR, textStatus, errorThrown) {
            try {
                var json_data = $.parseJSON(jqXHR.responseText)
                if (json_data['result'] == 'failed') {
                    $("#errorModalTitleText").text("Pkginfo delete error");
                    $("#errorModalDetailText").text(json_data['detail']);
                    $("#errorModal").modal("show");
                    return;
                }
            } catch(err) {
                // do nothing
            }
            //alert("ERROR: " + textStatus + "\n" + errorThrown);
            $("#errorModalTitleText").text("Pkginfo delete error");
            $("#errorModalDetailText").text(textStatus);
            $("#errorModal").modal("show");
            return;
        },
    });
}
