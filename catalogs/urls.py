from django.conf.urls import url
import catalogs.views

urlpatterns = [
    url(r'^$', catalogs.views.catalog_view),
    url(r'^_json_catalog_data_$', catalogs.views.json_catalog_data),
]