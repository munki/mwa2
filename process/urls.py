from django.conf.urls import url
import process.views

urlpatterns = [
    url(r'^$', process.views.index),
    url(r'^run$', process.views.run),
    url(r'^status$', process.views.status),
    url(r'^delete$', process.views.delete)
]