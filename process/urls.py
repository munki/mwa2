from __future__ import absolute_import
from django.urls import re_path
import process.views

urlpatterns = [
    re_path(r'^$', process.views.index),
    re_path(r'^run$', process.views.run),
    re_path(r'^status$', process.views.status),
    re_path(r'^delete$', process.views.delete)
]