"""
manifests/views.py
"""
from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

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
def index(request, manifest_path=None):
    '''Returns manifest list or detail'''
    if manifest_path and request.is_ajax():
        # return manifest detail
        if request.method == 'GET':
            LOGGER.debug("Got read request for %s", manifest_path)
            try:
                plist = Plist.read('manifests', manifest_path)
            except (FileDoesNotExistError, FileReadError), err:
                return HttpResponse(
                    json.dumps({'result': 'failed',
                                'exception_type': str(type(err)),
                                'detail': str(err)}),
                    content_type='application/json', status=404)
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
    # return list of available manifests
    LOGGER.debug("Got index request for manifests")
    context = {'page': 'manifests',
               'manifest_name': manifest_path}
    return render(request, 'manifests/manifests.html', context=context)
