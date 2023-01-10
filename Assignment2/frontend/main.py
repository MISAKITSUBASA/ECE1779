from logging import error
from flask import render_template, request, g,redirect,url_for
from frontend import webapp, memcache
from frontend.config import folder, db_config
from flask import json
import mysql.connector
import os
import requests
import base64
import uuid
import boto3
from apscheduler.schedulers.background import BackgroundScheduler
client_s3 = boto3.client('s3', region_name='us-east-1',aws_access_key_id='AKIAUJYC64AA3Y5YLEPM',
                          aws_secret_access_key='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')
import hashlib
from ec2_metadata import ec2_metadata

host = "http://18.208.169.223:5000/" #manger app ip not the same every time
# db connection is referenced from 1779-week-4-exercises
def connect_to_database():
    return mysql.connector.connect(user=db_config['user'],
                                   password=db_config['password'],
                                   host=db_config['host'],
                                   port = db_config['port'],
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

#upload the image to the local
@webapp.route('/api/upload', methods=['POST'])
def uploadApi():
    key = ""
    file = ""
    try:
        key = request.json["key"]
    except:
        key = request.form.get("key")
    
    file = request.files['file']

   
    if key =="":
        response = {
            "success": "false",
            "error": {
                "code": 400,
                "message": "no key provided"
            }
        }
        return render_template("upload.html",success=False)
    if not file:
        response = {
            "success": "false",
            "error": {
                "code": 400,
                "message": "Bad Request"
            }
        }
        return render_template("upload.html",success=False)

    file_name = str(uuid.uuid4()) + file.filename

    # make database connection
    cnx = get_db()
    cursor = cnx.cursor()
    # check if the key is already in the database
    query = "SELECT * FROM KeyList WHERE name = " + key
    cursor.execute(query)
    rows = cursor.fetchall()


    # create the image folder if not exit
    # if not os.path.isdir(folder):
    #     os.mkdir(folder)
    # file_path = os.path.join(folder, file_name)

    if len(rows) > 0:
        # key aleady exist so we update the data in the db
        query = "UPDATE KeyList SET path= '" + file_name + "' WHERE name = " + key
        cursor.execute(query)
        
        #TODO invalidate key
        #re = requests.post(host+"invalidate/" + key)

    if len(rows) == 0:
        # key does not exist insert the data in the db
        cursor.execute(
            "INSERT INTO KeyList (name,path) VALUES (%s, %s)", (key, file_name))
        cursor.execute(query)

    client_s3.upload_fileobj(file, "memcache-bucket",file_name)
    cnx.close()

    #invaidate key
    # check the hash and route it to the correct host
    route_ip = Md5(key)
    re = requests.post(route_ip + "invalidate/" + key)
    
    return render_template("upload.html",success=True)


@webapp.route('/upload')
def upload():
    return render_template("upload.html")


@webapp.route('/clear')
def clear():
    ip = ec2_metadata.public_ipv4
    re = requests.get("http://"+ip +":5000/backEnd/clear")
    return  render_template("configure.html",clear=True)

@webapp.route('/showPic', methods=['GET', 'POST'])
def show():
    '''
        This Function is used to display the showPic html and handle respones
    '''
    try:
        key_value = request.json["key_value"]
    except:
        # get the key_value from the request
        key_value = request.form.get("key_value")
    # get key_value
    if key_value != None and key_value != "":
        route_ip = Md5(key_value)
        if(route_ip):
            re = requests.post(route_ip + "backEnd/api/key/" + key_value)
        else:
            return webapp.response_class(
                    response=json.dumps("No ip found "),
                    status=404,
                    mimetype='application/json'
                ) 
        # get json data
        data = re.json()
        # case handle for not have the key in memcache
        if "error" in data.keys() and data['error']['code'] == 404:
            # make database connection
            cnx = get_db()
            cursor = cnx.cursor()

            # get the path for the image
            query = "SELECT path FROM KeyList WHERE name = " + key_value
            cursor.execute(query)
            # fetchall all rows
            rows = cursor.fetchall()

            # no such key finded
            if len(rows) == 0:
                # send not found
                return webapp.response_class(
                    response=json.dumps("No such key"),
                    status=404,
                    mimetype='application/json'
                )

            cnx.close()
            #get data from s3
            data = client_s3.get_object(Bucket = "memcache-bucket", Key = rows[0][0])['Body'].read()
            data = base64.b64encode(data)
            # # get binary data from itw
            # with open(rows[0][0], "rb") as image_file:
            #     data = base64.b64encode(image_file.read())

            re = requests.post(route_ip + "backEnd/putImage/" + key_value,
                               json={key_value: data.decode()})
            
            # rerender the page with content
            return render_template("showPic.html", source="data:image/jpg;base64, " + data.decode())

        # rerender the page with content
        return render_template("showPic.html", source="data:image/jpg;base64, " + data["content"])

    return render_template("showPic.html")


@webapp.route('/get_all_keys', methods=['GET'])
def getkeys():
    db = connect_to_database()
    cursor = db.cursor()
    # display all keys in the table "KeyList"
    query = "SELECT * FROM KeyList"
    cursor.execute(query)
    view = render_template("display_keys.html",
                           title="All Keys", cursor=cursor)
    db.close()
    return view


#  run the schduler on start
def initialize():
    # apsched = BackgroundScheduler()
    # apsched.start()
    # apsched.add_job(run_job, trigger="interval", seconds=5)
    return None


# Please rewrite the html file 'configure.html'!!!
@webapp.route('/configureApi', methods=['GET', 'POST'])
def configApi():
    db = connect_to_database()
    cursor = db.cursor()

    try:
        capacity = request.json["capacity"]
        policy = request.json["policy"]

    except:
        capacity = request.form.get("capacity")
        policy = request.form.get("policy")

    query = "SELECT * from config "
    cursor.execute(query)
    result = cursor.fetchall()

    query = "UPDATE config SET capacity = (%s), policy = (%s) WHERE ID = 1 "
    cursor.execute(query, (capacity, policy))

    if len(result) == 0:
        query = "INSERT config SET id = 1, capacity = (%s), policy = (%s)"
        cursor.execute(query, (capacity, policy))
                             
    db.close()
    return render_template(
        "configure.html",success=True)

# read stats from db to use in the plot gragh
@webapp.route('/statistics', methods=['GET', 'POST'])
def statistics():
    # make database connection
    cnx = get_db()       
    cursor = cnx.cursor()

    # get the path for the image
    query ="SELECT * FROM memcache.stats ORDER BY id DESC LIMIT 120"
    cursor.execute(query)
    # fetchall all rows
    rows = cursor.fetchall()
    
    l_num_item = []
    l_size = []
    l_requests = []
    l_miss_rate = []
    l_hit_rate = []
    time = 0
    rows = rows[::-1]

    for row in rows:
        l_size.append([time, row[1]])
        l_num_item.append([time, row[2]])
        l_requests.append([time, row[3]])
        l_miss_rate.append([time, row[4]])
        l_hit_rate.append([time, row[5]])
        time = time + 5

    return render_template("statistics.html",
        l_size = l_size,
        l_num_item = l_num_item,
        l_requests= l_requests,
        l_miss_rate= l_miss_rate,
        l_hit_rate= l_hit_rate)

@webapp.route('/configure', methods=['GET', 'POST'])
def config():
    view = render_template(
        "configure.html")
    return  view



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