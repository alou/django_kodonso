# -*- coding: utf-8 -*-

import settings
import os

settings.DEBUG = True
settings.MEDIA_ROOT = os.path.join(settings.ROOT_DIR, "media")

#~ settings.INSTALLED_APPS = settings.INSTALLED_APPS +\
                          #~ ('smuggler',
                           #~ 'django_extensions',
                           #~ 'debug_toolbar')
    
settings.INTERNAL_IPS = ('127.0.0.1',)
#settings.MIDDLEWARE_CLASSES = settings.MIDDLEWARE_CLASSES +\
#                             ('debug_toolbar.middleware.DebugToolbarMiddleware',)
settings.INTERCEPT_REDIRECTS = False

settings.SECRET_KEY = 'yz(t17sb48i5)*3g_su0@84*-yi9fo$o#7ao5fo%!g*c6-(fgf'
