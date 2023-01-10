from genericpath import isdir
from glob import glob
from flask import Flask
import os
global memcache
from backend.config import db_config
import shutil
import mysql.connector

webapp = Flask(__name__)
memcache = {} # each value in memcache is a dict {'name': , 'timeStamp':}

num_miss = 0 # number of miss
num_hit = 0 # number of hit
requestsCount = 0 # number of successful service with status 200

capacity = 1024*1024*100 # test for 100 MB
policy = "Random"

# db connection is referenced from 1779-week-4-exercises
def connect_to_database():
    return mysql.connector.connect(user=db_config['user'],
                                   password=db_config['password'],
                                   host=db_config['host'],
                                   port=db_config['port'],
                                   database=db_config['database'],
                                   autocommit=True)


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = connect_to_database()
    return db
#initialize the config table
db = connect_to_database()
cursor = db.cursor()
query = "SELECT * from config "
cursor.execute(query)
result = cursor.fetchall()
query = "UPDATE config SET capacity = (%s), policy = (%s) WHERE id = 1 "
cursor.execute(query, (1, policy))

if len(result) == 0:
    query = "INSERT config SET id = 1, capacity = (%s), policy = (%s)"
    cursor.execute(query, (capacity, policy))

from backend import main




