curently I have setup api service for jdb already, see (d:/jdb/doc/27-....)

setup reverse proxy for expense api there in apache apis.com.la.conf
like this:

apis@apissrv:~$ sudo cat /etc/apache2/sites-available/apis.com.la.conf
[sudo] password for apis:
<VirtualHost *:443>
    ServerName apis.com.la
    ServerAlias www.apis.com.la

    DocumentRoot /var/www/html/

    SSLEngine on

    <Directory /var/www/html/>
        Options Indexes FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>

    # Subdirectory for apims
    Alias /apims /var/www/html/apims
    <Directory /var/www/html/apims>
        Require all granted
    </Directory>

    # Subdirectory for nano
    Alias /nano /var/www/html/nano
    <Directory /var/www/html/nano>
        Require all granted
    </Directory>

    # Subdirectory for zkpush
    Alias /zkpush /var/www/html/zkpush
    <Directory /var/www/html/zkpush>
        Options -Indexes +FollowSymLinks
        AllowOverride None
        Require all granted
        RewriteEngine On
        RewriteBase /zkpush/
        RewriteCond %{REQUEST_FILENAME} !-f
        RewriteCond %{REQUEST_FILENAME} !-d
        RewriteRule ^(.*)$ /zkpush/index.php [L,QSA]
    </Directory>

    # Set secret key for apims project
    SetEnv ENCRYPTION_KEY "pYNrA+eqezCV17ZUP2Ki3Xn5WIJtOhxvLp9uDVNpkO4="

    # === Flask API proxy ===
    ProxyPreserveHost On
    ProxyPass /jdb_api http://127.0.0.1:8000/
    ProxyPassReverse /jdb_api http://127.0.0.1:8000/


    ErrorLog ${APACHE_LOG_DIR}/apis_error.log
    CustomLog ${APACHE_LOG_DIR}/apis_access.log combined
    Include /etc/letsencrypt/options-ssl-apache.conf
    SSLCertificateFile /etc/letsencrypt/live/apis.com.la-0002/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/apis.com.la-0002/privkey.pem

</VirtualHost>
apis@apissrv:~$

now we can add for msp and use different port 8001 to not touch the existing one: 


  1. Update your Apache Configuration
  Open your config file: sudo nano /etc/apache2/sites-available/apis.com.la.conf

  Add these lines right below your jdb_api section:

   1     # === MSP API proxy ===
   2     ProxyPreserveHost On
   3     ProxyPass /msp http://127.0.0.1:8001
   4     ProxyPassReverse /msp http://127.0.0.1:8001

  Note on the Path: 
  Because your Python code uses url_prefix='/msp', I removed the trailing slash / after the port 8001. This ensures that when someone calls https://apis.com.la/msp/upload,
  Apache sends the full path /msp/upload to your Python app, which matches your blueprint perfectly.

  2. Restart Apache
  After saving the file, check for errors and restart:
   1 sudo apachectl configtest
   2 sudo systemctl restart apache2

  3. Run your MSP API on Port 8001
  When you upload your code to the server, you should start it using Waitress (which is already in your requirements.txt). 

  Navigate to your project folder on the server and run:

   1 # Run in background using nohup so it stays alive after you close the terminal
   2 nohup waitress-serve --port=8001 api:app > msp_api.log 2>&1 &

  Summary of Access:
   * Oracle Project: Remains at https://apis.com.la/jdb_api/...
   * MSP Project: New endpoints at https://apis.com.la/msp/upload, https://apis.com.la/msp/getStatus, etc.

  Why this works:
  Apache acts as the "Traffic Controller." It looks at the URL:
   1. If it sees /jdb_api, it sends the request to the process at Port 8000.
   2. If it sees /msp, it sends the request to your new process at Port 8001.

  This is the standard way to host multiple independent APIs on a single Ubuntu server