from flask import render_template, url_for, request, g, redirect
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
import hashlib
def Md5(key):
    result = hashlib.md5(key.encode())
    hex = result.hexdigest()
    remainder = int(hex, base=16) % 16
    
    # get all the ips from mangerapp
    mangerapp_url =  "http://127.0.0.1:5001/getAllIps"
    res = requests.get(mangerapp_url)
    res = res.json()
    if len(res) != 0:
       node_chosen = remainder % len(res)
    
    ip = res[node_chosen]
    return ip

