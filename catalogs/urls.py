from __future__ import absolute_import
from django.conf.urls import url
import catalogs.views

urlpatterns = [
    url(r'^$', catalogs.views.catalog_view),
    url(r'^_json_catalog_data_$', catalogs.views.json_catalog_data),
    url(r'^get_pkg_ref_count/(?P<pkg_path>.*$)', catalogs.views.get_pkg_ref_count)
]