"""
process/models.py
"""

from django.db import models

# Create your models here.

class Process(models.Model):
    '''a class for tracking a long-running process'''
    name = models.CharField(max_length=256)
    pid = models.IntegerField(default=0)
    exited = models.BooleanField(default=False)
    exitcode = models.IntegerField(default=0)
    statustext = models.CharField(max_length=256, default='')
    percentdone = models.IntegerField(default=0)
    