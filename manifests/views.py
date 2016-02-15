"""
manifests/views.py
"""
from django.http import HttpResponse, Http404
from django.http import QueryDict
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import PermissionDenied

from manifests.models import Manifest, ManifestError, ManifestWriteError, \
                             ManifestAlreadyExistsError, \
                             ManifestDoesNotExistError, ManifestDeleteError, \
                             MANIFEST_LIST_STATUS_TAG
from process.models import Process

import json
import logging
import plistlib

LOGGER = logging.getLogger('munkiwebadmin')

def status(request):
    '''Returns status of long-running process'''
    LOGGER.debug('got status request for manifests_list_process')
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


#@login_required
@csrf_exempt
def api(request, manifest_path=None):
    if request.method == 'GET':
        LOGGER.debug("Got API GET request for manifests")
        if manifest_path:
            response = Manifest.readAsPlist(manifest_path)
            response['name'] = manifest_path
        else:
            manifest_list = Manifest.list()
            response = []
            for item_name in manifest_list:
                manifest = Manifest.readAsPlist(item_name)
                manifest['name'] = item_name
                response.append(manifest)
        return HttpResponse(json.dumps(response) + '\n',
                            content_type='application/json')
    if request.META.has_key('HTTP_X_METHODOVERRIDE'):
        # support browsers/libs that don't directly support the other verbs
        http_method = request.META['HTTP_X_METHODOVERRIDE']
        if http_method.lower() == 'put':
            request.method = 'PUT'
            request.META['REQUEST_METHOD'] = 'PUT'
            request.PUT = QueryDict(request.body)
        if http_method.lower() == 'delete':
            request.method = 'DELETE'
            request.META['REQUEST_METHOD'] = 'DELETE'
            request.DELETE = QueryDict(request.body)
        if http_method.lower() == 'patch':
            request.method = 'PATCH'
            request.META['REQUEST_METHOD'] = 'PATCH'
            request.PATCH = QueryDict(request.body)
    if request.method == 'POST':
        LOGGER.debug("Got API POST request for manifests")
        #if not request.user.has_perm('manifest.change_manifestfile'):
        #    raise PermissionDenied
        if manifest_path:
            return HttpResponse(
                json.dumps({'result': 'failed',
                            'exception_type': 'WrongHTTPMethodType',
                            'detail': 'This should be a PUT or PATCH request'}
                          ),
                content_type='application/json', status=400)
        json_data = json.loads(request.body)
        if json_data:
            manifest_path = json_data['name']
            del json_data['name']
            try:
                #Manifest.new(manifest_path, request.user, manifest_data=json_data)
                Manifest.new(manifest_path, None, manifest_data=json_data)
            except ManifestAlreadyExistsError, err:
                return HttpResponse(
                    json.dumps({'result': 'failed',
                                'exception_type': str(type(err)),
                                'detail': str(err)}),
                    content_type='application/json',
                    status=409)
            except ManifestWriteError, err:
                return HttpResponse(
                    json.dumps({'result': 'failed',
                                'exception_type': str(type(err)),
                                'detail': str(err)}),
                    content_type='application/json', status=403)
            except ManifestError, err:
                return HttpResponse(
                    json.dumps({'result': 'failed',
                                'exception_type': str(type(err)),
                                'detail': str(err)}),
                    content_type='application/json', status=403)
            else:
                json_data['name'] = manifest_path
                return HttpResponse(
                    json.dumps(json_data) + '\n',
                    content_type='application/json', status=201)

    elif request.method == 'PUT':
        LOGGER.debug("Got API PUT request for manifests")
        #if not request.user.has_perm('manifest.change_manifestfile'):
        #    raise PermissionDenied
        if not manifest_path:
            return HttpResponse(
                json.dumps({'result': 'failed',
                            'exception_type': 'WrongHTTPMethodType',
                            'detail': 'Perhaps this should be a POST request'}
                          ),
                content_type='application/json', status=400)
        json_data = json.loads(request.body)
        if not json_data:
            # need to deal with this issue
            return HttpResponse(
                json.dumps({'result': 'failed',
                            'exception_type': 'NoRequestBody',
                            'detail': 
                                'Request body was empty or missing valid data'}
                          ),
                content_type='application/json', status=400)
        if 'name' in json_data:
            # perhaps support rename here in the future, but for now,
            # ignore it
            del json_data['name']
        try:
            data = plistlib.writePlistToString(json_data)
            #Manifest.write(data, manifest_path, request.user)
            Manifest.write(data, manifest_path, None)
        except ManifestError, err:
            return HttpResponse(
                json.dumps({'result': 'failed',
                            'exception_type': str(type(err)),
                            'detail': str(err)}),
                content_type='application/json', status=403)
        else:
            json_data['name'] = manifest_path
            return HttpResponse(
                json.dumps(json_data) + '\n',
                content_type='application/json')

    elif request.method == 'PATCH':
        LOGGER.debug("Got API PATCH request for manifests")
        #if not request.user.has_perm('manifest.change_manifestfile'):
        #    raise PermissionDenied
        if not manifest_path:
            return HttpResponse(
                json.dumps({'result': 'failed',
                            'exception_type': 'WrongHTTPMethodType',
                            'detail': 'Perhaps this should be a POST request'}
                          ),
                content_type='application/json', status=400)
        json_data = json.loads(request.body)
        if not json_data:
            # need to deal with this issue
            return HttpResponse(
                json.dumps({'result': 'failed',
                            'exception_type': 'NoRequestBody',
                            'detail': 
                                'Request body was empty or missing valid data'}
                          ),
                content_type='application/json', status=400)
        if 'name' in json_data:
            # perhaps support rename here in the future, but for now,
            # ignore it
            del json_data['name']
        # read existing manifest
        manifest_data = Manifest.readAsPlist(manifest_path)
        manifest_data['name'] = manifest_path
        manifest_data.update(json_data)
        try:
            data = plistlib.writePlistToString(manifest_data)
            #Manifest.write(data, manifest_path, request.user)
            Manifest.write(data, manifest_path, None)
        except ManifestError, err:
            return HttpResponse(
                json.dumps({'result': 'failed',
                            'exception_type': str(type(err)),
                            'detail': str(err)}),
                content_type='application/json', status=403)
        else:
            manifest_data['name'] = manifest_path
            return HttpResponse(
                json.dumps(manifest_data) + '\n',
                content_type='application/json')

    elif request.method == 'DELETE':
        LOGGER.debug("Got API DELETE request for manifests")
        #if not request.user.has_perm('manifest.delete_manifestfile'):
        #    raise PermissionDenied
        if not manifest_path:
            return HttpResponse(
                json.dumps({'result': 'failed',
                            'exception_type': 'MassDeleteNotSupported',
                            'detail': 'Deleting all manifests is not supported'}
                          ),
                content_type='application/json', status=403)
        try:
            #Manifest.delete(manifest_path, request.user)
            Manifest.delete(manifest_path, None)
        except ManifestDoesNotExistError, err:
            return HttpResponse(
                json.dumps({'result': 'failed',
                            'exception_type': str(type(err)),
                            'detail': str(err)}),
                content_type='application/json', status=404)
        except ManifestDeleteError, err:
            return HttpResponse(
                json.dumps({'result': 'failed',
                            'exception_type': str(type(err)),
                            'detail': str(err)}),
                content_type='application/json', status=403)
        except ManifestError, err:
            return HttpResponse(
                json.dumps({'result': 'failed',
                            'exception_type': str(type(err)),
                            'detail': str(err)}),
                content_type='application/json', status=403)
        else:
            # success
            return HttpResponse(status=204)
    

@login_required
def index(request):
    '''Returns list of available manifests'''
    if request.is_ajax():
        LOGGER.debug("Got json request for manifests")
        search_section = request.GET.get('search_section')
        search_text = request.GET.get('search_text')
        manifest_list = Manifest.list()
        if search_section and search_text:
            # search the manifests
            LOGGER.debug("Manifest search terms: %s in %s"
                         % (search_text, search_section))
            filtered_names = []
            for name in manifest_list:
                manifest = Manifest.readAsPlist(name)
                if manifest:
                    for item in manifest.get(search_section, []):
                        if search_text.lower() in item.lower():
                            filtered_names.append(name)
                            break

            manifest_list = filtered_names
        # send it back in JSON format
        return HttpResponse(json.dumps(manifest_list),
                            content_type='application/json')
    else:
        LOGGER.debug("Got index request for manifests")
        context = {'page': 'manifests'}
        return render(request, 'manifests/manifests.html', context=context)


@login_required
def detail(request, manifest_path):
    '''Returns data on a given manifest'''
    if request.method == 'GET':
        LOGGER.debug("Got read request for %s", manifest_path)
        manifest = Manifest.read(manifest_path)
        if manifest is None:
            raise Http404("%s does not exist" % manifest_path)
        context = {'plist_text': manifest,
                   'pathname': manifest_path}
        return render(request, 'manifests/detail.html', context=context)
    if request.method == 'POST':
        # could be PUT, POST, or DELETE
        if request.META.has_key('HTTP_X_METHODOVERRIDE'):
            http_method = request.META['HTTP_X_METHODOVERRIDE']
            if http_method.lower() == 'delete':
                # DELETE
                LOGGER.debug("Got delete request for %s", manifest_path)
                if not request.user.has_perm('manifest.delete_manifestfile'):
                    raise PermissionDenied
                try:
                    Manifest.delete(manifest_path, request.user)
                except ManifestError, err:
                    return HttpResponse(
                        json.dumps({'result': 'failed',
                                    'exception_type': str(type(err)),
                                    'detail': str(err)}),
                        content_type='application/json')
                else:
                    return HttpResponse(
                        json.dumps({'result': 'success'}),
                        content_type='application/json')
            elif http_method.lower() == 'put':
                # regular POST (update/change)
                LOGGER.debug("Got write request for %s", manifest_path)
                if not request.user.has_perm('manifest.change_manifestfile'):
                    raise PermissionDenied
                if request.is_ajax():
                    json_data = json.loads(request.body)
                    if json_data and 'plist_data' in json_data:
                        plist_data = json_data['plist_data'].encode('utf-8')
                        try:
                            Manifest.write(
                                json_data['plist_data'], manifest_path,
                                request.user)
                        except ManifestError, err:
                            return HttpResponse(
                                json.dumps({'result': 'failed',
                                            'exception_type': str(type(err)),
                                            'detail': str(err)}),
                                content_type='application/json')
                        else:
                            return HttpResponse(
                                json.dumps({'result': 'success'}),
                                content_type='application/json')
            else:
                LOGGER.warning(
                    "Got unknown HTTP_X_METHODOVERRIDE for %s: %s",
                    manifest_path, http_method)
        else:
            # true POST request; create new resource
            LOGGER.debug("Got create request for %s", manifest_path)
            try:
                json_data = json.loads(request.body)
            except ValueError:
                json_data = None
            if json_data and 'plist_data' in json_data:
                plist_data = json_data['plist_data'].encode('utf-8')
                try:
                    Manifest.write(
                        json_data['plist_data'], manifest_path,
                        request.user)
                except ManifestError, err:
                    return HttpResponse(
                        json.dumps({'result': 'failed',
                                    'exception_type': str(type(err)),
                                    'detail': str(err)}),
                        content_type='application/json')
            else:
                try:
                    plist_data = Manifest.new(manifest_path, request.user)
                except ManifestError, err:
                    return HttpResponse(
                        json.dumps({'result': 'failed',
                                    'exception_type': str(type(err)),
                                    'detail': str(err)}),
                        content_type='application/json')
            context = {'plist_text': plist_data,
                       'pathname': manifest_path,}
            return render(request, 'manifests/detail.html', context=context)
