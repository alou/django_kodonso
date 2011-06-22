# -*- coding: utf-8 -*-

from django.conf.urls.defaults import *

urlpatterns = patterns('',

    # routing de l'application sur l'assiduité
    url(r"^$", "django_census.views.dashboard"),  
    
    url(r"^dashboard/$", 
         "django_census.views.dashboard",
         name="census-dashboard"),
        
    url(r"^all/(?:(?P<year>\d{4})/(?:(?P<duration>(?:month|week))/(?:(?P<duration_number>\d{1,2})/)*)*)*$",
        "django_census.views.global_report",
        name="census-all"),
   
    url(r"^by-schools/(?P<id>\d+)/(?P<village_name_slug>[a-z0-9\-]+)/(?:(?P<year>\d{4})/(?:(?P<duration>(?:month|week))/(?:(?P<duration_number>\d{1,2})/)*)*)*$", 
         "django_census.views.by_schools",
         name="census-by-schools"),
        
    url(r"^by-classes/(?P<id>\d+)/(?P<school_name_slug>[a-z0-9\-]+)/(?:(?P<year>\d{4})/(?:(?P<duration>(?:month|week))/(?:(?P<duration_number>\d{1,2})/)*)*)*$", 
       "django_census.views.by_classes",
       name="census-by-classes"),
       
    url(r"^report_management/(?P<num>\d+)*$",'django_census.views.report_management',
        name="census-report-management"),
          
    url(r"^management_/(?P<num>\d+)*$",'django_census.views.deleting',
        name="census-management"),
        #~ 
    url(r"^management_2/(?P<num>\d+)*$",'django_census.views.deleting_2',
        name="census-management-2"),
        
    url(r"^modification/(?P<num>\d+)$", "django_census.views.modification_report",
        name="census-modification-report"),    

    url(r"^modification/$", "django_census.views.modification_report",
        name="census-modification"),
        
   url(r"^delete_confirm/(?P<num>\d+)$", "django_census.views.delete_confirm",
        name="census-confirm"),
        
    url(r"^delete_confirm_2/(?P<num>\d+)$", "django_census.views.delete_confirm_2",
        name="census-confirm-2"),
 

    url(r'^logout/$', 'django_census.views.logout', name='logout_'),

    url(r"^training/$","django_census.views.census_report_training",
        name="census-report-training"),
        
          # les exports 
          
    url(r"^all/export/(?:(?P<year>\d{4})/(?:(?P<duration>(?:month|week))/(?:(?P<duration_number>\d{1,2})/)*)*)*$", 
        "django_census.views.global_report_census_csv",
        name="export_all_absence"),
            
    url(r"^report_management/export/(?P<num>\d+)*$", "django_census.views.export_census_manage",
        name="export_census_manage"),
        
   url( r"^by-schools/(?P<id>\d+)/export/(?P<village_name_slug>[a-z0-9\-]+)/(?:(?P<year>\d{4})/(?:(?P<duration>(?:month|week))/(?:(?P<duration_number>\d{1,2})/)*)*)*$",     
         "django_census.views.by_schools_census_csv",
        name="export_census_by_schools"),
        
   url(r"^by-classes/(?P<id>\d+)/export/(?P<school_name_slug>[a-z0-9\-]+)/(?:(?P<year>\d{4})/(?:(?P<duration>(?:month|week))/(?:(?P<duration_number>\d{1,2})/)*)*)*$", 
       "django_census.views.by_classes_census_csv",
       name="by_classes_census_csv"),

         #rapport pdf
    url(r"^rapport_pdf/$",
        "django_census.views.report_pdf",
        name = "census_raport_pdf"),
          # code
    
   url(r"^codification/$","django_census.views.codification_census",
           name="census-codif"),
     
         # evolution_census
   url(r"^evolution/(?P<id>\d+)/(?P<village_name_slug>[a-z0-9\-]+)/(?:(?P<year>\d{4})/(?:(?P<duration>(?:month|week))/(?:(?P<duration_number>\d{1,2})/)*)*)*$", 
         "django_census.views.evolution",
         name="census-evolution"),
   
         
   url(r"^prevision/$","django_census.views.prevision", name="prevision"),   
)
handler404 ="django-kodonso/django_stock.views.my_custom_404_view"

