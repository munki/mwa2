from django.http import HttpResponse
from models import Catalog
import json


def catalog_view(request):
    catalog_list = Catalog.list()
    print "Got request for catalog names"
    return HttpResponse(json.dumps(catalog_list),
                        content_type='application/json')

def json_catalog_data(request):
    print "Got request for catalog data"
    return HttpResponse(json.dumps(Catalog.catalog_info()),
                        content_type='application/json')

def get_pkg_ref_count(request, pkg_path):
    print "Got request for pkg ref count for %s" % pkg_path
    return HttpResponse(json.dumps(Catalog.get_pkg_ref_count(pkg_path)),
                        content_type='application/json')
                              