from django.http import HttpResponse, Http404
from django.http import QueryDict
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import PermissionDenied

from api.models import Plist, PlistError, PlistWriteError, \
                             PlistAlreadyExistsError, \
                             PlistDoesNotExistError, PlistDeleteError
import datetime
import json
import logging
import plistlib

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


#@login_required
@csrf_exempt
def api(request, kind, filepath=None):
    if kind not in ['manifests', 'pkgsinfo']:
        return HttpResponse(status=404)
    if request.method == 'GET':
        LOGGER.debug("Got API GET request for %s", kind)
        if filepath:
            response = Plist.read(kind, filepath)
            response = convert_dates_to_strings(response)
            response['filename'] = filepath
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
        #if not request.user.has_perm('manifest.change_manifestfile'):
        #    raise PermissionDenied
        if filepath:
            return HttpResponse(
                json.dumps({'result': 'failed',
                            'exception_type': 'WrongHTTPMethodType',
                            'detail': 'This should be a PUT or PATCH request'}
                          ),
                content_type='application/json', status=400)
        json_data = json.loads(request.body)
        if json_data:
            filepath = json_data['filename']
            del json_data['filename']
            try:
                #Plist.new(
                #    kind, filepath, request.user, manifest_data=json_data)
                Plist.new(kind, filepath, None, plist_data=json_data)
            except PlistAlreadyExistsError, err:
                return HttpResponse(
                    json.dumps({'result': 'failed',
                                'exception_type': str(type(err)),
                                'detail': str(err)}),
                    content_type='application/json',
                    status=409)
            except PlistWriteError, err:
                return HttpResponse(
                    json.dumps({'result': 'failed',
                                'exception_type': str(type(err)),
                                'detail': str(err)}),
                    content_type='application/json', status=403)
            except PlistError, err:
                return HttpResponse(
                    json.dumps({'result': 'failed',
                                'exception_type': str(type(err)),
                                'detail': str(err)}),
                    content_type='application/json', status=403)
            else:
                json_data['filename'] = filepath
                return HttpResponse(
                    json.dumps(json_data) + '\n',
                    content_type='application/json', status=201)

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
        if 'filename' in json_data:
            # perhaps support rename here in the future, but for now,
            # ignore it
            del json_data['filename']
        try:
            data = plistlib.writePlistToString(json_data)
            #Plist.write(data, kind, filepath, request.user)
            Plist.write(data, kind, filepath, None)
        except PlistError, err:
            return HttpResponse(
                json.dumps({'result': 'failed',
                            'exception_type': str(type(err)),
                            'detail': str(err)}),
                content_type='application/json', status=403)
        else:
            json_data['filename'] = filepath
            return HttpResponse(
                json.dumps(json_data) + '\n',
                content_type='application/json')

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
        if 'filename' in json_data:
            # perhaps support rename here in the future, but for now,
            # ignore it
            del json_data['filename']
        # read existing manifest
        plist_data = Plist.read(kind, filepath)
        plist_data['filename'] = filepath
        plist_data.update(json_data)
        try:
            data = plistlib.writePlistToString(plist_data)
            #Plist.write(data, kind, filepath, request.user)
            Plist.write(data, kind, filepath, None)
        except PlistError, err:
            return HttpResponse(
                json.dumps({'result': 'failed',
                            'exception_type': str(type(err)),
                            'detail': str(err)}),
                content_type='application/json', status=403)
        else:
            plist_data['name'] = filepath
            return HttpResponse(
                json.dumps(plist_data) + '\n',
                content_type='application/json')

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
        except PlistDoesNotExistError, err:
            return HttpResponse(
                json.dumps({'result': 'failed',
                            'exception_type': str(type(err)),
                            'detail': str(err)}),
                content_type='application/json', status=404)
        except PlistDeleteError, err:
            return HttpResponse(
                json.dumps({'result': 'failed',
                            'exception_type': str(type(err)),
                            'detail': str(err)}),
                content_type='application/json', status=403)
        except PlistError, err:
            return HttpResponse(
                json.dumps({'result': 'failed',
                            'exception_type': str(type(err)),
                            'detail': str(err)}),
                content_type='application/json', status=403)
        else:
            # success
            return HttpResponse(status=204)