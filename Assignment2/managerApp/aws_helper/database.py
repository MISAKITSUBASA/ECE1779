import sys
import boto3
import os
import mysql.connector

ENDPOINT='database-1.crlxn6xp41cl.us-east-1.rds.amazonaws.com'
PORT="3306"
USER="admin"
REGION="us-east-1"
os.environ['LIBMYSQL_ENABLE_CLEARTEXT_PLUGIN'] = '1'


password = "abc12345!"

try:
    conn =  mysql.connector.connect(host=ENDPOINT, user=USER, password=password, port=PORT,database = "memcache")
    cur = conn.cursor()
    cur.execute("""select * from KeyList""")
    query_results = cur.fetchall()
    print(query_results)
except Exception as e:
    print("Database connection failed due to {}".format(e))          
                