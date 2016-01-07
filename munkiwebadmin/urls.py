from django.conf.urls import include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
import django.contrib.auth.views

from django.contrib import admin
admin.autodiscover()

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    
    url(r'^login/$', django.contrib.auth.views.login, name='login'),
    url(r'^logout/$', django.contrib.auth.views.logout_then_login, name='logout'),
    url(r'^manifests/', include('manifests.urls')),
    url(r'^catalogs/', include('catalogs.urls')),
    url(r'^pkgsinfo/', include('pkgsinfo.urls')),
    url(r'^makecatalogs/', include('process.urls')),
    url(r'^$', django.contrib.auth.views.login, name='login'),
]
# comment out the following if you are serving
# static files a different way
urlpatterns += staticfiles_urlpatterns()
