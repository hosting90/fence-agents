#!@PYTHON@ -tt

import urllib,requests,json
import sys, re, signal
import atexit
import logging
sys.path.append("@FENCEAGENTSLIBDIR@")
from fencing import *

class HostingApi(object):
	def __init__(self, url, sid = None,fn = None):
		self.sid = sid
		self.fn = fn
		self.url = url
	
	def __getattr__(self, name):
		attr = type(self)(self.url,self.sid, name)
		
		return attr.__call__
	
	def __call__(self,**kwargs):
		"""docstring for __call"""
		if self.fn == None:
			return None
		if self.sid != None:
			kwargs['sid'] = self.sid
		if kwargs.has_key('post'):
			post_args = kwargs['post']
			del kwargs['post']
		else:
			post_args = None
		myurl = self.url+'/'+self.fn+'?reply=json&'+urllib.urlencode(kwargs)
		if post_args == None:
			u = requests.get(myurl)
			text = u.content
		else:
			u = requests.post(myurl, data=post_args)
			text = u.content
		
		ret = json.loads(text)
		
		if ret['reply']['status']['code'] == 0:
			del(ret['reply']['status'])
			return ret['reply']
		else:
			raise Exception((ret['reply']['status']['code'], ret['reply']['status']['text']))
		
	def login(self,uid,password):
		self.fn = 'login'
		self.sid = None
		ret = self.__call__(uid=uid,password=password)
		
		self.sid = ret['sid']
		return self
	
	def login_callback(self,login,callback_hash):
		self.fn = 'login_callback'
		self.sid = None
		ret = self.__call__(login=login,password=callback_hash)
		
		self.sid = ret['sid']
		return self

def name_to_id(conn,name):
	if name.isdigit():
		return name
	else:
		server_list = conn.vserver_list()['vservers']
		for vserver in server_list:
			if vserver['name'] == name or vserver['custom_name'] == name:
				return vserver['vserver_id']
		return None

def get_power_status(conn, options):
	if conn.vserver_detail(vserver_id = name_to_id(conn,options['--plug']))['vserver']['server_status'] == 'Running':
		return "on"
	else:
		return "off"

def get_outlets(conn, options):
	outlets = {}
	for vserver in conn.vserver_list()['vservers']:
		outlets[vserver['vserver_id']] = [vserver['custom_name'] if vserver['custom_name'] else vserver['name'], 'on' if vserver['server_status'] == 'Running' else 'off']
	return outlets

def set_power_status(conn, options):
	if options['--action'] == 'on':
		conn.vserver_start(vserver_id = name_to_id(conn,options['--plug']))
	else:
		conn.vserver_shutdown(vserver_id = name_to_id(conn,options['--plug']), timeout=0)
	return


def reboot_cycle(conn, options):
	print name_to_id(conn,options['--plug'])
	conn.vserver_reboot(vserver_id = name_to_id(conn,options['--plug']), timeout=0)
	return


def signal_handler(signum, frame):
	raise Exception("Signal \"%d\" received which has triggered an exit of the process." % signum)

def main():
	device_opt = ["ipaddr", "login", "passwd", "web", "ssl", "port", "method"]

	atexit.register(atexit_handler)

	signal.signal(signal.SIGTERM, signal_handler)

	options = check_input(device_opt, process_input(device_opt))
	
	all_opt['power_timeout']['default'] = 60
	
	##
	## Fence agent specific defaults
	#####
	docs = {}
	docs["shortdesc"] = "Fence agent for Hosting90 API"
	docs["longdesc"] = "fence_h90_api is an I/O Fencing agent \
which can be used with the virtual machines managed by Hosting90 \
Name of virtual machine (-n / port) is vserver_id, vserver_<id> or vserver name."
	docs["vendorurl"] = "http://www.hosting90.cz"
	show_docs(options, docs)

	logging.basicConfig(level=logging.INFO)
	logging.getLogger('suds.client').setLevel(logging.CRITICAL)
	logging.getLogger("requests").setLevel(logging.CRITICAL)
	logging.getLogger("urllib3").setLevel(logging.CRITICAL)
	##
	## Operate the fencing device
	####
	conn = HostingApi('https://'+options['--ip']+'/api')
	try:
		conn.login_callback(options['--username'],options['--password'])
	except:
		conn.login(options['--username'],options['--password'])
	

	##
	## Fence operations
	####
	result = fence_action(conn, options, set_power_status, get_power_status, get_outlets,reboot_cycle)
	sys.exit(result)

if __name__ == "__main__":
	main()
