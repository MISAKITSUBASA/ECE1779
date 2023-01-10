from flask import render_template, url_for, request, g, redirect
from backend import webapp, memcache, num_hit,num_miss,requestsCount,capacity,policy
from backend.config import db_config,folder
import mysql.connector
import os
import shutil
import base64
import sys
import json
from datetime import datetime
import random
import requests
import boto3
from apscheduler.schedulers.background import BackgroundScheduler
import hashlib

host = "http://18.208.169.223:5000/" #manger app ip not the same every time
global instanceId
from ec2_metadata import ec2_metadata
instanceId = ec2_metadata.instance_id


client_watch = boto3.client('cloudwatch', region_name='us-east-1', aws_access_key_id='AKIAUJYC64AA3Y5YLEPM',
                          aws_secret_access_key='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')


def cloudwatch_missRate(instance_id,miss_rate):
    re = client_watch.put_metric_data(
        Namespace='memcache',
        MetricData = [{
            'MetricName': 'missRate',
            'Dimensions': [
                {
                    'Name': 'InstanceId',
                    'Value': str(instance_id)
                },
            ],
            'Value': miss_rate,
            'Unit':'Percent',
            
        }]
    )
    return re
def cloudwatch_hitRate(instance_id,hit_rate):
    re = client_watch.put_metric_data(
        Namespace='memcache',
        MetricData = [{
            'MetricName': 'hitRate',
            'Dimensions': [
                {
                    'Name': 'InstanceId',
                    'Value': str(instance_id)
                },
            ],
            'Value': hit_rate,
            'Unit':'Percent',
            
        }]
    )
    return re
def cloudwatch_item_count(instance_id,count):
    re = client_watch.put_metric_data(
        Namespace='memcache',
        MetricData = [{
            'MetricName': 'itemInCache',
            'Dimensions': [
                {
                    'Name': 'InstanceId',
                    'Value': str(instance_id)
                },
            ],
            'Value': count,
            'Unit': 'Count'
            
        }]
    )
    return re
    
def cloudwatch_cache_size(instance_id,cache_size):
    re = client_watch.put_metric_data(
        Namespace='memcache',
        MetricData = [{
            'MetricName': 'CacheSize',
            'Dimensions': [
                {
                    'Name': 'InstanceId',
                    'Value': str(instance_id)
                },
            ],
            'Value': cache_size,
            'Unit':'Megabytes',
            
        }]
    )
    return re
def cloudwatch_request_count(instance_id,request_count):
    re = client_watch.put_metric_data(
        Namespace='memcache',
        MetricData = [{
            'MetricName': 'RequestCount',
            'Dimensions': [
                {
                    'Name': 'InstanceId',
                    'Value': str(instance_id)
                },
            ],
            'Value': request_count,
            'Unit':'Count',
            
        }]
    )
    return re



# db connection is referenced from 1779-week-4-exercises
def connect_to_database():
    return mysql.connector.connect(user=db_config['user'],
                                   password=db_config['password'],
                                   host=db_config['host'],
                                   database=db_config['database'],
                                   autocommit=True)


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
    return render_template("main.html")


"""
clear all the keys in the mem-cache
"""

@webapp.route('/clear', methods=['GET'])
def clear():

    global requestsCount
    memcache.clear()
    requestsCount = requestsCount + 1
    response = webapp.response_class(
        response=json.dumps("success"),
        status=200,
        mimetype='application/json'
    )

    return response

#drop single key 
@webapp.route('/invalidate/<key>', methods=['POST'])
def invalidateKey(key):
    status = 200
    response = json.dumps("OK")
    try:
        if key and key in memcache.keys():
            memcache.pop(key)
            # remove the image in the cache folder aoosciate with the key
            # filename = memcache[key]['name']
            # path_to_delete = os.path.join(folder, filename)
            # os.remove(path_to_delete)
        else:
            return webapp.response_class(
                response=json.dumps("key not found"),
                status=400,
                mimetype='application/json'
            )

    except Exception as e:
        status = 500
        response = json.dumps(e)

    response = webapp.response_class(
        response=response,
        status=status,
        mimetype='application/json'
    )

    return response


"""
Retrieve all keys: 
"""
@webapp.route('/api/list_keys', methods=['POST'])
#TODO: modify this in order to show all keys in database, not memcache
def getAllKeys():

    global requestsCount

    db = connect_to_database()
    cursor = db.cursor()
    # display all keys in the table "KeyList"
    query = "SELECT name FROM KeyList"
    cursor.execute(query)
    result = cursor.fetchall()

    if not result:  # if fails to retrieve keys, print error message
        body = {"success": "false", "error": {
            "code": 404,
            "message": "Fail to retrieve any keys"
        }}
        return webapp.response_class(
            response=json.dumps(body),
            status=404,
            mimetype='application/json'
        )
    else:
        body = {
            "success": "true", "keys": result
        }
        requestsCount = requestsCount + 1
        return webapp.response_class(
            json.dumps(body),
            status=200,
            mimetype='application/json',
            content_type='application/json'
        )

'''
    API for get image from memcache
'''
@webapp.route('/api/key/<key_value>', methods=['POST'])
def get_Image(key_value):
    
    global num_miss
    global num_hit
    global requestsCount
    global capacity

    if key_value == "":
        re = {
            "success": "false",
            "error": {
                "code": 404,
                "message": "Bad Key"
            }
        }
        return re

    # hit case
    if key_value in memcache.keys():
        num_hit = num_hit + 1
        requestsCount = requestsCount + 1
        data = memcache[key_value][0]

        # construct result
        result = {
            "success": "true", "content": data
        }
        # construct response status 200
        re = json.dumps(result)

        return re
    num_miss = num_miss + 1

    # handle case missed
    re = {
        "success": "false",
        "error": {
            "code": 404,
            "message": "Miss"
        }
    }
    return re

'''
API for Put, add content to memcache
'''
@webapp.route('/putImage/<key_value>', methods=["POST"])
def put_Image(key_value):
    global memcache
    global requestsCount
    global capacity
    global policy
    # get content from json
    content = request.get_json()
    content = content[key_value]
    # get size
    size_data = sys.getsizeof(content)
    size_mem = 0

    for key in memcache.keys():
        size_mem += sys.getsizeof(str(memcache[key]))
 
    # oversized content
    if size_data > capacity:
        # return response
        return webapp.response_class(
            json.dumps("exceed compacity"),
            status=400,
            mimetype='application/json',
            content_type='application/json'
        )

    # performing replacement policy
    while size_mem + size_data > capacity:
        size_mem = 0
        keys = list(memcache.keys())

        # Random Replacement
        if policy == "Random":
            
            rand_key_index = random.randint(0, len(keys)-1)
            memcache.pop(keys[rand_key_index], None)
            for key in memcache.keys():
                size_mem += sys.getsizeof(str(memcache[key]))


        # Least Recently Used
        elif policy == "LRU":
            least_recent_key = ""
            least_recent_ts = datetime.now()

            for key in keys:
                if memcache[key][1] < least_recent_ts:
                    least_recent_key = key
            memcache.pop(least_recent_key, None)
            for key in memcache.keys():
                size_mem += sys.getsizeof(str(memcache[key]))

    memcache.setdefault(key_value, (content, datetime.now()))
    
    for key in memcache.keys():
        size_mem += sys.getsizeof(str(memcache[key]))

    requestsCount = requestsCount + 1

    return webapp.response_class(
        json.dumps("ok"),
        status=200,
        mimetype='application/json',
        content_type='application/json'
    )


def get_stats():
    itemCount = len(memcache.items())
    cacheSize = 0

    for key in memcache.keys():
        cacheSize += sys.getsizeof(str(memcache[key]))

    mis_rate = 0
    hit_rate = 0
    if num_miss + num_hit == 0:
        mis_rate = 1
        hit_rate = 0
    else:
        mis_rate = num_miss/(num_miss+num_hit)
        hit_rate = num_hit/(num_miss+num_hit)

    response = {'itemCount': itemCount, 'cachesize': cacheSize/(1024*1024),
                "requestsCount": requestsCount, "missRate": mis_rate, "hitRate": hit_rate}

    return response


# refresh configuration
@webapp.route('/refresh_config', methods=['GET', 'POST'])
def refresh_config():
    global capacity
    global policy
    cnx = get_db()  # connect to database
    cursor = cnx.cursor()
    query = "SELECT * FROM config"
    cursor.execute(query)
    result = cursor.fetchall()
    capacity = result[0][1]*1024*1024
    policy = result[0][2]

    response = webapp.response_class(
        response=json.dumps("ok"),
        status=200,
        mimetype='application/json'
    )

    return response
# create instance call this to run jobs
@webapp.before_first_request
def run_job():
    apsched = BackgroundScheduler()
    apsched.start()
    apsched.add_job(cloudwatch_updater, trigger="interval", seconds=5)
    print("job for stats started")

def cloudwatch_updater():
    print("cloud watch update")
    stat =  get_stats()
    cloudwatch_missRate(instanceId,miss_rate=stat['missRate'])
    cloudwatch_cache_size(instanceId,stat['cachesize'])
    cloudwatch_hitRate(instanceId,stat['hitRate'])
    cloudwatch_item_count(instanceId,stat['itemCount'])
    cloudwatch_request_count(instanceId,stat['requestsCount'])

def Md5(key):
    result = hashlib.md5(key.encode())
    hex = result.hexdigest()
    remainder = int(hex, base=16) % 16
    
    # get all the ips from mangerapp
    mangerapp_url =  host + "getAllIps"
    res = requests.get(mangerapp_url)
    res = res.json()
    if len(res) != 0:
        node_chosen = remainder % len(res)
        ip = res[node_chosen]
        ip_str = "http://" + ip + ":5000/"
        return ip_str
    else:
        return False

@webapp.route('/distribute', methods=["POST"])
def distribute():
    global memcache
    new_dict = {}
    ip = request.json["ip"]

    ip = "http://" + ip + ":5000/"

    for key in memcache.keys():

        content = memcache[key]
        if Md5(key) != ip:
            url = Md5(key)

            re = requests.post(url + "backEnd/putImage/" + str(key), json={str(key): content[0]})

        else:
            new_dict.setdefault(key, content)

    memcache = new_dict.copy()

    return webapp.response_class(
        response=json.dumps("success"),
        status=200,
        mimetype='application/json'
    )


