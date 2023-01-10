
from flask import Flask
import mysql.connector

webapp = Flask(__name__)
from autoscaler.config import db_config

# db connection is referenced from 1779-week-4-exercises
def connect_to_database():
    return mysql.connector.connect(user=db_config['user'],
                                   password=db_config['password'],
                                   host=db_config['host'],
                                   database=db_config['database'],
                                   autocommit=True)
db = connect_to_database()
cursor = db.cursor()
# display all keys in the table "KeyList"
query = "SELECT * FROM autoScalerConfig"
cursor.execute(query)
result = cursor.fetchall()
global maxMissRate
global minMissRate
global ShrinkRatio
global ExpandRatio

if len(result) == 0:
    query = "INSERT autoScalerConfig SET id = 1, mode = 0, maxMissRate = (%s), minMissRate = (%s), ExpandRatio = (%s), ShrinkRatio = (%s)"
    cursor.execute(query, (0.6, 0.2, 1, 1))
    maxMissRate = 0.6
    minMissRate = 0.2
    ExpandRatio = 2
    ShrinkRatio = 0.5
else:
    maxMissRate = result[0][2]
    minMissRate = result[0][3]
    ExpandRatio = result[0][4]
    ShrinkRatio = result[0][5]
    # maxMissRate = 0.6
    # minMissRate = 0.2
    # ExpandRatio = 2
    # ShrinkRatio = 0.5

from autoscaler import main




