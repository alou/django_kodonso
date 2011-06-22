# -*- coding: utf-8 -*-

from django.conf.urls.defaults import *

urlpatterns = patterns('',


    url(r"^dashboard/$", "django_stock.views.dashboard",
         name="stock-dashboard"),

    url(r'^all/(?:(?P<year>\d{4})/(?:(?P<duration>(?:month|week))/(?:(?P<duration_number>\d{1,2})/)*)*)*$',
          'django_stock.views.global_report',
          name="stock-all"),     

    url(r'^by-products/(?P<id>\d+)/(?:(?P<village_name_slug>[a-z0-9\-]+)/(?:(?P<year>\d{4})/(?:(?P<duration>(?:month|week))/(?:(?P<duration_number>\d{1,2})/)*)*)*)*$',
         "django_stock.views.by_products",
         name="stock-by-products"),

    url(r'^by-places/(?P<id>\d+)/(?:(?P<product_name_slug>[a-z0-9\-]+)/(?:(?P<year>\d{4})/(?:(?P<duration>(?:month|week))/(?:(?P<duration_number>\d{1,2})/)*)*)*)*$',
           "django_stock.views.by_places",
           name="stock-by-places"),    

    url(r"^report_management/(?P<num>\d+)*$",'django_stock.views.report_management',
        name="stock-report-management"), 
      
    url(r"^training/$","django_stock.views.stock_report_training",
        name="stock-report-training"),          
    
    url(r"^management/(?P<num>\d+)*$",'django_stock.views.deleting',
        name="stock-management"),
        
    url(r"^management_2/(?P<num>\d+)*$",'django_stock.views.deleting_2',
        name="stock-management-2"),

    url(r"^modification/(?P<num>\d+)$", "django_stock.views.modification_report",
        name="stock-modification-report"),
        
    url(r"^delete_confirm/(?P<num>\d+)$", "django_stock.views.delete_confirm",
        name="stock-confirm"),
        
    url(r"^delete_confirm_2/(?P<num>\d+)$", "django_stock.views.delete_confirm_2",
        name="stock-confirm-2"),
        
    url(r"^login/$", 'django_stock.views.login', name='login'),

    url(r"^logout/$", 'django_stock.views.logout', name='logout'),

    
   
    #l'exports 

    url(r"^all/export/(?:(?P<year>\d{4})/(?:(?P<duration>(?:month|week))/(?:(?P<duration_number>\d{1,2})/)*)*)*$", 
        "django_stock.views.global_report_csv",
        name="export_all_stock"),
        
    url(r"^report_management/export/(?P<num>\d+)*$", 
        "django_stock.views.report_management_csv",
        name="export_manage_stock"),

    url(r'^by-products/export/(?P<id>\d+)/(?:(?P<village_name_slug>[a-z0-9\-]+)/(?:(?P<year>\d{4})/(?:(?P<duration>(?:month|week))/(?:(?P<duration_number>\d{1,2})/)*)*)*)*$',
         "django_stock.views.by_products_csv",
         name="by_products_csv"),

    url(r'^by-places/export/(?P<id>\d+)/(?:(?P<product_name_slug>[a-z0-9\-]+)/(?:(?P<year>\d{4})/(?:(?P<duration>(?:month|week))/(?:(?P<duration_number>\d{1,2})/)*)*)*)*$',
           "django_stock.views.by_places_csv",
           name="by_places_csv"), 
  
           
        # stock maximal
    
    url(r"^stockmaxim/$","django_stock.views.stock_max",
       name="stock_maxi"),
    url(r"^modification_stock_max/(?P<num>\d+)$", "django_stock.views.modif_stock_max",
        name="modification_max"),
        # rapport pdf
    url(r"^rapport_pdf_stock/$",
        "django_stock.views.report_pdf",
        name = "stock_raport_pdf"),
        
    # code
    
      url(r"^codification/$","django_stock.views.codification",
           name="stock-codif"),
           
      # evolution_stock
   url(r"^evolution/(?P<id>\d+)/(?P<village_name_slug>[a-z0-9\-]+)/(?:(?P<year>\d{4})/(?:(?P<duration>(?:month|week))/(?:(?P<duration_number>\d{1,2})/)*)*)*$", 
         "django_stock.views.evolution",
         name="stock-evolution"),      
           
     
    
)
handler404 ="django-kodonso/django_stock.views.my_custom_404_view"
