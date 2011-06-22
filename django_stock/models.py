#!/usr/bin/env python
# -*- coding= UTF-8 -*-
from django.contrib.auth.models import User, Group
from django.db import models
from lib.tools import get_week_boundaries
from django.utils.translation import ugettext, ugettext_lazy as _

from django.utils.translation import gettext_lazy

class Product(models.Model):

    name = models.CharField(max_length=60, verbose_name=_("Name of product"), unique= True)
    code_product  = models.CharField(max_length=20, unique = True)
    def __unicode__(self):
        return u"%s "%(self.name)
 
class Place(models.Model):

    name = models.CharField(max_length=60, 
                            verbose_name=_("Name of Schools"), 
                            unique= True)
    code_place  = models.CharField(max_length=20, unique = True)
    
    def __unicode__(self):
        return u"%s"%(self.name)
    
class Maximal(models.Model):
    
    class Meta:
        #rendre unique l'enssemble les éléments "products", "place".
        unique_together = ('product', 'place')
    
    product= models.ForeignKey(Product,verbose_name=_("Product"))
    place= models.ForeignKey(Place,verbose_name=_("Places"))
    stock_maximal= models.FloatField(verbose_name=_("maximum stock"))
    stock_day = models.FloatField(verbose_name=_("daily quantity"))
    def __unicode__(self):
        return u"%s %s %s %s"%(self.product,
                            self.place,
                            self.stock_maximal,
                            self.stock_day)
        
class Report(models.Model):
    
    place = models.ForeignKey(Place,verbose_name=_('Schools'))
    product = models.ForeignKey(Product,verbose_name= _('Product'))
    incomming = models.FloatField(verbose_name= _('Incomming'))
    consumption = models.FloatField(verbose_name=_("Consumption"))
    remaining = models.FloatField(verbose_name=_("Remaining"))
    date = models.DateField(verbose_name=_("Date"))
    warning = models.BooleanField(verbose_name=_("Warning"))
    reporter = models.ForeignKey(User,verbose_name=_('Reporter'), related_name="stock_report", blank = True)

    def get_absolute_url(self,date):
        self.date = date

        return self.date

    @classmethod
    def get_reports_filtered_by_duration(cls, year, duration, duration_quantity):
        """
            Retourne un queryset de rapports filtre selon la date
            obtenue a travers l'url.
            Cela permet donc d'avoir tous les rapports pour une annee
            et optionnellement pour un mois ou une semaine de cette 
            annee.
        """
    
        reports = Report.objects.filter(date__year=year)
        
        if duration == "month":                                                
            reports = reports.filter(date__month=duration_quantity)
        
        if duration == "week":
            first_day, last_day = get_week_boundaries(year, duration_quantity)
            reports = reports.filter(date__gte=first_day, 
                                    date__lte=last_day)
        return reports

    @property
    def max(self):
        
        #recupere l'objet maximal dans report
        return Maximal.objects.get(product=self.product, place=self.place).stock_maximal

    def save(self):
        """
        Calcul du restant en stock après un mouvement.
        """

        # Recupration de tous les reports filtrer par denrée et par village
        # puis ordonée par date.

        last_reports = Report.objects.filter(product__name=self.product.name,
                                                 place__name=self.place.name,
                                                 date__lt=self.date)\
                                     .order_by('-date')
        # Condition qui determine si il ya ou pas un restant de stock et
        # sauvegarde dans la base le restant actuelle après l'avoir calculé.
        previous_remaining = 0

        if last_reports:
            
            previous_remaining = last_reports[0].remaining

        self.remaining = previous_remaining + (self.incomming - self.consumption)

        super(Report, self).save()
        
        
        # on recupere tous les enregistrements suivant
        next_reports = Report.objects.filter(product__name=self.product.name,
                                                 place__name=self.place.name,
                                                 date__gt=self.date)\
                                      .order_by('date')
        
        # on met a jour le premier d'entre eux
        # comme il va faire de meme, cela va tous les mettre a jour
        if next_reports:
            next_reports[0].save()
            

    def __unicode__(self):
        return u"%s %s %s %s %s %s" % (self.incomming,
                                   self.product,
                                   self.consumption,
                                   self.remaining,
                                   self.date,
                                   self.warning)
