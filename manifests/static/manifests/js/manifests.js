function do_resize() {
    $('#item_editor').height($(window).height() - 180);
    //ace editor is dumb and needs the height specifically as well
    $('#plist').height($(window).height() - 180);
    $('#item_list').height($(window).height() - 100);
}

$(window).resize(do_resize);

$(document).ready(function() {
    initManifestsTable();
    hash = window.location.hash;
    if (hash.length > 1) {
        getManifestItem(hash.slice(1));
    }
    getCatalogNames();
    getCatalogData();
    $('#listSearchField').focus();
    do_resize();

    // Submit the new manifest form when the user clicks the Create button...
    $('[data-new="manifest"]').click( function(){
      newManifestItem();
    });
    //...or when they press the return key in the form field.
    $('#new-manifest-name').keydown( function(event){
      if(event.keyCode == 13) {
        // Prevent the browser from attempting to submit the form
        event.preventDefault();
        event.stopPropagation();
        newManifestItem();
      }
    });

    // Note the use of $(document).on() below: This is to address the fact
    // that the DOM elements we want to listen to might not yet exist.

    // Submit the duplicate manifest form when the user clicks the Duplicate
    // button...
    $(document).on('click', '[data-copy="manifest"]', function(){
      duplicateManifestItem();
    });

    //...or when they press the return key in the form field.
    $(document).on('keydown', '#manifest-copy-name', function(event) {
      if (event.keyCode == 13) {
        // Prevent the browser from attempting to submit the form
        event.preventDefault();
        event.stopPropagation();
        duplicateManifestItem();
      }
    });

    // When a modal is shown, and it contains an <input>, make sure it's
    // selected when the modal is shown.
    $(document).on('shown.bs.modal', '.modal', function(event){
      $(event.currentTarget).find('input').select();
    })

} );

function getCatalogNames() {
    var catalogListURL = '/catalogs/';
    $.ajax({
      method: 'GET',
      url: catalogListURL,
      timeout: 5000,
      global: false,
      cache: false,
      success: function(data) {
          $('#data_storage').data('catalog_names', data);
          // jQuery doesn't actually update the DOM; in order that we
          // can see what's going on, we'll also update the DOM item
          $('#data_storage').attr('data-catalog_names', data);
      },
    });
}


var render_name = function(data, type, full, meta) {
    return '<a href="#' + data + '" onClick="getManifestItem(\'' + data + '\')">' + data + '</a>';
}


function initManifestsTable() {
    $('#list_items').dataTable({
        ajax: {
            url: "/manifests/",
            cache: false,
            dataSrc: function ( json ) {
                // store these names for later auto-complete and validation use
                $('#data_storage').data('manifest_names', json);
                // jQuery doesn't actually update the DOM; in order that we
                // can see what's going on, we'll also update the DOM item
                $('#data_storage').attr('data-manifest_names', json);
                var rows = [];
                for ( var i=0 ; i < json.length ; i++ ) {
                    rows.push([json[i]]);
                }
                return rows;
            },
            complete: function(jqXHR, textStatus){
                  window.clearInterval(poll_loop);
                  $('#process_progress').modal('hide');
                },
            global: false,
        },
         "columnDefs": [
          { "targets": 0,
            "render": render_name,
          }],
         "sDom": "<t>",
         "bPaginate": false,
         "scrollY": "1280px",
         //"bScrollCollapse": true,
         "bInfo": false,
         "bFilter": true,
         "bStateSave": false,
         "aaSorting": [[0,'asc']]
     });
     // start our monitoring timer loop
     monitor_manifest_list();
     // tie our search field to the table
     var thisTable = $('#list_items').DataTable();
     $('#listSearchField').keyup(function(){
          thisTable.search($(this).val()).draw();
     });
}


function monitor_manifest_list() {
    $('#process_progress_title_text').text('Getting manifest data...')
    $('#process_progress_status_text').text('Processing...')
    poll_loop = setInterval(function() {
            update_status('/manifests/__get_manifest_list_status');
        }, 1000);
}


function cancelEdit() {
    //$('#cancelEditConfirmationModal').modal('hide');
    $('.modal-backdrop').remove();
    hideSaveOrCancelBtns();
    getManifestItem(current_pathname);
}


function discardChangesAndLoadNext() {
    //$('#saveOrCancelConfirmationModal').modal('hide');
    $('.modal-backdrop').remove();
    hideSaveOrCancelBtns();
    getManifestItem(requested_pathname);
}


function saveChangesAndLoadNext() {
    saveManifestItem();
    //$('#saveOrCancelConfirmationModal').modal('hide');
    $('.modal-backdrop').remove();
}


var js_obj = {};

var key_list = {'catalogs': 'Catalogs',
                'included_manifests': 'Included Manifests',
                'managed_installs': 'Managed Installs',
                'managed_uninstalls': 'Managed Uninstalls',
                'managed_updates': 'Managed Updates',
                'optional_installs': 'Optional Installs',
                };

var keys_and_types = {'catalogs': ['catalogname'],
                      'conditional_items': [{'condition': 'os_vers_minor > 9',
                                             'managed_installs': ['itemname']}],
                      'included_manifests': ['manifestname'],
                      'managed_installs': ['itemname'],
                      'managed_uninstalls': ['itemname'],
                      'managed_updates': ['itemname'],
                      'optional_installs': ['itemname'],
                     };


function getCurrentCatalogList() {
    if ( js_obj.hasOwnProperty('catalogs') ) {
        return js_obj['catalogs'];
    } else {
        return [];
    }
}


function getSuggestedItems() {
    // return a list of item names based on current manifest catalog list
    var data = $('#data_storage').data('catalog_data');
    if (data) {
        var catalog_list = getCurrentCatalogList();
        if (catalog_list.length == 0) {
            // search all available catalogs
            catalog_list = Object.keys(data);
        }
        var suggested = [];
        for (var i=0, l=catalog_list.length; i<l; i++) {
            var catalog_name = catalog_list[i];
            if ( data.hasOwnProperty(catalog_name) ) {
                if ( data[catalog_name].hasOwnProperty('suggested') ) {
                    Array.prototype.push.apply(suggested, data[catalog_name]['suggested']);
                }
            }
        }
        return uniques(suggested);
    } else {
        return [];
    }
}


function getValidInstallItems() {
    // return a list of item names based on current manifest catalog list
    var data = $('#data_storage').data('catalog_data');
    if (data) {
        var catalog_list = getCurrentCatalogList();
        if (catalog_list.length == 0) {
            // search all available catalogs
            catalog_list = Object.keys(data);
        }
        var valid = [];
        for (var i=0, l=catalog_list.length; i<l; i++) {
            var catalog_name = catalog_list[i];
            if ( data.hasOwnProperty(catalog_name) ) {
                Array.prototype.push.apply(valid, data[catalog_name]['suggested']);
                Array.prototype.push.apply(valid, data[catalog_name]['updates']);
                Array.prototype.push.apply(valid, data[catalog_name]['with_version']);
            }
        }
        return uniques(valid);
    } else {
        return [];
    }
}


var validator = function(path, val) {
    // returns a bootstrap class name to highlight items that aren't 'valid'
    var path_items = path.split('.');
    if (path_items.indexOf('catalogs') != -1) {
        //check val against valid catalog names
        var catalog_names = $('#data_storage').data('catalog_names');
        if (catalog_names && catalog_names.indexOf(val) == -1) return 'danger';
    }
    if (path_items.indexOf('included_manifests') != -1) {
        //check val against valid manifest names
        var manifest_names = $('#data_storage').data('manifest_names');
        if (manifest_names && manifest_names.indexOf(val) == -1) return 'danger';
    }
    if (path_items.indexOf('managed_installs') != -1 ||
        path_items.indexOf('managed_uninstalls') != -1 ||
        path_items.indexOf('managed_updates') != -1 ||
        path_items.indexOf('optional_installs') != -1) {
            //check val against valid install items
            var valid_names = getValidInstallItems();
            if (valid_names.length && valid_names.indexOf(val) == -1) {
                return 'danger';
            }
    }
    return null;
};


function setupTypeaheadForPropertyNames() {
    // typeahead/autocomplete for manifest keys
    // suggest keys that are not already in use
    if (js_obj == null) return;
    var keys_in_use = Object.keys(js_obj),
        suggested_keys = Object.keys(keys_and_types),
        keys_to_suggest = suggested_keys.filter(function(value, index, arr){
            return (keys_in_use.indexOf(value) == -1)
        });
    $('input.property').typeahead({source: keys_to_suggest});
}


function setupTypeahead() {
    // setup typeahead/autocomplete for various fields
    $('tr[data-path="catalogs"] textarea.value').typeahead({source: function(query, process) {
            return process($('#data_storage').data('catalog_names'));
        }
    });
    $('tr[data-path="included_manifests"] textarea.value').typeahead({source: function(query, process) {
            return process($('#data_storage').data('manifest_names'));
        }
    });
    $('tbody.connectable textarea.value').typeahead({source: function(query, process) {
            // should match managed_installs, managed_uninstalls,
            // managed_updates and optional_installs
            return process(getSuggestedItems());
        }
    });
    setupTypeaheadForPropertyNames();
}


function connectSortables() {
    // Connect our sortable lists of installer items so we can drag items
    // between them
    $('tr[data-path="managed_installs"] tbody').addClass('connectable');
    $('tr[data-path="managed_uninstalls"] tbody').addClass('connectable');
    $('tr[data-path="managed_updates"] tbody').addClass('connectable');
    $('tr[data-path="optional_installs"] tbody').addClass('connectable');
    $('tbody.connectable').sortable("option", "connectWith", '.connectable');
}

function setupHelpers() {
    connectSortables();
    setupTypeahead();
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
    setupHelpers();
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
   setupHelpers();
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
    setupHelpers();
}


function updatePlistAndDetail(data) {
    js_obj = data;
    showSaveOrCancelBtns();
    updatePlist();
    setupHelpers();
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
var selected_tab_viewname = "#basicstab";
var editor = null;

function getManifestItem(pathname) {
    if ($('#save_and_cancel').length && !$('#save_and_cancel').hasClass('hidden')) {
        requested_pathname = pathname;
        $("#saveOrCancelConfirmationModal").modal("show");
        event.preventDefault();
        return;
    }
    var manifestItemURL = '/manifests/' + pathname;
    $.ajax({
      method: 'GET',
      url: manifestItemURL,
      timeout: 10000,
      cache: false,
      success: function(data) {
          $('#manifest_detail').html(data);
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
        $('#manifest_detail').html("")
        current_pathname = "";
      },
      dataType: 'html'
    });
}


function duplicateManifestItem() {
    /*if ($('#save_and_cancel').length && !$('#save_and_cancel').hasClass('hidden')) {
        requested_pathname = pathname;
        $("#saveOrCancelConfirmationModal").modal("show");
        event.preventDefault();
        return;
    }*/
    var manifest_names = $('#data_storage').data('manifest_names');
    var pathname = $('#manifest-copy-name').val();
    if (manifest_names.indexOf(pathname) != -1) {
        alert('That manifest name is already in use!');
        $('#manifest-copy-name').select();
        return;
    }
    $('#copyManifestModal').modal('hide');
    $('.modal-backdrop').remove();
    $('#manifest-copy-name').val("");
    var manifestItemURL = '/manifests/' + pathname;
    var plist_data = editor.getValue();
    var postdata = JSON.stringify({'plist_data': plist_data})

    $.ajax({
        method: 'POST',
        url: manifestItemURL,
        data: postdata,
        timeout: 10000,
        cache: false,
        success: function(data) {
            try {
                json_data = $.parseJSON(data);
                // it's JSON, and therefore there was an issue
                if (json_data['result'] == 'failed') {
                    $("#errorModalTitleText").text("Manifest creation error");
                    $("#errorModalDetailText").text(json_data['detail']);
                    $("#errorModal").modal("show");
                    return;
                }
            } catch(err) {
                // not JSON; it's HTML
                $('#list_items').DataTable().ajax.reload();
                getManifestItem(pathname);
                window.location.hash = pathname;
            }
        },
        error: function(jqXHR, textStatus, errorThrown) {
            alert("ERROR: " + textStatus + "\n" + errorThrown);
            $('#manifest_detail').html("")
            current_pathname = "";
            requested_pathname = "";
        },
        dataType: 'html'
    });
}


function saveManifestItem() {
    var plist_data = editor.getValue();
    var postdata = JSON.stringify({'plist_data': plist_data})
    var manifestItemURL = '/manifests/' + current_pathname;
    $.ajax({
      method: 'POST',
      headers: {'X_METHODOVERRIDE': 'PUT'},
      url: manifestItemURL,
      data: postdata,
      timeout: 10000,
      success: function(data) {
        if (data['result'] == 'failed') {
            $("#errorModalTitleText").text("Manifest save error");
            $("#errorModalDetailText").text(data['detail']);
            $("#errorModal").modal("show");
            return;
        }
        hideSaveOrCancelBtns();
        if (requested_pathname.length) {
            getManifestItem(requested_pathname);
        } else {
            //trigger a rebuild/redraw
            //plistChanged();
            //hideSaveOrCancelBtns();
        }
      },
      error: function(jqXHR, textStatus, errorThrown) {
        alert("ERROR: " + textStatus + "\n" + errorThrown);
      },
      dataType: 'json'
    });
}



function newManifestItem() {
    /*if ($('#save_and_cancel').length && !$('#save_and_cancel').hasClass('hidden')) {
        requested_pathname = pathname;
        $("#saveOrCancelConfirmationModal").modal("show");
        event.preventDefault();
        return;
    }*/
    var manifest_names = $('#data_storage').data('manifest_names');
    var pathname = $('#new-manifest-name').val();
    if (manifest_names.indexOf(pathname) != -1) {
        alert('That manifest name is already in use!');
        $('#new-manifest-name').select();
        return;
    }
    $('#newManifestModal').modal('hide');
    $('.modal-backdrop').remove();
    $('#new-manifest-name').val("");
    var manifestItemURL = '/manifests/' + pathname;

    $.ajax({
      method: 'POST',
      url: manifestItemURL,
      timeout: 10000,
      cache: false,
      success: function(data) {
          try {
              json_data = $.parseJSON(data);
              // it's JSON, and therefore there was an issue
              if (json_data['result'] == 'failed') {
                    $("#errorModalTitleText").text("Manifest creation error");
                    $("#errorModalDetailText").text(json_data['detail']);
                    $("#errorModal").modal("show");
                    return;
              }
          } catch(err) {
              // not JSON; it's HTML
              $('#manifest_detail').html(data);
              val = $('#plist').text();
              try { js_obj = PlistParser.parse(val); }
              catch (err) {
                  //alert('Error in parsing plist. ' + err);
                  js_obj = null;
              }
          }
          editor = initializeAceEditor('plist', plistChanged);
          $('#editortabs a[href="' + selected_tab_viewname + '"]').tab('show');
          setupView(selected_tab_viewname);
          current_pathname = pathname;
          requested_pathname = "";
          $('#list_items').DataTable().ajax.reload();
      },
      error: function(jqXHR, textStatus, errorThrown) {
        alert("ERROR: " + textStatus + "\n" + errorThrown);
        $('#manifest_detail').html("")
        current_pathname = "";
        requested_pathname = "";
      },
      dataType: 'html'
    });
}


function deleteManifestItem() {
    $('.modal-backdrop').remove();
    var manifestItemURL = '/manifests/' + current_pathname;
    $.ajax({
      method: 'POST',
      url: manifestItemURL,
      data: '',
      headers: {'X_METHODOVERRIDE': 'DELETE'},
      success: function(data) {
          if (data['result'] == 'failed') {
              $("#errorModalTitleText").text("Manifest delete error");
              $("#errorModalDetailText").text(data['detail']);
              $("#errorModal").modal("show");
              return;
          }
          window.location.hash = '';
          $('#manifest_detail').html('');
          $('#list_items').DataTable().ajax.reload();
      },
      error: function(jqXHR, textStatus, errorThrown) {
        alert("ERROR: " + textStatus + "\n" + errorThrown);
      },
      dataType: 'json'
    });
}
