from __future__ import absolute_import
from django.urls import re_path
import pkgsinfo.views

urlpatterns = [
    re_path(r'^$', pkgsinfo.views.index),
    re_path(r'^__get_process_status$', pkgsinfo.views.status),
    re_path(r'^_json$', pkgsinfo.views.getjson),
    re_path(r'^(?P<pkginfo_path>^.*$)', pkgsinfo.views.detail)
]