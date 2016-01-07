from django.http import HttpResponse, HttpRequest, HttpResponseRedirect
#from django.template import RequestContext
from django.shortcuts import render
from django.template.context_processors import csrf
from django.core.urlresolvers import reverse
#from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import Permission
from django.contrib.auth.models import User
from django.conf import settings
from django import forms

from models import Manifest, MANIFEST_LIST_STATUS_TAG
from catalogs.models import Catalog
from process.models import Process

import fnmatch
import json
import os


def status(request):
    print 'got status request for manifests_list_process'
    status_response = {}
    processes = Process.objects.filter(name=MANIFEST_LIST_STATUS_TAG)
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
def index(request):
    if request.is_ajax():
        print "Got json request for manifests"
        manifest_list = Manifest.list()
        # send it back in JSON format
        return HttpResponse(json.dumps(manifest_list),
                            content_type='application/json')
    else:
        print "Got index request for manifests"
        c = {'page': 'manifests'}
        return render(request, 'manifests/manifests.html', context=c)


@login_required
def detail(request, manifest_path):
    if request.method == 'GET':
        print "Got read request for %s" % manifest_path
        manifest = Manifest.read(manifest_path)
        #autocomplete_data = Manifest.getAutoCompleteData(manifest_path)
        if manifest is None:
            raise Http404("%s does not exist" % manifest_path)
        c = {'plist_text': manifest,
             'pathname': manifest_path}
        return render(request, 'manifests/detail.html', context=c)
    if request.method == 'POST':
        # could be PUT, POST, or DELETE
        if request.META.has_key('HTTP_X_METHODOVERRIDE'):
            http_method = request.META['HTTP_X_METHODOVERRIDE']
            if http_method.lower() == 'delete':
                print "Got delete request for %s" % manifest_path
                if not request.user.has_perm('manifest.delete_manifestfile'):
                    raise PermissionDenied
                Manifest.delete(manifest_path, request.user)
                return HttpResponse(
                    json.dumps('success'), content_type='application/json')
            elif http_method.lower() == 'put':
                # regular POST (update/change)
                print "Got write request for %s" % manifest_path
                if not request.user.has_perm('manifest.change_manifestfile'):
                    raise PermissionDenied
                if request.is_ajax():
                    json_data = json.loads(request.body)
                    if json_data and 'plist_data' in json_data:
                        plist_data = json_data['plist_data'].encode('utf-8')
                        Manifest.write(
                            json_data['plist_data'], manifest_path,
                            request.user)
                        return HttpResponse(
                            json.dumps('success'),
                            content_type='application/json')
            else:
                print "Got unknown HTTP_X_METHODOVERRIDE for %s: %s" % (
                    manifest_path, http_method)
        else:
            # true POST request; create new resource
            print "Got create request for %s" % manifest_path
            try:
                json_data = json.loads(request.body)
            except ValueError:
                json_data = None
            if json_data and 'plist_data' in json_data:
                plist_data = json_data['plist_data'].encode('utf-8')
                Manifest.write(
                    json_data['plist_data'], manifest_path,
                    request.user)
            else:
                plist_data = Manifest.new(manifest_path, request.user)
            c = {'plist_text': plist_data,
                 'pathname': manifest_path,}
            return render(request, 'manifests/detail.html', context=c)
