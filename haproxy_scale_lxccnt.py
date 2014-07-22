#!/usr/bin/python

# haproxy_scale_lxccnt.py

import re
import subprocess
import getopt
import sys
import threading
import time


num_cnt = 0
max_cnt = 5
stb_cnt = 2
curr_cnt = stb_cnt + 1
next_cnt = stb_cnt + 1 + 1
template = 'appweb0'
ntemp = ''
f_flag = 0
hap_frontend_text = '\nfrontend http-in\n        bind *:80\n        default_backend phpmy\n\nbackend phpmy\n'
ha_element = ''
ha_list = []

def process_args():
    global template
    global stb_cnt
    global max_cnt
    myopts, args = getopt.getopt(sys.argv[1:], 'm:s:t:')
    for o, a in myopts:
        if o == '-m':
            max_cnt = int(a)
        elif o == '-s':
            stb_cnt = int(a)
        elif o == '-t':
            template = str(a)
        else:
            print 'Usage:%s -m max_containers -s stable_containers -t template_containers'

    print 'Maxcount = %d\nStable Count = %d\nTemplate = %s' % (max_cnt, stb_cnt, template)


def validate_futures():
    global f_flag
    ret = subprocess.Popen(['lxc-ls'], stdout=subprocess.PIPE)
    out = ret.stdout.read()
    inst = out.split('\n')
    for num_cnt in range(1, max_cnt + 1):
        ntemp = template.replace('0', str(num_cnt))
        print ntemp
        if ntemp in inst:
            print '%s Already Running' % ntemp
            f_flag = 1
        else:
            print '%s not Already Running' % ntemp

    ret = subprocess.Popen(['lxc-ls', '--stopped'], stdout=subprocess.PIPE)
    out = ret.stdout.read()
    inst = out.split('\n')
    if template in inst:
        print 'Template is created and stopped'
    else:
        print 'Please ensure the template is created and not running'
        f_flag = 1
    if f_flag == 1:
        print 'Remove all instances.Only Template should be created and stopped'
        sys.exit(1)


def clone_and_ready_stb():
    for num_cnt in range(1, stb_cnt + 1):
        ntemp = template.replace('0', str(num_cnt))
        print 'Create Stb container %d %s' % (num_cnt, ntemp)
        ret = subprocess.Popen(['lxc-clone', template, ntemp])
        time.sleep(5)

    print 'All Stable Containers Created\n'


def append_hap_frontend():
    global hap_frontend_text
    with open('/etc/haproxy/haproxy.cfg', 'a') as hafile:
        hafile.write(hap_frontend_text)
    print 'HAProxy FrontEnd Config Updated'


def start_stbcnts():
    for num_cnt in range(1, stb_cnt + 1):
        ntemp = template.replace('0', str(num_cnt))
        print 'Starting Stable Container %d %s' % (num_cnt, ntemp)
        ret = subprocess.Popen(['lxc-start',
         '-n',
         ntemp,
         '-d'])
        time.sleep(10)

    print 'All Stable Containers started'


def create_append_hap_stb_list():
    serverstr = ''
    for num_cnt in range(1, stb_cnt + 1):
        ntemp = template.replace('0', str(num_cnt))
        ret = subprocess.Popen(['lxc-ls', '--fancy'], stdout=subprocess.PIPE)
        ret2 = subprocess.Popen(['grep', '-i', ntemp], stdin=ret.stdout, stdout=subprocess.PIPE)
        out = ret2.stdout.readline()
        outln = re.sub('\\s+', ':', out)
        ele = outln.split(':')
        serverstr = '%s \tserver %s %s:%d check\n' % (serverstr,
         ele[0],
         ele[2],
         80)

    with open('/etc/haproxy/haproxy.cfg', 'a') as hafile:
        hafile.write(serverstr)
    print 'Created and Appended Stable HA List'


def start_hap():
    ret = subprocess.Popen(['haproxy',
     '-f',
     '/etc/haproxy/haproxy.cfg',
     '-p',
     '/var/run/haproxy-private.pid'])
    time.sleep(5)


def ready_next_cnt():
    global next_cnt
    ntemp = template.replace('0', str(next_cnt))
    ret = subprocess.Popen(['lxc-clone', template, ntemp])
    time.sleep(5)



def tail_forever(fn):
    global f_flag
    tailh = subprocess.Popen(['tail','-f', fn], stdout=subprocess.PIPE)
    ucount = 0
    dcount = 0
    sumresptime = 0
    while 1:
	try:
        	line = tailh.stdout.readline()
        	st_line = line.split(' ')
        	timedet = st_line[9].split('/')
        	resptime = int(timedet[4])
		#print("Response Time : %d Count %d" % (resptime, ucount))
        	if resptime > 1000:
            		ucount = ucount + 1
		if ucount >= 400 and f_flag == 0 and curr_cnt < max_cnt:
			f_flag = 1
	    		print("Scale Up")
			scale_up()
	    		ucount = 0
		if ucount >=400 and f_flag == 1:
			ucount = 0

        	if resptime < 500 and curr_cnt > stb_cnt:
            		dcount = dcount + 1
		if dcount >= 50 and curr_cnt > stb_cnt and f_flag == 0 :
			f_flag = 1
			scale_down()
	    		print("Scale Down")
	    		dcount = 0
	except:
		pass
	
def scale_down():
	global f_flag,next_cnt,curr_cnt
	serverstr = ''
	print("In Scale F_flag %d %d starting" % (next_cnt,f_flag ))
	if f_flag == 1:
		print("destroying %d " % (curr_cnt+1) )
        	ntemp = template.replace('0', str(curr_cnt+1))
        	ret = subprocess.Popen(['lxc-destroy', '-n',ntemp])
		time.sleep(5)
		print("Stopping current  : %d" % curr_cnt)
        	ntemp = template.replace('0', str(curr_cnt))
        	ret = subprocess.Popen(['lxc-stop','-s','-n',ntemp])
		time.sleep(5)

		print "HA Proxy File remove %s" % ntemp

		haf = open("/etc/haproxy/haproxy.cfg","r")
		haf_lines = haf.readlines()
		haf.close()

		hafw = open("/etc/haproxy/haproxy.cfg.new","w")
		for line in haf_lines:
			if ntemp in line:
				pass
			else:
				hafw.write(line)
		hafw.close()

		retmv = subprocess.Popen(['mv','/etc/haproxy/haproxy.cfg.new','/etc/haproxy/haproxy.cfg'])	

		ret3 = subprocess.Popen(['cat','/var/run/haproxy-private.pid'],stdout=subprocess.PIPE)
		ha_pid = int(ret3.stdout.readline().strip("\n"))
		ret4 = subprocess.Popen(['haproxy','-f','/etc/haproxy/haproxy.cfg','-p','/var/run/haproxy-private.pid','-st',str(ha_pid)])
		print "Restarted HA Proxy"
		next_cnt = curr_cnt - 1
		print("Scale down done")
		curr_cnt = curr_cnt - 1
		f_flag = 0

def scale_up():
	global f_flag,next_cnt,curr_cnt
	serverstr = ''
	print("In Scale F_flag %d %d starting" % (next_cnt,f_flag ))
	if f_flag == 1:
		print("In Scale F_flag %d starting" % next_cnt )
        	ntemp = template.replace('0', str(next_cnt))
        	ret = subprocess.Popen(['lxc-start', '-n',ntemp,"-d"])
		time.sleep(5)
		print("Starting next : %d" % next_cnt)
        	ret = subprocess.Popen(['lxc-ls', '--fancy'], stdout=subprocess.PIPE)
        	ret2 = subprocess.Popen(['grep', '-i', ntemp], stdin=ret.stdout, stdout=subprocess.PIPE)
        	out = ret2.stdout.readline()
        	outln = re.sub('\\s+', ':', out)
        	ele = outln.split(':')
        	serverstr = '%s \tserver %s %s:%d check\n' % (serverstr,
         	ele[0],
         	ele[2],
         	80)

    		with open('/etc/haproxy/haproxy.cfg', 'a') as hafile:
        		hafile.write(serverstr)

		print "HA Proxy File updated"

		ret3 = subprocess.Popen(['cat','/var/run/haproxy-private.pid'],stdout=subprocess.PIPE)
		ha_pid = int(ret3.stdout.readline().strip("\n"))
		ret4 = subprocess.Popen(['haproxy','-f','/etc/haproxy/haproxy.cfg','-p','/var/run/haproxy-private.pid','-st',str(ha_pid)])
		print "Restarted HA Proxy"
		curr_cnt = curr_cnt + 1
		next_cnt = curr_cnt + 1
		ready_next_cnt()
		print "New Container Created"
		f_flag = 0

#Not Used was not comfortable with tail with threads
#def tail_logs_process():
#    fn = '/var/log/haproxy.log'
#   threading.Thread(target=tail_forever, args=(fn,)).start()


def main():
    global curr_cnt
    global next_cnt
   
    process_args()
    validate_futures()
    clone_and_ready_stb()
    append_hap_frontend()
    start_stbcnts()
    create_append_hap_stb_list()
    start_hap()
    curr_cnt = stb_cnt
    next_cnt = curr_cnt + 1
    ready_next_cnt()
    tail_forever("/var/log/haproxy.log")


if __name__ == '__main__':
    main()
