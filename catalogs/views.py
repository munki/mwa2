"""
catalogs//views.py
"""

from django.http import HttpResponse
from catalogs.models import Catalog
import json
import logging

LOGGER = logging.getLogger('munkiwebadmin')

def catalog_view(request):
    '''Returns list of catalog names in JSON format'''
    catalog_list = Catalog.list()
    LOGGER.debug("Got request for catalog names")
    return HttpResponse(json.dumps(catalog_list),
                        content_type='application/json')

def json_catalog_data(request):
    '''Returns complied and sorted catalog data in JSON format'''
    LOGGER.debug("Got request for catalog data")
    return HttpResponse(json.dumps(Catalog.catalog_info()),
                        content_type='application/json')

def get_pkg_ref_count(request, pkg_path):
    '''Returns the number of pkginfo files referencing a given pkg_path'''
    LOGGER.debug("Got request for pkg ref count for %s", pkg_path)
    return HttpResponse(json.dumps(Catalog.get_pkg_ref_count(pkg_path)),
                        content_type='application/json')
                              