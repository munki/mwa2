from django.conf.urls import url
import api.views

urlpatterns = [
    url(r'^(?P<kind>manifests)/(?P<filepath>.*$)', api.views.api),
    url(r'^(?P<kind>pkgsinfo)/(?P<filepath>.*$)', api.views.api)
]
