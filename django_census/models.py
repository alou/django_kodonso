#!/usr/bin/env python
# -*- coding= UTF-8 -*-

import operator
from django.contrib.auth.models import User, Group
from django.db import models
from django import forms
from django.db.models import Avg, Sum
from lib.tools import get_week_boundaries
from django.utils.translation import ugettext, ugettext_lazy as _

from django.utils.translation import gettext_lazy

class Village (models.Model):
    
    name = models.CharField(max_length=200, unique= True,verbose_name=_(u"Name of place"))
    
    def __unicode__(self):
        return u"%s " %( self.name)
 

class School (models.Model):
    
    village = models.ForeignKey(Village, verbose_name=_(u'Places'))
    name = models.CharField(max_length=200, unique= True,verbose_name=_(u"Name of school"))
    code_school = models.CharField(max_length=20, unique = True)
    
    def __unicode__(self):
        return u"%s "%(self.name)


# TODO : ne pas autoriser la mise ajour si les effectifs descendent au dessous
# des absents dans les raports

class SchoolClass(models.Model):
    
    school = models.ForeignKey(School)
    grade = models.CharField(max_length=200,verbose_name= _(u'Class'))
    boys_count = models.IntegerField(max_length=500,verbose_name=_(u"Total boy"))
    girls_count = models.IntegerField(max_length=500,verbose_name=_(u"Total Girl"))
    teachers_count = models.IntegerField(max_length=500,verbose_name=_(u"Total number of teachers"))
    begin_year = models.IntegerField(max_length=4,verbose_name=_(u"Begin year"))
    end_year = models.IntegerField(max_length=4,verbose_name=_(u"end_year"))
    code_schoolclass = models.CharField(max_length=20, unique = True)    
    people_missing_day = models.FloatField(verbose_name=_(u"Daily absences of pupils"))
    teacher_missing_day = models.FloatField(verbose_name=_(u"Daily absences of teachers"))
    def __unicode__(self):
        return u"%s > %s > %s (%s-%s)" %\
                 (self.school.village, 
                  self.school, 
                  self.grade, 
                  self.begin_year, 
                  self.end_year)


class Report(models.Model):
    
    school_class = models.ForeignKey(SchoolClass, verbose_name =_(u'Class'))
    boys_absentees = models.IntegerField(max_length=500,verbose_name=_(u"Boy absent"))
    girls_absentees = models.IntegerField(max_length=200,verbose_name=_(u"Girl absent"))
    teacher_absentees = models.IntegerField(max_length=200,verbose_name=_(u"teacher absent"))
    date = models.DateField()
    warning = models.BooleanField(verbose_name=_(u"Warning"))
    reporter = models.ForeignKey(User,verbose_name=_('Reporter'),related_name="census_report", blank = True)
    
    def __unicode__(self):
        return u"%s (%s) : %s boys / %s girls / %s teachers" %\
                 (self.school_class.school.village,
                  self.date,
                  self.boys_absentees,
                  self.girls_absentees,
                  self.teacher_absentees)
     
     
    @classmethod                                  
    def get_most_important_abs_rates(cls, queryset):
        """
        Revoit deux listes des plus important taux absenteisme dans 
        ce queryset par eleves et par prof.
        """
        
        # TODO : prendre les 10 plus gros taux d'absenteismes
        # Utiliser les clés de annotate pour limiter les transferts nom
        average_abs = queryset.values("school_class__school__name",
                                      "school_class__school__id")\
                              .annotate(Avg('boys_absentees'),                     
                                        Avg('girls_absentees'),                   
                                        Avg('teacher_absentees'))
       
        students_abs_rate = [] 
        teachers_abs_rate = [] 
       
        for school_abs in average_abs:
            
            students_rate = {} 
            teachers_rate = {}
            
            school_name = school_abs['school_class__school__name']
            school_id = school_abs['school_class__school__id']
            
            school_count = SchoolClass.objects\
                                   .filter(school__name=school_name )\
                                   .values("school__name")\
                                   .annotate(Sum("boys_count"),
                                             Sum("girls_count"),
                                             Sum("teachers_count")).get()
              
            students_rate["school_name"] = school_name
            teachers_rate["school_name"] = school_name
            students_rate["school_id"] = school_id
            teachers_rate["school_id"] = school_id
            
            students_rate["students_abs_rate"] = ((school_abs['boys_absentees__avg']
                                                    + school_abs['girls_absentees__avg'])
                                                  / (school_count['boys_count__sum']
                                                    + school_count['girls_count__sum']
                                                  )) * 100
                                            
            teachers_rate["teachers_abs_rate"] = (school_abs['teacher_absentees__avg']
                                                  / (school_count['teachers_count__sum']
                                                  )) * 100
            
            students_abs_rate.append(students_rate)
            teachers_abs_rate.append(teachers_rate)
        
        students_abs_rate.sort(key=operator.itemgetter("students_abs_rate"), 
                                      reverse=True)
        teachers_abs_rate.sort(key=operator.itemgetter("teachers_abs_rate"), 
                                      reverse=True)
         
        return (students_abs_rate, teachers_abs_rate)


    @classmethod
    def get_reports_filtered_by_duration(cls, year, 
                                         duration=None, 
                                         duration_number=None):
        """
            Retourne un queryset de rapports filtre selon la date
            obtenue a travers l'url.
            Cela permet donc d'avoir tous les rapports pour une annee
            et optionnellement pour un mois ou une semaine de cette 
            annee.
        """
    
        reports = Report.objects.filter(date__year=year)
        
        if duration == "month":                                                
            reports = reports.filter(date__month=duration_number)
        
        if duration == "week":
            first_day, last_day = get_week_boundaries(year, 
                                                      duration_number)
            reports = reports.filter(date__gte=first_day, 
                                     date__lte=last_day)
        return reports  
