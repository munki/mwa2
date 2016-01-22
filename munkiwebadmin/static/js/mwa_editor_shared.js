function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                var cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

$.ajaxSetup({
    cache: false,
    beforeSend: function(xhr, settings) {
        if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
        }
    }
});

var loadingTimeout;
$(document).ajaxStart(function() {
    loadingTimeout = setTimeout(function() {
        $('#process_progress_title_text').text('Processing...')
        $('#process_progress_status_text').text('')
        $('#process_progress').modal('show')
    }, 2000);
})

$(document).ajaxStop(function() {
    clearTimeout(loadingTimeout);
    $('#process_progress').modal('hide')
})

function uniques(arr) {
    var a = [];
    for (var i=0, l=arr.length; i<l; i++)
        if (a.indexOf(arr[i]) === -1 && arr[i] !== '')
            a.push(arr[i]);
    return a;
}


function getCatalogData() {
    var catalogDataURL = '/catalogs/_json_catalog_data_';
    $.ajax({
      method: 'GET',
      url: catalogDataURL,
      timeout: 10000,
      global: false,
      cache: false,
      success: function(data) {
          $('#data_storage').data('catalog_data', data);
          // jQuery doesn't actually update the DOM; in order that we
          // can see what's going on, we'll also update the DOM item
          $('#data_storage').attr('data-catalog_data', data);
          // update the catalog dropdown list (if it exists)
          $('#catalog_dropdown_list').triggerHandler('custom.update');
      },
    });
}


function initializeAceEditor(element_id, change_fn) {
    editor = ace.edit(element_id);
    editor.setTheme("ace/theme/sqlserver");
    editor.getSession().setMode("ace/mode/xml");
    editor.setShowPrintMargin(false);
    editor.getSession().setUseWrapMode(true);
    editor.resize(true);
    editor.getSession().on('change', change_fn);
    return editor
}


function detectUnsavedChanges() {
    /*$('#item_editor').on('keyup keydown', 'input, textarea', function (e) {
        if (e.keyCode < 37 || e.keyCode > 40) {
            showSaveOrCancelBtns()
        }
    });*/
    $(window).on('beforeunload', function () {
        if ($('#save_and_cancel') && !$('#save_and_cancel').hasClass('hidden')) {
            return 'You haven\'t saved your changes.';
        }
    });
}


var poll_loop;
function update_status(from_url) {
    $('#process_progress').modal('show');
    $.ajax({
        type: 'GET',
        url: from_url,
        dataType: 'json',
        global: false,
        success: function(data) {
            if (!data.exited ) {
                var statustext = data.statustext;
                if (statustext) {
                    $('#process_progress_status_text').text(statustext);
                }
            } else {
                $('#process_progress_status_text').text('');
            }
        }
    });
}


function showSaveOrCancelBtns() {
    $('#delete_btn').addClass('hidden');
    $('#save_and_cancel').removeClass('hidden');
}


function hideSaveOrCancelBtns() {
    $('#save_and_cancel').addClass('hidden');
    $('#delete_btn').removeClass('hidden');
}