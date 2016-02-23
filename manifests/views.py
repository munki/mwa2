"""
manifests/views.py
"""
from django.http import HttpResponse, Http404
#from django.http import QueryDict
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
#from django.views.decorators.csrf import csrf_exempt
#from django.core.exceptions import PermissionDenied

#from manifests.models import Manifest, MANIFEST_LIST_STATUS_TAG
from api.models import Plist, FileDoesNotExistError, FileReadError
from process.models import Process

import json
import logging
import plistlib

LOGGER = logging.getLogger('munkiwebadmin')


def status(request):
    '''Returns status of long-running process'''
    LOGGER.debug('got status request for manifests_list_process')
    status_response = {}
    processes = Process.objects.filter(name='manifests_list_process')
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
    '''Returns list of available manifests'''
    LOGGER.debug("Got index request for manifests")
    context = {'page': 'manifests'}
    return render(request, 'manifests/manifests.html', context=context)


@login_required
def detail(request, manifest_path):
    '''Returns data on a given manifest'''
    if request.method == 'GET':
        LOGGER.debug("Got read request for %s", manifest_path)
        try:
            plist = Plist.read('manifests', manifest_path)
        except FileDoesNotExistError:
            raise Http404("%s does not exist" % manifest_path)
        manifest_text = plistlib.writePlistToString(plist)
        context = {'plist_text': manifest_text,
                   'pathname': manifest_path}
        return render(request, 'manifests/detail.html', context=context)
    if request.method == 'POST':
        return HttpResponse(
            json.dumps({'result': 'failed',
                        'exception_type': 'MethodNotSupported',
                        'detail': 'POST/PUT/DELETE should use the API'}),
            content_type='application/json', status=404)