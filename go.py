#!/usr/bin/env python

from globusonline.transfer.api_client import x509_proxy, Transfer, create_client_from_args
import datetime
import time
import getpass
import re

#Endpoints
src_machine="rontrompert#ronsmac"
dest_machine="surfsara#dCache_gridftp"

#Myproxy server
myproxy="px.grid.sara.nl"

#Amount of hours that the transfers are allowed to take
max_hours=12

#Input file
file="inputfile"


api=None
username=None
passwd=None
m=re.compile('(\S+)\s+(\S+)')

def activate(endpoint_name):
# Try autoactivate when the proxy expires within 1 hour
# Set 1 hour in seconds, if transfers will take longer, set the value accordingly
    code, reason, result = api.endpoint_autoactivate(endpoint_name,
                                                     if_expires_in=3600*max_hours)
    if result["code"].startswith("AutoActivationFailed"):
# Autoactivation failed. Let's try manual activation
        reqs = api.endpoint_activation_requirements(endpoint_name, type="myproxy")[2]
        reqs.set_requirement_value("myproxy", "hostname",myproxy)

        reqs.set_requirement_value("myproxy", "username",username)
        reqs.set_requirement_value("myproxy", "passphrase",passwd)
        reqs.set_requirement_value("myproxy", "lifetime_in_hours",str(max_hours))
        result = api.endpoint_activate(endpoint_name,reqs)

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

if __name__ == '__main__':

    api, _ = create_client_from_args()
    username=raw_input('Enter Myproxy username:')
    passwd=getpass.getpass('Enter MyProxy pass phrase:')
    activate(src_machine)
    activate(dest_machine)

    code, message, data = api.transfer_submission_id()
    submission_id = data["value"]
    deadline = datetime.datetime.utcnow() + datetime.timedelta(hours=max_hours)
    sync_level=None
    label=None
    t = Transfer(submission_id, src_machine, dest_machine, deadline,sync_level,label,verify_checksum=False)

    f=open(file,'r')
    list=f.readlines()
    f.close

    for line in list:
        mtch=m.match(line)
        if mtch==None:
            sys.stderr.write('Invalid input in input file.\n')
            sys.exit(1)
        paths=mtch.groups()
        if len(paths)!=2:
            sys.stderr.write('Invalid input in input file.\n')
            sys.exit(1)

        t.add_item(paths[0], paths[1])
    code, reason, data = api.transfer(t)
    task_id = data["task_id"]

#    display_tasksummary(); print
    display_task(task_id); print
