// Javascript for catalogs views

$(document).ready(function() {
   $('#catalog_items').dataTable({
        "sDom": "<'row'<'col-xs-4'l><'col-xs-4'f>r>t<'row'<'col-xs-4'i><'col-xs-4'p>>",
        "bPaginate": false,
        "sScrollY": "480px",
        //"bScrollCollapse": true,
        "bInfo": false,
        "bFilter": true,
        "bStateSave": true,
        "aaSorting": [[0,'asc']]
    });
} );

function getCatalogItem(catalog_name, catalog_index, item_name, item_version)     {
    var catalogItemURL = '/catalogs/' + catalog_name + '/' + catalog_index + '/';
    $.get(catalogItemURL, function(data) {
        $('#catalog_item_detail').html(data);
    });
    $('.catalog_item[name="' + item_name + '"]').addClass('selected');
    $('.catalog_item[name!="' + item_name + '"]').removeClass('selected');
}
