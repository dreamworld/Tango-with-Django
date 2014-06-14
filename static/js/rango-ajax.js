$(document).ready(function() {

        $('#likes').click(function(){
        	var catid;
        	catid = $(this).attr("data-catid");
        	$.get('/rango/like_category/',{category_id: catid},function(data){
        		$('#like_count').html(data);
        		$('#likes').hide();
        	});
        	
        });
        
        $('#suggestion').keyup(function(){
            var query;
            query = $(this).val();
        	$.get('/rango/suggest_category/',{starts_with: query},function(data){
        		$('#cats').html(data);
        	});
        });
        
        $('.rango-add').click(function(){
            var btnClicked = $(this);
            var title = $(this).attr("data-title");
            var url = $(this).attr("data-url");
            var cat_id = $(this).attr("data-catid");
            
            var encodedTitle = encodeURIComponent(title);
            var encodedUrl = encodeURIComponent(url);
            
            $.get('/rango/auto_add_page/', {title:encodedTitle, url: encodedUrl, catid:cat_id}, function(data){
            	$('#page').html(data);
            	btnClicked.hide();
            });
        	
        	
        });
        
        
        
        
        
        
        

});