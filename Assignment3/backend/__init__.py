from genericpath import isdir
from glob import glob
from flask import Flask
import os
global memcache
from backend.config import db_config
import shutil

webapp = Flask(__name__)

# TODO
memcache = {} # each value in memcache is a dict {'name': , 'timeStamp':}

# TODO num_miss... 改为Dictionary， key -> username, item -> value...

num_miss = {} # number of miss
num_hit = {} # number of hit
requestsCount = {} # number of successful service with status 200
miss_rate = {} # miss rate
capacity = {} 
# 1024*1024*100 # test for 100 MB

policy = {}
# initial polcy RANDOM

from backend import main




