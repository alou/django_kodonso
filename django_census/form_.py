#!/usr/bin/env python
# -*- coding= UTF-8 -*-
from django.contrib.auth.models import Group
from models import *
from django import forms
from django.contrib.admin import widgets as adminwidgets
from django.utils.translation import ugettext, ugettext_lazy as _

class CensusReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = []
        
           
    def clean_boys_absentees(self):
        """
        Vérifie que le nombre de garçons absents rapporté n'est pas 
        supérieur à l'effectif de la classe.
        """
        try:
            absentees = self.cleaned_data['boys_absentees']
            boys_count = self.cleaned_data['school_class'].boys_count
            if absentees > boys_count:
                error = ugettext("Invalid entries: the number of absentees") + "  " + " ( " + str(absentees) + " ) " + ugettext("  is superior  to total number of boys") + "  " + " ( " + str(boys_count) + " ) " + "  " + ugettext("in this class")
              
            
            

                raise forms.ValidationError(error)
                
            if absentees < 0 :
                error = ugettext("Invalid entries: the number of absentees") + " "+ " ( " + str(absentees) +" ) "   + " " +  ugettext("should not be negative")
                raise forms.ValidationError(error)
                
        except UnboundLocalError:
            pass
        except KeyError:
            pass
        
                
        return absentees

   
    def clean_girls_absentees(self):
        """
        Vérifie que le nombre de filles absentes rapporté n'est pas 
        supérieur à l'effectif de la classe.
        """
        try:
            absentees = self.cleaned_data['girls_absentees']
            girls_count = self.cleaned_data['school_class'].girls_count
            if absentees > girls_count:
                
                error = ugettext("Invalid entries: the number of absentees") + " " + " ( " + str(absentees) + " ) " + ugettext("  is superior  to total number of girls  ") + "  "+  " ( "  + str(girls_count) + " ) " + "  " + ugettext("in this class")
                
                    
                raise forms.ValidationError(error)
                
            if absentees < 0 :
                error = ugettext("Invalid entries: the number of absentees") + " "+ " ( " + str(absentees) +" ) "   + " " +  ugettext("should not be negative")
                
                raise forms.ValidationError(error)
                
        except UnboundLocalError:
            pass
        except KeyError:
            pass
        return absentees
        
    
    def clean_teacher_absentees(self):

        """
        Vérifie que le nombre d'enseignants absents rapporté n'est pas 
        supérieur à l'effectif de la classe.
        """
        try:
            absentees = self.cleaned_data['teacher_absentees']
            teachers_count = self.cleaned_data['school_class'].teachers_count
            if absentees > teachers_count:
                error = ugettext("Invalid entries: the number of absentees") + " ( " + str(absentees) +" ) " + ugettext("  is superior  to total number of teachers  ") + "  " + " ( " + str(teachers_count) + " ) " + "  " + ugettext("in this class")
    
 
                raise forms.ValidationError(error)
                
            if absentees < 0 :
                error = ugettext("Invalid entries: the number of absentees") + " "+ " ( " + str(absentees) +" ) "   + " " +  ugettext("should not be negative")
                raise forms.ValidationError(error)
                
        except KeyError:
            pass
        except UnboundLocalError:
            pass
        return absentees
    

class ModificationForm(forms.Form):
    school_class = forms.ChoiceField(label=_(u"Class"), choices=[(school.id , school) for school in SchoolClass.objects.all()])
    boys_absentees = forms.IntegerField(label =_('Boy absent'))
    girls_absentees = forms.IntegerField(label =_('Girl absent'))
    teacher_absentees = forms.IntegerField(label =_("Teacher absent"))
    date = forms.DateField(label =_('Date'))

class LoginForm_(forms.Form):
    username = forms.CharField(max_length=100)
    password = forms.CharField(max_length=100, widget=forms.PasswordInput)
    
class AdminForm(forms.ModelForm):
    class Meta:
        model=Group

class PrevisionForm(forms.Form):
    
    prevision = forms.FloatField(label =_("FAO quota (g)"))

class report_pdfForm(forms.Form):
    date_debut = forms.DateField(label= _("start date"))
    date_fin = forms.DateField(label= _("end date"))
