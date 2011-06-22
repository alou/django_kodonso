#!/usr/bin/env python
# -*- coding= UTF-8 -*-

from django.utils.translation import ugettext, ugettext_lazy as _
from models import *
from django import forms
from django.contrib.auth.models import User, Group, User
from datetime import *

class StockMaxi(forms.Form):

    #product= forms.CharField(max_length=60, label=_("Product"))
    #place= forms.CharField(max_length=60, label=_("Places"))
    stock_maximal= forms.FloatField(label=_("maximum stock"))
    stock_day = forms.FloatField(label=_("daily quantity"))
    
    
class StockReportForm(forms.ModelForm):
    class Meta:
        model=Report
        exclude = ['remaining']
    
    def clean_consumption(self):
        """
        Vérifie que le nombre de garçons absents rapporté n'est pas 
        supérieur à l'effectif de la classe.
        """
        try:
        
            rest= Report.objects.filter(place =self.cleaned_data['place'], product = self.cleaned_data['product'] ).order_by('-date')[0]
            ref= rest.remaining + self.cleaned_data['incomming']
        except IndexError:
            ref= self.cleaned_data['incomming'] 
            #~ rest={'place': self.cleaned_data['place'], 'product': self.cleaned_data['product'], 'incomming': self.cleaned_data['incomming'], 'date': self.cleaned_data['date'], 'comsuption': self.cleaned_data['comsuption'], 'remaining': self.cleaned_data['remaining']}
        except KeyError:
            try:
                ref= rest.remaining
            except UnboundLocalError:
                pass
        conso = self.cleaned_data['consumption']
        
        
        try:
            if conso > ref:
                
                error = ugettext("Invalid entries: Consumer input") + " "+ " ( " + str(conso) +" ) " + ugettext("is superior to quantity in stock") + " "+ " ( " + str(ref) +" ) "
                
                #~ error = ("""Saisie incorrecte : la consommation saisie (%s)"""
                         #~ """ est superieur à la quantite en stock (%s)""") % (conso, ref)
                raise forms.ValidationError(error)
                
                
            if conso < 0:
                
                error = ugettext("Invalid entries: Consumer input must not be negative")
                
                #error = ("""Saisie incorrecte : la consommation saisie ne doit pas être négative """)
                raise forms.ValidationError(error)

 
        except UnboundLocalError:
            pass
        
        return conso
        
    
    def clean_incomming(self):
        entre = self.cleaned_data['incomming']
        if entre < 0 :
            
            error = ugettext("Invalid entries: the entry must not be negative")
            #error ="""saisie incorrecte:l'entrée ne doit pas etre negative"""
            raise forms.ValidationError(error)
        return entre
        
        
            

class ModificationForm(forms.Form):
    
    product = forms.ChoiceField(label=_(u"Product"), choices=[(product.id , product) for product in Product.objects.all()])
    place = forms.ChoiceField(label=_(u"School"), choices=[(place.id , place.name) for place in Place.objects.all()])
    incomming = forms.FloatField(label=_('Incomming'))
    consumption = forms.FloatField(label=_('Consumption'))
    date = forms.DateField(label=_('Date'))

class LoginForm(forms.Form):
    username = forms.CharField(max_length=100,label = _("Username"))
    password = forms.CharField(max_length=100, label =_("Password") ,widget=forms.PasswordInput)
    
    
class AdminForm(forms.Form):
    
    def __init__(self, *args, **kwargs):
        super(AdminForm, self).__init__(*args, **kwargs)
        self.fields['groupe'].choices = [(group.id, group.name) for group in Group.objects.all()]


    username = forms.CharField(max_length=100,label = _("Username"))
    password = forms.CharField(max_length=100, label =_("Password") ,widget=forms.PasswordInput)
    last_name = forms.CharField(max_length=100, label =_("Last name"))
    first_name = forms.CharField(max_length=100, label =_("First name"))
    email = forms.EmailField(label =_("Email"))
    actif = forms.BooleanField(label =_("Actif") , initial= True)
    groupe = forms.MultipleChoiceField(label=_("Group"))
    
class ModifAdminForm(forms.Form):

    last_name = forms.CharField(max_length=100, label =_("Last name"))
    first_name = forms.CharField(max_length=100, label =_("First name"))
    email = forms.EmailField(label =_("Email"))
        
class Admin1Form(forms.Form):
    username = forms.CharField(max_length=100,label = _("Username"))
    password = forms.CharField(max_length=100, label =_("Password"))
        
class ContactForm(forms.Form):
   
    name = forms.CharField(max_length=100)
    e_mail = forms.CharField(max_length=100)
    password = forms.CharField(max_length=100, widget=forms.PasswordInput)
    password = forms.CharField(max_length=100, widget=forms.PasswordInput)
   
    

class Groupe_manage(forms.ModelForm):
    class Meta:
        model=User
        exclude = ['password', 'user_permissions', 'last_login', 'date_joined', 'is_staff', 'is_superuser' ]
        
class report_pdfForm(forms.Form):
    date_debut = forms.DateField(label= _("start date"))
    date_fin = forms.DateField(label= _("end date"))
