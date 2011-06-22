/* TODO : compresser script js y compris ceux de jquery en prod */

$(document).ready(function(){
 
  // on fait table par table plutot que par tr
  // pour eviter que la premiere ligne du second tableau
  // soit consideree comme paire
     
  $("table").each(function(){
        $(this).find("tbody tr:odd").addClass("even");
  });


    $("table") 
    .tablesorter({widgets: ['zebra']}) 
    .tablesorterPager({container: $("#pager")
    });  

});

