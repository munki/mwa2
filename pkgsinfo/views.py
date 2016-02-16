"""
pkgsinfo/views.py
"""

from django.http import HttpResponse, QueryDict, Http404
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from pkgsinfo.models import Pkginfo, PkginfoError, PkginfoAlreadyExistsError,\
                            PkginfoDoesNotExistError, PkginfoWriteError, \
                            PkginfoDeleteError, PKGSINFO_STATUS_TAG
from process.models import Process

from xml.parsers.expat import ExpatError

import json
import logging
import os
import plistlib
import urllib2
import datetime

REPO_DIR = settings.MUNKI_REPO_DIR
ICONS_DIR = os.path.join(REPO_DIR, 'icons')
STATIC_URL = settings.STATIC_URL
try:
    ICONS_URL = settings.ICONS_URL
except AttributeError:
    ICONS_URL = None

LOGGER = logging.getLogger('munkiwebadmin')


def convert_dates_to_strings(plist):
    '''Converts all date objects in a plist to strings. Enables encoding into
    JSON'''
    if isinstance(plist, dict):
        for key, value in plist.items():
            if isinstance(value, datetime.datetime):
                plist[key] = value.isoformat()
            if isinstance(value, dict):
                plist[key] = convert_dates_to_strings(value)
            if isinstance(value, list):
                plist[key] = convert_dates_to_strings(value)
        return plist
    if isinstance(plist, list):
        for value in plist:
            if isinstance(value, datetime.datetime):
                value = value.isoformat()
            if isinstance(value, dict):
                value = convert_dates_to_strings(value)
            if isinstance(value, list):
                value = convert_dates_to_strings(value)
        return plist


def get_icon_url(pkginfo_plist):
    '''Attempt to build an icon url for the pkginfo'''
    if ICONS_URL:
        icon_known_exts = ['.bmp', '.gif', '.icns', '.jpg', '.jpeg', '.png',
                           '.psd', '.tga', '.tif', '.tiff', '.yuv']
        icon_name = pkginfo_plist.get('icon_name') or pkginfo_plist['name']
        if not os.path.splitext(icon_name)[1] in icon_known_exts:
            icon_name += '.png'
        icon_path = os.path.join(ICONS_DIR, icon_name)
        if os.path.isfile(icon_path):
            return ICONS_URL + urllib2.quote(icon_name.encode('UTF-8'))
    return STATIC_URL + 'img/GenericPkg.png'


def status(request):
    '''Get and return a status message for the process generating
    the pkgsinfo list'''
    LOGGER.debug('got status request for pkgsinfo_list_process')
    status_response = {}
    processes = Process.objects.filter(name=PKGSINFO_STATUS_TAG)
    if processes:
        # display status from one of the active processes
        # (hopefully there is only one!)
        process = processes[0]
        status_response['statustext'] = process.statustext
    else:
        status_response['statustext'] = 'Processing'
    return HttpResponse(json.dumps(status_response),
                        content_type='application/json')


@login_required
def getjson(request):
    '''Return pkgsinfo as json data -- used by the DataTable that
    displays the list of pkginfo items. Perhaps could be moved into the
    index methods'''
    LOGGER.debug("Got json request for pkgsinfo")
    pkginfo_list = Pkginfo.list()
    # send it back in JSON format
    return HttpResponse(json.dumps(pkginfo_list),
                        content_type='application/json')


@login_required
def index(request):
    '''Index methods: GET and POST'''
    if request.method == "GET":
        LOGGER.debug("Got index request for pkgsinfo")
        context = {'page': 'pkgsinfo',
                   'search': request.GET.get('search', ''),
                   'catalog': request.GET.get('catalog', 'all')}
        return render(request, 'pkgsinfo/pkgsinfo.html', context=context)
    if request.method == 'POST':
        # DELETE
        if request.META.has_key('HTTP_X_METHODOVERRIDE'):
            http_method = request.META['HTTP_X_METHODOVERRIDE']
            if http_method.lower() == 'delete':
                LOGGER.info("Got mass delete request for pkginfos")
                if not request.user.has_perm('pkgsinfo.delete_pkginfofile'):
                    raise PermissionDenied
                json_data = json.loads(request.body)
                pkginfo_list = json_data.get('pkginfo_list', [])
                try:
                    Pkginfo.mass_delete(
                        pkginfo_list, request.user,
                        delete_pkg=json_data.get('deletePkg', False)
                    )
                except PkginfoError, err:
                    return HttpResponse(
                        json.dumps({'result': 'failed',
                                    'exception_type': str(type(err)),
                                    'detail': str(err)}),
                        content_type='application/json')
                else:
                    return HttpResponse(
                        json.dumps({'result': 'success'}),
                        content_type='application/json')
        # regular POST (update/change)
        LOGGER.info("Got mass update request for pkginfos")
        if not request.user.has_perm('pkgsinfo.change_pkginfofile'):
            raise PermissionDenied
        json_data = json.loads(request.body)
        pkginfo_list = json_data.get('pkginfo_list', [])
        catalogs_to_add = json_data.get('catalogs_to_add', [])
        LOGGER.debug('Adding catalogs: %s', catalogs_to_add)
        catalogs_to_delete = json_data.get('catalogs_to_delete', [])
        LOGGER.debug('Removing catalogs: %s', catalogs_to_delete)
        try:
            Pkginfo.mass_edit_catalogs(
                pkginfo_list, catalogs_to_add, catalogs_to_delete,
                request.user)
        except PkginfoError, err:
            return HttpResponse(
                json.dumps({'result': 'failed',
                            'exception_type': str(type(err)),
                            'detail': str(err)}),
                content_type='application/json')
        else:
            return HttpResponse(
                json.dumps({'result': 'success'}),
                content_type='application/json')


@login_required
def detail(request, pkginfo_path):
    '''Return detail for a specific pkginfo'''
    if request.method == 'GET':
        LOGGER.debug("Got read request for %s", pkginfo_path)
        pkginfo = Pkginfo.read(pkginfo_path)
        if pkginfo is None:
            raise Http404("%s does not exist" % pkginfo_path)
        try:
            pkginfo_plist = plistlib.readPlistFromString(pkginfo)
            installer_item_path = pkginfo_plist.get(
                'installer_item_location', '')
            icon_url = get_icon_url(pkginfo_plist)
        except (ExpatError, IOError):
            installer_item_path = ''
            icon_url = STATIC_URL + 'img/GenericPkg.png'
        context = {'plist_text': pkginfo,
                   'pathname': pkginfo_path,
                   'installer_item_path': installer_item_path,
                   'icon_url': icon_url}
        return render(request, 'pkgsinfo/detail.html', context=context)
    if request.method == 'POST':
        # DELETE
        if request.META.has_key('HTTP_X_METHODOVERRIDE'):
            http_method = request.META['HTTP_X_METHODOVERRIDE']
            if http_method.lower() == 'delete':
                LOGGER.info("Got delete request for %s", pkginfo_path)
                if not request.user.has_perm('pkgsinfo.delete_pkginfofile'):
                    raise PermissionDenied
                json_data = json.loads(request.body)
                try:
                    Pkginfo.delete(
                        pkginfo_path, request.user,
                        delete_pkg=json_data.get('deletePkg', False)
                    )
                except PkginfoError, err:
                    return HttpResponse(
                        json.dumps({'result': 'failed',
                                    'exception_type': str(type(err)),
                                    'detail': str(err)}),
                        content_type='application/json')
                else:
                    return HttpResponse(
                        json.dumps({'result': 'success'}),
                        content_type='application/json')

        # regular POST (update/change)
        LOGGER.info("Got write request for %s", pkginfo_path)
        if not request.user.has_perm('pkgsinfo.change_pkginfofile'):
            raise PermissionDenied
        if request.is_ajax():
            json_data = json.loads(request.body)
            if json_data and 'plist_data' in json_data:
                plist_data = json_data['plist_data'].encode('utf-8')
                try:
                    Pkginfo.write(
                        plist_data, pkginfo_path, request.user)
                except PkginfoError, err:
                    return HttpResponse(
                        json.dumps({'result': 'failed',
                                    'exception_type': str(type(err)),
                                    'detail': str(err)}),
                        content_type='application/json')
                else:
                    return HttpResponse(
                        json.dumps({'result': 'success'}),
                        content_type='application/json')

