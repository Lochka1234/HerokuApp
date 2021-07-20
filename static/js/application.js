 $('document').ready(function() {
     $('nav a').each(function() {
         if ('http://127.0.0.1:5000'+$(this).attr('href') === window.location.href)
         {
             $(this).addClass('active');
         }
     });
 });