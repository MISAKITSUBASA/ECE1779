from logging import error
from flask import render_template, request, g, redirect, url_for, flash
from frontend import webapp, memcache
from frontend.config import folder, db_config
from flask import json
import os
import requests
import base64
import uuid
import boto3
import mysql
import sys
from frontend.cognito_idp_actions import CognitoIdentityProviderWrapper

client_lambda = boto3.client(
    "lambda",
    region_name="us-east-1",
    aws_access_key_id="AKIAUJYC64AA3Y5YLEPM",
    aws_secret_access_key="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",
)
cognito_client_id = "45fv086p1rdnsdmgstgutch14n"
user_pool_id = "us-east-1_aPrJccD9Q"

client_Rekognition = boto3.client(
    "rekognition",
    region_name="us-east-1",
    aws_access_key_id="AKIAUJYC64AA3Y5YLEPM",
    aws_secret_access_key="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",
)
cognito_client = boto3.client(
    "cognito-idp",
    region_name="us-east-1",
    aws_access_key_id="AKIAUJYC64AA3Y5YLEPM",
    aws_secret_access_key="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",
)

client_s3 = boto3.client(
    "s3",
    region_name="us-east-1",
    aws_access_key_id="AKIAUJYC64AA3Y5YLEPM",
    aws_secret_access_key="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",
)

client_dDB = boto3.client(
    "dynamodb",
    region_name="us-east-1",
    aws_access_key_id="AKIAUJYC64AA3Y5YLEPM",
    aws_secret_access_key="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",
)

host = "https://vb262exj8i.execute-api.us-east-1.amazonaws.com/dev/"  # manger app ip not the same every time
cog_wrapper = CognitoIdentityProviderWrapper(
    cognito_client, user_pool_id, cognito_client_id
)

global user_name
global logedin
global email

logedin = False
user_name = None
email = None


# db connection is referenced from 1779-week-4-exercises
def connect_to_database():
    return mysql.connector.connect(
        user=db_config["user"],
        password=db_config["password"],
        host=db_config["host"],
        port=db_config["port"],
        database=db_config["database"],
        autocommit=True,
    )


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = connect_to_database()
    return db


@webapp.teardown_appcontext
def teardown_db(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


@webapp.route("/")
def main():
    return render_template("main.html", success=logedin)


@webapp.route("/signout")
def signout():
    global logedin
    global user_name
    logedin = False
    user_name = None
    return render_template("main.html", success=logedin)


# upload the image to the local
@webapp.route("/api/upload", methods=["POST"])
def uploadApi():
    key = ""
    file = ""
    try:
        key = request.json["key"]
    except:
        key = request.form.get("key")

    file = request.files["file"]

    if key == "":
        response = {
            "success": "false",
            "error": {"code": 400, "message": "no key provided"},
        }
        available_space = storage()
        return render_template(
            "upload.html",
            success_up=False,
            success=logedin,
            available_space=available_space,
        )
    if not file:
        response = {
            "success": "false",
            "error": {"code": 400, "message": "Bad Request"},
        }
        available_space = storage()
        return render_template(
            "upload.html",
            success_up=False,
            success=logedin,
            available_space=available_space,
        )

    file_name = file.filename

    users3map = get_user_s3_map()
    available_space = storage()
    response = client_s3.list_objects_v2(Bucket=users3map)
    old = response["KeyCount"]

    try:
        response = client_Rekognition.detect_labels(
            Image={
                "S3Object": {
                    "Bucket": users3map,
                    "Name": key,
                },
            },
            MaxLabels=1,
        )
        print(response)
        label = response["Labels"][0]["Name"]
    except:
        label = "did not find the object"

    print(label, "label")
    response = client_s3.delete_object(Bucket=users3map, Key=key)

    data = {"user_name": user_name}

    re = requests.post(host + "invalidate/" + key, json=data)

    response = client_s3.list_objects_v2(Bucket=users3map)

    client_s3.put_object(Body=file, Bucket=users3map, Key=key, ContentType="image/jpeg")

    response = client_s3.list_objects_v2(Bucket=users3map)
    new = response["KeyCount"]
    file_size = 0
    for item in response["Contents"]:
        if key == item["Key"]:
            file_size = item["Size"]
    print(file_size)
    print(available_space, "available_space")
    print(
        available_space * 1024 * 1024 > file_size,
        "available_space*1024*1024 > file_size",
    )
    print(old == new)

    if old < new and available_space * 1024 *1024 > file_size:
        # handle AI label
        # get label from AI
        response = client_Rekognition.detect_labels(
            Image={
                "S3Object": {
                    "Bucket": users3map,
                    "Name": key,
                },
            },
            MaxLabels=1,
        )

        label = response["Labels"][0]["Name"]

        # get key exist ['Item'] in side
        response = client_dDB.get_item(
            TableName=user_name + "Label", Key={"label": {"S": label}}
        )

        if "Item" not in response.keys():
            # no label exisit
            response = client_dDB.put_item(
                TableName=user_name + "Label",
                Item={"label": {"S": label}, "keys": {"SS": [key]}},
            )
            # print("add new label to table", response)
        else:

            old_keys = response["Item"]["keys"]["SS"]
            old_keys.append(key)
            old_keys = list(dict.fromkeys(old_keys))
            response = client_dDB.update_item(
                TableName=user_name + "Label",
                Key={"label": {"S": label}},
                AttributeUpdates={"keys": {"Value": {"SS": old_keys}}},
            )
            # print("Update label table", response)
        available_space = storage()
        return render_template(
            "upload.html",
            success=logedin,
            success_up=True,
            available_space=available_space,
        )
    elif new == old and available_space * 1024 * 1024 > file_size:
        print("entered ")
        print(label, "new label")
        response = client_dDB.get_item(
            TableName=user_name + "Label", Key={"label": {"S": label}}
        )
        keys = response["Item"]["keys"]["SS"]
        keys.remove(key)
        if len(keys) > 0:
            response = client_dDB.update_item(
                TableName=user_name + "Label",
                Key={"label": {"S": label}},
                AttributeUpdates={"keys": {"Value": {"SS": keys}}},
            )
        else:
            response = client_dDB.delete_item(
                TableName=user_name + "Label",
                Key={
                    "label": {
                        "S": label,
                    }
                },
            )

        response = client_Rekognition.detect_labels(
            Image={
                "S3Object": {
                    "Bucket": users3map,
                    "Name": key,
                },
            },
            MaxLabels=1,
        )

        label = response["Labels"][0]["Name"]

        response = client_dDB.get_item(
            TableName=user_name + "Label", Key={"label": {"S": label}}
        )

        if "Item" not in response.keys():
            # no label exisit
            response = client_dDB.put_item(
                TableName=user_name + "Label",
                Item={"label": {"S": label}, "keys": {"SS": [key]}},
            )
            # print("add new label to table", response)
        else:

            old_keys = response["Item"]["keys"]["SS"]
            old_keys.append(key)
            old_keys = list(dict.fromkeys(old_keys))
            response = client_dDB.update_item(
                TableName=user_name + "Label",
                Key={"label": {"S": label}},
                AttributeUpdates={"keys": {"Value": {"SS": old_keys}}},
            )

        available_space = storage()
        return render_template(
            "upload.html",
            success=logedin,
            success_up=True,
            available_space=available_space,
        )
    else:
        return render_template(
            "upload.html",
            success=logedin,
            success_up=False,
            excced=True,
            available_space=available_space,
        )


@webapp.route("/upload")
def upload():
    if not logedin:
        return render_template("login.html")
    available_space = storage()
    return render_template(
        "upload.html", success=logedin, available_space=available_space
    )


def storage():
    total_space = client_dDB.get_item(
        TableName="users3map",
        Key={"username": {"S": user_name}},
        AttributesToGet=[
            "s3limit",
        ],
    )["Item"]["s3limit"]["N"]
    total_space = float(total_space)
    users3map = get_user_s3_map()
    response = client_s3.list_objects_v2(Bucket=users3map)
    # print(response)
    used_space_bytes = 0
    if "Contents" in response.keys():
        for obj in response["Contents"]:
            used_space_bytes = obj["Size"] + used_space_bytes
    # print(total_space)
    available_space = total_space - (used_space_bytes / 1024 / 1024)

    return round(available_space, 2)


@webapp.route("/login", methods=["POST", "GET"])
def login():
    try:
        global user_name
        challenge = "ADMIN_USER_PASSWORD_AUTH"
        password = request.form.get("password")
        user_name = request.form.get("username")
        # print(password, "...,", type(password))
        # print(user_name, "....,", type(user_name))
        if challenge == "ADMIN_USER_PASSWORD_AUTH":
            if user_name and password:
                # print("enter")
                response = cog_wrapper.start_sign_in(user_name, password)
                if "AccessToken" in response["AuthenticationResult"]:
                    # print("log in successful!")
                    global logedin
                    logedin = True
                    # print(response["AuthenticationResult"]["AccessToken"])
                    # add memcache for user
                    re = requests.post(host + "addMemcache/" + user_name)
                    # print(re.content)
                    return render_template("main.html", success=True)
        return render_template("login.html", success=True)
    except Exception as e:
        # print(e)
        # print("wrong credential")
        return render_template("login.html", success=False)


@webapp.route("/confirm", methods=["POST", "GET"])
def confirm():
    user_default_limit = 10
    # print(email)
    code = request.form.get("code")
    if user_name and code:
        # print(user_name)
        confirmed = cog_wrapper.confirm_user_sign_up(user_name, code)
        # print(confirmed)
        # TODO
        # need to handle same email case.

        # handle wrong code

        if confirmed:
            # TODO
            # setup LAMBDA watch data usage
            # add S3 bucket using username

            # add trigger of S3 to the lambda function

            s3_bucket_name = str(uuid.uuid4()) + user_name
            arn = "arn:aws:s3:::" + s3_bucket_name
            response = client_s3.create_bucket(Bucket=s3_bucket_name)
            # add the permission to the lamda

            client_lambda.add_permission(
                FunctionName="photoApplicationTest",
                StatementId=s3_bucket_name,
                Action="lambda:InvokeFunction",
                Principal="s3.amazonaws.com",
                SourceArn=arn,
            )

            response = client_s3.put_bucket_notification_configuration(
                Bucket=s3_bucket_name,
                NotificationConfiguration={
                    "LambdaFunctionConfigurations": [
                        {
                            "LambdaFunctionArn": "arn:aws:lambda:us-east-1:295822090241:function:photoApplicationTest",
                            "Events": ["s3:ObjectCreated:*"],
                        }
                    ]
                },
            )

            # print(response)

            # add info to dymodb
            response = client_dDB.put_item(
                TableName="users3map",
                Item={
                    "username": {"S": user_name},
                    "s3map": {"S": s3_bucket_name},
                    "s3limit": {"N": str(user_default_limit)},
                    "email": {"S": email},
                },
            )
            # print(response)

            # add info to dymodb

            response = client_dDB.put_item(
                TableName="s3usersmap",
                Item={
                    "username": {"S": user_name},
                    "s3map": {"S": s3_bucket_name},
                    "email": {"S": email},
                },
            )
            # create memcacheStat
            response = client_dDB.create_table(
                TableName=str(user_name + "MecacheStat"),
                AttributeDefinitions=[
                    {"AttributeName": "id", "AttributeType": "N"},
                    {"AttributeName": "missrate", "AttributeType": "N"},
                ],
                KeySchema=[
                    {"AttributeName": "id", "KeyType": "HASH"},
                    {"AttributeName": "missrate", "KeyType": "RANGE"},
                ],
                ProvisionedThroughput={
                    "ReadCapacityUnits": 10,
                    "WriteCapacityUnits": 10,
                },
            )
            # print(response)
            # create user image label table
            response = client_dDB.create_table(
                TableName=str(user_name + "Label"),
                AttributeDefinitions=[
                    {"AttributeName": "label", "AttributeType": "S"},
                ],
                KeySchema=[
                    {"AttributeName": "label", "KeyType": "HASH"},
                ],
                ProvisionedThroughput={
                    "ReadCapacityUnits": 10,
                    "WriteCapacityUnits": 10,
                },
            )

            return render_template("login.html", success=True)

    return render_template("confirm.html")


@webapp.route("/resend", methods=["POST", "GET"])
def resendConfirm():
    delivery = cog_wrapper.resend_confirmation(user_name)
    """
    print(
        f"Confirmation code sent by {delivery['DeliveryMedium']} "
        f"to {delivery['Destination']}."
    )
    """
    return render_template("confirm.html")


@webapp.route("/signup", methods=["POST", "GET"])
def signup():
    global user_name
    global email

    email = request.form.get("email")
    password = request.form.get("password")
    user_name = request.form.get("username")
    if user_name and password and email:
        confirmed = cog_wrapper.sign_up_user(user_name, password, email)
        if not confirmed:
            return render_template("confirm.html")
        else:
            return render_template("login.html", success=True)
    return render_template("signup.html")


@webapp.route("/clear")
def clear():
    re = requests.get(host + "clear/" + user_name)

    # print(re.content)

    return render_template("configure.html", clear=True, success=logedin)


@webapp.route("/showPic", methods=["GET", "POST"])
def show():
    """
    This Function is used to display the showPic html and handle respones
    """
    try:
        key_value = request.json["key_value"]
    except:
        # get the key_value from the request
        key_value = request.form.get("key_value")

    # get key_value
    if key_value != None and key_value != "":
        data = {"user_name": user_name}
        # print(data)
        re = requests.post(host + "api/key/" + key_value, json=data)
        # get json data
        # print(re.content)
        data = re.json()
        print(data)
        # case handle for not have the key in memcache
        if "error" in data.keys() and data["error"]["code"] == 404:
            print("entered")
            users3map = get_user_s3_map()

            try:
                # get data from s3
                data = client_s3.get_object(Bucket=users3map, Key=key_value)[
                    "Body"
                ].read()
            except:
                return webapp.response_class(
                    response=json.dumps("No such key"),
                    status=404,
                    mimetype="application/json",
                )

            data = base64.b64encode(data)

            re = requests.post(
                host + "putImage/" + key_value,
                json={key_value: data.decode(), "user_name": user_name},
            )
            print("XXXXXXX")
            print(key_value)

            response = client_s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": users3map, "Key": key_value},
                ExpiresIn=60,
            )

            # rerender the page with content

            print(response, "resposne")

            return render_template(
                "showPic.html",
                source=response,
                success=logedin,
                key=key_value,
            )

        # rerender the page with content
        return render_template(
            "showPic.html",
            source="data:image/jpg;base64, " + data["content"],
            success=logedin,
            key=key_value,
        )

    return render_template("showPic.html", success=logedin)


@webapp.route("/get_all_keys", methods=["GET"])
def getkeys():
    keys = []

    users3map = get_user_s3_map()
    response = client_s3.list_objects_v2(Bucket=users3map)
    # print(response)
    if "Contents" in response.keys():
        for obj in response["Contents"]:
            keys.append((obj["Key"], obj["Size"], obj["LastModified"]))

    view = render_template(
        "display_keys.html", title="All Keys", cursor=keys, success=logedin
    )

    # db.close()
    return view


#  run the schduler on start
def initialize():
    return None


# Please rewrite the html file 'configure.html'!!!
@webapp.route("/configureApi", methods=["GET", "POST"])
def configApi():
    try:
        capacity = request.json["capacity"]
        policy = request.json["policy"]

    except:
        capacity = request.form.get("capacity")
        policy = request.form.get("policy")

    j = {"capacity": capacity, "policy": policy}
    # print(j)
    re = requests.post(host + "api/config_memcache/" + user_name, json=j)
    # print(re)
    # db = connect_to_database()
    # cursor = db.cursor()

    # try:
    #     capacity = request.json["capacity"]
    #     policy = request.json["policy"]

    # except:
    #     capacity = request.form.get("capacity")
    #     policy = request.form.get("policy")

    # query = "SELECT * from config "
    # cursor.execute(query)
    # result = cursor.fetchall()

    # query = "UPDATE config SET capacity = (%s), policy = (%s) WHERE ID = 1 "
    # cursor.execute(query, (capacity, policy))

    # if len(result) == 0:
    #     query = "INSERT config SET id = 1, capacity = (%s), policy = (%s)"
    #     cursor.execute(query, (capacity, policy))

    # db.close()
    return render_template("configure.html", success=logedin, success_config=True)


# read stats from db to use in the plot gragh
@webapp.route("/statistics", methods=["GET", "POST"])
def statistics():
    # make database connection
    cnx = get_db()
    cursor = cnx.cursor()

    # get the path for the image
    query = "SELECT * FROM memcache.stats ORDER BY id DESC LIMIT 120"
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

    return render_template(
        "statistics.html",
        l_size=l_size,
        l_num_item=l_num_item,
        l_requests=l_requests,
        l_miss_rate=l_miss_rate,
        l_hit_rate=l_hit_rate,
        success=logedin,
    )


@webapp.route("/gallery", methods=["GET", "POST"])
def gallery():
    allPics = []

    users3map = get_user_s3_map()
    # print(client_s3.list_objects_v2(Bucket=users3map), "@@@@@@@")
    if not logedin:
        return render_template("login.html")
    if "Contents" in client_s3.list_objects_v2(Bucket=users3map).keys():
        for my_bucket_object in client_s3.list_objects_v2(Bucket=users3map)["Contents"]:
            key = my_bucket_object["Key"]
            # print(key)

            # data = client_s3.get_object(Bucket=users3map, Key=key)["Body"].read()
            # # print(data)
            # data = base64.b64encode(data)
            response = client_s3.generate_presigned_url(
                "get_object", Params={"Bucket": users3map, "Key": key}, ExpiresIn=60
            )
            allPics.append(response)
            # allPics.append("data:image/jpg;base64," + data.decode())

        return render_template("gallery.html", allPics=allPics, success=logedin)
    else:
        return render_template(
            "gallery.html", allPics=[], no_pic="True", success=logedin
        )


@webapp.route("/configure", methods=["GET", "POST"])
def config():
    return render_template("configure.html", success=logedin, success_config=False)


def get_user_s3_map():
    global user_name
    # print(user_name, "Username")
    return client_dDB.get_item(
        TableName="users3map",
        Key={"username": {"S": user_name}},
        AttributesToGet=[
            "s3map",
        ],
    )["Item"]["s3map"]["S"]


@webapp.route("/showImageByLabel", methods=["GET", "POST"])
def showImageByLabel():
    response = client_dDB.scan(TableName=user_name + "Label", AttributesToGet=["label"])
    labels = []
    # print(response)
    for label in response["Items"]:
        labels.append(label["label"]["S"])
    # print(labels)

    return render_template("searchByLabel.html", labels=labels, success=logedin)


@webapp.route("/diplayByLabel", methods=["GET", "POST"])
def diplayByLabel():
    # print("entered")
    label = request.form.get("label")
    print(label, "XLabel")
    # print(label)
    allPics = []
    keys = []
    users3map = get_user_s3_map()
    # print(client_s3.list_objects_v2(Bucket=users3map), "@@@@@@@")

    response = client_dDB.get_item(
        TableName=user_name + "Label", Key={"label": {"S": label}}
    )
    # print(response)
    # print(response['Item']['keys']['SS'])
    keys = response["Item"]["keys"]["SS"].copy()
    # print(keys)
    if not logedin:
        return render_template("login.html")
    print(keys, "keys!!!!!")
    print(
        client_s3.list_objects_v2(Bucket=users3map).keys(),
        "client_s3.list_objects_v2(Bucket=users3map).keys()",
    )
    if "Contents" in client_s3.list_objects_v2(Bucket=users3map).keys():
        for my_bucket_object in client_s3.list_objects_v2(Bucket=users3map)["Contents"]:
            key = my_bucket_object["Key"]
            print(key, "Current Key")
            if key in keys:
                response = client_s3.generate_presigned_url(
                    "get_object", Params={"Bucket": users3map, "Key": key}, ExpiresIn=60
                )
                print(key, "key!!!!")
                print(response, "response!!!!")
                #     #print(key)
                #     data = client_s3.get_object(Bucket=users3map, Key=key)["Body"].read()
                #    # print(data)
                #     data = base64.b64encode(data)
                #     allPics.append("data:image/jpg;base64," + data.decode())
                allPics.append(response)
        return render_template("gallery.html", allPics=allPics, success=logedin)
    else:
        return render_template(
            "gallery.html", allPics=[], no_pic="True", success=logedin
        )


@webapp.route("/delete_img", methods=["GET", "POST"])
def delete_img():
    # delete img in labels
    print("****************HERE")
    key = request.form.get("key_value")
    print("***************KEY")
    print(key)
    users3map = get_user_s3_map()
    print("****************users3map")
    print(users3map)

    response = client_Rekognition.detect_labels(
        Image={
            "S3Object": {
                "Bucket": users3map,
                "Name": key,
            },
        },
        MaxLabels=1,
    )

    label = response["Labels"][0]["Name"]

    print("**********LABEL")
    print(label)

    response = client_dDB.get_item(
        TableName=user_name + "Label", Key={"label": {"S": label}}
    )
    print(response, "rrrr")
    print(label, "label")
    keys = response["Item"]["keys"]["SS"]

    print("*************old keys")
    print(keys)
    keys.remove(key)
    print("**************new keys")
    print(keys)
    if len(keys) > 0:
        response = client_dDB.update_item(
            TableName=user_name + "Label",
            Key={"label": {"S": label}},
            AttributeUpdates={"keys": {"Value": {"SS": keys}}},
        )
    else:
        response = client_dDB.delete_item(
            TableName=user_name + "Label",
            Key={
                "label": {
                    "S": label,
                }
            },
        )

    # delete image in s3

    response = client_s3.delete_object(
        Bucket=users3map,
        Key=key,
    )
    print("*****************response")
    print(response)

    keys = []
    response = client_s3.list_objects_v2(Bucket=users3map)
    # print(response)
    if "Contents" in response.keys():
        for obj in response["Contents"]:
            keys.append((obj["Key"], obj["Size"], obj["LastModified"]))

    # delete img in memcache
    data = {"user_name": user_name}

    re = requests.post(host + "invalidate/" + key, json=data)
    print("**********invalidate")
    print(re)

    view = render_template(
        "display_keys.html", title="All Keys", cursor=keys, success=logedin
    )
    return view
