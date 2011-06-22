# -*- coding: utf-8 -*-

from django.conf.urls.defaults import *
from settings import MEDIA_ROOT, DEBUG

from django.contrib import admin
admin.autodiscover()


urlpatterns = patterns('',

    url(r"^$","django_stock.views.login", name="login"),
    url(r"^home/$","django_stock.views.home", name="kodonso-home"),
    url(r"^census/", include("django_census.urls")),
    url(r"^stock/", include("django_stock.urls")),

    # Administration
    url(r"^menu_admin/(?P<num>\d+)*$", "django_stock.views.menu_admin",
        name="administration"), 
        
    url(r"^ajout-utilisateur/$", "django_stock.views.add_user",
        name="adduser"),
    
    
    #~ url(r"^Modif_Utilisateur/(?P<num>\d+)*$", "django_stock.views.users",
        #~ name="modif_utilisateur"),
        
   url(r"^Modif_group/(?P<num>\d+)*$", "django_stock.views.modif_groupe",
        name="modif_group"),
              
)

# Outil de dev donc on ne les active que en mode debug
# Ils requièrent des applications qui sont importées
# dans local_settings.py

if DEBUG :
    urlpatterns += patterns('', 
    
          # Permet de servir les fichiers statiques durant 
          # le developpement. ex : css, js, images
          url(r'^static/(?P<path>.*)$', 
             'django.views.static.serve',
             {'document_root': MEDIA_ROOT, 'show_indexes': True}),
           
          # Permet l'export des données en fixture
          # 'smuggler' doit se trouver en premier
          
          url(r'^admin/', include('smuggler.urls')), 
    )
   
   
# Inclusion de l'admin en dernier car on doit l'inclure après
# smuggler
urlpatterns += patterns('', 
    url(r'^admin/', include(admin.site.urls)),
)


