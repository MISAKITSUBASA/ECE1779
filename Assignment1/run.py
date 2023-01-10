from werkzeug.middleware.dispatcher import DispatcherMiddleware
from frontend import webapp as frontEnd
from backend import webapp as backEnd
from flask import Flask

from werkzeug.serving import run_simple

app= DispatcherMiddleware(frontEnd, {
    '/backEnd': backEnd
})
run_simple('0.0.0.0', 5000, app, use_debugger=False, use_reloader=True, use_evalex=True, threaded= True)
