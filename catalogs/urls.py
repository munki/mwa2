from __future__ import absolute_import
from django.urls import re_path
import catalogs.views

urlpatterns = [
    re_path(r'^$', catalogs.views.catalog_view),
    re_path(r'^_json_catalog_data_$', catalogs.views.json_catalog_data),
    re_path(r'^get_pkg_ref_count/(?P<pkg_path>.*$)', catalogs.views.get_pkg_ref_count)
]