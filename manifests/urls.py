from __future__ import absolute_import
from django.urls import re_path
import manifests.views

urlpatterns = [
    re_path(r'^$', manifests.views.index, name='manifests'),
    re_path(r'^__get_manifest_list_status$', manifests.views.status),
    re_path(r'^(?P<manifest_path>.*$)', manifests.views.index)
]