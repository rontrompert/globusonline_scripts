#!/usr/bin/env python

from globusonline.transfer.api_client import x509_proxy, Transfer, create_client_from_args
import traceback
import datetime
import time

#Endpoints
my_machine="rontrompert#ronsmac"
other_machine="surfsara#dCache"

api=None

def unicode_(data):
    """
    Coerce any type to unicode, assuming utf-8 encoding for strings.
    """
    if isinstance(data, unicode):
        return data
    if isinstance(data, str):
        return unicode(data, "utf-8")
    else:
        return unicode(data)

def display_activation(endpoint_name):
    print "=== Endpoint pre-activation ==="
    display_endpoint(endpoint_name)
    print
    code, reason, result = api.endpoint_autoactivate(endpoint_name,
                                                     if_expires_in=600)
    print "result: %s (%s)" % (result["code"], result["message"])
    if result["code"].startswith("AutoActivationFailed"):
        print "Auto activation failed, ls and transfers will likely fail!"
        reqs = api.endpoint_activation_requirements(endpoint_name, type="myproxy")[2]
        reqs.set_requirement_value("myproxy", "hostname","px.grid.sara.nl")
        reqs.set_requirement_value("myproxy", "username","ron")
        reqs.set_requirement_value("myproxy", "passphrase","XXXXXXXXXXX")
        result = api.endpoint_activate(endpoint_name,reqs)
    print "=== Endpoint post-activation ==="
    display_endpoint(endpoint_name)
    print

def display_endpoint(endpoint_name):
    code, reason, data = api.endpoint(endpoint_name)
    _print_endpoint(data)

def _print_endpoint(ep):
    name = ep["canonical_name"]
    print name
    if ep["activated"]:
        print "  activated (expires: %s)" % ep["expire_time"]
    else:
        print "  not activated"
    if ep["public"]:
        print "  public"
    else:
        print "  not public"
    if ep["myproxy_server"]:
        print "  default myproxy server: %s" % ep["myproxy_server"]
    else:
        print "  no default myproxy server"
    servers = ep.get("DATA", ())
    print "  servers:"
    for s in servers:
        uri = s["uri"]
        if not uri:
            uri = "GC endpoint, no uri available"
        print "    " + uri,
        if s["subject"]:
            print " (%s)" % s["subject"]
        else:
            print

def display_ls(endpoint_name, path=""):
    code, reason, data = api.endpoint_ls(endpoint_name, path)
    # Server returns canonical path; "" maps to the users default path,
    # which is typically their home directory "/~/".
    path = data["path"]
    print "Contents of %s on %s:" % (path, endpoint_name)
    headers = "name, type, permissions, size, user, group, last_modified"
    headers_list = headers.split(", ")
    print headers
    for f in data["DATA"]:
        print ", ".join([unicode_(f[k]) for k in headers_list])

def display_tasksummary():
    code, reason, data = api.tasksummary()
    print "Task Summary for %s:" % api.username
    for k, v in data.iteritems():
        if k == "DATA_TYPE":
            continue
        print "%3d %s" % (int(v), k.upper().ljust(9))

def display_tasksummary():
    code, reason, data = api.tasksummary()
    print "Task Summary for %s:" % api.username
    for k, v in data.iteritems():
        if k == "DATA_TYPE":
            continue
        print "%3d %s" % (int(v), k.upper().ljust(9))

def _print_task(data, indent_level=0):
    """
    Works for tasks and subtasks, since both have a task_id key
    and other key/values are printed by iterating through the items.
    """
    indent = " " * indent_level
    indent += " " * 2
    for k, v in data.iteritems():
        if k in ("DATA_TYPE", "LINKS"):
            continue
        print indent + "%s: %s" % (k, v)

def display_task(task_id, show_subtasks=True):
    code, reason, data = api.task(task_id)
    print "Task %s:" % task_id
    _print_task(data, 0)

    if show_subtasks:
        code, reason, data = api.subtask_list(task_id)
        subtask_list = data["DATA"]
        for t in subtask_list:
            print "  subtask %s:" % t["task_id"]
            _print_task(t, 4)

def wait_for_task(task_id, timeout=120):
    status = "ACTIVE"
    while timeout and status == "ACTIVE":
        code, reason, data = api.task(task_id, fields="status")
        status = data["status"]
        time.sleep(1)
        timeout -= 1

    if status != "ACTIVE":
        print "Task %s complete!" % task_id
        return True
    else:
        print "Task still not complete after %d seconds" % timeout
        return False

if __name__ == '__main__':

    api, _ = create_client_from_args()
    display_activation(my_machine)
    display_activation(other_machine)

    code, message, data = api.transfer_submission_id()
    submission_id = data["value"]
    deadline = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)
    t = Transfer(submission_id, "rontrompert#ronsmac", "surfsara#dCache", deadline)
    t.add_item("/Users/rontrompert/go.py", "/pnfs/grid.sara.nl/data/users/ron/testfile300")
    code, reason, data = api.transfer(t)
    task_id = data["task_id"]

    display_tasksummary(); print
    display_task(task_id); print

    if wait_for_task(task_id):
        print "=== After completion ==="
        display_tasksummary(); print
        display_task(task_id); print
        display_ls("surfsara#dCache","/pnfs/grid.sara.nl/data/users/ron/"); print
