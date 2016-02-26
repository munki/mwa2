"""
pkgsinfo/views.py
"""

from django.http import HttpResponse, Http404
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.conf import settings

from pkgsinfo.models import Pkginfo, PKGSINFO_STATUS_TAG
from process.models import Process
from api.models import Plist, \
                       FileError, FileDoesNotExistError

import json
import logging
import os
import plistlib
import urllib2

REPO_DIR = settings.MUNKI_REPO_DIR
ICONS_DIR = os.path.join(REPO_DIR, 'icons')
STATIC_URL = settings.STATIC_URL
try:
    ICONS_URL = settings.ICONS_URL
except AttributeError:
    ICONS_URL = None

LOGGER = logging.getLogger('munkiwebadmin')


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
    pkginfo_list = Pkginfo.data()
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
                    return HttpResponse(
                        json.dumps({
                            'result': 'failed',
                            'exception_type': 'PkginfoDeletePermissionDenied',
                            'detail': "Missing needed permissions"}),
                        content_type='application/json', status=403)
                json_data = json.loads(request.body)
                pkginfo_list = json_data.get('pkginfo_list', [])
                try:
                    Pkginfo.mass_delete(
                        pkginfo_list, request.user,
                        delete_pkgs=json_data.get('deletePkg', False)
                    )
                except FileError, err:
                    return HttpResponse(
                        json.dumps({'result': 'failed',
                                    'exception_type': str(type(err)),
                                    'detail': str(err)}),
                        content_type='application/json', status=403)
                else:
                    return HttpResponse(
                        json.dumps({'result': 'success'}),
                        content_type='application/json')
        # regular POST (update/change)
        LOGGER.info("Got mass update request for pkginfos")
        if not request.user.has_perm('pkgsinfo.change_pkginfofile'):
            return HttpResponse(
                json.dumps({
                    'result': 'failed',
                    'exception_type': 'PkginfoEditPermissionDenied',
                    'detail': "Missing needed permissions"}),
                content_type='application/json', status=403)
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
        except FileError, err:
            return HttpResponse(
                json.dumps({'result': 'failed',
                            'exception_type': str(type(err)),
                            'detail': str(err)}),
                content_type='application/json', status=403)
        else:
            return HttpResponse(
                json.dumps({'result': 'success'}),
                content_type='application/json')


@login_required
def detail(request, pkginfo_path):
    '''Return detail for a specific pkginfo'''
    if request.method == 'GET':
        LOGGER.debug("Got read request for %s", pkginfo_path)
        try:
            plist = Plist.read('pkgsinfo', pkginfo_path)
        except FileDoesNotExistError:
            raise Http404("%s does not exist" % pkginfo_path)
        default_items = {
            'display_name': '',
            'description': '',
            'category': '',
            'developer': '',
            'unattended_install': False,
            'unattended_uninstall': False
        }
        for item in default_items:
            if not item in plist:
                plist[item] = default_items[item]
        pkginfo_text = plistlib.writePlistToString(plist)
        installer_item_path = plist.get('installer_item_location', '')
        icon_url = get_icon_url(plist)
        context = {'plist_text': pkginfo_text,
                   'pathname': pkginfo_path,
                   'installer_item_path': installer_item_path,
                   'icon_url': icon_url}
        return render(request, 'pkgsinfo/detail.html', context=context)
    if request.method == 'POST':
        return HttpResponse(
            json.dumps({'result': 'failed',
                        'exception_type': 'MethodNotSupported',
                        'detail': 'POST/PUT/DELETE should use the API'}),
            content_type='application/json', status=404)
