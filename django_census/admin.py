#!/usr/bin/env python
# -*- coding= UTF-8 -*-

from models import *
from django.contrib import admin
from django.core.exceptions import ValidationError


# TODO : effectuer un strip() sur toutes les saisies textes importants
# avant de sauvegarder, ex : nom de village, grade de classe, nom de produit
# pour eviter que l'utilisateur ne rentre des espaces inutiles

class ReportAdminForm(forms.ModelForm):

    class Meta:
        model = Report
        
    def clean_boys_absentees(self):
        """
        Vérifie que le nombre de garçons absents rapporté n'est pas 
        supérieur à l'effectif de la classe.
        """
       
        absentees = self.cleaned_data['boys_absentees']
        boys_count = self.cleaned_data['school_class'].boys_count
        
        if absentees > boys_count:
            
            error = ugettext("Invalid entries: the number of absentees") + "  " + " ( " + str(absentees) + " ) " + ugettext("  is superior  to total number of boys") + "  " + " ( " + str(boys_count) + " ) " + "  " + ugettext("in this class")
            #~ v=ugettext("Invalid entries: the number of absentees")
            #~ error = v 


            raise forms.ValidationError(error)
        
        return absentees

   
    def clean_girls_absentees(self):
        """
        Vérifie que le nombre de filles absentes rapporté n'est pas 
        supérieur à l'effectif de la classe.
        """
        absentees = self.cleaned_data['girls_absentees']
        girls_count = self.cleaned_data['school_class'].girls_count
        
       
        if absentees > girls_count:
            
            error = ugettext("Invalid entries: the number of absentees") + " " + " ( " + str(absentees) + " ) " + ugettext("  is superior  to total number of girls  ") + "  "+  " ( "  + str(girls_count) + " ) " + "  " + ugettext("in this class")
            
            #~ error = ("""Saisie incorrecte : le nombre d'absents (%s)"""
                     #~ """ est superieur à l'effectif total des filles (%s)"""
                     #~ """ de cette classe """) % (absentees, girls_count)
                    
            raise forms.ValidationError(error)
        
        return absentees
        
    
    def clean_teacher_absentees(self):

        """
        Vérifie que le nombre d'enseignants absents rapporté n'est pas 
        supérieur à l'effectif de la classe.
        """
        absentees = self.cleaned_data['teacher_absentees']
        teachers_count = self.cleaned_data['school_class'].teachers_count
        
       
        if absentees > teachers_count:
            
            error = ugettext("Invalid entries: the number of absentees") + " ( " + str(absentees) +" ) " + ugettext("  is superior  to total number of teachers  ") + "  " + " ( " + str(teachers_count) + " ) " + "  " + ugettext("in this class")
            #~ error = ("""Saisie incorrecte : le nombre d'absents (%s)"""
                     #~ """ est superieur à l'effectif total des teachers (%s)"""
                     #~ """ de cette classe """) % (absentees, teachers_count)
                    
 
            raise forms.ValidationError(error)
        
        return absentees
    


       
class SchoolClassAdminForm(forms.ModelForm):
    class Meta:
        model = SchoolClass    
    def clean_boys_count(self):
       
        boys_count = self.cleaned_data['boys_count']
        school_name = self.cleaned_data['school'].name
        print boys_count
        print school_name

        effectif = []
                
        for eff in Report.objects.all():
            if eff.school_class.school.name == school_name:
                effectif.append(eff.boys_absentees)

        if effectif == []:
            if boys_count < boys_count +1:
                boys_count
            return boys_count
        else:
            if boys_count < max(effectif):
                
                error = ("""Saisie incorrecte : le nombre d'absents maximum(%s)"""
                         """ est superieur à l'effectif total des gaçons (%s)"""
                         """ de cette classe """) % (max(effectif), boys_count)




                raise forms.ValidationError(error)
            
            return max(effectif)
        
    def clean_girls_count(self):
        try:
            girls_count = self.cleaned_data['girls_count']
            school_name = self.cleaned_data['school'].name
        except KeyError:
            pass
        effectif = []
                
        for eff in Report.objects.all():
            if eff.school_class.school.name == school_name:
                effectif.append(eff.girls_absentees)
        if effectif == []:
            if girls_count < girls_count +1:
                girls_count
            return girls_count
        else:
            if girls_count < max(effectif):
                
                error = ("""Saisie incorrecte : le nombre d'absents maximum(%s)"""
                         """ est superieur à l'effectif total des filles(%s)"""
                         """ de cette classe """) % (max(effectif), girls_count)
                         
                        
                       

                raise forms.ValidationError(error)
            
        return max(effectif)
    def clean_teachers_count(self):
       
        teachers_count = self.cleaned_data['teachers_count']
        school_name = self.cleaned_data['school'].name
        
        effectif = []
                
        for eff in Report.objects.all():
            if eff.school_class.school.name == school_name:
                effectif.append(eff.teacher_absentees)
        
        if effectif == []:
            if teachers_count < teachers_count +1:
                teachers_count
            return teachers_count
        else:
            if teachers_count < max(effectif):
                
                error = ("""Saisie incorrecte : le nombre d'absents maximum(%s)"""
                         """ est superieur à l'effectif total des professeurs (%s)"""
                         """ de cette classe """) % (max(effectif), teachers_count)

                raise forms.ValidationError(error)
            
            return max(effectif)
   
class ReportAdmin(admin.ModelAdmin):
    list_display = ('school_class', 
                    'boys_absentees', 
                    'girls_absentees', 
                    'teacher_absentees', 
                    'date', 'warning','reporter')
    list_filter = ['school_class']
    form = ReportAdminForm
    

class SchoolAdmin(admin.ModelAdmin):
    list_display = ('village', 'name','code_school')
    
class SchoolClassAdmin(admin.ModelAdmin):
    list_display = ('school', 
                    'grade', 
                    'boys_count', 
                    'girls_count', 
                    'teachers_count', 
                    'begin_year',
                    'end_year',
                    'code_schoolclass')
    form = SchoolClassAdminForm

    
    
  
admin.site.register(Village, )
admin.site.register(School, SchoolAdmin)
admin.site.register(SchoolClass, SchoolClassAdmin)
admin.site.register(Report, ReportAdmin)


            
            
