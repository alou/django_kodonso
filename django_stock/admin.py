#!/usr/bin/env python
# -*- coding= UTF-8 -*-
from django.contrib import admin
from models import *
from django import forms
from django.core.exceptions import ValidationError
from datetime import datetime

class ReportAdminForm(forms.ModelForm):
    
    class Meta:
        model = Report 
           
    def clean_date(self):
        # on recupere l'année, le jour, et le mois
        report_year = self.cleaned_data['date'].year
        report_day = self.cleaned_data['date'].day
        report_month = self.cleaned_data['date'].month
        # on constitue notre format de date
        report_date =  str(report_day) + '-' + str(report_month) + '-' + str(report_year)
        
        date = datetime.strptime(str(report_date), "%d-%m-%Y" )
        
        
        return date
    
    def clean_incomming (self):
		"""
		Vérifie que le produit entrée a un niveau maximum.
		"""
	   # on recupere le village, le produit et l'entrée.
		villages = self.cleaned_data['place'].name
		produit = self.cleaned_data['product'].name
		entree = self.cleaned_data['incomming']
		
		liste =[]
		
		for max in Maximal.objects.all():
			if villages == max.place.name and produit == max.product.name:
				liste.append(max.place.name)
		
		if liste != []:
			villages 
			return entree  
		else:
		   
			error = ("""Saisissez un stock maximal pour le prduit < %s > du village < %s > """) %(produit,villages)

			raise forms.ValidationError(error)
		
		return entree    


class ReportAdmin(admin.ModelAdmin):

    list_display = ('place','product','incomming', 
                    'consumption','remaining', 'date', 'warning', 'reporter')
    fields = ('place','product','incomming', 'consumption', 'date')
    form = ReportAdminForm

               
class MaximalAdmin(admin.ModelAdmin):
    list_display = ('product', 
                    'place', 
                    'stock_maximal')
    list_filter = ('product', 'place')
    #form = MaximaltAdminForm
    
    
#~ admin.site.register(Product)
#~ admin.site.register(Place)
#~ admin.site.register(Report, ReportAdmin)
#~ admin.site.register(Maximal,MaximalAdmin)
