from werkzeug.middleware.dispatcher import DispatcherMiddleware
from managerApp import webapp as manager
from autoscaler import webapp as auto

from werkzeug.serving import run_simple

app= DispatcherMiddleware(manager, {
    '/autoscaler': auto,
})
run_simple('0.0.0.0', 5000, app, use_debugger=False, use_reloader=True, use_evalex=True, threaded= True)


