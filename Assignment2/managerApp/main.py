import json
import os
import requests
import boto3
import mysql.connector
from flask import redirect, render_template, request, url_for
import time
from managerApp import webapp
from managerApp.aws_helper.AwsEC2 import AwsEC2
from managerApp.config import root_aws_key, root_aws_key_id
import random
from datetime import datetime, timedelta

ENDPOINT = "database-1.crlxn6xp41cl.us-east-1.rds.amazonaws.com"
PORT = "3306"
USER = "admin"
REGION = "us-east-1"
os.environ['LIBMYSQL_ENABLE_CLEARTEXT_PLUGIN'] = '1'
PASS = "abc12345!"

host = "http://18.208.169.223:5000/" #manger app ip not the same every time

# initialize the AwsEC2 class
# client = boto3.client('ec2',"us-east-1" )
ec2_client = boto3.client(service_name='ec2',
                          region_name='us-east-1',
                          aws_access_key_id='AKIAUJYC64AA3Y5YLEPM',
                          aws_secret_access_key='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')

cloud_client = boto3.client(service_name='cloudwatch',
                            region_name='us-east-1',
                            aws_access_key_id='AKIAUJYC64AA3Y5YLEPM',
                            aws_secret_access_key='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')

client_s3 = boto3.client('s3', region_name='us-east-1',aws_access_key_id='AKIAUJYC64AA3Y5YLEPM',
                          aws_secret_access_key='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')

ec2 = AwsEC2(ec2_client)


# connect to the database
def database_connector():
    try:
        conn = mysql.connector.connect(
            host=ENDPOINT, user=USER, password=PASS, port=PORT, database="memcache",autocommit=True)
        # cur.execute("""""")
        # query_results = cur.fetchall()
        # print(query_results)
        return conn
    except Exception as e:
        print("Database connection failed due to {}".format(e))


@webapp.route('/')
def main():
    # cur = database_connector()
    # cur.execute("""select * from memcache""")
    # query_results = cur.fetchall()
    # print(query_results)

    return render_template("main.html")


# increase nodes in manual mode


@webapp.route('/increase', methods=["POST"])
def manual_increase():
    ec2.updateAndRefreshDictInfo()
    if len(ec2) < 8:
        ec2.createNewInstance()
        redistribute_memcache()
        return webapp.response_class(
            json.dumps("success"),
            status=200,
            mimetype='application/json',
            content_type='application/json'
        )
    return webapp.response_class(
        json.dumps("already 8 nodes"),
        status=400,
        mimetype='application/json',
        content_type='application/json'
    )

# # decrease nodes in manual mode


@webapp.route('/decrease', methods=["POST"])
def manual_decrease():

    ec2.updateAndRefreshDictInfo()
    if len(ec2) > 1:
        index = random.randint(0, len(ec2.ec2Dict)-1)
        terminate_id = list(ec2.ec2Dict.keys())[index]
        poped_node = ec2.ec2Dict.pop(terminate_id)
        redistribute_memcache(pop_node=poped_node, terminate_id=terminate_id)
        # ec2.terminateInstance(terminate_id)
        # terminate a node randomly
        return webapp.response_class(
            json.dumps("success"),
            status=200,
            mimetype='application/json',
            content_type='application/json'
        )
    return webapp.response_class(
        json.dumps("there is no node"),
        status=400,
        mimetype='application/json',
        content_type='application/json'
    )


@webapp.route('/stats')
def stats():

    now = datetime.utcnow()
    l_miss_rate_dict = {}
    l_miss_rate = []
    for instanceId in ec2.ec2Dict.keys():
        response = cloud_client.get_metric_statistics(
            Namespace='memcache',
            Dimensions=[
                {
                    'Name': 'InstanceId',
                    'Value': str(instanceId)
                }
            ],
            MetricName='missRate',
            StartTime=now - timedelta(seconds=1800),
            EndTime=now,
            Period=60,
            Statistics=[
                'Maximum'
            ],
            Unit='Percent'
        )
        for r in response['Datapoints']:
            new_key = ((now - r['Timestamp'].replace(tzinfo=None)).seconds//60) % 60
            if new_key in l_miss_rate_dict.keys():
                l_miss_rate_dict[new_key
                                 ] = l_miss_rate_dict[new_key] + r['Maximum']
            else:
                l_miss_rate_dict.setdefault(new_key, r['Maximum'])

    l = l_miss_rate_dict.keys()

    for key in sorted(l, reverse=True):
        l_miss_rate.append([30 - key, l_miss_rate_dict[key]])

    for timepair in l_miss_rate:
        timepair[1] = timepair[1] / len(ec2)

    l_hit_rate_dict = {}
    l_hit_rate = []
    for instanceId in ec2.ec2Dict.keys():
        response = cloud_client.get_metric_statistics(
            Namespace='memcache',
            Dimensions=[
                {
                    'Name': 'InstanceId',
                    'Value': str(instanceId)
                }
            ],
            MetricName='hitRate',
            StartTime=now - timedelta(seconds=1800),
            EndTime=now,
            Period=60,
            Statistics=[
                'Maximum'
            ],
            Unit='Percent'
        )
        for r in response['Datapoints']:
            new_key = ((now - r['Timestamp'].replace(tzinfo=None)).seconds//60) % 60
            if new_key in l_hit_rate_dict.keys():
                l_hit_rate_dict[new_key
                                ] = l_hit_rate_dict[new_key] + r['Maximum']
            else:
                l_hit_rate_dict.setdefault(new_key, r['Maximum'])

    l = l_hit_rate_dict.keys()

    for key in sorted(l, reverse=True):
        l_hit_rate.append([30 - key, l_hit_rate_dict[key]])

    for timepair in l_hit_rate:
        timepair[1] = timepair[1] / len(ec2)

    l_size_dict = {}
    l_size = []
    for instanceId in ec2.ec2Dict.keys():
        response = cloud_client.get_metric_statistics(
            Namespace='memcache',
            Dimensions=[
                {
                    'Name': 'InstanceId',
                    'Value': str(instanceId)
                }
            ],
            MetricName='CacheSize',
            StartTime=now - timedelta(seconds=1800),
            EndTime=now,
            Period=60,
            Statistics=[
                'Maximum'
            ],
            Unit='Megabytes'
        )
        for r in response['Datapoints']:
            new_key = ((now - r['Timestamp'].replace(tzinfo=None)).seconds//60) % 60
            if new_key in l_size_dict.keys():
                l_size_dict[new_key
                            ] = l_size_dict[new_key] + r['Maximum']
            else:
                l_size_dict.setdefault(new_key, r['Maximum'])

    l = l_size_dict.keys()

    for key in sorted(l, reverse=True):
        l_size.append([30 - key, l_size_dict[key]])

    for timepair in l_size:
        timepair[1] = timepair[1] / len(ec2)

    l_num_item_dict = {}
    l_num_item = []
    for instanceId in ec2.ec2Dict.keys():
        response = cloud_client.get_metric_statistics(
            Namespace='memcache',
            Dimensions=[
                {
                    'Name': 'InstanceId',
                    'Value': str(instanceId)
                }
            ],
            MetricName='itemInCache',
            StartTime=now - timedelta(seconds=1800),
            EndTime=now,
            Period=60,
            Statistics=[
                'Maximum'
            ],
            Unit='Count'
        )
        for r in response['Datapoints']:
            new_key = ((now - r['Timestamp'].replace(tzinfo=None)).seconds//60) % 60
            if new_key in l_num_item_dict.keys():
                l_num_item_dict[new_key
                                ] = l_num_item_dict[new_key] + r['Maximum']
            else:
                l_num_item_dict.setdefault(new_key, r['Maximum'])

    l = l_num_item_dict.keys()

    for key in sorted(l, reverse=True):
        l_num_item.append([30 - key, l_num_item_dict[key]])

    for timepair in l_num_item:
        timepair[1] = timepair[1] / len(ec2)

    l_requests_dict = {}
    l_requests = []
    for instanceId in ec2.ec2Dict.keys():
        response = cloud_client.get_metric_statistics(
            Namespace='memcache',
            Dimensions=[
                {
                    'Name': 'InstanceId',
                    'Value': str(instanceId)
                }
            ],
            MetricName='RequestCount',
            StartTime=now - timedelta(seconds=1800),
            EndTime=now,
            Period=60,
            Statistics=[
                'Maximum'
            ],
            Unit='Count'
        )
        for r in response['Datapoints']:

            new_key = ((now - r['Timestamp'].replace(tzinfo=None)).seconds//60) % 60

            if new_key in l_requests_dict.keys():
                l_requests_dict[new_key] = l_requests_dict[new_key] + r['Maximum']
            else:
                l_requests_dict.setdefault(new_key, r['Maximum'])

    l = l_requests_dict.keys()

    for key in sorted(l, reverse=True):
        l_requests.append([30 - key, l_requests_dict[key]])

    for timepair in l_requests:
        timepair[1] = timepair[1] / len(ec2)

    return render_template("stats.html",
                           l_size=l_size,
                           l_num_item=l_num_item,
                           l_requests=l_requests,
                           l_miss_rate=l_miss_rate,
                           l_hit_rate=l_hit_rate)


@webapp.route('/config')
def charts():
    ec2.updateAndRefreshDictInfo()
    return render_template("config.html", node_num=len(ec2))


@webapp.route('/configMemCache', methods=['POST'])
def configMemCache():
    capacity = request.form.get("capacity")
    policy = request.form.get("policy")
    # ec2.updateAndRefreshDictInfo()
    # get all the ips of ec2s
    ips = ec2.getAllIps()


    for i in ips:
        url = "http://" + i + ":5000/configureApi"
        re = requests.post(url, {"capacity": capacity, "policy": policy})

        re2 = requests.post("http://" + i + ":5000/backEnd/refresh_config")

    re = webapp.response_class(
        json.dumps("success"),
        status=200,
        mimetype='application/json',
        content_type='application/json'
    )
    return re

@webapp.route("/switchToManual", methods=['POST','GET'])
def switchToManual():

    # conn = database_connector()
    # cur = conn.cursor()
    # qurey = '''UPDATE autoScalerConfig SET mode=0 where id = 0;'''
    # cur.execute(qurey)
    # query_results = cur.fetchall()
    # print(query_results)

    re = requests.post(url=host+"autoscaler/turnOnManual")
    return  webapp.response_class(
        json.dumps("success chane to manual"),
        status=200,
        mimetype='application/json',
        content_type='application/json'
    )

@webapp.route("/switchToAuto", methods=['POST','GET'])
def switchToAuto():

    re = requests.post(url=host+"autoscaler/turnOnAuto")
    # conn = database_connector()
    # cur = conn.cursor()
    # qurey = '''UPDATE autoScalerConfig SET mode=1 where id = 0;'''
    # cur.execute(qurey)
    # query_results = cur.fetchall()
    # print(query_results)

    return webapp.response_class(
        json.dumps("success chane to Auto"),
        status=200,
        mimetype='application/json',
        content_type='application/json'
    )


@webapp.route('/configautoscaler')
def configautoscaler():
    return render_template("configautoscaler.html")


@webapp.route('/APIconfigAutoScale', methods=['POST', 'GET'])
def APIconfigAutoScale():
    missrate_max = request.form.get("missrate_max")

    missrate_min = request.form.get("missrate_min")

    expand_ratio = request.form.get("expand_ratio")

    shrink_ratio = request.form.get("shrink_ratio")

    print(
        f"update config data for scaler: {missrate_max},{missrate_min},{expand_ratio},{shrink_ratio}")

    # connect to database
    conn = database_connector()
    cur = conn.cursor()

    # update database table
    query = "SELECT * from autoScalerConfig "
    cur.execute(query)
    result = cur.fetchall()
    
    print("updating autoscaler config")
    query = "UPDATE autoScalerConfig SET mode = 0, maxMissRate = (%s), minMissRate = (%s), ExpandRatio = (%s), ShrinkRatio = (%s) WHERE id = 1 "
    cur.execute(query, (missrate_max, missrate_min,
                expand_ratio, shrink_ratio))
    conn.close()
    #ask the autoscaler to refresh the policy 
    re2 = requests.post(host+"autoscaler/refreshPolicy")


    return render_template(
        "configautoscaler.html", success=True)


@webapp.route('/Delete', methods=['POST'])
def Delete():
    # delete everything in database
    conn = database_connector()
    cur = conn.cursor()
    query = "DELETE FROM KeyList where name != 10000"
    cur.execute(query)
    conn.close()
    # delete everything in s3
    keys = []
  
    bucket_name = "memcache-bucket"
    resp = client_s3.list_objects_v2(Bucket=bucket_name)
    if 'Contents' not in resp.keys():
        pass
    else:
        for obj in resp['Contents']:
            keys.append(obj['Key'])

        for key in keys:
            client_s3.delete_object(Bucket=bucket_name, Key=key)
    ec2.updateAndRefreshDictInfo()
    clearMemcache()

    return render_template(
        "config.html", clearall=True)


@webapp.route('/clearMemcache', methods=['POST'])
# TODO:clear all memecache
def clearMemcache():
    # ec2.updateAndRefreshDictInfo()
    # get all the ips of ec2s
    ips = ec2.getAllIps()

    for i in ips:
        url = "http://" + i + ":5000/configureApi"
        re2 = requests.get("http://" + i + ":5000/backEnd/clear")

    return webapp.response_class(
        json.dumps("success"),
        status=200,
        mimetype='application/json',
        content_type='application/json'
    )


@webapp.route('/getAllIps', methods=['GET'])
def getAllip():
    # get all the ips of ec2s
    ips = ec2.getAllIps()

    return ips


@webapp.route('/getAllIds', methods=['GET'])
def getAllids():
    return list(ec2.ec2Dict.keys())


def redistribute_memcache(pop_node=None, terminate_id=None):
    
    if pop_node == None:
        time.sleep(60)
        for instanceid in ec2.ec2Dict.keys():
            ip = ec2.ec2Dict[instanceid]['PublicIpAddress']

            ip_str = "http://" + ip + ":5000/backEnd/distribute"
            data = {"ip":ip}
            re = requests.post(ip_str, json=data)
    else:
        
        ip = pop_node["PublicIpAddress"]
        ip_str = "http://" + ip + ":5000/backEnd/distribute"
        data = {"ip":ip}

        re = requests.post(ip_str, json=data)


        ec2.terminateInstance(terminate_id)
        ec2.updateAndRefreshDictInfo()

        for instanceid in ec2.ec2Dict.keys():
            ip = ec2.ec2Dict[instanceid]['PublicIpAddress']
            ip_str = "http://" + ip + ":5000/backEnd/distribute"
            data = {"ip":ip}
            re = requests.post(ip_str,json=data)

    return webapp.response_class(
        json.dumps("success"),
        status=200,
        mimetype='application/json',
        content_type='application/json'
    )
