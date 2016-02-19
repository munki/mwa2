from django.http import HttpResponse, Http404
from django.http import QueryDict
from django.http import FileResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import PermissionDenied


from api.models import Plist, MunkiFile
from api.models import FileError, FileWriteError, \
                       FileAlreadyExistsError, \
                       FileDoesNotExistError, FileDeleteError

import datetime
import json
import logging
import os
import mimetypes
import plistlib
import re

LOGGER = logging.getLogger('munkiwebadmin')


def normalizeValueForFiltering(value):
    '''Converts value to a list of strings'''
    if isinstance(value, (int, float, bool, basestring, dict)):
        return [str(value).lower()]
    if isinstance(value, list):
        return [str(item).lower() for item in value]
    return []


def convert_dates_to_strings(plist):
    '''Converts all date objects in a plist to strings. Enables encoding into
    JSON'''
    if isinstance(plist, dict):
        for key, value in plist.items():
            if isinstance(value, datetime.datetime):
                plist[key] = value.isoformat()
            if isinstance(value, (list, dict)):
                plist[key] = convert_dates_to_strings(value)
        return plist
    if isinstance(plist, list):
        for value in plist:
            if isinstance(value, datetime.datetime):
                value = value.isoformat()
            if isinstance(value, (list, dict)):
                value = convert_dates_to_strings(value)
        return plist


def convert_strings_to_dates(jdata):
    '''Attempt to automatically convert JSON date strings to date objects for
    plists'''
    iso_date_pattern = re.compile(
        "^\d{4}-[01]\d-[0-3]\dT[0-2]\d:[0-5]\d:[0-5]\dZ*$")
    if isinstance(jdata, dict):
        for key, value in jdata.items():
            if ('date' in key.lower() and isinstance(value, basestring)
                    and iso_date_pattern.match(value)):
                jdata[key] = datetime.datetime.strptime(
                    value[:19], "%Y-%m-%dT%H:%M:%S")
            if isinstance(value, (list, dict)):
                jdata[key] = convert_strings_to_dates(value)
        return jdata
    if isinstance(jdata, list):
        for value in jdata:
            # we don't support lists of dates, so no need to check
            # for those
            if isinstance(value, (list, dict)):
                value = convert_string_to_dates(value)
        return jdata


#@login_required
@csrf_exempt
def plist_api(request, kind, filepath=None):
    if kind not in ['manifests', 'pkgsinfo']:
        return HttpResponse(status=404)

    response_type = 'json'
    if request.META.get('HTTP_ACCEPT') == 'application/xml':
        response_type = 'xml_plist'
    request_type = 'json'
    if request.META.get('CONTENT_TYPE') == 'application/xml':
        request_type = 'xml_plist'

    if request.method == 'GET':
        LOGGER.debug("Got API GET request for %s", kind)
        if filepath:
            response = Plist.read(kind, filepath)
            if response_type == 'json':
                response = convert_dates_to_strings(response)
        else:
            filter_terms = request.GET.copy()
            if 'api_fields' in filter_terms.keys():
                api_fields = filter_terms['api_fields'].split(',')
                del filter_terms['api_fields']
            else:
                api_fields = None
            item_list = Plist.list(kind)
            response = []
            for item_name in item_list:
                if (api_fields == ['filename'] 
                        and filter_terms.keys() in ([], ['filename'])):
                    # don't read each manifest if all we want is filenames
                    plist = {'filename': item_name}
                    if 'filename' in filter_terms.keys():
                        if filter_terms['filename'].lower() not in item_name:
                            continue
                    response.append(plist)
                else:
                    plist = Plist.read(kind, item_name)
                    plist = convert_dates_to_strings(plist)
                    plist['filename'] = item_name
                    matches_filters = True
                    for key, value in filter_terms.items():
                        if key not in plist:
                            matches_filters = False
                            continue
                        plist_value = normalizeValueForFiltering(plist[key])
                        match = next(
                            (item for item in plist_value 
                             if value.lower() in item.lower()), None)
                        if not match:
                            matches_filters = False
                            continue
                    if matches_filters:
                        if api_fields:
                            # filter to just the requested fields
                            plist = {key: plist[key] for key in plist.keys()
                                     if key in api_fields}
                        response.append(plist)
        if response_type == 'json':
            return HttpResponse(json.dumps(response) + '\n',
                                content_type='application/json')
        else:
            return HttpResponse(plistlib.writePlistToString(response),
                                content_type='application/xml')

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
        LOGGER.debug("Got API POST request for %s", kind)
        #if not request.user.has_perm('manifest.change_manifestfile'):
        #    raise PermissionDenied
        if filepath:
            return HttpResponse(
                json.dumps({'result': 'failed',
                            'exception_type': 'WrongHTTPMethodType',
                            'detail': 'This should be a PUT or PATCH request'}
                          ),
                content_type='application/json', status=400)
        if request_type == 'json':
            request_data = json.loads(request.body)
            request_data = convert_strings_to_dates(request_data)
        else:
            request_data = plistlib.readPlistFromString(request.body)
        if request_data:
            filepath = request_data['filename']
            del request_data['filename']
            try:
                #Plist.new(
                #    kind, filepath, request.user, manifest_data=json_data)
                Plist.new(kind, filepath, None, plist_data=request_data)
            except FileAlreadyExistsError, err:
                return HttpResponse(
                    json.dumps({'result': 'failed',
                                'exception_type': str(type(err)),
                                'detail': str(err)}),
                    content_type='application/json',
                    status=409)
            except FileWriteError, err:
                return HttpResponse(
                    json.dumps({'result': 'failed',
                                'exception_type': str(type(err)),
                                'detail': str(err)}),
                    content_type='application/json', status=403)
            except FileError, err:
                return HttpResponse(
                    json.dumps({'result': 'failed',
                                'exception_type': str(type(err)),
                                'detail': str(err)}),
                    content_type='application/json', status=403)
            else:
                if response_type == 'json':
                    request_data = convert_dates_to_strings(request_data)
                    return HttpResponse(
                        json.dumps(request_data) + '\n',
                        content_type='application/json', status=201)
                else:
                    return HttpResponse(
                        plistlib.writePlistToString(request_data),
                        content_type='application/xml', status=201)

    elif request.method == 'PUT':
        LOGGER.debug("Got API PUT request for %s", kind)
        #if not request.user.has_perm('manifest.change_manifestfile'):
        #    raise PermissionDenied
        if not filepath:
            return HttpResponse(
                json.dumps({'result': 'failed',
                            'exception_type': 'WrongHTTPMethodType',
                            'detail': 'Perhaps this should be a POST request'}
                          ),
                content_type='application/json', status=400)
        if request_type == 'json':
            request_data = json.loads(request.body)
            request_data = convert_strings_to_dates(request_data)
        else:
            request_data = plistlib.readPlistFromString(request.body)
        if not json_data:
            # need to deal with this issue
            return HttpResponse(
                json.dumps({'result': 'failed',
                            'exception_type': 'NoRequestBody',
                            'detail': 
                                'Request body was empty or missing valid data'}
                          ),
                content_type='application/json', status=400)
        if 'filename' in request_data :
            # perhaps support rename here in the future, but for now,
            # ignore it
            del request_data['filename']
        
        try:
            data = plistlib.writePlistToString(request_data)
            #Plist.write(data, kind, filepath, request.user)
            Plist.write(data, kind, filepath, None)
        except FileError, err:
            return HttpResponse(
                json.dumps({'result': 'failed',
                            'exception_type': str(type(err)),
                            'detail': str(err)}),
                content_type='application/json', status=403)
        else:
            if response_type == 'json':
                request_data = convert_dates_to_strings(request_data)
                return HttpResponse(
                    json.dumps(request_data) + '\n',
                    content_type='application/json')
            else:
                return HttpResponse(
                    plistlib.writePlistToString(request_data),
                    content_type='application/xml')

    elif request.method == 'PATCH':
        LOGGER.debug("Got API PATCH request for %s" % kind)
        #if not request.user.has_perm('manifest.change_manifestfile'):
        #    raise PermissionDenied
        if not filepath:
            return HttpResponse(
                json.dumps({'result': 'failed',
                            'exception_type': 'WrongHTTPMethodType',
                            'detail': 'Perhaps this should be a POST request'}
                          ),
                content_type='application/json', status=400)
        if request_type == 'json':
            request_data = json.loads(request.body)
            request_data = convert_strings_to_dates(request_data)
        else:
            request_data = plistlib.readPlistFromString(request.body)
        if not request_data:
            # need to deal with this issue
            return HttpResponse(
                json.dumps({'result': 'failed',
                            'exception_type': 'NoRequestBody',
                            'detail': 
                                'Request body was empty or missing valid data'}
                          ),
                content_type='application/json', status=400)
        if 'filename' in request_data:
            # perhaps support rename here in the future, but for now,
            # ignore it
            del request_data['filename']
        # read existing manifest
        plist_data = Plist.read(kind, filepath)
        #plist_data['filename'] = filepath
        plist_data.update(request_data)
        try:
            data = plistlib.writePlistToString(plist_data)
            #Plist.write(data, kind, filepath, request.user)
            Plist.write(data, kind, filepath, None)
        except FileError, err:
            return HttpResponse(
                json.dumps({'result': 'failed',
                            'exception_type': str(type(err)),
                            'detail': str(err)}),
                content_type='application/json', status=403)
        else:
            if response_type == 'json':
                plist_data = convert_dates_to_strings(plist_data)
                return HttpResponse(
                    json.dumps(plist_data) + '\n',
                    content_type='application/json')
            else:
                return HttpResponse(
                    plistlib.writePlistToString(plist_data),
                    content_type='application/xml')

    elif request.method == 'DELETE':
        LOGGER.debug("Got API DELETE request for %s", kind)
        #if not request.user.has_perm('manifest.delete_manifestfile'):
        #    raise PermissionDenied
        if not filepath:
            return HttpResponse(
                json.dumps({'result': 'failed',
                            'exception_type': 'MassDeleteNotSupported',
                            'detail': 'Deleting all items is not supported'}
                          ),
                content_type='application/json', status=403)
        try:
            #Plist.delete(kind, filepath, request.user)
            Plist.delete(kind, filepath, None)
        except FileDoesNotExistError, err:
            return HttpResponse(
                json.dumps({'result': 'failed',
                            'exception_type': str(type(err)),
                            'detail': str(err)}),
                content_type='application/json', status=404)
        except FileDeleteError, err:
            return HttpResponse(
                json.dumps({'result': 'failed',
                            'exception_type': str(type(err)),
                            'detail': str(err)}),
                content_type='application/json', status=403)
        except FileError, err:
            return HttpResponse(
                json.dumps({'result': 'failed',
                            'exception_type': str(type(err)),
                            'detail': str(err)}),
                content_type='application/json', status=403)
        else:
            # success
            return HttpResponse(status=204)


#@login_required
@csrf_exempt
def file_api(request, kind, filepath=None):
    if kind not in ['icons', 'pkgs']:
        return HttpResponse(status=404)
    if request.method == 'GET':
        LOGGER.debug("Got API GET request for %s", kind)
        if filepath:
            fullpath = MunkiFile.get_fullpath(kind, filepath)
            if not os.path.exists(fullpath):
                return HttpResponse(
                    json.dumps({'result': 'failed',
                                'exception_type': 'FileDoesNotExist',
                                'detail': '%s does not exist' % filepath}),
                    content_type='application/json', status=404)
            try:
                response = FileResponse(open(fullpath, 'rb'),
                    content_type=mimetypes.guess_type(fullpath)[0])
                response['Content-Length'] = os.path.getsize(fullpath)
                response['Content-Disposition'] = (
                    'attachment; filename="%s"' % os.path.basename(filepath))
                return response
            except (IOError, OSError), err:
                return HttpResponse(
                    json.dumps({'result': 'failed',
                                'exception_type': str(type(err)),
                                'detail': str(err)}),
                    content_type='application/json', status=403)
        else:
            response = MunkiFile.list(kind)
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
        LOGGER.debug("Got API POST request for %s", kind)
        filename = request.POST.get('filename') or filepath
        filedata = request.FILES.get('filedata')
        if not (filename and filedata):
            # malformed request
            return HttpResponse(
                json.dumps({'result': 'failed',
                            'exception_type': 'BadRequest',
                            'detail': 'Missing filename or filedata'}),
                content_type='application/json', status=400)
        try:
            MunkiFile.new(kind, filedata, filename, None)
        except FileError, err:
            return HttpResponse(
                json.dumps({'result': 'failed',
                            'exception_type': str(type(err)),
                            'detail': str(err)}),
                content_type='application/json', status=403)
        else:
            return HttpResponse(
                json.dumps({'filename': filename}),
                content_type='application/json', status=200)

    if request.method in ('PUT', 'PATCH'):
        LOGGER.debug("Got API %s request for %s", request.method, kind)
        response = HttpResponse(
            json.dumps({'result': 'failed',
                        'exception_type': 'NotAllowed',
                        'detail': 'This method is not supported'}),
            content_type='application/json', status=405)
        response['Allow'] = 'GET, POST, DELETE'
        return response

    if request.method == 'DELETE':
        LOGGER.debug("Got API DELETE request for %s", kind)
        #if not request.user.has_perm('manifest.delete_manifestfile'):
        #    raise PermissionDenied
        if not filepath:
            return HttpResponse(
                json.dumps({'result': 'failed',
                            'exception_type': 'MassDeleteNotSupported',
                            'detail': 'Deleting all items is not supported'}
                          ),
                content_type='application/json', status=403)
        try:
            #MunkiFile.delete(kind, filepath, request.user)
            MunkiFile.delete(kind, filepath, None)
        except FileDoesNotExistError, err:
            return HttpResponse(
                json.dumps({'result': 'failed',
                            'exception_type': str(type(err)),
                            'detail': str(err)}),
                content_type='application/json', status=404)
        except FileDeleteError, err:
            return HttpResponse(
                json.dumps({'result': 'failed',
                            'exception_type': str(type(err)),
                            'detail': str(err)}),
                content_type='application/json', status=403)
        except FileError, err:
            return HttpResponse(
                json.dumps({'result': 'failed',
                            'exception_type': str(type(err)),
                            'detail': str(err)}),
                content_type='application/json', status=403)
        else:
            # success
            return HttpResponse(status=204)