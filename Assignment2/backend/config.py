from email import policy
from requests import request


db_config = {'user': 'admin',
             'password': 'abc12345!',
             'host': 'database-1.crlxn6xp41cl.us-east-1.rds.amazonaws.com',
             'database': 'memcache',
             'port':"3306"}

requestsCount = 0 # number of requests served, 
folder = "./static"




