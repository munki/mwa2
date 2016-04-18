## Introduction

This is version 2 of MunkiWebAdmin, a web-based administration tool for Munki.

All reporting (formerly part of MunkiWebAdmin) has been removed from MunkiWebAdmin2 — consider using Sal or MunkiReport-PHP for reporting. Both are excellent.

MunkiWebAdmin2 focuses on web-based editing of manifests and pkginfo files.

This is in-development code. Use it with production Munki repo with care -- make sure you have functioning backups!

## Getting started

On OS X (10.7+):

*   Download and expand this zip:    
    https://github.com/munki/contrib/raw/master/mwa2_demo.zip

*   Via the command-line, run the script within the expanded zip:
    `/Users/me/Downloads/mwa2_demo/run_mwa2.sh`

*   Follow the script prompts. Of note, at one place you'll be advised to edit a settings file. Specifically, you'll edit `mwa2/munkiwebadmin/settings.py`. Near the end of this file is this:

```python
# MUNKI_REPO_DIR holds the local filesystem path to the Munki repo
MUNKI_REPO_DIR = '/Users/Shared/munki_repo'
```

*   Edit `MUNKI_REPO_DIR` to point to a Munki repo to use with MWA2. Please don't point it at your production repo unless you like living very dangerously. This repo should be writable by the user running MWA2.

*   After editing `settings.py`, run `run_mwa2.sh` again to continue the setup process.

*   Once all the setup tasks are complete, a development server will be launched, and MWA2 should be available at http://localhost:8080

#### run_mwa2.sh script details

*   Clones `https://github.com/munki/mwa2.git` from GitHub into the script directory. (if needed)
*   Copies `settings_template.py` to `settings.py` and asks you to edit it. (if needed)
*   Creates the needed sqlite3 database. (if needed)
*   Prompts you to create the initial superuser. (if needed)
*   Uses the included CherryPy dev server to serve MWA2.

## Docker

A Docker file for running MWA2 under Docker is available here: https://github.com/macadmins/docker-mwa2  
This is maintained by a third-party; please direct support questions about the Docker file to the maintainers of that project.

## Acknowledgements

MunkiWebAdmin2 makes use of the following open source components:

*   Python (tested version 2.7.10) - https://www.python.org
*   Django (tested version 1.9.1) - https://www.djangoproject.com
*   jQuery (version 1.11.3 included) - http://jquery.com
*   JQuery-UI (version 1.11.4 included) - http://jqueryui.com
*   Bootstrap (version 3.3.6 included) - http://getbootstrap.com
*   Bootstrap itself includes Glyphicons - http://glyphicons.com
*   DataTables (version 1.10.10 included) - http://datatables.net
*   Ace - (version as of 06 Jan 2016 included) - https://ace.c9.io/ 
*   The GUI plist editor was inspired by and borrows code from Davis Durman's FlexiJsonEditor - https://github.com/DavidDurman/FlexiJsonEditor
*   The JavaScript plist parser was adapted from Todd Gehman's PlistParser: https://github.com/pugetive/plist_parser
*   Chosen - (verson 1.4.2 included) - http://harvesthq.github.io/chosen/

Additionally, the demo files make use of:

*   Virtualenv - https://virtualenv.readthedocs.org/en/latest/
*   Pip - https://pypi.python.org/pypi/pip
*   django-wsgiserver - https://pypi.python.org/pypi/django-wsgiserver 
     -- with a small modification by me to get it to run on Django 1.9 - specifically changing line 326 of `django_wsgiserver/management/commands/runwsgiserver.py` from:
    `self.validate(display_num_errors=True)` to `self.check(display_num_errors=True)`
