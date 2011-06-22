#!/usr/bin/env python
# -*- coding= UTF-8 -*-
import operator
import csv

from models import * 
from django_census.form_ import CensusReportForm, ModificationForm, PrevisionForm, report_pdfForm
from django.db.models import Avg, Sum, Q
from lib.tools import extract_date_info_from_url
from django.shortcuts import render_to_response,HttpResponseRedirect, redirect
from django.core.paginator import Paginator, EmptyPage
from django.core.urlresolvers import reverse
from django.template.defaultfilters import slugify
from django.contrib.auth import authenticate, login as django_login, logout as django_logout
from django.contrib.auth.decorators import login_required
from form_ import LoginForm_
from django.http import Http404
from django.http import HttpResponse

from lib.tools import *
from datetime import datetime, timedelta

from django.utils.translation import ugettext, ugettext_lazy as _
from django.core.mail import send_mail

def my_custom_404_view():
    
    return render_to_response('django_stock/404.html')
    
@login_required
def dashboard(request):
    """
    Afficher un résumé de la situation actuelle pour le recencement
    des élèves et de professeurs.
    """
    
    # Récupération des données des quatre tableaux récapitulant l'absence des
    # élèves et des enseignants hier et la semaine derniere
    # recuperation de la date et du numero de semaine actuelles
    today = datetime.today()
    delta = timedelta(1)
    year, week_number, week_day = today.isocalendar()
    
    # recuperation de la date d'hier et de celle du premier et du dernier
    # jour de la semaine derniere
    yesterday = today - delta
    previous_week = week_number-1
    last_week_boundaries = get_week_boundaries(year,previous_week)
    
    # On filtre les rapports par ces dates
    yesterday_queryset = Report.objects.filter(date=yesterday)[:5]
    
    last_weeks_queryset = Report.objects.filter(date__gte=last_week_boundaries[0], 
                                                date__lte=last_week_boundaries[1])[:5]          
    
    # on recupere les plus grosses absences pour ces dates
    yesterdays_students_abs_rate, yesterdays_teachers_abs_rate = Report.get_most_important_abs_rates(yesterday_queryset)
    lasts_week_students_abs_rate, lasts_week_teachers_abs_rate = Report.get_most_important_abs_rates(last_weeks_queryset)
    
    
    warning_report = Report.objects.filter(warning=True).order_by('-date')[:5]
    for report in warning_report:
        report.s_day= SchoolClass.objects.get(id=report.school_class.id)
    
    
    for report in warning_report:
        if (report.boys_absentees + report.girls_absentees) > report.s_day.people_missing_day:
            report.sub_census_p = (report.boys_absentees + report.girls_absentees)-report.s_day.people_missing_day
            report.eleve = True
            
        elif report.teacher_absentees >= report.s_day.teacher_missing_day:
            report.sub_census_t = report.teacher_absentees - report.s_day.teacher_missing_day
            report.prof = True
    
    
    ctx = {"yesterdays_teachers_abs_rate": yesterdays_teachers_abs_rate,
         "yesterdays_students_abs_rate": yesterdays_students_abs_rate,
         "lasts_week_students_abs_rate": lasts_week_students_abs_rate,
         "lasts_week_teachers_abs_rate": lasts_week_teachers_abs_rate,"user":request.user,
         "warning_report":warning_report
          }
    
    return render_to_response('django_census/dashboard.html', ctx)


def global_report(request, *args, **kwargs):                            
    """
        Affiche l'état général de l'absenteisme par village.
    """
    
    # on recupere les rapports filtres pour la date demandee
    year, duration, duration_number = extract_date_info_from_url(kwargs)
    village_reports = Report.get_reports_filtered_by_duration(year, 
                                                              duration, 
                                                              duration_number)\
                                                              .values("school_class__school__village__name",
                                                              "school_class__school__village__id")
                                                       
   
    # TODO : Transformer cette fonction en middleware ou context processor
    # car ça devient gigantesque
    previous_date_url, \
    todays_date_url, \
    next_date_url, \
    previous_date, \
    current_date, \
    next_date, \
    todays_date, \
    todays_date_is_before, \
    todays_date_is_after = get_time_pagination(request,year, duration,
                                               duration_number, "census-all")
    week_date_url, \
    month_date_url, \
    year_date_url = get_duration_pagination(year, duration,
                                            duration_number, "census-all")
               
    # on calcule les absences dans tous ces rapports
    village_abs_sum = village_reports.values("school_class__school__village__name",
                                             "school_class__school__village__id")\
                                    .annotate(boys_absentees=Sum('boys_absentees'),
                                              girls_absentees=Sum('girls_absentees'),
                                              teacher_absentees=Sum('teacher_absentees'))
    villages_abs = []
    villages_with_activities = set()
    
    rapport_f=Report.objects.filter(date__year= year)
    
    for village_abs in village_abs_sum:
        total_count_boys,total_abs_girls,total_abs_teachers,total_count_boys,total_count_girls,total_count_teachers=0,0,0,0,0,0

        village_id = village_abs['school_class__school__village__id']
        
        # Todo le de rapport doit etre par an
        
        # Calcul du nombre de jours
        filter_nb_jr=rapport_f.filter(school_class__school__village__id= village_id)
        nb_jr =len (filter_nb_jr)

        # on recupere le nombre d'eleves et de profs total
        # pour toutes les classes de chaque village
        attendees_count = SchoolClass.objects\
                        .filter(school__village__id=village_id)\
                        .values("school__village__id")\
                        .annotate(boys_count=Sum("boys_count"),
                                  girls_count=Sum("girls_count"), 
                                  teachers_count=Sum("teachers_count")).get()

        # on met a jour le dictionnaire qui contient toutes les informations qu'on va 
        # passer au template
        village_abs["village_name"] = village_abs['school_class__school__village__name']     
        village_abs["village_id"] = village_id
        village_abs.update(attendees_count)
        
        # on fait les totaux pour tous les villages
        total_abs_boys = village_abs["boys_absentees"]
        total_abs_girls = village_abs["girls_absentees"]
        total_abs_teachers = village_abs["teacher_absentees"]
              
        total_count_boys = attendees_count["boys_count"]
        total_count_girls =  attendees_count["girls_count"]
        total_count_teachers = attendees_count["teachers_count"]

        village_abs["moy_abs_boys"] = (total_abs_boys * 100)/(total_count_boys * nb_jr)
        village_abs["moy_abs_girls"] = (total_abs_girls * 100)/(total_count_girls * nb_jr)
        village_abs["moy_abs_teachers"] = (total_abs_teachers * 100)/(total_count_teachers * nb_jr)
        village_abs["total_abs_boys"] = total_abs_boys
        village_abs["total_abs_girls"] = total_abs_girls
        village_abs["total_abs_teachers"] = total_abs_teachers
        village_abs["nb_jr"] = nb_jr        
        villages_abs.append(village_abs)
    
        # on met a jour un set contenant la liste de tous les villages
        # qui possedent des rapports pour cette date
        villages_with_activities.add(village_abs['school_class__school__village__name'])
     
    ctx = {"villages_abs": villages_abs,"user":request.user}
   
    if not villages_with_activities:
        ctx.update({"in_empty_case": ugettext("No appeal has been made")})

    else:
        # on liste les village sans rapports pour cette date
        village_whithout_activities = []
        
        for village in Village.objects.all():
            if village.name not in villages_with_activities:
                village_whithout_activities.append(village.name)
     
    ctx.update(locals())
    
    return render_to_response('django_census/global_report.html', ctx)
    
    
def global_report_census_csv(request, *args, **kwargs):

    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment;filename=global_report_census_csv.csv'
    
    # Create the CSV writer using the HttpResponse as the "file"
    writer = csv.writer(response)
    writer.writerow([ugettext('Places').encode('utf-8'),ugettext('Boys').encode('utf-8'),
                    ugettext('Girls').encode('utf-8'),ugettext('Teachers').encode('utf-8'),ugettext('Number of days').encode('utf-8')])
    
    # on recupere les rapports filtres pour la date demandee
    year, duration, duration_number = extract_date_info_from_url(kwargs)
    
    village_reports = Report.get_reports_filtered_by_duration(year, 
                                                              duration, 
                                                              duration_number).order_by('school_class__school__village__name',
                                                              'school_class__school__village__id')
    # on calcule les absences dans tous ces rapports
    village_abs_sum = village_reports.values("school_class__school__village__name",
                                             "school_class__school__village__id")\
                                    .annotate(boys_absentees=Sum('boys_absentees'),
                                              girls_absentees=Sum('girls_absentees'),
                                              teacher_absentees=Sum('teacher_absentees'))
    villages_abs = []

    villages_with_activities = set()
    
    rapport_f=Report.objects.filter(date__year= year)
    
    for village_abs in village_abs_sum:
        total_count_boys,total_abs_girls,total_abs_teachers,total_count_boys,total_count_girls,total_count_teachers=0,0,0,0,0,0

        village_id = village_abs['school_class__school__village__id']
        
        # Todo le de rapport doit etre par an
        
        # Calcul du nombre de jours
        filter_nb_jr=rapport_f.filter(school_class__school__village__id= village_id)
        nb_jr =len (filter_nb_jr)

        # on recupere le nombre d'eleves et de profs total
        # pour toutes les classes de chaque village
        attendees_count = SchoolClass.objects\
                        .filter(school__village__id=village_id)\
                        .values("school__village__id")\
                        .annotate(boys_count=Sum("boys_count"),
                                  girls_count=Sum("girls_count"), 
                                  teachers_count=Sum("teachers_count")).get()

        # on met a jour le dictionnaire qui contient toutes les informations qu'on va 
        # passer au template
        village_abs["village_name"] = village_abs['school_class__school__village__name']     
        village_abs["village_id"] = village_id
        village_abs.update(attendees_count)
        
        # on fait les totaux pour tous les villages
        total_abs_boys = village_abs["boys_absentees"]
        total_abs_girls = village_abs["girls_absentees"]
        total_abs_teachers = village_abs["teacher_absentees"]
        
        total_count_boys = attendees_count["boys_count"]
        total_count_girls =  attendees_count["girls_count"]
        total_count_teachers = attendees_count["teachers_count"]
        
        village_abs["total_abs_boys"] = total_abs_boys
        village_abs["total_abs_girls"] = total_abs_girls
        village_abs["total_abs_teachers"] = total_abs_teachers
        village_abs["nb_jr"] = nb_jr
        villages_abs.append(village_abs)

    # l'export csv 
    # on boucle sur villages_abs pour obtenir toutes les données de la page
    for village_abs in villages_abs:
        writer.writerow([village_abs['village_name'],(village_abs['boys_absentees']),
                        (village_abs['girls_absentees']),(village_abs['teacher_absentees']), (village_abs['nb_jr']),])
                        
    return response 

def by_schools(request, *args, **kwargs):
    """
     Affiche l'absenteisme de toutes les ecoles d'un village par 
     filles, garcons et enseignants
    """
    
    id_ = int(request.POST.get('to_display', 0)) or int(kwargs["id"])
    
    # charger le village dont on veut afficher les ecoles
    # si ce village n'existe pas, mettre une page d'erreur
    try: 
        #village = School.objects.get(id=id_).village
        village = Village.objects.get(id=id_)
        
    except Village.DoesNotExist:
        raise Http404
        
    year, duration, duration_number = extract_date_info_from_url(kwargs)
    
    if request.method == 'POST' :
        return get_redirection("census-by-schools", village,
                                year, duration, duration_number)
        
    navigation_form = get_navigation_form(Village.objects.all(),
                                          ugettext("Change place"),
                                          village,
                                          "census-by-schools",
                                          year, duration, duration_number)
    
    total_count_boys, total_count_girls, total_count_teachers = 0, 0, 0
    total_abs_boys, total_abs_girls, total_abs_teachers = 0, 0, 0
    
    # on recupere les rapports filtres pour la date demandee
    reports = Report.get_reports_filtered_by_duration(year, 
                                                      duration, 
                                                      duration_number)

    previous_date_url, \
    todays_date_url, \
    next_date_url,\
    previous_date,\
    current_date,\
    next_date,\
    todays_date,\
    todays_date_is_before,\
    todays_date_is_after = get_time_pagination(request,year, duration,
                                               duration_number, 
                                               "census-by-schools",
                                               additional_args=(id_, 
                                               slugify(village.name)))
    week_date_url, \
    month_date_url,\
    year_date_url = get_duration_pagination(year, duration,
                                            duration_number, 
                                            "census-by-schools",
                                            additional_args=(id_, 
                                            slugify(village.name)))
 
    filtre_anterieur=Report.objects.filter(school_class__school__village__id=id_ ,date__year=year,date__month=duration_number - 1)
    filtre__anterieurs=Report.objects.filter(school_class__school__village__id=id_ ,date__year=year,date__month=duration_number - 2)                                      
    interdir_pas_donne=filtre_anterieur
    interdir_pas_donne=filtre__anterieurs    
    
    #~ # Nombre de jours 
    #~ filtre_nb_jr = reports.filter(school_class__school__village__id=id_)
    #~ nb_jr = len(filtre_nb_jr)

    # on recupere une liste contenant garcons, filles et enseignants
    # absents pour chaque ecole
    # Absence 
    schools_abs_sum = reports.filter(school_class__school__village__id=id_)\
                             .values("school_class__school__name",
                              "school_class__school_id")\
                             .annotate(boys_absentees=Sum('boys_absentees'),                     
                              girls_absentees=Sum('girls_absentees'),                  
                              teacher_absentees=Sum('teacher_absentees'))         
    
    schools_abs = [] 
    schools_with_activities = set()
    
    rapport_f=Report.objects.filter(date__year= year)
    
    for school_abs in schools_abs_sum:
        
        total_count_boys, total_count_girls, total_count_teachers, total_abs_boys, total_abs_girls, total_abs_teachers = 0, 0, 0, 0, 0, 0
        
        school_id = school_abs['school_class__school_id']
        
       # Calcul du nombre de jours
        filter_nb_jr=rapport_f.filter(school_class__school__id= school_id)
        nb_jr =len (filter_nb_jr)
        
        # on recupere le nombre total d'eleves et de profs 
        # pour toutes les classes de chaque ecole
        # Effectif total 
        attendees_count = SchoolClass.objects\
                        .filter(school__id = school_id)\
                        .values("school__name", "school__id")\
                        .annotate(boys_count = Sum("boys_count"),
                                  girls_count = Sum("girls_count"), 
                                  teachers_count = Sum("teachers_count")).get()
                                  
        # on met a jour le dictionnaire qui contient toutes les informations qu'on va 
        # passer au template
        school_abs["school_name"] = school_abs['school_class__school__name']
        school_abs["school_id"] = school_id
        school_abs.update(attendees_count)
        
        # on fait les totaux pour tous les villages
        total_abs_boys = school_abs["boys_absentees"]
        total_abs_girls = school_abs["girls_absentees"]
        total_abs_teachers = school_abs["teacher_absentees"]
        
        total_count_boys = attendees_count["boys_count"]
        total_count_girls =  attendees_count["girls_count"]
        total_count_teachers = attendees_count["teachers_count"]
        
        school_abs["moy_abs_boys"] = (total_abs_boys * 100)/(total_count_boys * nb_jr)
        school_abs["moy_abs_girls"] = (total_abs_girls * 100)/(total_count_girls * nb_jr)
        school_abs["moy_abs_teachers"] = (total_abs_teachers * 100)/(total_count_teachers * nb_jr)
        school_abs["total_abs_boys"] = total_abs_boys
        school_abs["total_abs_girls"] = total_abs_girls
        school_abs["total_abs_teachers"] = total_abs_teachers
        school_abs["nb_jr"] = nb_jr        
        
        schools_abs.append(school_abs)
        schools_with_activities.add(school_abs["school_name"])

    ctx = {"schools_abs": schools_abs, "village": village,"user":request.user}

    if not schools_with_activities:
        ctx.update({"in_empty_case": ugettext("No appeal has been made")})

    else:
        # lister les ecoles sans releves d'absence
        school_whithout_activities = []
        all_school = School.objects.filter(village__id= village.id)

        for school in all_school:
            if school.name not in schools_with_activities:
                school_whithout_activities.append(school.name)
    
    ctx.update(locals())
                    
    return render_to_response('django_census/by_schools.html', ctx)
    
def by_schools_census_csv(request, *args, **kwargs):
    
    # Create the HttpResponse object with the appropriate CSV header.
    
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment;filename= export_census_by_schools.csv'
    
    # Create the CSV writer using the HttpResponse as the "file"
    
    writer = csv.writer(response)
    writer.writerow([ugettext('Schools').encode('utf-8'),ugettext('Boys').encode('utf-8'),
                        ugettext('Girls').encode('utf-8'),ugettext('Teachers').encode('utf-8'),
                        ugettext('Number of day').encode('utf-8')],)
    
    """
     Affiche l'absenteisme de toutes les ecoles d'un village par 
     filles, garcons et enseignants
    """

    id_ = int(request.POST.get('to_display', 0)) or int(kwargs["id"])
    
    # charger le village dont on veut afficher les ecoles
    # si ce village n'existe pas, mettre une page d'erreur
    try: 
        village = School.objects.get(id=id_).village
    except Village.DoesNotExist:
        raise Http404
        
    year, duration, duration_number = extract_date_info_from_url(kwargs)
        
    if request.method == 'POST' :
        return get_redirection("census-by-schools", village,
                                year, duration, duration_number)
        
    navigation_form = get_navigation_form(Village.objects.all(),
                                          ugettext("Change place"),
                                          village,
                                          "census-by-schools",
                                          year, duration, duration_number)
    
    total_count_boys, total_count_girls, total_count_teachers = 0, 0, 0
    total_abs_boys, total_abs_girls, total_abs_teachers = 0, 0, 0

    # on recupere les rapports filtres pour la date demandee
    reports = Report.get_reports_filtered_by_duration(year, 
                                                      duration, 
                                                      duration_number)

    previous_date_url, \
    todays_date_url, \
    next_date_url,\
    previous_date,\
    current_date,\
    next_date,\
    todays_date,\
    todays_date_is_before,\
    todays_date_is_after = get_time_pagination(request,year, duration,
                                               duration_number, 
                                               "census-by-schools",
                                               additional_args=(id_, 
                                                                slugify(village.name)))
    week_date_url, \
    month_date_url,\
    year_date_url = get_duration_pagination(year, duration,
                                            duration_number, 
                                            "census-by-schools",
                                            additional_args=(id_, 
                                                                slugify(village.name)))

  
    # on recupere une liste contenant garcons, filles et enseignants
    # absents pour chaque ecole
    schools_abs_sum = reports.filter(school_class__school__village__id=id_)\
                             .values("school_class__school__name",
                              "school_class__school_id")\
                             .annotate(boys_absentees=Sum('boys_absentees'),                     
                              girls_absentees=Sum('girls_absentees'),                  
                              teacher_absentees=Sum('teacher_absentees'))         
    
    schools_abs = [] 
    schools_with_activities = set()
    
    rapport_f=Report.objects.filter(date__year= year)
    
    for school_abs in schools_abs_sum:
        
        total_count_boys, total_count_girls, total_count_teachers, total_abs_boys, total_abs_girls, total_abs_teachers = 0, 0, 0, 0, 0, 0
        
        school_id = school_abs['school_class__school_id']
       
       # Calcul du nombre de jours
        filter_nb_jr=rapport_f.filter(school_class__school__id= school_id)
        nb_jr =len (filter_nb_jr)
        
        # on recupere le nombre total d'eleves et de profs 
        # pour toutes les classes de chaque ecole
        # Effectif total 
        attendees_count = SchoolClass.objects\
                        .filter(school__id=school_id)\
                        .values("school__name", "school__id")\
                        .annotate(boys_count=Sum("boys_count"),
                                  girls_count=Sum("girls_count"), 
                                  teachers_count=Sum("teachers_count")).get()
                                  
        # on met a jour le dictionnaire qui contient toutes les informations qu'on va 
        # passer au template
        school_abs["school_name"] = school_abs['school_class__school__name']
        school_abs["school_id"] = school_id
        school_abs.update(attendees_count)
        
        # on fait les totaux pour tous les villages
        total_abs_boys = school_abs["boys_absentees"]
        total_abs_girls = school_abs["girls_absentees"]
        total_abs_teachers = school_abs["teacher_absentees"]
        
        total_count_boys = attendees_count["boys_count"]
        total_count_girls =  attendees_count["girls_count"]
        total_count_teachers = attendees_count["teachers_count"]

        school_abs["moy_abs_boys"] = (total_abs_boys * 100)/(total_count_boys * nb_jr)
        school_abs["moy_abs_girls"] = (total_abs_girls * 100)/(total_count_girls * nb_jr)
        school_abs["moy_abs_teachers"] = (total_abs_teachers * 100)/(total_count_teachers * nb_jr)
        school_abs["total_abs_boys"] = total_abs_boys
        school_abs["total_abs_girls"] = total_abs_girls
        school_abs["total_abs_teachers"] = total_abs_teachers
        school_abs["nb_jr"] = nb_jr        
        
        schools_abs.append(school_abs)
    for report in schools_abs:

        writer.writerow([report['school_name'].encode('utf-8'),
                        report['boys_absentees'], 
                        report["girls_absentees"],
                        report['teacher_absentees'],report['nb_jr']
                        ])
    return response 
    
def by_classes(request, *args, **kwargs):
    """
     Affiche l'absenteisme de toutes les ecoles d'une ecole par 
     filles, garcons et enseignants
    """

    id_ = int(request.POST.get('to_display', 0)) or int(kwargs["id"])

    # charger l'ecole dont on veut afficher les classes
    # si ce village n'existe pas, mettre une page d'erreur
    try: 
        school = School.objects.get(id=id_)
        
    except School.DoesNotExist:
        raise Http404

    year, duration, duration_number = extract_date_info_from_url(kwargs)
    
    if request.method == 'POST' :
        return get_redirection("census-by-classes", school,
                                year, duration, duration_number)

    schools = School.objects.filter(village__id=school.village.id)
    navigation_form = get_navigation_form(schools,
                                          ugettext("Changing schools"),
                                          school,
                                          "census-by-classes",
                                          year, duration, duration_number)
    
    total_count_boys, total_count_girls, total_count_teachers = 0, 0, 0
    total_abs_boys, total_abs_girls, total_abs_teachers = 0, 0, 0
    
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
    todays_date_is_after = get_time_pagination(request,year, duration,
                                                duration_number, 
                                                "census-by-classes",
                                                additional_args=(id_,
                                                                 slugify(school.name)))
    week_date_url,\
    month_date_url,\
    year_date_url = get_duration_pagination(year, duration,
                                            duration_number,
                                            "census-by-classes",
                                            additional_args=(id_,
                                                             slugify(school.name)))
    
    # c'est la moyenne par ecole 
    # on recupere une liste contenant garcons, filles et enseignants
    # absents pour chaque classe
    classes_abs_avg = reports.filter(Q(school_class__school__id=id_), 
                                     Q(school_class__begin_year=year) 
                                     | Q(school_class__end_year=year))\
                              .values('school_class__id')\
                              .annotate(boys_absentees=Avg("boys_absentees"),
                                        girls_absentees=Avg('girls_absentees'),
                                        teacher_absentees=Avg('teacher_absentees'))

    classes_abs = []
    classes_with_activities = set()
    for class_abs in classes_abs_avg:
        
        class_id = class_abs['school_class__id']
        school_class = SchoolClass.objects.get(id=class_id)
        
        # on recupere le nombre total d'eleves et de profs 
        # pour toutes les classes de chaque école
        # et on met a jour le dico qui contient toutes les infos qu'on va 
        # passer au template
        class_abs["class_name"] = school_class.grade
        class_abs["boys_count"] = school_class.boys_count
        class_abs["girls_count"] = school_class.girls_count
        class_abs["teachers_count"] = school_class.teachers_count
        classes_abs.append(class_abs)
        
        # on fait les totaux pour toutes les classes
        total_abs_boys += class_abs["boys_absentees"]
        total_abs_girls += class_abs["girls_absentees"]
        total_abs_teachers += class_abs["teacher_absentees"]
          
        total_count_boys += class_abs["boys_count"]
        total_count_girls += class_abs["girls_count"]
        total_count_teachers += class_abs["teachers_count"]
        
        # on met a jour un set contenant la liste de toutes les classes
        # qui possedent des rapports pour cette date
        classes_with_activities.add(class_id)
        
    ctx = {"classes_abs": classes_abs, "school": school,"user":request.user}
    
    if not classes_with_activities:
        ctx.update({"in_empty_case": ugettext("No appeal has been made")})

    else:
        # lister les classes sans releves d'absence
        classes_whithout_activities = []
        all_classes = SchoolClass.objects.filter(Q(school__id=id_),
                                                 Q(begin_year=year) 
                                                 | Q(end_year=year))

        for school_class in all_classes:
            if school_class.id not in classes_with_activities:
                classes_whithout_activities.append(school_class.grade)
        
    ctx.update(locals())

    return render_to_response('django_census/by_classes.html',ctx)
def by_classes_census_csv(request, *args, **kwargs):
    
    # Create the HttpResponse object with the appropriate CSV header.
    
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment;filename= export_census_by_schools.csv'
    
    # Create the CSV writer using the HttpResponse as the "file"
    
    writer = csv.writer(response)
    writer.writerow([ugettext('Classe').encode('utf-8'),ugettext('Boys absentes').encode('utf-8'),ugettext('Total Boys').encode('utf-8'),ugettext('Girls absentes').encode('utf-8'),ugettext('Total girls').encode('utf-8'),ugettext('Teachers absentes').encode('utf-8'),ugettext('Total teachers')])
    
    """
     Affiche l'absenteisme de toutes les ecoles d'une ecole par 
     filles, garcons et enseignants
    """

    id_ = int(request.POST.get('to_display', 0)) or int(kwargs["id"])

    # charger l'ecole dont on veut afficher les ecoles
    # si ce village n'existe pas, mettre une page d'erreur
    try: 
        school = School.objects.get(id=id_)
    except School.DoesNotExist:
        raise Http404

    year, duration, duration_number = extract_date_info_from_url(kwargs)
    
    if request.method == 'POST' :
        return get_redirection("census-by-classes", school,
                                year, duration, duration_number)

    schools = School.objects.filter(village__id=school.village.id)
    navigation_form = get_navigation_form(schools,
                                          ugettext("Changing schools"),
                                          school,
                                          "census-by-classes",
                                          year, duration, duration_number)
    
    total_count_boys, total_count_girls, total_count_teachers = 0, 0, 0
    total_abs_boys, total_abs_girls, total_abs_teachers = 0, 0, 0
    
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
    todays_date_is_after = get_time_pagination(request,year, duration,
                                                duration_number, 
                                                "census-by-classes",
                                                additional_args=(id_,
                                                                 slugify(school.name)))
    week_date_url,\
    month_date_url,\
    year_date_url = get_duration_pagination(year, duration,
                                            duration_number,
                                            "census-by-classes",
                                            additional_args=(id_,
                                                             slugify(school.name)))
    
    # c'est la moyenne par ecole 
    # on recupere une liste contenant garcons, filles et enseignants
    # absents pour chaque classe
    classes_abs_avg = reports.filter(Q(school_class__school__id=id_), 
                                     Q(school_class__begin_year=year) 
                                     | Q(school_class__end_year=year))\
                              .values('school_class__id')\
                              .annotate(boys_absentees=Avg("boys_absentees"),
                                        girls_absentees=Avg('girls_absentees'),
                                        teacher_absentees=Avg('teacher_absentees'))

    classes_abs = []
    liste=[]
    classes_with_activities = set()
    for class_abs in classes_abs_avg:
        
        class_id = class_abs['school_class__id']
        school_class = SchoolClass.objects.get(id=class_id)
        
        # on recupere le nombre total d'eleves et de profs 
        # pour toutes les classes de chaque classe
        # et on met a jour le dico qui contient toutes les infos qu'on va 
        # passer au template
        class_abs["class_name"] = school_class.grade
        liste.append(school_class.grade)
        class_abs["boys_count"] = school_class.boys_count
       
        class_abs["girls_count"] = school_class.girls_count
        class_abs["teachers_count"] = school_class.teachers_count
        classes_abs.append(class_abs)
        # on fait les totaux pour toutes les classes
        total_abs_boys += class_abs["boys_absentees"]
        total_abs_girls += class_abs["girls_absentees"]
        total_abs_teachers += class_abs["teacher_absentees"]
          
        total_count_boys += class_abs["boys_count"]
        total_count_girls += class_abs["girls_count"]
        total_count_teachers += class_abs["teachers_count"]
         
    
    
    for report in classes_abs :

        writer.writerow([report['class_name'].encode('utf-8'),
                        int((report['boys_absentees'])),int((report['boys_count'])), 
                        int((report["girls_absentees"])),int(( report['girls_count'])),
                        int((report['teacher_absentees'])),int((report['teachers_count']))
                        ])
    writer.writerow(['Total',total_abs_boys,total_count_boys,total_abs_girls,total_count_girls,total_abs_teachers,total_count_teachers])
    return response 
        
def report_management(request, *args, **kwargs):
    alerte= False
    group_users =''
    try :
        group_users = request.user.groups.values_list() 
    except IndexError:
        pass
    # on recupere le numero depuis l'url si le numero 
    # est none on donne 1 par  defaut
    num = kwargs["num"] or 1
    
    # on ordonne par dates recentes les rapports
    reports = Report.objects.order_by('school_class__school__village__name', '-date')
 
    # s'execute si la base est vide
    if not reports.count():
        ctx = {"in_empty_case": ugettext("No appeal has been made")}
        
    # s'execute si il ya des données dans la base
    else: 
       
        # pour mettre 20 elements par page
        paginator = Paginator(reports, 20)
          
        try:
            page = paginator.page(int(num))
        
        #affiche une erreur Http404 si la page est vide  
        except EmptyPage:
            raise Http404
        # si le numero de la page est 2 
        page.is_before_first = (page.number == 2)
        # si le numero de la page est egale au numero de l'avant derniere page
        page.is_before_last = (page.number == paginator.num_pages - 1)
        # on constitue l'url de la page suivante
        page.url_next = reverse('census-report-management', args=[int(num) + 1])
        # on constitue l'url de la page precedente
        page.url_previous= reverse('census-report-management', args=[int(num) - 1])
        # on constitue l'url de la 1ere page
        page.url_first = reverse('census-report-management')
        # on constitue l'url de la derniere page
        page.url_last = reverse('census-report-management', args = [paginator.num_pages])
        # on constitue l'url du formulaire de saisie
                
        for report in page.object_list:
        
            village = report.school_class.school.village
            school = report.school_class.school
        
            # on recupere l'année, le nombre de semaines et le nombre de jours
            year, week_number, day_number = report.date.isocalendar()
            
            # on constitue l'url du lien pointant sur le nom de l'ecole
            report.url_schools = reverse('census-by-schools', 
                                         args=[village.id,
                                               slugify(village.name),
                                               year, 'week', week_number])
                                                                   
            # on constitue l'url du lien pointant sur le nom de la classe
            report.url_classes = reverse('census-by-classes', 
                                          args=[school.id,
                                                slugify(school.name),
                                                year, 'week', week_number])
            # on constitue l'url du lien pointant sur la vue de la confirmation du rapport
            report.url_delete = reverse('census-confirm', args=[report.id])
            # on constitue l'url du lien pointant sur la vue de la modification du rapport
            report.url_modification = reverse("census-modification-report", args=[report.id])
        ctx = {"page":page, "paginator":paginator,"user":request.user, 'lien':'before'}
    for group_user in group_users:
        if group_user[1] in ['Census-Admin','Census-Reporter', 'Standard']:
            # on charge le formulaire
            form = CensusReportForm()
            ctx.update( {'form':form,'valide':'before','save':'before'})
            
            if request.method == 'POST':
                form = CensusReportForm(request.POST)
                if request.POST['date']:
                    if len(request.POST['date'].split('-'))==3:
                        #on recupere et on change le format de la date du formulaire
                        day, month ,year = request.POST['date'].split('-')
                        if len(day)== 4:
                            new_format = day + '-' + month + '-' + year
                        else:
                            new_format = year + '-' + month + '-' + day
                        # on cree un dictionnaire et on le remplie avec les données POST 
                        
                        try:                        
                            report_warning = SchoolClass.objects.filter(id=request.POST['school_class'])
                            if (int(request.POST['boys_absentees'])+ int(request.POST['girls_absentees'])) > report_warning[0].people_missing_day or int(request.POST['teacher_absentees']) >= report_warning[0].teacher_missing_day:
                                dict = {'reporter':request.user.id,'school_class': request.POST['school_class'],'boys_absentees': request.POST['boys_absentees'],'girls_absentees': request.POST['girls_absentees'],
                                    'teacher_absentees': request.POST['teacher_absentees'],'date': new_format, 'warning': True}   
                                alerte =True 
                                    
                            else:
                                dict = {'reporter':request.user.id,'school_class': request.POST['school_class'],'boys_absentees': request.POST['boys_absentees'],'girls_absentees': request.POST['girls_absentees'],
                                    'teacher_absentees': request.POST['teacher_absentees'],'date': new_format, 'warning': False}
                                
                            form = CensusReportForm(dict)
                        
                        
                            # on verifie si le rapport poste existe deja
                            duplicate = Report.objects.filter(school_class = dict['school_class'], boys_absentees = dict['boys_absentees'],girls_absentees = dict['girls_absentees'], teacher_absentees = dict['teacher_absentees'], date = dict['date'] )
                        except ValueError:
                            pass
                        
                    # on verifie le formulaire
                    if form.is_valid():
                        # si il n'ya pas de doublon on execute cela
                        if not duplicate:
                            if alerte:
                                try:
                                    recipients = [user.email for user in Group.objects.get(name='Standard').user_set.all()]
                                except:
                                    recipients = []
                                    
                                send_mail(ugettext('Warning Kodonso'),ugettext("There's a school whose absenteeism is High, please consuter http://rtl.gotdns.org"), 'fanga.computing@gmail.com',  recipients, fail_silently=False)
 
                            form.save()
                            return HttpResponseRedirect(reverse('census-report-management'))
                        #si il ya des doublon on execute cela
                        else:
                            ctx.update({'form':form,'valide':'sent', 'err':ugettext("The report already exists")})
                ctx.update({'form':form,'valide':'sent'})  
        else :
            ctx.update({'save':'sent','error':ugettext('you can not add report ')})
        return render_to_response('django_census/report_management.html', ctx)


def census_report_training(request,*args, **kwargs):
    reports = Report.objects.filter(reporter=request.user.id).order_by('-date')
    alerte= False
    
    for report in reports:
        # on constitue l'url du lien pointant sur la vue de la confirmation du rapport
        report.url_delete_2 = reverse('census-confirm-2', args=[report.id])
        # on constitue l'url du lien pointant sur la vue de la modification du rapport
        report.url_modification = reverse("census-modification-report", args=[report.id])
    form = CensusReportForm()
    if request.method == 'POST':
        form = CensusReportForm(request.POST)
        if request.POST['date']:
            if len(request.POST['date'].split('-'))==3:
                #on recupere et on change le format de la date du formulaire
                day, month ,year = request.POST['date'].split('-')
                if len(day)== 4:
                    new_format = day + '-' + month + '-' + year
                else:
                    new_format = year + '-' + month + '-' + day
                # on cree un dictionnaire et on le remplie avec les données POST 
                
                try:                        
                    report_warning = SchoolClass.objects.filter(id=request.POST['school_class'])
                    if (int(request.POST['boys_absentees'])+ int(request.POST['girls_absentees'])) > report_warning[0].people_missing_day or int(request.POST['teacher_absentees']) >= report_warning[0].teacher_missing_day:
                        dict = {'reporter':request.user.id,'school_class': request.POST['school_class'],'boys_absentees': request.POST['boys_absentees'],'girls_absentees': request.POST['girls_absentees'],
                            'teacher_absentees': request.POST['teacher_absentees'],'date': new_format, 'warning': True}   
                        alerte =True
                            
                    else:
                        dict = {'reporter':request.user.id,'school_class': request.POST['school_class'],'boys_absentees': request.POST['boys_absentees'],'girls_absentees': request.POST['girls_absentees'],
                            'teacher_absentees': request.POST['teacher_absentees'],'date': new_format, 'warning': False}
                    form = CensusReportForm(dict)
                    duplicate = Report.objects.filter(school_class = dict['school_class'], boys_absentees = dict['boys_absentees'],girls_absentees = dict['girls_absentees'], teacher_absentees = dict['teacher_absentees'], date = dict['date'] )
                
                except ValueError:
                    pass       
        if form.is_valid():
            if not duplicate:
                if alerte:
                    try:
                        recipients = [user.email for user in Group.objects.get(name='Standard').user_set.all()]
                    except:
                        recipients = []
                        
                    send_mail(ugettext('Warning Kodonso'), ugettext("There is one school dont high absenteeism, please consuter http://rtl.gotdns.org "), 'fanga.computing@gmail.com',  recipients, fail_silently=False)
 
                form.save()
                return HttpResponseRedirect(reverse('census-report-training'))
            #si il ya des doublon on execute cela
            else:
                return render_to_response('django_census/training_census.html',{'err':ugettext('This report already exists'), 'form':form, 'reports':reports, 'user':request.user})
    return render_to_response('django_census/training_census.html',{'form':form, 'reports':reports, 'user':request.user}) 
    

def delete_confirm(request,*args, **kwargs):
    """
        Confirmation de la suppression d'un rapport
    """
    group_users =''
    try :
        group_users = request.user.groups.values_list() 
    except IndexError:
        pass
    
    try: 
        for group_user in group_users:
            if group_user[1] in ['Census-Admin', 'Standard']:
                # on recupere le numero du rapport depuis l'url
                id_report = kwargs["num"] 
                # supprime le rapport
                report = Report.objects.get(id = id_report)
                report.url_delete = reverse('census-management', args=[report.id])
            return render_to_response('django_census/delete.html',{'report':report})
    except UnboundLocalError:
        return render_to_response('page_right.html')

def delete_confirm_2(request,*args, **kwargs):
    """
        Confirmation de la suppression d'un rapport
    """
    
    # on recupere le numero du rapport depuis l'url
    id_report = kwargs["num"] 
    # supprime le rapport
    report = Report.objects.get(id = id_report)
    report.url_delete_2 = reverse('census-management-2', args=[report.id])
    return render_to_response('django_census/delete_2.html',{'report':report})
    
        
def export_census_manage(request, *args, **kwargs):
    
    # on recupere le numero depuis l'url si le numero 
    # est none on donne 1 par  defaut
    num = kwargs["num"] or 1
    
    # on ordonne par dates recentes les rapports
    reports = Report.objects.order_by('school_class__school__village__name', '-date')
 
    # s'execute si la base est vide
    if not reports.count():
        ctx = {"in_empty_case": ugettext("No appeal has been made")}
        
    # s'execute s'il ya des données dans la base
    else: 
       
        # pour mettre 20 elements par page
        paginator = Paginator(reports, 20)
          
        try:
            page = paginator.page(int(num))
        
        #affiche une erreur Http404 si l'on de passe la page est vide    
        except EmptyPage:
            raise Http404
        # si le numero de la page est 2 
        page.is_before_first = (page.number == 2)
        # si le numero de la page est egale au numero de l'avant derniere page
        page.is_before_last = (page.number == paginator.num_pages - 1)
        # on constitue l'url de la page suivante
        page.url_next = reverse('census-report-management', args=[int(num) + 1])
        # on constitue l'url de la page precedente
        page.url_previous= reverse('census-report-management', args=[int(num) - 1])
        # on constitue l'url de la 1ere page
        page.url_first = reverse('census-report-management')
        # on constitue l'url de la derniere page
        page.url_last = reverse('census-report-management', args = [paginator.num_pages])

        # Create the HttpResponse object with the appropriate CSV header.

        response = HttpResponse(mimetype='text/csv')
        response['Content-Disposition'] = 'attachment;filename=export_census_manage.csv'
    
        # Create the CSV writer using the HttpResponse as the "file"
    
        writer = csv.writer(response)
        writer.writerow([ugettext('Places').encode('utf-8'),ugettext('Schools').encode('utf-8'),ugettext('Classes').encode('utf-8'),ugettext('Boys').encode('utf-8'),ugettext('Girls').encode('utf-8'),ugettext('Teachers').encode('utf-8'),ugettext('Date').encode('utf-8')])
        # on recupere les rapports filtres pour la date demandee
        
        for report in page.object_list:
            writer.writerow([report.school_class.school.village, 
                            report.school_class.school,
                            ( str(report.school_class.grade )+'  '+str(report.school_class.begin_year)+' - '+str(report.school_class.end_year)), 
                            (str(report.boys_absentees) +' / '+str(report.school_class.boys_count)),
                            (str(report.girls_absentees )+' / '+str( report.school_class.girls_count)), 
                            (str(report.teacher_absentees)+' / '+str( report.school_class.teachers_count)), 
                            report.date])
           
        return response 
    
def deleting(request,*args, **kwargs):
    """
        Suppression de rapport
    """
    
    # on recupere le numero du rapport depuis l'url
    id_report = kwargs["num"] 
    # supprime le rapport
    Report.objects.get(id = id_report).delete()
    reports = Report.objects.all()
    for report in reports:
        report.save()
    return HttpResponseRedirect(reverse('census-report-management'))
    
def deleting_2(request,*args, **kwargs):
    """
        Suppression de rapport
    """
    
    # on recupere le numero du rapport depuis l'url
    id_report = kwargs["num"] 
    # supprime le rapport
    Report.objects.get(id = id_report).delete()
    reports = Report.objects.all()
    for report in reports:
        report.save()
    return HttpResponseRedirect(reverse('census-report-training'))

def modification_report(request,*args, **kwargs):
    """
        Modifiction de rapport
    """
    group_users =''
    try :
        group_users = request.user.groups.values_list() 
    except IndexError:
        pass
    
    # on recupere le numero du rapport depuis l'url
    id_report = kwargs["num"] 
    # on recupere ce rapport
    report = Report.objects.get(id = id_report)
    # on cree un dictionnaire et on le remplie
    dict ={}
    dict = {'school_class': report.school_class.id,'boys_absentees': report.boys_absentees,'girls_absentees': report.girls_absentees,
            'teacher_absentees': report.teacher_absentees,'date': report.date}
    for group_user in group_users:
        if group_user[1] in ['Census-Admin', 'Standard']:
            # on passe le dictionnaire au formulaire      
            form = ModificationForm(dict)
    # on verifie le formulaire
    if request.method=='POST':
        form = ModificationForm(request.POST)
        
        if form.is_valid():
            
            max = SchoolClass.objects.filter(id=request.POST['school_class'])
            
            report.boys_absentees = int(request.POST['boys_absentees'])
            report.girls_absentees = int(request.POST['girls_absentees'])
            report.teacher_absentees = int(request.POST['teacher_absentees'])
            report.date = request.POST['date']
           
            
            for m in max:
                if (int(request.POST['boys_absentees'])+ int(request.POST['girls_absentees'])) < max[0].people_missing_day and int(request.POST['teacher_absentees']) <= max[0].teacher_missing_day:
                    report.warning=False
                    report.save()
                    
                elif (int(request.POST['boys_absentees'])+ int(request.POST['girls_absentees'])) > max[0].people_missing_day or int(request.POST['teacher_absentees']) >= max[0].teacher_missing_day:
                    report.warning=True
                    report.save()
            return HttpResponseRedirect(reverse('census-report-management'))
     
    try:
        return render_to_response('django_census/census_modification.html',{'form':form,'user':request.user})
    except UnboundLocalError:
        return render_to_response('page_right.html')       
        

def login(request):
    """
    login est la views qui permet de se connecter
    """
    state = ugettext("Please login ...")
    
    #Initialise username et password à vide
    
    username = password = ''
    """
    On appel la fonction LoginForm() dans le formulaire
    
    """
    
    form = LoginForm_()
   
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
                    
                    return redirect(dashboard)
                    
            else:
                state = ugettext("Your Account is not active, please contact the site admin.")
        else:
            state = ugettext("Your username and / or your password is incorrect.")
    return render_to_response('authente_.html',{'form':form, 'state': state})

def logout(request):
    """ 
    logout est la views qui permet de se deconnecter
    
    """
    django_logout(request)
    return redirect("/")
def codification_census(request):
    #recuperer tout les classes
    classes=SchoolClass.objects.all()
    
    #recupere code classe, code ecole, nom de village, niveau de classe, nom de l'école
    code_class_school_village_grade = classes.values("code_schoolclass",
                                                      "school__code_school",
                                                      "school__name","school__village__name",
                                                      "grade").order_by("school__village__name")
    ctx={'code_class_school_village_grade':code_class_school_village_grade ,"user": request.user}
   
    return render_to_response('django_census/code.html', ctx)
    
def prevision(request):
    """ 
    Calcule de la prévision de stock des écoles par village
    """
    # Calcul du nombre total de garçons et de filles durant l'année scolaire
    effectifs = SchoolClass.objects.values("school__name", "school__village__name", "begin_year").annotate(Sum("boys_count"), Sum("girls_count"))
    
    form = PrevisionForm()
    ctx={}
    prevision=[]
    for effectif in effectifs:
        #calcul de l'effectif total d'une école
        effectif["total_count"] = 0
        effectif['total_count'] = effectif['boys_count__sum'] + effectif['girls_count__sum']
        if request.method == "POST":
            
            try :
                pre= int(request.POST.values()[0])
            except ValueError:
                message= "Veuillez saisir un chiffre"
                ctx={'message':message}
                pre=75
            
            #calcul de la quantité prévisionnelle
            effectif["prevision"] = (pre * effectif['total_count'] *12 * 9)/1000
        else:
            pre=75
            effectif["prevision"] = (pre * effectif['total_count'] *12 * 9)/1000
            message= ""
            ctx={'message':message}
        
        prevision.append(effectif)
    ctx.update({'previsions':prevision, 'form':form, 'prev':pre,"user": request.user})
    
    return render_to_response('django_census/prevision.html', ctx)

def report_pdf(request, *args, **kwargs):
    classes_abs_avg = ""
    date_fi =date_de= ''
    form = report_pdfForm()
    ctx = {"user": request.user}
    if request.method=='POST':
        try:
            date_de = request.POST['date_debut']
            date_fi = request.POST['date_fin']
            day,month,year= date_de.split('-')
            date_debut = year + '-' + month + '-' + day
            if date_fi:
                day,month,year= date_fi.split('-')
                date_fin = year + '-' + month + '-' + day 
            else:
                d = date.today()
                date_fin = str(d.year)+'-'+str(d.month)+'-'+str(d.day)
                date_fi = str(d.day)+'-'+str(d.month)+'-'+str(d.year)
                            
            classes_abs_avg = Report.objects.filter(Q(date__gte= date_debut ,date__lte= date_fin), )\
                                  .values('school_class__school__village__name','school_class__school__name')\
                                  .annotate(boys_absentees_s=Sum("boys_absentees"),
                                            girls_absentees_s=Sum("girls_absentees"),
                                            teacher_absentees_s=Sum("teacher_absentees"),
                                            boys_count=Sum('school_class__boys_count'),
                                            girls_count=Sum('school_class__girls_count'),
                                            teachers_count=Sum('school_class__teachers_count'))
      
            classes_abs= Report.objects.filter(Q(date__gte= date_debut ,date__lte= date_fin), )\
                                      .values('school_class__school__village__name','school_class__school__name','school_class__boys_count','school_class__girls_count','school_class__teachers_count')
            liste =[]
            for list_village in classes_abs_avg:
                if list_village['school_class__school__village__name'] not in liste:
                    liste.append(list_village['school_class__school__village__name'])
            li=[]
            effectif_gar=0
            
            for place in liste:
    
                filtre_village=Report.objects.filter(date__gte= date_debut ,date__lte= date_fin ,school_class__school__village__name=place)\
                                   .values('school_class__school__village__name')\
                                   .annotate(boys_absentees_s=Sum("boys_absentees"),
                                            girls_absentees_s=Sum("girls_absentees"),
                                            teacher_absentees_s=Sum("teacher_absentees"),
                                            boys_count=Sum('school_class__boys_count'),
                                            girls_count=Sum('school_class__girls_count'),
                                            )
                total_report=Report.objects.filter(date__gte= date_debut ,date__lte= date_fin ,school_class__school__village__name=place).count()

                for c in classes_abs_avg:
                    if c['school_class__school__village__name']==place:
                        for sum_absence in filtre_village:
                            
                            total_absence=sum_absence['boys_absentees_s']+sum_absence['girls_absentees_s']+sum_absence['teacher_absentees_s']
                            effectif_total=sum_absence['boys_count']+sum_absence['girls_count']
            
                            moyenne=(total_absence*100)/float((effectif_total*total_report))
                            li.append({'moyenne':moyenne,'village':place,'ecole':c['school_class__school__name'],'boys_absentees':c['boys_absentees_s'],'girls_absentees':c['girls_absentees_s'],'teacher_absentees_s':c['teacher_absentees_s'],'boys_count':c['boys_count'],'girls_count':c['girls_count'],'teachers_count':c['teachers_count']})
                            ctx = {'li':li}
        except ValueError :
            pass
        if not classes_abs_avg:
            ctx.update({'form':form,'in_empty': ugettext (u"This report contains no period")})
        ctx.update({'form':form , 'classes_abs_avg':classes_abs_avg , 'date_de':date_de ,'date_fi':date_fi })
    else:
        ctx.update({'form':form,'in_empty': ugettext(" Select a period to view reports")})
    return render_to_response('django_census/report_pdf.html',ctx)

def evolution (request, *args, **kwargs):
    id_report = int(kwargs["id"])
    year = int(kwargs["year"])
    
    
    duration = kwargs["duration"]
    if duration =='month':
        liste_village_month_moyenne=[]
        duration_number = int(kwargs["duration_number"])
        week ='week'
        #recupere le premier nbre de week
        week_numbers = date(year,duration_number,1).isocalendar()[1]
        
        li=[]
        for e in range(1,7):
            #recuperation du village=école les absences à une date
            reports = Report.get_reports_filtered_by_duration(year,
                                                              week, 
                                                              week_numbers)
            
            weeks='week'+ str(week_numbers)
           #recuperation du village=école les absences sous forme de dictionnaire
            dict_report=reports.filter(school_class__school__village__id=id_report)\
                               .values("school_class__school__village__id",'school_class__school__village__name')\
                               .annotate(boys_absentees=Sum('boys_absentees'),
                               girls_absentees=Sum('girls_absentees'),
                               teacher_absentees=Sum('teacher_absentees'))
            dict_reporttt=reports.filter(school_class__school__village__id=id_report)\
                               .values("school_class__school__village__id",'school_class__school__village__name','school_class__boys_count','school_class__girls_count','school_class__teachers_count')\
                               
            
             # compte le nbre de rapport par mois
            rapp=reports.filter(school_class__school__village__id=id_report).count()
           #recuperation du village=école les absences sous forme de liste
            filtre_anterieur=reports.filter(school_class__school__village__id=id_report)
            effect_gar,effect_fill,effect_tea=0,0,0
            for dates in dict_reporttt:
                effect_gar +=dates['school_class__boys_count'] 
                effect_fill += dates['school_class__girls_count']
                effect_tea +=dates['school_class__teachers_count']
            
            
                
            for trie_rapport in dict_report:
                total_gar=trie_rapport['boys_absentees']
                total_fill= trie_rapport['girls_absentees']
                total_tea= trie_rapport['teacher_absentees']
                
                village_nom = trie_rapport['school_class__school__village__name']
                moyenne=(total_gar *100/(effect_gar*rapp))+(total_fill *100/(effect_fill*rapp))+(total_tea *100/(effect_tea*rapp))
               
                liste_village_month_moyenne.append([village_nom,weeks,moyenne,week_numbers])
                
                
            y=week_numbers
            #recuperation du nbr de week dans une liste
            li.append([y])
            #recuperation du nbre de week en incrementant    
            week_numbers = week_numbers+1
            
        li=[]
        increment_rapport=0
        listes=[]
        while increment_rapport < len(liste_village_month_moyenne):
            s=liste_village_month_moyenne[increment_rapport]
            village,weeks,Moyenne,week_numb=s[0],s[1],s[2],s[3]
            increment_rapport=increment_rapport+1
            li.append({'weeks':weeks,'Moyenne':Moyenne})
            #recuperation du nbre de week et la moyenne dans un liste 
            listes.append([week_numb,Moyenne])
            
    ctx={}
    duration = kwargs["duration"]
    
    
    if duration =='week':
        try:    
            duration_number = int(kwargs["duration_number"])
            date_du_p = get_week_boundaries(year, duration_number)[0]
            c=date(date_du_p.year,date_du_p.month,date_du_p.day)
            liste=[]
            for i in range(7):
                c=date(date_du_p.year,date_du_p.month,date_du_p.day+i)
                rapport=Report.get_reports_filtered_by_duration(year, 
                                                  duration, 
                                                  duration_number)
                 #recuperation du village=école les absences sous forme de dictionnaire
                report = rapport.filter(school_class__school__village__id = id_report,date=c)\
                            .values("school_class__school__village__id",'school_class__school__village__name')\
                            .annotate(boys_absentees=Sum('boys_absentees'),
                               girls_absentees=Sum('girls_absentees'),
                               teacher_absentees=Sum('teacher_absentees'))
                dict_reporttt=rapport.filter(school_class__school__village__id=id_report)\
                                     .values("school_class__school__village__id",'school_class__school__village__name','school_class__boys_count','school_class__girls_count','school_class__teachers_count')\
                
               
                # compte le nbre de rapport par week
                rapp = rapport.filter(school_class__school__village__id = id_report,date=c).count()
                 #recuperation du village=école les absences sous forme de liste a une date
                rapportss = rapport.filter(school_class__school__village__id = id_report,date=c)
                effect_gar,effect_fill,effect_tea=0,0,0
                for dates in dict_reporttt:
                    effect_gar +=dates['school_class__boys_count'] 
                    effect_fill += dates['school_class__girls_count']
                    effect_tea +=dates['school_class__teachers_count']

                for h in rapportss:
                    jours=h.date.strftime('%A')
                
                    break
               
                for trie_rapport in report:
                    total_gar=trie_rapport['boys_absentees']
                    total_fill= trie_rapport['girls_absentees']
                    total_tea= trie_rapport['teacher_absentees']
                    village_nom = trie_rapport['school_class__school__village__name']
                    moyenne=(total_gar *100/(effect_gar*rapp))+(total_fill *100/(effect_fill*rapp))+(total_tea *100/(effect_tea*rapp))
                 
                    
                    liste.append([village_nom,jours,moyenne,c.day])
            
        
            li=[]
            increment_rapport=0
            listes=[]
            while increment_rapport < len(liste):
                s=liste[increment_rapport]
                village,day,Moyenne,num_jour=s[0],s[1],s[2],s[3]
                c=day
                increment_rapport=increment_rapport+1
                #recuperation du nbr de week dans une liste
                li.append({'jours':c,'Moyenne':Moyenne})
                #recuperation du nbre de week et la moyenne dans un liste
                listes.append([num_jour,Moyenne])
            
            ctx={}
        except ValueError:
            ctx={}
        
    
    if not duration:
        liste_village_month_moyenne=[]
        for month_number in range(1,13):
            rapport=Report.objects.filter(school_class__school__village__id=id_report,date__year=year,date__month=month_number)\
                                            .values("school_class__school__village__id",'school_class__school__village__name')\
                                            .annotate(boys_absentees=Sum('boys_absentees'),
                                                  girls_absentees=Sum('girls_absentees'),
                                                  teacher_absentees=Sum('teacher_absentees'))
            
            filtre_anterieur=Report.objects.filter(school_class__school__village__id=id_report ,date__year=year,date__month=month_number)
            for dates in filtre_anterieur:
                rapport_date=dates.date
                effect_gar=dates.school_class.boys_count 
                effect_fill= dates.school_class.girls_count
                effect_tea=dates.school_class.teachers_count
                
                break
                
            rapp=Report.objects.all().filter(school_class__school__village__id=id_report,date__year=year,date__month=month_number).count()
        
            for trie_rapport in rapport:
               
                total_gar=trie_rapport['boys_absentees']
                total_fill= trie_rapport['girls_absentees']
                total_tea= trie_rapport['teacher_absentees']
                village_nom = trie_rapport['school_class__school__village__name']
                moyenne=(total_gar *100/(effect_gar*rapp))+(total_fill *100/(effect_fill*rapp))+(total_tea *100/(effect_tea*rapp))
                id_village = trie_rapport['school_class__school__village__id']
                month1= format_date(rapport_date ,"MMMM")
                liste_village_month_moyenne.append([village_nom,month1,moyenne,month_number])
            li=[]
            increment_rapport=0
            listes=[]
            while increment_rapport < len(liste_village_month_moyenne):
                s=liste_village_month_moyenne[increment_rapport]
                village,mois,Moyenne,month_number=s[0],s[1],s[2],s[3]
                increment_rapport=increment_rapport+1
                li.append({'mois':mois,'Moyenne':Moyenne})
                listes.append([month_number,Moyenne])
        
    ctx=locals()
    ctx.update({'user':request.user })

    return render_to_response('django_census/evolution.html', ctx)
    
