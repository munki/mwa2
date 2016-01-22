from django.http import HttpResponse, HttpRequest, HttpResponseRedirect
#from django.template import RequestContext
from django.shortcuts import render
from django.template.context_processors import csrf
from django.views.decorators.csrf import csrf_exempt
from django.core.urlresolvers import reverse
from django.http import Http404
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied

from models import Pkginfo, PkginfoError, PKGSINFO_STATUS_TAG
from catalogs.models import Catalog
from process.models import Process

import json
import plistlib
import sys


def status(request):
    print 'got status request for pkgsinfo_list_process'
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
    print "Got json request for pkgsinfo"
    pkginfo_list = Pkginfo.list()
    # send it back in JSON format
    return HttpResponse(json.dumps(pkginfo_list),
                        content_type='application/json')


@login_required
def index(request):
    print "Got index request for pkgsinfo"
    c = {'page': 'pkgsinfo',
         'search': request.GET.get('search', ''),
         'catalog': request.GET.get('catalog', 'all')}
    return render(request, 'pkgsinfo/pkgsinfo.html', context=c)


@login_required
def list(request):
    print "Got list request for pkgsinfo"
    pkgsinfo = Pkginfo.list()
    c = {'pkgsinfo': pkgsinfo,} 
    return render(request, 'pkgsinfo/list.html', context=c)


@login_required
def detail(request, pkginfo_path):
    if request.method == 'GET':
        print "Got read request for %s" % pkginfo_path
        pkginfo = Pkginfo.read(pkginfo_path)
        if pkginfo is None:
            raise Http404("%s does not exist" % pkginfo_path)
        try:
            pkginfo_plist = plistlib.readPlistFromString(pkginfo)
            installer_item_path = pkginfo_plist.get('installer_item_location', '')
        except Exception:
            installer_item_path = ''
        c = {'plist_text': pkginfo,
             'pathname': pkginfo_path,
             'installer_item_path': installer_item_path}
        return render(request, 'pkgsinfo/detail.html', context=c)
    if request.method == 'POST':
        # DELETE
        if request.META.has_key('HTTP_X_METHODOVERRIDE'):
            http_method = request.META['HTTP_X_METHODOVERRIDE']
            if http_method.lower() == 'delete':
                print "Got delete request for %s" % pkginfo_path
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
        print "Got write request for %s" % pkginfo_path
        if not request.user.has_perm('pkgsinfo.change_pkginfofile'):
            raise PermissionDenied
        if request.is_ajax():
            json_data = json.loads(request.body)
            if json_data and 'plist_data' in json_data:
                plist_data = json_data['plist_data'].encode('utf-8')
                try:
                    Pkginfo.write(
                        json_data['plist_data'], pkginfo_path, request.user)
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

