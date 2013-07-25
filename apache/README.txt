Apache
======

Requirements
------------

 - mod_rewrite
 - mod_proxy
 _ mod_auth_pubtkt


Vhost
-----


<VirtualHost 192.168.2.100:80>
    ServerAdmin webmaster@dummy-host.example.com
    ServerName gatekeeper.novareto.de
         # RewriteRules

        TKTAuthPublicKey cert/gatekeeper.novareto.de_pubkey.pem 
        <Proxy http://192.168.2.111:8080/*> 
          AuthType mod_auth_pubtkt 
          TKTAuthLoginURL http://sso.novareto.de/ 
          TKTAuthTimeoutURL http://sso.novareto.de/?timeout=1 
          TKTAuthUnauthURL http://sso.novareto.de/?unauth=1 
          TKTAuthPassthruBasicAuth on
          TKTAuthPassthruBasicKey mKaqGWwAVNnthL6J
          TKTAuthDebug 3 
          require valid-user 
        </Proxy>


        RewriteEngine on
        
        RewriteRule ^(/?.*) http://dashboard.novareto.de [L,P]

</VirtualHost>


<VirtualHost 192.168.2.100:80>
    ServerAdmin webmaster@dummy-host.example.com
    ServerName shop.novareto.de
         # RewriteRules

        TKTAuthPublicKey cert/gatekeeper.novareto.de_pubkey.pem 
        <Proxy http://192.168.2.111:8080/*> 
          AuthType mod_auth_pubtkt 
          TKTAuthLoginURL http://sso.novareto.de/ 
          TKTAuthTimeoutURL http://sso.novareto.de/?timeout=1 
          TKTAuthUnauthURL http://sso.novareto.de/?unauth=1 
          TKTAuthPassthruBasicAuth on
          TKTAuthPassthruBasicKey mKaqGWwAVNnthL6J
          TKTAuthDebug 3 
          require valid-user 
        </Proxy>


        RewriteEngine on
        RewriteRule ^(/?.*) http://192.168.2.111:8080/shop/++vh++http:shop.novareto.de:80/++$1 [L,P]

</VirtualHost>

