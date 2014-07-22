HAProxyScaleLXC
===============

HAProxy Autoscale of LXC Containers



Reference Blog
Alex's Blog of Simple AutoScale with HAProxy

I guess it was the AWS blog videos where in one of the videos I saw a
discussion that NASA was using AWS autoscaling feature, which scales EC2
instances on the basis of traffic/load volume/processing. To be honest
this is not only NASA use case but a very generic use case for any
enterprise.

I thought that the AWS infrastructure was built such a way that this was
possible , I took it as a mental exercise to find out “How did they do
it?” which introduced me to various technology words such as Eucalyptus
which allows building of various “as-a-service” systems , until I came
across OpenShift Origin a open source PaaS where application sandboxes
aka Gears could be scaled on the basis of traffic/load. Reading
OpenShift Origin Ruby source code gave out a bunch of details but I was
looking for something more simple.

Alex’s blog gave a very good example of autoscaling with HAProxy with
fixed list servers in HAProxy backend configuration.

Using Alex’s blog as as stepping stone I wanted to take one more step to
and make the backend server list dynamic, by creating/destroying LXC
containers as per response times per request from HAProxy logs and
dynamically add/remove servers from HAProxy configurations with minimal
impact HAProxy restarts.

The setup again was simple : Host Machine : Mac OSX Maverick : I used
JMeter running on host to create increasing and decreasing HTTP Request
loads to test scale up and scale down. Ubuntu Guest on VirtualBox
(Bridged Network) LXC Containers on internal virtual bridge

As mentioned before ,the idea is to load balance a simple PHP webpage on
2 LXC containers which is done by HA Proxy. if the LXC container
response time in HAProxy logs > 1000 (Tt) in Httplog of HAProxy then a
new container has to be started and added to HA Proxy Backend server
list; The next container to be started is cloned from a template
container (not running but stopped) and readied before hand. Update has
to be made to haproxy.cfg file and haproxy restarted.

The pseudocode is

Process arguments 
Validate if future containers up until max are already existing …exit if any existing
Clone and ready containers up until stbcnt 
Append haproxy frontend definitions to haproxy.cfg 
Create stable containers list by getting IPadd (stb_list)
Append stb_list to haproxy.cfg Start all stable containers 
Start haproxy with pid file 
Clone and ready stbcnt + 1 container 
Tail logs 


Tail Logs Process would have the following steps

process Tt
if Tt > 1000
process and enable ready container
if current <= maxcnt
clone and ready next container 
else 
max containers reached 
else Tt << 200 
process and remove current container
destroy ready container 
stop the current container if running 
update ready to current


This is not a prime time auto scaling solution; but my attempt to build
some with components. I am indeed planning to test and further
improve.Again this was a fun project to work on.
