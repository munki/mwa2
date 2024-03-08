from __future__ import absolute_import
from django.urls import re_path
import api.views

urlpatterns = [
    re_path(r'^(?P<kind>catalogs$)', api.views.plist_api),
    re_path(r'^(?P<kind>catalogs)/(?P<filepath>.*$)', api.views.plist_api),
    re_path(r'^(?P<kind>manifests$)', api.views.plist_api),
    re_path(r'^(?P<kind>manifests)/(?P<filepath>.*$)', api.views.plist_api),
    re_path(r'^(?P<kind>pkgsinfo$)', api.views.plist_api),
    re_path(r'^(?P<kind>pkgsinfo)/(?P<filepath>.*$)', api.views.plist_api),
    re_path(r'^(?P<kind>icons$)', api.views.file_api),
    re_path(r'^(?P<kind>icons)/(?P<filepath>.*$)', api.views.file_api),
    re_path(r'^(?P<kind>pkgs$)', api.views.file_api),
    re_path(r'^(?P<kind>pkgs)/(?P<filepath>.*$)', api.views.file_api),
]
