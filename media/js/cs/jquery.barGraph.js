/**
 * --------------------------------------------------------------------
 * jQuery-Plugin "barGraph"
 * by Siddharth S aka Tony Sundharam, lordtottuu@gmail.com
 * for Net Tuts, www.net.tutsplus.com

 * Copyright (c) 2009 Siddharth
 * Dual licensed under MIT and GPL
 * Usage Notes: Please refer to the Net Tuts article
 * Version: 1.0, 08.06.2009 	
 * --------------------------------------------------------------------
**/

(function($){
	$.fn.barGraph = function(settings) {
	
	// Option variables
	var defaults = {  
	         barOpacity : 0.8,
			 barSpacing: 50,
	 	 	 barWidth: 25, 
			 cvHeight: 300,
			 numYlabels: 15,
			 xOffset: 20,
	 	 	 labelColour: "#000000", 
	 	 	 disableGrid: false, 
			 hideDataSource: true,
			 scale: false,
	 	 	 showValue: true, 
			 showOutline: true,
	 	 	 theme: "Ocean",
           };  
		   
	// Merge the passed parameters with the defaults	   
    var option = $.extend(defaults, settings);  
	
	// Cycle through each passed object
	this.each(function() { 
					   
	// Canvas Variables
    var cv, ctx;
	 
	// Graph variables
	var gValues = [];
	var xLabels = [];
	var yLabels = [];
	var maxVal, minVal, gWidth, gHeight, gTheme;
	var dataSource = $(this).attr("id");
	 
	// Themes
	var thPink = ['#FFCCCC','#FFCCCC','#FFC0C0','#FFB5B5','#FFADAD','#FFA4A4','#FF9A9A','#FF8989','#FF6D6D'];
	var thBlue = ['#ACE0FF','#9CDAFF','#90D6FF','#86D2FF','#7FCFFF','#79CDFF','#72CAFF','#6CC8FF','#57C0FF'];
	var thGreen = ['#D1FFA6','#C6FF91','#C0FF86','#BCFF7D','#B6FF72','#B2FF6B','#AAFE5D','#A5FF51','#9FFF46'];
	var thAssorted = ['#FF93C2','#FF93F6','#E193FF','#B893FF','#93A0FF','#93D7FF','#93F6FF','#ABFF93','#FF9B93'];
	
	grabValues();
	initCanvas();
	minmaxValues(gValues);
	shadeGraphArea();
	drawXlabels();
    drawYlabels();
	if(!option.disableGrid) { drawGrid(); }
	if(option.showValue) { drawValue(); }
	drawGraph();
	   
	function grabValues ()
	 {
	 	// Access the required table cell, extract and add its value to the values array.
		 // $("tr").children("td:odd").each(function(){
		 // $("#"+dataSource).find("td:odd").each(function(){
		 // $("#"+dataSource+" tr td:odd").each(function(){
		 $("#"+dataSource+" tr td:nth-child(4)").each(function(){
		 gValues.push($(this).text());
	 	 });
	 
		 // Access the required table cell, extract and add its value to the xLabels array.
		 $("#"+dataSource+" tr td:nth-child(1)").each(function(){
	 	xLabels.push($(this).text());
	 	 });
		 
		switch(option.theme)
		{
			case 'Ocean':
			gTheme = thBlue;
			break;
			case 'Foliage':
			gTheme = thGreen;
			break;
			case 'Cherry Blossom':
			gTheme = thPink;
			break;
			case 'Spectrum':
			gTheme = thAssorted;
			break;
		} 
	 } 
	
	function initCanvas ()
	 {
		 $("#"+dataSource).after("<canvas id=\"bargraph-"+dataSource+"\" class=\"barGraph\"> </canvas> <br />");
		 
	 	// Try to access the canvas element 
     	cv = $("#bargraph-"+dataSource).get(0);
	 	cv.width=gValues.length*(option.barSpacing+option.barWidth)+option.xOffset+option.barSpacing;
		cv.height=option.cvHeight;
		gWidth=cv.width;
		gHeight=option.cvHeight-20;
	 
	 	if (!cv.getContext) 
	 	{ return; }
	 
     	// Try to get a 2D context for the canvas and throw an error if unable to
     	ctx = cv.getContext('2d');
	 	if (!ctx) 
	 	{ return; }
	 }
	   
    function drawGraph ()
	 {
	    for(index=0; index<gValues.length; index++)
	      {
		    ctx.save();
			if (option.showOutline)
			{
			ctx.fillStyle = "#000";
			ctx.strokeRect( x(index), y(gValues[index]), width(), height(gValues[index]));  
			}
			ctx.fillStyle = gTheme[getColour(index)];
		    ctx.globalAlpha = option.barOpacity;
	        ctx.fillRect( x(index), y(gValues[index]), width(), height(gValues[index]));  
			ctx.fillStyle = "#000";
			ctx.fillRect( option.xOffset, gHeight, gWidth, 1); 
		    ctx.restore();
	      }
	 }
	  
	function drawValue ()
      {
		  for(index=0; index<gValues.length; index++)
	      {
		      ctx.save();
			  ctx.fillStyle= "#000";
			  ctx.font = "10px 'arial'";
			  var valAsString = gValues[index].toString();
		      var valX = (option.barWidth/2)-(valAsString.length*3);
		      ctx.fillText(gValues[index], x(index)+valX,  y(gValues[index])-4);
			  ctx.restore();
		  }
      } 
	  
	function shadeGraphArea ()
      {
	    ctx.fillStyle = "#F2F2F2";
	    ctx.fillRect(option.xOffset, 0, gWidth-option.xOffset, gHeight); 
      }
	  
	function drawGrid ()
      {
		  for(index=0; index<option.numYlabels; index++)
	      {
		   ctx.fillStyle = "#AAA";
		   ctx.fillRect( option.xOffset, y(yLabels[index])+3, gWidth, 1);
		  }
      }  
	  
	function drawYlabels()
      {
		 ctx.save(); 
	     for(index=0; index<option.numYlabels; index++)
	      {
			  if (!option.scale)
			  {
		  		 yLabels.push(Math.round(maxVal/option.numYlabels*(index+1)));
			  }
			  else
			  {
				  var val= minVal+Math.ceil(((maxVal-minVal)/option.numYlabels)*(index+1));
		  		  yLabels.push(Math.ceil(val));  
			  }
		   ctx.fillStyle = option.labelColour;
		   var valAsString = yLabels[index].toString();
		   var lblX = option.xOffset - (valAsString.length*7);
		   ctx.fillText(yLabels[index], lblX, y(yLabels[index])+10);
	      }
		   if (!option.scale)
		   {
	        	ctx.fillText("", option.xOffset -7, gHeight+7);
		   }
		  else
		  {
		    var valAsString = minVal.toString();
		    var lblX = option.xOffset - (valAsString.length*7);
		    ctx.fillText(minVal, lblX, gHeight+7);  
		  }
		  ctx.restore();
      }  

	function drawXlabels ()
      {
		 ctx.save();
		 ctx.font = "10px 'arial'";
		 ctx.fillStyle = option.labelColour;
		 for(index=0; index<gValues.length; index++)
	     {
		 ctx.fillText(xLabels[index], x(index), gHeight+17);
		 }
		 ctx.restore();
      }
	 
	function width ()
      {
	   return option.barWidth;
      }
	 
	function height (param)
      {
	   return scale(param);
      }
	 
	function x (param)
      {
	   return (param*option.barWidth)+((param+1)*option.barSpacing)+option.xOffset;
      }
	 
	function y (param)
      {
	   return gHeight - scale (param) ;
      }
	  
	function scale (param)
      {
	   return ((option.scale) ? Math.round(((param-minVal)/(maxVal-minVal))*gHeight) : Math.round((param/maxVal)*gHeight));
      }
	 
	function minmaxValues (arr)
     {
		maxVal=0;
		
	    for(i=0; i<arr.length; i++)
	    {
		 if (maxVal<parseInt(arr[i]))
		 {
		 maxVal=parseInt(arr[i]);
	     } 
	    }
		minVal=maxVal;
		for(i=0; i<arr.length; i++)
	    {
		 if (minVal>parseInt(arr[i]))
		 {
		 minVal=parseInt(arr[i]);
	     }  
		}
	   maxVal*= 1.1;
       minVal = minVal - Math.round((maxVal/10));
	 }
	 
	function getColour (param)
      {
         return Math.ceil(Math.abs(((gValues.length/2) -param)));
	  }
	  
	if (option.hideDataSource) { $("#"+dataSource).remove();}
	
	});
              
	// returns the jQuery object to allow for chainability.
	return this;
	}
	
})(jQuery);
