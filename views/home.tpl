<!DOCTYPE html> 
<head>
</head>
<body>
<a href="#" id="start">Start</a>
<div id="fb-root"></div>
<script type="text/javascript" src="https://ajax.googleapis.com/ajax/libs/jquery/1.6.1/jquery.min.js"></script>
<script>
  var app_id = '232293086787125', page_id = '178568815531741';
  window.fbAsyncInit = function() {
    FB.init({appId: app_id, status: true, cookie: true, xfbml:
        true, channelUrl: document.location.protocol + '//' + document.location.host + '/channel/xd_receiver.html'});
    document.getElementById('start').onclick = function(){
      FB.getLoginStatus(function(response){
          FB.login(function(response){
              if (response.session) {
                  user_token = response.session.access_token,
                  FB.api('/me/accounts', function(response){
                      page_token = '';
                      // lookup access token of page.
                      window.console.log(response)
                      for (i = 0; i < response.data.length; i++) {
                          if (response.data[i].id = page_id)
                          {
                              page_token = response.data[i].access_token;
                              break;
                          }
                      }
                      $.post('/', {page_id:page_id, user_token:user_token,page_token:page_token},function(data){
                          if (data.status) alert('Access token saved');
                      });
                  });
              }
          }, {perms:'publish_stream,manage_pages, offline_access'});
      });
      return false;
    }
  };
  (function() {
    var e = document.createElement('script'); e.async = true;
    e.src = document.location.protocol +
      '//connect.facebook.net/en_US/all.js';
    document.getElementById('fb-root').appendChild(e);
  }());
</script>
</body>
</html>
