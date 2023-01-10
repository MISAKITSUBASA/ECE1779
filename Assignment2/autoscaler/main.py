from flask import render_template, url_for, request, g, redirect
from autoscaler import webapp,maxMissRate,minMissRate,ExpandRatio,ShrinkRatio
from autoscaler.config import db_config

import mysql.connector
import os
import shutil
import base64
import sys
import json
from datetime import datetime, timedelta
import random
import requests
import boto3
import math
from apscheduler.schedulers.background import BackgroundScheduler
import time 
 # db connection is referenced from 1779-week-4-exercises
def connect_to_database():
    return mysql.connector.connect(user=db_config['user'],
                                   password=db_config['password'],
                                   host=db_config['host'],
                                   database=db_config['database'],
                                   autocommit=True)
manager_ip =  "http://18.208.169.223:5000/"
client = boto3.client(service_name = 'cloudwatch',
                   region_name = 'us-east-1',
                   aws_access_key_id='AKIAUJYC64AA3Y5YLEPM',
                   aws_secret_access_key='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')



MAX_SIZE_NODE = 8
MIN_SIZE_NODE = 1


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = connect_to_database()
    return db


@webapp.teardown_appcontext
def teardown_db(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@webapp.route('/')
def main():
    # if (mode == 0):
    #     print("This is manual mode")
    # elif(mode == 1):
    #     apsched = BackgroundScheduler()
    #     apsched.start()
    #     apsched.add_job(autoscale, trigger="interval", seconds=60, id='automode')
    return render_template("main.html")

@webapp.route('/refreshPolicy',methods=['POST'])
def refresh_policy():
    global maxMissRate
    global minMissRate
    global ShrinkRatio
    global ExpandRatio
    try:
        db = connect_to_database()
        cursor = db.cursor()
        # display all keys in the table "KeyList"
        query = "SELECT * FROM autoScalerConfig"
        cursor.execute(query)
        result = cursor.fetchall()
        maxMissRate = result[0][2]
        minMissRate = result[0][3]
        ExpandRatio = result[0][4]
        ShrinkRatio = result[0][5]
    

    except Exception as e:
        print(e)
    return  webapp.response_class(
            status=200,
            mimetype='application/json',
            content_type='application/json'
        )




@webapp.route('/turnOnAuto',methods=['POST','GET'])
def turnOnAuto():
    global apsched
    apsched = BackgroundScheduler()
    apsched.start()
    print("job on autoscalar started")
    apsched.add_job(autoscale, trigger="interval", seconds=60, id='automode')

    return  webapp.response_class(
            status=200,
            mimetype='application/json',
            content_type='application/json'
        )

    
@webapp.route('/turnOnManual',methods=['POST','GET'])
def turnOnManual():
    apsched.shutdown(wait=False)
    print("autoscalar job ended")
    return  webapp.response_class(
            status=200,
            mimetype='application/json',
            content_type='application/json'
        )



def get_ave_cache_miss_rate_cloudwatch(instance_ids):
    total_miss_rate = 0
    for i in instance_ids:
        response = client.get_metric_statistics(
            Namespace='memcache',
            Dimensions=[
                {
                    'Name': 'InstanceId',
                    'Value': str(i)
                }
            ],
            MetricName='missRate',
            StartTime=datetime.utcnow() - timedelta(seconds=60),
            EndTime=datetime.utcnow(),
            Period=60,
            Statistics=[
                'Maximum'
            ],
            Unit='Percent'
        )

        result =  response['Datapoints']
        # when there are no data points
        if len(result) != 0 :
            total_miss_rate += result[0]['Maximum']          
    
    return total_miss_rate / len(instance_ids)
    

def autoscale():
    # get the miss rate from cloudwatch
    
    try:
        print("autoscla right now")
        re = requests.get(manager_ip+ "getAllIds")
        data = re.json()
        ave_miss = get_ave_cache_miss_rate_cloudwatch(data) 
        num_of_instances = len(data)
        # ave_miss = 0.1

        if(ave_miss > 0):
            if ave_miss >= maxMissRate:
                 # add an instance
                expand_size = math.floor(float(num_of_instances) * ExpandRatio)

                if num_of_instances < 8:
                    for i in range(expand_size - num_of_instances):
                        print("add one ec2 instance")
                        re3 = requests.post(manager_ip + "increase")
                        # time.sleep(60)
                else:
                    print("number of instance size larger than 8 stop!!!")
             
                
            elif ave_miss <= minMissRate:
                   # terminate an intance 
                shrink_size = math.floor(float(num_of_instances) * ShrinkRatio)
                if num_of_instances > 1:
                    for i in range(num_of_instances - shrink_size):
                        print("delete one ec2 instance")
                        re2 = requests.post(manager_ip + "decrease")
                        # time.sleep(60)
                else:
                    print("number of instance less than 1 stop!!!")
        else:
            print("")
               
            
            
    except Exception as e:
        print(e)





    


