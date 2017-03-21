"""
api/models.py
"""
from django.conf import settings

import os
import logging
import plistlib
from xml.parsers.expat import ExpatError

from munkiwebadmin.utils import MunkiGit
from process.utils import record_status

REPO_DIR = settings.MUNKI_REPO_DIR

LOGGER = logging.getLogger('munkiwebadmin')

try:
    GIT = settings.GIT_PATH
except AttributeError:
    GIT = None

class FileError(Exception):
    '''Class for file errors'''
    pass


class FileReadError(FileError):
    '''Error reading a file'''
    pass


class FileWriteError(FileError):
    '''Error writing a file'''
    pass


class FileDeleteError(FileError):
    '''Error deleting a file'''
    pass


class FileDoesNotExistError(FileError):
    '''Error when file doesn't exist at pathname'''
    pass


class FileAlreadyExistsError(FileError):
    '''Error when creating a new file at an existing pathname'''
    pass


class Plist(object):
    '''Pseudo-Django object'''
    @classmethod
    def list(cls, kind):
        '''Returns a list of available plists'''
        kind_dir = os.path.join(REPO_DIR, kind)
        plists = []
        for dirpath, dirnames, filenames in os.walk(kind_dir):
            record_status(
                '%s_list_process' % kind,
                message='Scanning %s...' % dirpath[len(kind_dir)+1:])
            # don't recurse into directories that start with a period.
            dirnames[:] = [name for name in dirnames
                           if not name.startswith('.')]
            subdir = dirpath[len(kind_dir):].lstrip(os.path.sep)
            if os.path.sep == '\\':
                plists.extend([os.path.join(subdir, name).replace('\\', '/')
                               for name in filenames
                               if not name.startswith('.')])
            else:
                plists.extend([os.path.join(subdir, name)
                               for name in filenames
                               if not name.startswith('.')])
        return plists

    @classmethod
    def new(cls, kind, pathname, user, plist_data=None):
        '''Returns a new plist object'''
        filepath = os.path.join(REPO_DIR, kind, os.path.normpath(pathname))
        if os.path.exists(filepath):
            raise FileAlreadyExistsError(
                '%s/%s already exists!' % (kind, pathname))
        plist_parent_dir = os.path.dirname(filepath)
        if not os.path.exists(plist_parent_dir):
            try:
                # attempt to create missing intermediate dirs
                os.makedirs(plist_parent_dir)
            except (IOError, OSError), err:
                LOGGER.error('Create failed for %s/%s: %s', kind, pathname, err)
                raise FileWriteError(err)
        if plist_data:
            plist = plist_data
        else:
            # create a useful empty plist
            if kind == 'manifests':
                plist = {}
                for section in [
                        'catalogs', 'included_manifests', 'managed_installs',
                        'managed_uninstalls', 'managed_updates',
                        'optional_installs']:
                    plist[section] = []
            elif kind == "pkgsinfo":
                plist = {
                    'name': 'ProductName',
                    'display_name': 'Display Name',
                    'description': 'Product description',
                    'version': '1.0',
                    'catalogs': ['development']
                }
        data = plistlib.writePlistToString(plist)
        try:
            with open(filepath, 'w') as fileref:
                fileref.write(data.encode('utf-8'))
            LOGGER.info('Created %s/%s', kind, pathname)
            if user and GIT:
                MunkiGit().add_file_at_path(filepath, user)
        except (IOError, OSError), err:
            LOGGER.error('Create failed for %s/%s: %s', kind, pathname, err)
            raise FileWriteError(err)
        return data

    @classmethod
    def read(cls, kind, pathname):
        '''Reads a plist file and returns the plist as a dictionary'''
        filepath = os.path.join(REPO_DIR, kind, os.path.normpath(pathname))
        if not os.path.exists(filepath):
            raise FileDoesNotExistError('%s/%s not found' % (kind, pathname))
        try:
            plistdata = plistlib.readPlist(filepath)
            return plistdata
        except (IOError, OSError), err:
            LOGGER.error('Read failed for %s/%s: %s', kind, pathname, err)
            raise FileReadError(err)
        except (ExpatError, IOError):
            # could not parse, return empty dict
            return {}

    @classmethod
    def write(cls, data, kind, pathname, user):
        '''Writes a text data to (plist) file'''
        filepath = os.path.join(REPO_DIR, kind, os.path.normpath(pathname))
        plist_parent_dir = os.path.dirname(filepath)
        if not os.path.exists(plist_parent_dir):
            try:
                # attempt to create missing intermediate dirs
                os.makedirs(plist_parent_dir)
            except OSError, err:
                LOGGER.error('Create failed for %s/%s: %s', kind, pathname, err)
                raise FileWriteError(err)
        try:
            with open(filepath, 'w') as fileref:
                fileref.write(data)
            LOGGER.info('Wrote %s/%s', kind, pathname)
            if user and GIT:
                MunkiGit().add_file_at_path(filepath, user)
        except (IOError, OSError), err:
            LOGGER.error('Write failed for %s/%s: %s', kind, pathname, err)
            raise FileWriteError(err)

    @classmethod
    def delete(cls, kind, pathname, user):
        '''Deletes a plist file'''
        filepath = os.path.join(REPO_DIR, kind, os.path.normpath(pathname))
        if not os.path.exists(filepath):
            raise FileDoesNotExistError(
                '%s/%s does not exist' % (kind, pathname))
        try:
            os.unlink(filepath)
            LOGGER.info('Deleted %s/%s', kind, pathname)
            if user and GIT:
                MunkiGit().delete_file_at_path(filepath, user)
        except (IOError, OSError), err:
            LOGGER.error('Delete failed for %s/%s: %s', kind, pathname, err)
            raise FileDeleteError(err)


class MunkiFile(object):
    '''Pseudo-Django object'''
    @classmethod
    def get_fullpath(cls, kind, pathname):
        '''Returns full filesystem path to requested resource'''
        return os.path.join(REPO_DIR, kind, pathname)

    @classmethod
    def list(cls, kind):
        '''Returns a list of available plists'''
        files_dir = os.path.join(REPO_DIR, kind)
        files = []
        for dirpath, dirnames, filenames in os.walk(files_dir):
            # don't recurse into directories that start with a period.
            dirnames[:] = [name for name in dirnames if not name.startswith('.')]
            subdir = dirpath[len(files_dir):].lstrip(os.path.sep)
            if os.path.sep == '\\':
                files.extend([os.path.join(subdir, name).replace('\\', '/')
                              for name in filenames
                              if not name.startswith('.')])
            else:
                files.extend([os.path.join(subdir, name)
                              for name in filenames
                              if not name.startswith('.')])
        return files

    @classmethod
    def new(cls, kind, fileupload, pathname, user):
        '''Creates a new file from a file upload; returns
        FileAlreadyExistsError if the file already exists at the path'''
        filepath = os.path.join(REPO_DIR, kind, os.path.normpath(pathname))
        if os.path.exists(filepath):
            raise FileAlreadyExistsError(
                '%s/%s already exists!' % (kind, pathname))
        file_parent_dir = os.path.dirname(filepath)
        if not os.path.exists(file_parent_dir):
            try:
                # attempt to create missing intermediate dirs
                os.makedirs(file_parent_dir)
            except (IOError, OSError), err:
                LOGGER.error(
                    'Create failed for %s/%s: %s', kind, pathname, err)
                raise FileWriteError(err)
        cls.write(kind, fileupload, pathname, user)

    @classmethod
    def write(cls, kind, fileupload, pathname, user):
        '''Retreives a file upload and saves it to pathname'''
        filepath = os.path.join(REPO_DIR, kind, os.path.normpath(pathname))
        try:
            with open(filepath, 'w') as fileref:
                for chunk in fileupload.chunks():
                    fileref.write(chunk)
            LOGGER.info('Wrote %s/%s', kind, pathname)
        except (IOError, OSError), err:
            LOGGER.error('Write failed for %s/%s: %s', kind, pathname, err)
            raise FileWriteError(err)

    @classmethod
    def delete(cls, kind, pathname, user):
        '''Deletes file at pathname'''
        filepath = os.path.join(REPO_DIR, kind, os.path.normpath(pathname))
        if not os.path.exists(filepath):
            raise FileDoesNotExistError(
                '%s/%s does not exist' % (kind, pathname))
        try:
            os.unlink(filepath)
            LOGGER.info('Deleted %s/%s', kind, pathname)
        except (IOError, OSError), err:
            LOGGER.error('Delete failed for %s/%s: %s', kind, pathname, err)
            raise FileDeleteError(err)
        