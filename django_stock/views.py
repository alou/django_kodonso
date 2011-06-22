#!/usr/bin/env python
# -*- coding= UTF-8 -*-

import operator
import csv
import os

from models import * 

from django_stock.form_ import StockReportForm, ModificationForm ,report_pdfForm
from django.db.models import Avg, Sum, Q
from lib.tools import extract_date_info_from_url
from django.shortcuts import render_to_response,HttpResponseRedirect, redirect
from django.core.paginator import Paginator, EmptyPage
from django.core.urlresolvers import reverse
from django.template.defaultfilters import slugify
from django.contrib.auth import authenticate, login as django_login, logout as django_logout
from django.contrib.auth.decorators import login_required
from form_ import LoginForm, AdminForm, Admin1Form, ContactForm, ModifAdminForm ,StockMaxi
from django.utils.datastructures import MultiValueDictKeyError
from django.http import Http404,HttpResponse 
from django.db import IntegrityError
from lib.tools import *
from datetime import date, timedelta

from django.contrib.auth.models import User, Group

from django.utils.translation import ugettext, ugettext_lazy as _
from django.core.mail import send_mail

def my_custom_404_view():
    
    return render_to_response('django_stock/404.html')


def home(request):
    """
        Affiche la page d'acceuil.
    """
    return render_to_response('django_stock/home.html')
    
@login_required
def dashboard(request):
    """
    Afficher un résumé de la situation actuelle pour le stock
    des denrees de cantine.
    """

    lowest_remaining_by_place = Report.objects.order_by('remaining',
                                                        'place',
                                                        'date')[:5]

    # recuperation denrées en pénurie en pourcentage

    for report in lowest_remaining_by_place:
        try:
            report.maximum = report.remaining *100 /report.max
        except :
            report.maximum = ugettext("no maximum stock.")
            
    lowest_remaining_by_product = Report.objects.order_by('remaining',
                                                           'product', 
                                                           'date')[:5]
                                                           

    # recuperation villages en pénurie en pourcentage

    for report in lowest_remaining_by_product:
        try:
            report.maximum = report.remaining *100 / report.max
        except :
            report.maximum = ugettext("no maximum stock.")
  
    top_consumption = Report.objects.order_by('consumption')[:5]
    
    # recuperation des consommations en pourcentage
    
    for report in top_consumption:
        try:
            report.maximum = report.remaining *100 / report.max
        except :
            report.maximum = ugettext("no maximum stock.")
    
    
    recent_comsumptions = Report.objects.filter(consumption__gt=0)\
                                        .order_by('-date')[:5] 
                                        
    recent_incommings = Report.objects.filter(incomming__gt=0)\
                                      .order_by('-date')[:5]   

    # on recupere les derniere consommation et les dernieres entrees
    for report in recent_comsumptions:
        report.sign = "-"
        report.quantity = report.consumption
        report.type = "consumption"
        
    for report in recent_incommings:
        report.sign = "+"
        report.quantity = report.incomming
        report.type = "incomming"
        
    # on ordonne ca par date
    last_reports = list(recent_comsumptions) + list(recent_incommings)
    last_reports.sort(key=operator.attrgetter("date"), reverse=True)
    warning_report = Report.objects.filter(warning=True).order_by('-date')[:5]
    for report in warning_report:
        report.s_day= Maximal.objects.get(place=report.place, product=report.product)
    
    for report in warning_report:
        report.sub_stock = report.consumption-report.s_day.stock_day
        

    ctx = {'last_reports': last_reports,
           'top_consumption': top_consumption,
           'warning_report':warning_report,
           'lowest_remaining_by_product': lowest_remaining_by_product,
           'lowest_remaining_by_place': lowest_remaining_by_place,"user": request.user}

    return render_to_response('django_stock/dashboard.html', ctx)
    
def global_report(request, *args, **kwargs):
    """
        Affiche l'état général des stocks pour chaque village
        et chaque denree
    """
    # on recupere les rapports filtres pour la date demandee
    year, duration, duration_number = extract_date_info_from_url(kwargs)


    previous_date_url,\
    todays_date_url,\
    next_date_url,\
    previous_date,\
    current_date,\
    next_date,\
    todays_date,\
    todays_date_is_before,\
    todays_date_is_after = get_time_pagination(request, year,
                                                duration,
                                                duration_number, "stock-all")

    week_date_url,\
    month_date_url,\
    year_date_url = get_duration_pagination(year,duration,duration_number,
                                            "stock-all")
    
    
    reports = Report.get_reports_filtered_by_duration\
                                                    (year, duration, duration_number)\
                                                    .values('place__name',
                                                    'product__name', 'place__id',
                                                    'product__id')\
                                                    .annotate(Sum('incomming'), 
                                                    Sum('consumption'))

                                                

    total_incomming, total_consumption, total_remaining = 0, 0, 0
    
     # on recupere les noms des produits pour lesquels on a des 
     # releves de stocks
     # et on calcule le total des stock
    reports_with_activities = set()
    for report in reports:
        report['remaining']=0
        report['remaining']=report['incomming__sum']-report['consumption__sum']
        total_incomming += report['incomming__sum']
        total_consumption += report['consumption__sum']
        #~ total_remaining += report['remaining']
        
        reports_with_activities.add(report['place__name'])
    ctx = {'reports':reports,"user": request.user}
    
    if not reports_with_activities:
        ctx.update({"in_empty_case": ugettext("No record of stock"),"user": request.user})
    
    else:
        
        # lister les villages sans mouvement de stock
        place_whithout_activities = []
        
        for place in Place.objects.all():
            if place.name not in reports_with_activities:
                place_whithout_activities.append(place.name)
                
    ctx.update(locals())    

    return render_to_response('django_stock/global_report.html', ctx)
  
    
# Creer un middleware qui donne accès à l'url_name courrant si il
# existe
def global_report_csv(request, *args, **kwargs):

    # on recupere les rapports filtres pour la date demandee
    year, duration, duration_number = extract_date_info_from_url(kwargs)
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment;filename=stock_global_report.csv'

    writer = csv.writer(response)
    writer.writerow([ugettext('Place').encode('utf-8'),ugettext('Product').encode('utf-8'),ugettext('Incomming').encode('utf-8'),ugettext('Consumption').encode('utf-8'),ugettext('Remaining stocks').encode('utf-8')])
     
    previous_date_url,\
    todays_date_url,\
    next_date_url,\
    previous_date,\
    current_date,\
    next_date,\
    todays_date,\
    todays_date_is_before,\
    todays_date_is_after = get_time_pagination(request, year,
                                                duration,
                                                duration_number, "stock-all")

    week_date_url,\
    month_date_url,\
    year_date_url = get_duration_pagination(year,duration,duration_number,
                                            "stock-all")
    
    
    reports = Report.get_reports_filtered_by_duration\
                                                    (year, duration, duration_number)\
                                                    .values('place__name',
                                                    'product__name', 'place__id',
                                                    'product__id')\
                                                    .annotate(Sum('incomming'), 
                                                    Sum('consumption'))

                                                

    total_incomming, total_consumption, total_remaining = 0, 0, 0
    
     
    liste=[]
    reports_with_activities = set()
    for report in reports:
        # recuperation du village, produits, entree, consommation
        dict={}
        dict['remaining']=report['incomming__sum']-report['consumption__sum']
        dict['place']=report['place__name']
        dict['product']=report['product__name']
        dict['incomming__sum']=total_incomming +report['incomming__sum']
        dict['consumption__sum'] = total_consumption +report['consumption__sum']
        #~ total_remaining += report['remaining']
        liste.append(dict)
        # reports_with_activities.add(report['remaining'])
   
    for repports in liste:
        writer.writerow([repports['place'],repports['product'].encode('utf-8'), repports['incomming__sum'], repports['consumption__sum'], repports['remaining']])
       
    return response
    
def by_products(request, *args, **kwargs):
   
    """
        Affiche l'état des stocks pour chaque chaque denree d'un 
        village
    """
    id_ = int(request.POST.get('to_display', 0)) or int(kwargs["id"])
    
    # charger l'ecole dont on veut afficher les ecoles
    # si ce village n'existe pas, mettre une page d'erreur
    try: 
        place = Place.objects.get(id=id_)
    except Place.DoesNotExist:
        raise Http404
    
    year, duration, duration_number = extract_date_info_from_url(kwargs)
    
    if request.method == 'POST':
        return get_redirection("stock-by-products", place,
                                year, duration, duration_number)
        
    navigation_form = get_navigation_form(Place.objects.all(),
                                          ugettext("Change school"),
                                          place,
                                          "stock-by-products",
                                          year, duration, duration_number)
        
    total_incomming, total_consumption,total_remaining = 0, 0, 0

    # on recupere les rapports filtres pour la date demandee
    reports = Report.get_reports_filtered_by_duration(year, 
                                                     duration, 
                                                     duration_number)

    previous_date_url,\
    todays_date_url,\
    next_date_url,\
    previous_date,\
    current_date,\
    next_date,\
    todays_date,\
    todays_date_is_before,\
    todays_date_is_after = get_time_pagination(request,year, duration,duration_number, 
                                                "stock-by-products",
                                                additional_args=(id_, 
                                                                  slugify(place.name)))
    
    week_date_url,\
    month_date_url,\
    year_date_url = get_duration_pagination(year, duration, duration_number, 
                                            "stock-by-products",
                                            additional_args=(id_, 
                                                              slugify(place.name)))
    
    # on filtre par village
    reports = reports.filter(place__id=id_)
     
    # calcul des sommes des s et des sorties  
    products_sum = reports.values("product__name",
                                  "product__id")\
                         .annotate(incomming=Sum("incomming"), 
                                   consumption=Sum("consumption"))
    
    product_with_activities = set()
    reports_by_product = []
    for product_sum in products_sum:
    
        last_report = reports.filter(product__id=product_sum["product__id"])\
                             .order_by('-date')[0]
        by_product_dict = {}
        
        # remplissage du dictionnaire by_product_dict 
        by_product_dict["id_"] = product_sum["product__id"]
        by_product_dict["product"] = product_sum["product__name"]  
        by_product_dict["incomming"] = product_sum["incomming"]
        by_product_dict["consumption"] = product_sum["consumption"] 
        by_product_dict["remaining"] = product_sum["incomming"] - product_sum["consumption"]
        
        reports_by_product.append(by_product_dict)
        
        total_incomming += product_sum["incomming"]
        total_consumption += product_sum["consumption"]
        total_remaining += last_report.remaining
        
        # on recupere les noms des produits pour lesquelles 
        # on a des mouvements de stock
        product_with_activities.add(by_product_dict["product"])
    
    ctx = {'village': place,"user": request.user ,'valide':'before' }
    
    if not product_with_activities:
        ctx.update({"in_empty_case": ugettext("No record of stock")})
    else:
        
        # lister les produits sans mouvement de stock
        product_whithout_activities = []
        
        for product in Product.objects.all():
            if product.name not in product_with_activities:
                product_whithout_activities.append(product.name)

    ctx.update(locals())
        
    return render_to_response('django_stock/by_products.html', ctx)





def by_products_csv(request, *args, **kwargs):
    
    # Create the HttpResponse object with the appropriate CSV header.
    
    
    

    
    id_ = int(request.POST.get('to_display', 0)) or int(kwargs["id"])
    
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment;filename=product_csv.csv'
    writer = csv.writer(response)
    writer.writerow([ugettext('Product').encode('utf-8'),ugettext('Incomming').encode('utf-8'),ugettext('Consumption').encode('utf-8'),ugettext('Remaining stocks').encode('utf-8')])
    
    # charger l'ecole dont on veut afficher les ecoles
    # si ce village n'existe pas, mettre une page d'erreur
    try: 
        place = Place.objects.get(id=id_)
    except Place.DoesNotExist:
        raise Http404
    
    year, duration, duration_number = extract_date_info_from_url(kwargs)
    
    if request.method == 'POST':
        return get_redirection("stock-by-products", place,
                                year, duration, duration_number)
        
    navigation_form = get_navigation_form(Place.objects.all(),
                                          ugettext("Change school"),
                                          place,
                                          "stock-by-products",
                                          year, duration, duration_number)
        
    total_incomming, total_consumption,total_remaining = 0, 0, 0

    # on recupere les rapports filtres pour la date demandee
    reports = Report.get_reports_filtered_by_duration(year, 
                                                     duration, 
                                                     duration_number)

    previous_date_url,\
    todays_date_url,\
    next_date_url,\
    previous_date,\
    current_date,\
    next_date,\
    todays_date,\
    todays_date_is_before,\
    todays_date_is_after = get_time_pagination(request,year, duration,duration_number, 
                                                "stock-by-products",
                                                additional_args=(id_, 
                                                                  slugify(place.name)))
    
    week_date_url,\
    month_date_url,\
    year_date_url = get_duration_pagination(year, duration, duration_number, 
                                            "stock-by-products",
                                            additional_args=(id_, 
                                                              slugify(place.name)))
    
    # on filtre par village
    reports = reports.filter(place__id=id_)
     
    # calcul des sommes des s et des sorties  
    products_sum = reports.values("product__name",
                                  "product__id")\
                         .annotate(incomming=Sum("incomming"), 
                                   consumption=Sum("consumption"))
    
    product_with_activities = set()
    reports_by_product = []
    for product_sum in products_sum:
    
        last_report = reports.filter(product__id=product_sum["product__id"])\
                             .order_by('-date')[0]
        by_product_dict = {}
        
        # remplissage du dictionnaire by_product_dict 
        by_product_dict["id_"] = product_sum["product__id"]
        by_product_dict["product"] = product_sum["product__name"]  
        by_product_dict["incomming"] = product_sum["incomming"]
        by_product_dict["consumption"] = product_sum["consumption"] 
        by_product_dict["remaining"] = product_sum["incomming"] - product_sum["consumption"]
        
        reports_by_product.append(by_product_dict)
        
        total_incomming += product_sum["incomming"]
        total_consumption += product_sum["consumption"]
        total_remaining += last_report.remaining

        
    for report in reports_by_product:
      
        writer.writerow([report['product'].encode('utf-8'), report['incomming'], report['consumption'], report['remaining']])
    writer.writerow(['Total',total_incomming,total_consumption,total_remaining])
    return response
    

def by_places (request,*args, **kwargs):
    """
        Affiche l'état des stocks pour chaque village 
        qui consomment une denree
    """
    
    id_ = int(request.POST.get('to_display', 0)) or int(kwargs["id"])
    
    # charger l'ecole dont on veut afficher les ecoles
    # si ce village n'existe pas, mettre une page d'erreur
    try: 
        product = Product.objects.get(id=id_)
    except Product.DoesNotExist:
        raise Http404
        
    year, duration, duration_number = extract_date_info_from_url(kwargs)
        
    # comme partie du formulaire
    if request.method == 'POST' :
        return get_redirection("stock-by-places", product,
                                year, duration, duration_number)
        
    navigation_form = get_navigation_form(Product.objects.all(),
                                          ugettext("Change Product"),
                                          product,
                                          "stock-by-places",
                                          year, duration, duration_number)
    
    total_incomming, total_consumption, total_remaining = 0, 0, 0
    
    # on a filtrer par entrée, mois, année, nom de denrée
    reports = Report.get_reports_filtered_by_duration(year, 
                                                     duration, 
                                                     duration_number)

    previous_date_url,\
    todays_date_url,\
    next_date_url,\
    previous_date,\
    current_date,\
    next_date,\
    todays_date,\
    todays_date_is_before,\
    todays_date_is_after = get_time_pagination(request,year, duration, duration_number,
                                                "stock-by-places",
                                                additional_args=(id_,
                                                                slugify(product.name)))

    week_date_url,\
    month_date_url,\
    year_date_url = get_duration_pagination(year, duration, duration_number,
                                            "stock-by-places",
                                            additional_args=(id_,
                                                            slugify(product.name)))

    # on filtre par produit
    reports = reports.filter(product__id=id_)
    
    # calcul des sommes des entrées et des sorties 
    places_sum = reports.values("place__name", "place__id")\
                        .annotate(Sum("incomming"), 
                                  Sum("consumption"))
        
    # filtrage par produit
    village_reports = []
    place_with_activities = set()
    for place_sum in places_sum:
        
        last_report = reports.filter(place__id=place_sum["place__id"])\
                             .order_by('-date')[0]      
    
        by_place_dict={}
        
        # remplissage du dictionnaire by_place_dict 
        by_place_dict["id_"] = place_sum["place__id"]
        by_place_dict["place"] = place_sum["place__name"]  
        by_place_dict["incomming"] = place_sum["incomming__sum"]
        by_place_dict["consumption"] = place_sum["consumption__sum"] 
        by_place_dict["remaining"] = place_sum["incomming__sum"] - place_sum["consumption__sum"] 

        village_reports.append(by_place_dict)

        total_incomming += by_place_dict["incomming"]
        total_consumption += by_place_dict["consumption"]
        total_remaining += by_place_dict["remaining"]
        
        place_with_activities.add(place_sum["place__name"])
    
        

    ctx = {'product': product,"user": request.user}

    if not place_with_activities:
        ctx.update({"in_empty_case": ugettext("No record of stock")})
    else:    
       
        # lister les villages sans mouvement de stock
        place_whithout_activities = []

        for place in Place.objects.all():
            if place.name not in place_with_activities:
                place_whithout_activities.append(place.name)
                
    ctx.update(locals())
         
    return render_to_response('django_stock/by_places.html', ctx)
    
def by_places_csv(request, *args, **kwargs):
    # Create the HttpResponse object with the appropriate CSV header.
    
    id_ = int(request.POST.get('to_display', 0)) or int(kwargs["id"])
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment;filename=product_csv.csv'
    
    # Create the CSV writer using the HttpResponse as the "file"
    
    writer = csv.writer(response)
    writer.writerow([ugettext('School').encode('utf-8'),ugettext('Incomming').encode('utf-8'),ugettext('Consumption').encode('utf-8'),ugettext('Remaining').encode('utf-8')])
    """
        Affiche l'état des stocks pour chaque village 
        qui consomment une denree
    """
    
    id_ = int(request.POST.get('to_display', 0)) or int(kwargs["id"])
    
    # charger l'ecole dont on veut afficher les ecoles
    # si ce village n'existe pas, mettre une page d'erreur
    try: 
        product = Product.objects.get(id=id_)
    except Product.DoesNotExist:
        raise Http404
        
    year, duration, duration_number = extract_date_info_from_url(kwargs)
        
    # comme partie du formulaire
    if request.method == 'POST' :
        return get_redirection("stock-by-places", product,
                                year, duration, duration_number)
        
    navigation_form = get_navigation_form(Product.objects.all(),
                                          "Changer de denrée",
                                          product,
                                          "stock-by-places",
                                          year, duration, duration_number)
    
    total_incomming, total_consumption, total_remaining = 0, 0, 0
    
    # on a filtrer par entrée, mois, année, nom de denrée
    reports = Report.get_reports_filtered_by_duration(year, 
                                                     duration, 
                                                     duration_number)

    previous_date_url,\
    todays_date_url,\
    next_date_url,\
    previous_date,\
    current_date,\
    next_date,\
    todays_date,\
    todays_date_is_before,\
    todays_date_is_after = get_time_pagination(request,year, duration, duration_number,
                                                "stock-by-places",
                                                additional_args=(id_,
                                                                slugify(product.name)))

    week_date_url,\
    month_date_url,\
    year_date_url = get_duration_pagination(year, duration, duration_number,
                                            "stock-by-places",
                                            additional_args=(id_,
                                                            slugify(product.name)))

    # on filtre par produit
    reports = reports.filter(product__id=id_)
    
    # calcul des sommes des entrées et des sorties 
    places_sum = reports.values("place__name", "place__id")\
                        .annotate(Sum("incomming"), 
                                  Sum("consumption"))
        
    # filtrage par produit
    village_reports = []
    place_with_activities = set()
    for place_sum in places_sum:
        
        last_report = reports.filter(place__id=place_sum["place__id"])\
                             .order_by('-date')[0]      
    
        by_place_dict={}
        
        # remplissage du dictionnaire by_place_dict 
        by_place_dict["id_"] = place_sum["place__id"]
        by_place_dict["place"] = place_sum["place__name"]  
        by_place_dict["incomming"] = place_sum["incomming__sum"]
        by_place_dict["consumption"] = place_sum["consumption__sum"] 
        by_place_dict["remaining"] =  place_sum["incomming__sum"] - place_sum["consumption__sum"]
        total_incomming += by_place_dict["incomming"]
        total_consumption += by_place_dict["consumption"]
        total_remaining += by_place_dict["remaining"]
        village_reports.append(by_place_dict)
        
    for report in village_reports:

        writer.writerow([report['place'].encode('utf-8'), report['incomming'], report['consumption'], report['remaining']])
    writer.writerow(['Total',total_incomming,total_consumption,total_remaining])
    return response
    
def report_management(request, *args, **kwargs):
    alerte= False
    group_users =''
    
    try :
        # on recupere le groupe de l'utilisateur connecté
        group_users = request.user.groups.values_list() 
    except IndexError:
        pass
    # on recupere le numero depuis l'url si le numero 
    # est none on donne 1 par  defaut
    num = kwargs["num"] or 1
    
    # on ordonne par dates recentes les rapports 
    
    reports = Report.objects.order_by('place__name','-date')
    
    #pour mettre 20 rapport par page
    paginator = Paginator(reports, 20)
    
    # s'execute si la base est vide  
    if not reports.count():
        ctx = {"in_empty_case": ugettext("No record of stock ")}
    
    # s'execute si il ya des données dans la base
    else:

        try:
            page = paginator.page(int(num))
            
        # affiche une erreur Http404 si l'on de passe la page est vide    
        except EmptyPage:
            raise Http404
        # si le numero de la page est 2
        page.is_before_first = (page.number == 2 )
        # si le numero de la page est egale au numero de l'avant derniere page
        page.is_before_last = (page.number == paginator.num_pages - 1)
        # on constitue l'url de la page suivante
        page.url_next = reverse('stock-report-management', args=[int(num) + 1])
        # on constitue l'url de la page precedente
        page.url_previous= reverse('stock-report-management', args=[int(num) - 1])
        # on constitue l'url de la 1ere page
        page.url_first = reverse('stock-report-management')
        # on constitue l'url de la derniere page
        page.url_last = reverse('stock-report-management',
                                args=[paginator.num_pages])
              
        for report in page.object_list:
        
            # on recupere l'année, le nombre de semaines et le nombre de jours
            year, week_number, day_number = report.date.isocalendar()
            
            # on constitue l'url du lien pointant sur le nom du village
            report.url_place = reverse('stock-by-products',
                                       args=[report.place.id,
                                             slugify(report.place),
                                             year,'week',week_number])
                                             
            # on constitue l'url du lien pointant sur le nom du product
            report.url_product = reverse('stock-by-places',
                                          args=[report.product.id,
                                                slugify(report.product),
                                                year,'week', week_number])
           
            # on constitue l'url du lien pointant sur la vue de la confirmation du rapport
            report.url_delete = reverse('stock-confirm', args=[report.id])
           
            # on constitue l'url du lien pointant sur la vue de la modification du rapport
            report.url_modification = reverse("stock-modification-report", args=[report.id])
            ctx = {"page": page, "paginator": paginator,"user": request.user, 'lien':'before'}
   
    # on verifie si l'utilisateur fait partie de ces groupes  
    for group_user in group_users:  
        if group_user[1] in ['Stock-Admin','Stock-Reporter', 'Standard']:
            # on charge le formulaire
            form = StockReportForm()
            ctx.update( {'form':form,'valide':'before', 'save':'before'})
        
            if request.method == 'POST':
                form = StockReportForm(request.POST)
                if len(request.POST['date'].split('-'))==3:
                    #on recupere et on change le format de la date du formulaire
                    if request.POST['date'] :
                        day, month ,year = request.POST['date'].split('-')
                        if len(day)== 4:
                            new_format = day + '-' + month + '-' + year
                        else:
                            new_format = year + '-' + month + '-' + day

                        # on cree un dictionnaire et on le remplie avec les données POST                                              
                        report_warning = Maximal.objects.filter(place=request.POST['place'], product=request.POST['product'])
                        try:
                            if int(request.POST['consumption']) > report_warning[0].stock_day:
                                dict = {'reporter':request.user.id,'product': request.POST['product'],'place': request.POST['place'],'incomming': request.POST['incomming'],
                                        'consumption': request.POST['consumption'],'date': new_format, 'warning': True}
                                alerte = True 
                            else:
                                dict = {'reporter':request.user.id,'product': request.POST['product'],'place': request.POST['place'],'incomming': request.POST['incomming'],
                                        'consumption': request.POST['consumption'],'date': new_format, 'warning': False}
                        except ValueError:
                            dict = {'reporter':request.user.id,'product': request.POST['product'],'place': request.POST['place'],'incomming': request.POST['incomming'],
                                        'consumption': request.POST['consumption'],'date': new_format, 'warning': False}
                        except IndexError:
                            dict = {'reporter':request.user.id,'product': request.POST['product'],'place': request.POST['place'],'incomming': request.POST['incomming'],
                                        'consumption': request.POST['consumption'],'date': new_format, 'warning': False}
                        try:
                            # on verifie si le rapport poste existe deja
                            duplicate = Report.objects.filter(place=dict['place'],product=dict['product'], incomming=dict['incomming'], consumption=dict['consumption'], date=dict['date'])
                        except ValueError:
                            pass
                        form = StockReportForm(dict)
              
                # on verifie le formulaire
                if form.is_valid():
                    # si il n'ya pas de doublon on execute cela
                    if not duplicate:
                        if alerte :
                            try:
                                recipients = [user.email for user in Group.objects.get(name='Standard').user_set.all()]
                            except:
                                recipients = []
                            send_mail(ugettext('Warning Kodonso'), ugettext("There is a school that has exceeded its daily consumption, please consuter http://rtl.gotdns.org "), 'fanga.computing@gmail.com',  recipients, fail_silently=False)
     
                        form.save()
                        
                        return HttpResponseRedirect(reverse('stock-report-management'))
                    #si il ya des doublon on execute cela
                    else:
                        ctx.update({'form':form,'valide':'sent', 'err':ugettext("This report already exists")})
                ctx.update({'form':form,'valide':'sent'})
        else :
            ctx.update({'save':'sent', 'error':ugettext('you can not add report ')})
   
        return render_to_response('django_stock/report_management.html', ctx)

def stock_report_training(request, *args, **kwargs):
    alerte= False
    reports = Report.objects.filter(reporter=request.user.id).order_by('-date')
    for report in reports:
        # on constitue l'url du lien pointant sur la vue de la confirmation du rapport
        report.url_delete_2 = reverse('stock-confirm-2', args=[report.id])
    form = StockReportForm()
    if request.method == 'POST':
        form = StockReportForm(request.POST)
        if request.POST['date'] :
            day, month ,year = request.POST['date'].split('-')
            if len(day)== 4:
                new_format = day + '-' + month + '-' + year
            else:
                new_format = year + '-' + month + '-' + day
            report_warning = Maximal.objects.filter(place=request.POST['place'], product=request.POST['product'])
            try:
                if int(request.POST['consumption']) > report_warning[0].stock_day:
                    dict = {'reporter':request.user.id,'product': request.POST['product'],'place': request.POST['place'],'incomming': request.POST['incomming'],
                            'consumption': request.POST['consumption'],'date': new_format, 'warning': True}
                    alerte= True 
                else:
                    dict = {'reporter':request.user.id,'product': request.POST['product'],'place': request.POST['place'],'incomming': request.POST['incomming'],
                            'consumption': request.POST['consumption'],'date': new_format, 'warning': False}
           
            except IndexError:
                dict = {'reporter':request.user.id,'product': request.POST['product'],'place': request.POST['place'],'incomming': request.POST['incomming'],
                            'consumption': request.POST['consumption'],'date': new_format, 'warning': False}
           
            except ValueError:
                dict = {'reporter':request.user.id,'product': request.POST['product'],'place': request.POST['place'],'incomming': request.POST['incomming'],
                            'consumption': request.POST['consumption'],'date': new_format, 'warning': False}
            try:
                # on verifie si le rapport poste existe deja
                duplicate = Report.objects.filter(place=dict['place'],product=dict['product'], incomming=dict['incomming'], consumption=dict['consumption'], date=dict['date'])
                
            except ValueError:
                pass
            form = StockReportForm(dict)
        
        if form.is_valid():
            
            if not duplicate:
                if alerte :
                    try:
                        recipients = [user.email for user in Group.objects.get(name='Standard').user_set.all()]
                    except:
                        recipients = []
                    send_mail(ugettext('Warning Kodonso'), ugettext("There is a school that has exceeded its daily consumption, please consuter rtl.gotdns.org"), 'fanga.computing@gmail.com',  recipients, fail_silently=False)
     
                form.save()
                return HttpResponseRedirect(reverse('stock-report-training'))
            else:
                return render_to_response('django_stock/training_stock.html',{'err':ugettext("This report already exists"),'form':form, 'reports':reports, 'user':request.user})
    return render_to_response('django_stock/training_stock.html',{'form':form, 'reports':reports, 'user':request.user})   


def report_management_csv(request, *args, **kwargs):
    
    # on recupere le numero depuis l'url si le numero 
    # est none on donne 1 par  defaut
    num = kwargs["num"] or 1
    
    # on ordonne par dates recentes les rapports 
    reports = Report.objects.order_by('place__name','-date')
    
    # pour mettre 20 rapport par page
    paginator = Paginator(reports, 20)
    
    # s'execute si la base est vide  
    if not reports.count():
        ctx = {"in_empty_case": ugettext("No record of stock ")}
    
    # s'execute si il ya des données dans la base
    else:

        try:
            page = paginator.page(int(num))
            
        # affiche une erreur Http404 si l'on de passe la page est vide    
        except EmptyPage:
            raise Http404
        # si le numero de la page est 2
        page.is_before_first = (page.number == 2 )
        # si le numero de la page est egale au numero de l'avant derniere page
        page.is_before_last = (page.number == paginator.num_pages - 1)
        # on constitue l'url de la page suivante
        page.url_next = reverse('stock-report-management', args=[int(num) + 1])
        # on constitue l'url de la page precedente
        page.url_previous= reverse('stock-report-management', args=[int(num) - 1])
        # on constitue l'url de la 1ere page
        page.url_first = reverse('stock-report-management')
        # on constitue l'url de la derniere page
        page.url_last = reverse('stock-report-management',
                                args=[paginator.num_pages])
       
        response = HttpResponse(mimetype='text/csv')
        response['Content-Disposition'] = 'attachment;filename=report_management_csv.csv'
        
        writer = csv.writer(response)
        writer.writerow([ugettext('Place').encode('utf-8'),ugettext('Product').encode('utf-8'),ugettext('Incomming').encode('utf-8'),ugettext('Consumption').encode('utf-8'),ugettext('Remaining stocks').encode('utf-8'),ugettext('Date').encode('utf-8')])

        for report in page.object_list:
            writer.writerow([report.place, report.product, report.incomming, report.consumption, report.remaining, report.date])
        return response 


def delete_confirm(request,*args, **kwargs):
    """
        Confirmation de la suppression d'un rapport
    """
    group_users =''
    try :
        # on recupere le groupe de l'utilisateur connecté
        group_users = request.user.groups.values_list() 
    except IndexError:
        pass
        
    try: 
        # on verifie si l'utilisateur fait partie de ces groupes
        for group_user in group_users:
            if group_user[1] in ['Stock-Admin', 'Standard']:
                # on recupere le numero du rapport depuis l'url 
                id_report = kwargs["num"] 
                # on recupere ce rapport
                report = Report.objects.get(id = id_report)
                # on constitue l'url du lien pointant sur la vue de la suppression du rapport
                report.url_delete = reverse('stock-management', args=[report.id])
                  
            return render_to_response('django_stock/delete.html',{'report':report,"user": request.user})
    except UnboundLocalError:
        return render_to_response('page_right.html')
        
def delete_confirm_2(request,*args, **kwargs):
    """
        Confirmation de la suppression d'un rapport
    """
    
    # on recupere le numero du rapport depuis l'url 
    id_report = kwargs["num"] 
    # on recupere ce rapport
    report = Report.objects.get(id = id_report)
    # on constitue l'url du lien pointant sur la vue de la suppression du rapport
    report.url_delete_2 = reverse('stock-management-2', args=[report.id])
          
    return render_to_response('django_stock/delete_2.html',{'report':report,"user": request.user})
   
        
def deleting(request,*args, **kwargs):
    """
        Suppression de rapport
    """
    
    # on recupere le numero du rapport depuis l'url
    id_report = kwargs["num"] 
    report = Report.objects.get(id = id_report)
    
    # supprime le rapport
    report.delete()
    reports = Report.objects.all()
    for report in reports:
        report.save()
    
    
    return HttpResponseRedirect(reverse('stock-report-management'))
    
def deleting_2(request,*args, **kwargs):
    """
        Suppression de rapport
    """
    
    # on recupere le numero du rapport depuis l'url
    id_report = kwargs["num"] 
    report = Report.objects.get(id = id_report)
    
    # supprime le rapport
    report.delete()
    reports = Report.objects.all()
    for report in reports:
        report.save()
    
    
    return HttpResponseRedirect(reverse('stock-report-training'))


def modification_report(request,*args, **kwargs):
    """
        Modifiction de rapport
    """
    group_users =''
    try :
        # on recupere le groupe de l'utilisateur connecté
        group_users = request.user.groups.values_list() 
    except IndexError:
        pass
    # on recupere le numero du rapport depuis l'url
    id_report = kwargs["num"] 
    # on recupere ce rapport
    report = Report.objects.get(id = id_report)
    # on cree un dictionnaire et on le remplie 
    dict ={}
    dict = {'product': report.product.id,'place': report.place.id,'incomming': report.incomming,
            'consumption': report.consumption,'date': report.date}
    
    # on verifie si l'utilisateur fait partie de ces groupes
    for group_user in group_users:
        if group_user[1] in ['Stock-Admin', 'Standard']:
            # on passe le dictionnaire au formulaire
            form = ModificationForm(dict)
    max=Maximal.objects.all()
    if request.method=='POST':
        form = ModificationForm(request.POST)
        max=Maximal.objects.filter(product__id=request.POST['product'], place__id=request.POST['place'])
        
        # on verifie le formulaire
        if form.is_valid():
            report.consumption = float(request.POST['consumption'])
            report.incomming = float(request.POST['incomming'])
            report.date = request.POST['date']
            for m in max:
                
                if float(request.POST['consumption']) < m.stock_day:
                    
                    report.warning=False 
                    report.save()
                    
                elif float(request.POST['consumption']) > m.stock_day:
                    report.warning=True
                    report.save()
            
            
            return HttpResponseRedirect(reverse('stock-report-management'))
    try:
        return render_to_response('django_stock/modification.html',{'form':form})
    except UnboundLocalError:
            return render_to_response('page_right.html')    


def login(request):
    """
        login est la views qui permet de se connecter
    """
    state = ugettext("Please login ...")
    
    #Initialise username et password à vide
    
    username = password = ''

    # On appel la fonction LoginForm() dans le formulaire
   
    form = LoginForm()
    
    if request.method=='POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        url  = request.GET.get('next')
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                django_login(request, user)
                state = ugettext("Interconnection of good!")
                if url:
                    return HttpResponseRedirect(request, url)
                else:
                    #~ if request.user.groups.values_list()[0][1] in ['Stock-Admin', 'Stock-Reporter']:
                        #~ return redirect('stock-dashboard')
                        
                    if request.user.groups.values_list()[0][1] in ['Census-Admin', 'Census-Reporter']:
                        return redirect('census-dashboard')
                    #~ if request.user.groups.values_list()[0][1] in ['Stock_Data_Entry']:
                        #~ return redirect('stock-report-training')
                        
                    if request.user.groups.values_list()[0][1] in ['Census_Data_Entry']:
                        return redirect('census-report-training')
                    
                    if request.user.groups.values_list()[0][1] in ['Standard', 'Guest']:
                        return redirect('census-dashboard')
                    #~ else:
                        #~ return redirect('census-dashboard')
            else:
                 state = ugettext("Your Account is not active, please contact the site admin.")
        else:
            state = ugettext("Your username and / or your password is incorrect.")
    return render_to_response('authente.html',{'form':form, 'state': state})

def logout(request):
    """ 
        logout est la views qui permet de se deconnecter
    """
    
    django_logout(request)
    return redirect("/")

def menu_admin(request,*args, **kwargs):
    
    users = User.objects.all() 
    group_users =''
    try :
        # on recupere le groupe de l'utilisateur connecté
        group_users = request.user.groups.values_list()
    except IndexError:
        pass
    
    for group_user in group_users:
        # on verifie si l'utilisateur fait partie de ces groupes.
        if group_user[1] in  ['Stock-Admin','Census-Admin', 'Standard']:            
            for user in users:
                user.groupe=[]
                for groupu in user.groups.values():
                    user.groupe.append( groupu['name'])
                user.url = reverse('modif_group', args=[user.id])
            ctx = {"user": request.user,'users':users}
        
    try: 
        return render_to_response('admin_menu.html',ctx)
    except UnboundLocalError:
        return render_to_response('page_right.html') 

def add_user(request,*args, **kwargs):    
    """ Permet la creation des utilisateurs """

    group_users =''
    
    try :
        # on recupere le groupe de l'utilisateur connecté
        group_users = request.user.groups.values_list()
    except IndexError:
        pass
        
    for group_user in group_users:
        # on verifie si l'utilisateur fait partie de ces groupes.
        if group_user[1] in  ['Stock-Admin','Census-Admin', 'Standard']:
            #On charge le formulaire.
            form = AdminForm()
            ctx = {'form': form, "user": request.user}
            
            if request.method=='POST':
                #On charge le formulaire en lui passant comme paramettre la requette POST.
                form = AdminForm(request.POST)
                ctx.update({'form': form})
                #On cree une liste qui contiendra les groupes de l'utilisateur connecter.
                online_user_group = []
                #On cree une liste qui contiendra les groupes de l'utilisateur à creer.
                created_group = []
                #Liste intermediaire.
                previews = []
                
                for group in request.user.groups.values():
                    #On recupere la liste des groupes de l'utilisateur connecter.
                     online_user_group.append(group['name'])
                     
                #On recupere tous les groupes selectionner par l'utilisateur connecter.
                for group in request.POST.getlist('groupe'):
                    previews.append(Group.objects.get(id=group))
                    
                #On rempli la liste qui contient les groupes de l'utilisateur à creer.
                for pre in previews:
                    created_group.append(pre.name)
                    
                try:
                    #On verifie si Standart fait parti de la liste des groupes de l'utilisateur connecter.
                    if 'Standard' in online_user_group:
                        if form.is_valid():
                            username = request.POST.get('username')
                            password = request.POST.get('password')
                            email = request.POST.get('email')
                            
                            #On oblige l'utilisateur connecter a remplir tous les champs.
                            if username != '' and password != '' and email != '' and request.POST.get('first_name')!='' and request.POST.get('last_name') !='' and request.POST.get('groupe')!='':
                                try:
                                    user= User.objects.create_user(username, email,password)
                                except IntegrityError:
                                    ctx.update({'error':ugettext("the user name already exists")})
                                    return render_to_response('add_user.html',ctx)
                                    
                                user.is_staff = request.POST.get('is_staff')
                                user.is_active = request.POST.get('actif')
                                
                                if user.is_active:
                                    user.first_name = request.POST.get('first_name')
                                    user.last_name = request.POST.get('last_name')
                                    user.is_staff = True
                                    user.is_active = True
                                    for group in request.POST.getlist('groupe'):
                                        user.groups.add(Group.objects.get(id=group))
                                    user.save()
                                    
                                else:
                                    user.first_name = request.POST.get('first_name')
                                    user.last_name = request.POST.get('last_name')
                                    user.is_staff = False
                                    user.is_active = False
                                    for group in request.POST.getlist('groupe'):
                                        user.groups.add(Group.objects.get(id=group))
                                    user.save()
                                return HttpResponseRedirect(reverse('administration'))
                                
                        return render_to_response('add_user.html',ctx)
                    
                    #On verifie si Stock-Admin est dans la liste des groupes de l'utilisateur connecter et 
                    #si le groupe selectionner est Stock-Admin ou Stock-Reporter
                    elif 'Stock-Admin' in online_user_group and created_group[0] in ['Stock-Reporter','Stock-Admin']:
                        if form.is_valid():
                            username = request.POST.get('username')
                            password = request.POST.get('password')
                            email = request.POST.get('email')
                            
                            #On oblige l'utilisateur connecter à remplir tous les champs.
                            if username != '' and password != '' and email != '' and request.POST.get('first_name')!='' and request.POST.get('last_name') !='' and request.POST.get('groupe')!='':
                                try:
                                    user= User.objects.create_user(username, email,password)
                                except IntegrityError:
                                    ctx.update({'error':ugettext("the user name already exists")})
                                    return render_to_response('add_user.html',ctx)
                                    
                                user.is_staff = request.POST.get('is_staff')
                                user.is_active = request.POST.get('actif')
                                
                                if user.is_active:
                                    user.first_name = request.POST.get('first_name')
                                    user.last_name = request.POST.get('last_name')
                                    user.is_staff = True
                                    user.is_active = True
                                    for group in request.POST.getlist('groupe'):
                                        user.groups.add(Group.objects.get(id=group))
                                    user.save()
                                else:
                                    user.first_name = request.POST.get('first_name')
                                    user.last_name = request.POST.get('last_name')
                                    user.is_staff = False
                                    user.is_active = False
                                    for group in request.POST.getlist('groupe'):
                                        user.groups.add(Group.objects.get(id=group))
                                    user.save()
                                return HttpResponseRedirect(reverse('comfirm_user'))
                                
                        return render_to_response('add_user.html',ctx)
                     
                    #On verifie si Census-Admin est dans la liste des groupes de l'utilisateur connecter et 
                    #si le groupe selectionner est Census-Admin ou Census-Reporter   
                    elif 'Census-Admin' in online_user_group and created_group[0] in ['Census-Reporter','Census-Admin']:
                        if form.is_valid():
                            username = request.POST.get('username')
                            password = request.POST.get('password')
                            email = request.POST.get('email')
                            
                            #On oblige l'utilisateur connecter à remplir tous les champs.
                            if username != '' and password != '' and email != '' and request.POST.get('first_name')!='' and request.POST.get('last_name') !='' and request.POST.get('groupe')!='':
                                
                                try:
                                    user= User.objects.create_user(username, email,password)
                                except IntegrityError:
                                    ctx.update({'error':ugettext("the user name already exists")})
                                    return render_to_response('add_user.html',ctx)
                                    
                                user.is_staff = request.POST.get('is_staff')
                                user.is_active = request.POST.get('actif')
                                
                                if user.is_active:
                                    user.first_name = request.POST.get('first_name')
                                    user.last_name = request.POST.get('last_name')
                                    user.is_staff = True
                                    user.is_active = True
                                    for group in request.POST.getlist('groupe'):
                                        user.groups.add(Group.objects.get(id=group))
                                    user.save()
                                else:
                                    user.first_name = request.POST.get('first_name')
                                    user.last_name = request.POST.get('last_name')
                                    user.is_staff = False
                                    user.is_active = False
                                    for group in request.POST.getlist('groupe'):
                                        user.groups.add(Group.objects.get(id=group))
                                    user.save()
                                return HttpResponseRedirect(reverse('comfirm_user'))
                        return render_to_response('add_user.html',ctx)
                     
                    #On verifie si Stock-Admin est dans la liste des groupes de l'utilisateur connecter.
                    if 'Stock-Admin' in online_user_group:
                        ctx.update({'error1': ugettext("you can add a user Stock-Admin or Stock-Reporter")})
                    #On verifie si Census-Admin est dans la liste des groupes de l'utilisateur connecter.
                    elif 'Census-Admin' in online_user_group:
                        ctx.update({'error1': ugettext("you can add a user Census-Admin or Census-Reporter")})
                    
                    return render_to_response('add_user.html',ctx)
                except IndexError:
                    ctx.update({'error1': ugettext("Shosse at least one group")})
                    return render_to_response('add_user.html',ctx)
                    
    try: 
        return render_to_response('add_user.html',ctx)
    except UnboundLocalError:
        return render_to_response('page_right.html')

def modif_groupe(request,*args, **kwargs):
    """ Permet a l'administrateur de gerer le groupe de ses utilisateurs """
    
    users = User.objects.all() 
    
    group_users =''
    
    try :
        # on recupere le groupe de l'utilisateur connecté
        group_users = request.user.groups.values_list()
    except IndexError:
        pass
        
    #on cree l'url de chaque utilisateur
    for user in users:
        user.url = reverse('administration', args=[user.id])
        
    for group_user in group_users:
        # on verifie si l'utilisateur fait partie de ces groupes
        if group_user[1] in  ['Stock-Admin','Census-Admin', 'Standard']:    
            stock1 = stock2 = census1 = census2 = ""
            id_user = kwargs["num"]  
            #On recupere l'utilisateur dont l'id est egal à id_user
            util= User.objects.get(id = id_user)
            ctx={'util':util, "user": request.user}
            #on cree un dictionnaire avec les informations de l'utilisateur recuperer
            dict={'username':util.username, 'password': util.password, 'last_name': util.last_name, 'first_name': util.first_name, 'email': util.email}
            #On charge le formulaire de modification avec le dictionnaire cree
            form = ModifAdminForm(dict)
            ctx.update({'form':form})
            #On recupere tous les groupes de l'utilisateur qu'on veut modifier
            groupes=util.groups.all()
            
            for groupe in groupes:
                #~ #On verifie si un des groupes de l'utilisateur correspond à Stock-Reporter
                #~ if groupe.name in ['Stock-Reporter']:
                    #~ #On cree une variable de type boolean pour le faire passer dans le context en vue d'etre utiliser dans le html.
                    #~ cocher_stock_report = True
                    #~ ctx.update({'cocher_stock_report':cocher_stock_report})
                #~ #On verifie si un des groupes de l'utilisateur correspond à 'Stock-Admin'
                #~ if groupe.name in ['Stock-Admin']:
                    #~ #On cree une variable de type boolean pour le faire passer dans le context en vue d'etre utiliser dans le html.
                    #~ cocher_stock_admin = True
                    #~ ctx.update({'cocher_stock_admin':cocher_stock_admin})
                #On verifie si un des groupes de l'utilisateur correspond à Census-Reporter   
                if groupe.name in ['Census-Reporter']:
                    #On cree une variable de type boolean pour le faire passer dans le context en vue d'etre utiliser dans le html.
                    cocher_census_report = True
                    ctx.update({'cocher_census_report':cocher_census_report})
                #On verifie si un des groupes de l'utilisateur correspond à Census-Reporter
                if groupe.name in ['Census-Admin']:
                    #On cree une variable de type boolean pour le faire passer dans le context en vue d'etre utiliser dans le html.
                    cocher_census_admin = True
                    ctx.update({'cocher_census_admin':cocher_census_admin})  
                    
                 #On verifie si un des groupes de l'utilisateur correspond à Visiteur
                if groupe.name in ['Guest']:
                    #On cree une variable de type boolean pour le faire passer dans le context en vue d'etre utiliser dans le html.
                    cocher_visiteur = True
                    ctx.update({'cocher_visiteur':cocher_visiteur})  
                
                #~ #On verifie si un des groupes de l'utilisateur correspond à Stock_Data_Entry
                #~ if groupe.name in ['Stock_Data_Entry']:
                    #~ #On cree une variable de type boolean pour le faire passer dans le context en vue d'etre utiliser dans le html.
                    #~ cocher_stock_data_entry = True
                    #~ ctx.update({'cocher_stock_data_entry':cocher_stock_data_entry})  
                    
                #On verifie si un des groupes de l'utilisateur correspond à Census_Data_Entry
                if groupe.name in ['Census_Data_Entry']:
                    #On cree une variable de type boolean pour le faire passer dans le context en vue d'etre utiliser dans le html.
                    cocher_census_data_entry = True
                    ctx.update({'cocher_census_data_entry':cocher_census_data_entry})  
                    
            if request.method == 'POST':
                #On charge le formulaire avec les donnees de la requette POST.
                form = ModifAdminForm(request.POST)
                
                if form.is_valid():
                    util.last_name = request.POST['last_name']
                    util.first_name = request.POST['first_name']
                    util.email = request.POST['email']
                    util.save()
                    
                #~ try:
                    #~ #On verifie si le groupe stock_reporter est cocher
                    #~ if request.POST['stock_reporter']=='on':
                        #~ util.groups.add(Group.objects.get(name = 'Stock-Reporter'))
                #~ except MultiValueDictKeyError:
                    #~ # Si le groupe n'est pas cocher au moment de l'enregistrement, il est enlevé.
                    #~ util.groups.remove(Group.objects.get(name = 'Stock-Reporter'))
                    #~ 
                #~ try:
                    #~ #On verifie si le groupe stock_admin est cocher
                    #~ if request.POST['stock_admin']=='on':
                        #~ util.groups.add(Group.objects.get(name = 'Stock-Admin'))
                #~ except MultiValueDictKeyError:
                    #~ # Si le groupe n'est pas cocher au moment de l'enregistrement, il est enlevé.
                    #~ util.groups.remove(Group.objects.get(name = 'Stock-Admin'))
                 
                try:
                    #On verifie si le groupe census_reporter est cocher
                    if request.POST['census_reporter']=='on':
                        util.groups.add(Group.objects.get(name = 'Census-Reporter'))
                except MultiValueDictKeyError:
                    # Si le groupe n'est pas cocher au moment de l'enregistrement, il est enlevé.
                    util.groups.remove(Group.objects.get(name = 'Census-Reporter'))
                 
                try:
                    #On verifie si le groupe census_admin est cocher
                    if request.POST['census_admin']=='on':
                        util.groups.add(Group.objects.get(name = 'Census-Admin'))
                except MultiValueDictKeyError:
                    # Si le groupe n'est pas cocher au moment de l'enregistrement, il est enlevé.
                    util.groups.remove(Group.objects.get(name = 'Census-Admin'))
                    
                try:
                    #On verifie si le groupe visiteur est cocher
                    if request.POST['visiteur']=='on':
                        util.groups.add(Group.objects.get(name = 'Guest'))
                except MultiValueDictKeyError:
                    # Si le groupe n'est pas cocher au moment de l'enregistrement, il est enlevé.
                    util.groups.remove(Group.objects.get(name = 'Guest'))
                    
                #~ try:
                    #~ #On verifie si le groupe Stock_Data_Entry est cocher
                    #~ if request.POST['stock_data_entry']=='on':
                        #~ util.groups.add(Group.objects.get(name = 'Stock_Data_Entry'))
                #~ except MultiValueDictKeyError:
                    #~ # Si le groupe n'est pas cocher au moment de l'enregistrement, il est enlevé.
                    #~ util.groups.remove(Group.objects.get(name = 'Stock_Data_Entry'))
                    
                try:
                    #On verifie si le groupe Stock_Data_Entry est cocher
                    if request.POST['census_data_entry']=='on':
                        util.groups.add(Group.objects.get(name = 'Census_Data_Entry'))
                except MultiValueDictKeyError:
                    # Si le groupe n'est pas cocher au moment de l'enregistrement, il est enlevé.
                    util.groups.remove(Group.objects.get(name = 'Census_Data_Entry'))
                    
                return HttpResponseRedirect(reverse('administration'))
                
        try: 
            #on charge la page modif_group.html
            return render_to_response('modif_group.html',ctx)
        except UnboundLocalError:
            #on cherga la page d'erreur
            return render_to_response('page_right.html')
   
    #on charge la page modif_group.html
    return render_to_response('modif_group.html',ctx)

def codification (request):
    #recuperer tout les classes
    code=Place.objects.all()
    #recuperer le code des villages et leurs noms
    code_place = code.values("code_place","name")
    
    #recuperer tout les produits
    codes=Product.objects.all()
    #recuperer tout les codes des produits et leurs noms
    code_product = codes.values("code_product","name")

    ctx={'code_place':code_place,'code_product':code_product,"user": request.user}
   
    return render_to_response('django_stock/code.html', ctx)

def stock_max(request,*args, **kwargs):
    maxi=Maximal.objects.all()
    for max in maxi:
        max.url=reverse('modification_max',args=[max.id])

    ctx={'stockmaxi':maxi,"user": request.user}
    return render_to_response('django_stock/stockmaxi.html',ctx)
    
def modif_stock_max(request,*args, **kwargs):
    id_maxi= kwargs["num"]
    maxi = Maximal.objects.get(id=id_maxi)
    dict ={}
    dict = {'product':maxi.product,'place':maxi.place,'stock_maximal':maxi.stock_maximal,'stock_day':maxi.stock_day}
    form =StockMaxi(dict)
 
    if request.method=='POST':
        form = StockMaxi(request.POST)
        # on verifie le formulaire
        if form.is_valid():
            maxi.stock_maximal = float(request.POST['stock_maximal'])
            maxi.stock_day = float(request.POST['stock_day'])
            maxi.save()
            return HttpResponseRedirect(reverse('stock_maxi'))
    try:
        return render_to_response('django_stock/modification_stock_max.html',{'form':form, 'dict': dict,"user": request.user})
    except UnboundLocalError:
            return render_to_response('page_right.html')    

    #~ if request.method == 'POST':
        #~ form = StockMaxi(request.POST)
    
    return render_to_response('django_stock/modification_stock_max.html',{'form':form,"user": request.user})

def report_pdf(request):
    form = report_pdfForm()
    
    reportqs,date_debut,date_fin="","",""
    ctx = {"user": request.user}
    if request.method == 'POST':
        try:
            date_debut = request.POST['date_debut']
            date_fin = request.POST['date_fin']
            day,month,year= date_debut.split('-')
            date_de = year + '-' + month + '-' + day
            if date_fin=="":
                d=date.today()
                date_fi= str(d.year)+'-'+str(d.month)+'-'+str(d.day)
                date_fin=str(d.day)+'-'+str(d.month)+'-'+str(d.year)
            else:
                day,month,year= date_fin.split('-')
                date_fi = year + '-' + month + '-' + day
            reportqs = Report.objects.filter(date__gte = date_de ,date__lte =date_fi).values('place__name',
                                                                                            'product__name', 'place__id',
                                                                                            'product__id')\
                                                                                            .annotate(Sum('incomming'), 
                                                                                                    Sum('consumption'))
        except ValueError:
            pass
        for ret in reportqs:
            ret['remaining']=ret['incomming__sum']-ret['consumption__sum']
            
        ctx.update({'form':form,"date_debut": date_debut,"date_fin": date_fin,'liste_dic':reportqs})
        
        if not reportqs:
            ctx.update({'form':form,'in_empty_case': ugettext(u" This report contains no period")})
            
        return render_to_response('django_stock/report_pdf_stock.html',ctx)
    else :

        ctx.update({'form':form,'in_empty_case': ugettext(" Select a period to view reports")})
            
    return render_to_response('django_stock/report_pdf_stock.html',ctx)

def evolution(request,*args, **kwargs):
    id_report = int(kwargs["id"])
    year = int(kwargs["year"])
    duration = kwargs["duration"]
    liste=[]
    moyenne_temps=[]
    listes=[]
    increment_rapport=0
    user_username= request.user 
    if not duration :
        #recuperation de village=ecole sortis et id_village
        for month_number in range(1,13):
            rapport=Report.objects.filter(place__id=id_report,date__year=year,date__month=month_number)\
                          .values("place__name", "place__id")\
                          .annotate(consumption=Sum("consumption"))
            # compte le nbre de rapport par ans
            compt_rapport=Report.objects.all().filter(place__id=id_report,date__year=year,date__month=month_number).count()
            #recuperation les entrées, denrées, sortis a une date et les stocks restant par village=ecole
            filtre_anterieur = Report.objects.all().filter(place__id=id_report,date__year=year,date__month=month_number)
            
            for dates in filtre_anterieur:
                #recuperation du premier rapport et ecole 
                rapport_date=dates.date
                ecole=dates.place
                break
                #recuperation de la moyenne le mois l'école et le nombre de mois
            for moyen_rapport in rapport:
                moyenne=moyen_rapport['consumption']/compt_rapport
                month1= format_date(rapport_date ,"MMMM")
                liste.append([month1,moyenne,ecole,month_number])
        #recuperation le mois la moyenne l'école et le nombre de mois
        while increment_rapport < len(liste):
            moy_ecol_mois=liste[increment_rapport]
            mois,Moyenne,ecole,month_numb=moy_ecol_mois[0],moy_ecol_mois[1],moy_ecol_mois[2],moy_ecol_mois[3]
            increment_rapport=increment_rapport+1
            moyenne_temps.append({'Moyenne':Moyenne,'mois':mois})       
            listes.append([month_numb,Moyenne])
        
    if duration =='month':
        duration_number = int(kwargs["duration_number"])
        week ='week'
        week_numbers = date(year,duration_number,1).isocalendar()[1]
        for e in range(1,7):
            reports = Report.get_reports_filtered_by_duration(year,
                                                          week, 
                                                          week_numbers)
            
            weeks='week'+ str(week_numbers)
            #recuperation de village=ecole sortis et id_village
            rapport=reports.filter(place__id=id_report)\
                     .values("place__name", "place__id")\
                     .annotate(consumption=Sum("consumption"))
            # compte le nbre de rapport par mois        
            compt_rapport=reports.filter(place__id=id_report).count()
            
            for moyen_rapport in rapport:
                #recuperation du premier rapport et ecole 
                moyenne=moyen_rapport['consumption']/compt_rapport
                ecole=moyen_rapport["place__name"]
                #recuperation de la moyenne le week-end l'école et le nombre de week-end
                liste.append([weeks,moyenne,ecole,week_numbers])
            
            #recuperation du nombre de week-end
            week_numbers = week_numbers+1
        #recuperation le mois la moyenne l'école et le nombre de week-end    
        while increment_rapport < len(liste):
            moy_ecol_week=liste[increment_rapport]
            weeks,Moyenne,ecole,week_numb=moy_ecol_week[0],moy_ecol_week[1],moy_ecol_week[2],moy_ecol_week[3]
            increment_rapport=increment_rapport+1
            moyenne_temps.append({'weeks':weeks,'Moyenne':Moyenne})
            listes.append([week_numb,Moyenne])
        
    if duration =='week':
        try:
            duration_number = int(kwargs["duration_number"])
            date_du_p = get_week_boundaries(year, duration_number)[0]
            premier_jour_semaine=date(date_du_p.year,date_du_p.month,date_du_p.day)
            
            for nb_jour in range(7):
                #recuperation des 7 jour de la semaine
                premier_jour_semaine=date(date_du_p.year,date_du_p.month,date_du_p.day+nb_jour)
                #recuperation les entrées, denrées, sortis a une date et les stocks restant par village
                rapport=Report.get_reports_filtered_by_duration(year, 
                                                     duration, 
                                                     duration_number)
                
                #recuperation de village=ecole sortis et id_village                                     
                report = rapport.filter(place__id = id_report,date=premier_jour_semaine)\
                                 .values("place__name", "place__id")\
                                 .annotate(consumption=Sum("consumption"))
                # compte le nbre de rapport par semaine
                compt_rapport = rapport.filter(place__id = id_report,date=premier_jour_semaine).count()
                #recuperation les entrées, denrées, sortis a une date et les stocks restant par village
                filtre_anterieur = rapport.filter(place__id = id_report,date=premier_jour_semaine)
                
                for dates in filtre_anterieur:
                   jours=dates.date.strftime('%A')
                   ecole=dates.place
                   break
                for moyen_rapport in report:
                    moyenne=moyen_rapport['consumption']/compt_rapport
                    #recuperation de la moyenne le jour l'école et la date du jour
                    liste.append([jours,moyenne,ecole,premier_jour_semaine.day])
             #recuperation le jour la moyenne l'école et la date du jour
            while increment_rapport < len(liste):
                moy_ecol_day=liste[increment_rapport]
                day,Moyenne,ecole,name_jour=moy_ecol_day[0],moy_ecol_day[1],moy_ecol_day[2],moy_ecol_day[3]
                jour=day
                increment_rapport=increment_rapport+1
                moyenne_temps.append({'jours':jour,'Moyenne':Moyenne})
                listes.append([name_jour,Moyenne])
                
        except ValueError:
            ctx={}
    
    ctx= locals()

         
    return render_to_response('django_stock/evolution_stock.html', ctx)       
