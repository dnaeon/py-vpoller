/*-
 * Copyright (c) 2014 Marin Atanasov Nikolov <dnaeon@gmail.com>
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer
 *    in this position and unchanged.
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 *
 * THIS SOFTWARE IS PROVIDED BY THE AUTHOR(S) ``AS IS'' AND ANY EXPRESS OR
 * IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
 * OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
 * IN NO EVENT SHALL THE AUTHOR(S) BE LIABLE FOR ANY DIRECT, INDIRECT,
 * INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
 * NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 * THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
 * THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */


#include <zmq.h>

#include "threads.h"
#include "cfg.h"
#include "sysinc.h"
#include "module.h"
#include "log.h"

#define MODULE_CONFIG_FILE "/etc/zabbix/vpoller_module.conf"
#define VPOLLER_TASK_TEMPLATE "{ \
			           \"method\": \"%s\", \
			           \"hostname\": \"%s\", \
                                   \"name\": \"%s\", \
			           \"properties\": [ \"%s\" ], \
			           \"key\": \"%s\", \
			           \"helper\": \"vpoller.helpers.zabbix\" \
                               }"

int zbx_module_vpoller(AGENT_REQUEST *request, AGENT_RESULT *result);

/* The variable keeps timeout setting for item processing */
static int item_timeout = 0;

/* Default vPoller settings */
static unsigned CONFIG_VPOLLER_TIMEOUT = 10000;
static unsigned CONFIG_VPOLLER_RETRIES = 1;
static char    *CONFIG_VPOLLER_PROXY   = "tcp://localhost:10123";

/* ZeroMQ context used for creating sockets that connect to vPoller */ 
static void *zcontext = NULL;

/* Zabbix keys provided by this module */
static ZBX_METRIC keys[] = {
  /* KEY,       FLAG,          FUNCTION,           TEST PARAMS */
  { "vpoller",	CF_HAVEPARAMS, zbx_module_vpoller, NULL },
  { NULL },
};

/*
 * Function:
 *    zbx_module_load_config()
 * 
 * Purpose:
 *     Parses the vPoller module configuration file
 */
static void
zbx_module_load_config(void)
{
   zabbix_log(LOG_LEVEL_INFORMATION, "Loading vPoller module configuration file %s",
	      MODULE_CONFIG_FILE);

  /*
   * The cfg_line entries below are in the following format/order:
   *
   * PARAMETER, VAR, TYPE, MANDATORY, MIN, MAX
   */
  static struct cfg_line cfg[] = {
    { "vPollerTimeout", &CONFIG_VPOLLER_TIMEOUT, TYPE_INT, PARM_MAND, 1000, 60000 },
    { "vPollerRetries", &CONFIG_VPOLLER_RETRIES, TYPE_INT, PARM_MAND, 1, 100 },
    { "vPollerProxy", &CONFIG_VPOLLER_PROXY, TYPE_STRING, PARM_MAND, 0, 0 },
    { NULL },
  };
  
  parse_cfg_file(MODULE_CONFIG_FILE, cfg, ZBX_CFG_FILE_OPTIONAL, ZBX_CFG_STRICT);
}

/*
 * Function:
 *     zbx_module_api_version()
 *
 * Purpose: 
 *     Returns version number of the module interface
 *
 * Return value: 
 *     ZBX_MODULE_API_VERSION_ONE - the only version supported by
 *     Zabbix currently.
 */
int
zbx_module_api_version(void)
{
  return (ZBX_MODULE_API_VERSION_ONE);
}

/*
 * Function:
 *    zbx_module_item_timeout()
 *
 * Purpose: 
 *    Set timeout value for processing of items
 *
 * Parameters: 
 *    timeout - timeout in seconds, 0 - no timeout set
 */
void
zbx_module_item_timeout(int timeout)
{
  item_timeout = timeout;
}

/*
 * Function:
 *    zbx_module_item_list()
 *
 * Purpose:
 *    Returns list of item keys supported by the module
 *
 * Return value: 
 *    List of item keys
 */
ZBX_METRIC *
zbx_module_item_list(void)
{
  return (keys);
}

/*
 * Function: 
 *    zbx_module_vpoller()
 *
 * Purpose:
 *    Send task requests to vPoller for processing
 *
 *    The `vpoller` key expects the following parameters
 *    when called through Zabbix:
 *
 *    vpoller[<method>, <hostname>, <name>, <properties>, <key>]
 * 
 *    And the parameters that it expects are these:
 *
 *    <method> - vPoller method to be processed
 *    <hostname> - VMware vSphere server hostname
 *    <name> - Name of the vSphere object (e.g. VM name, ESXi name)
 *    <properties> - vSphere properties to be collected
 *    <key> - Additional information passed as a 'key' to vPoller 
 */
int
zbx_module_vpoller(AGENT_REQUEST *request, AGENT_RESULT *result)
{
  void *zsocket = NULL;  /* ZeroMQ socket */
  zmq_msg_t msg_in;      /* Incoming ZeroMQ message from vPoller */

  const char *method,    /* vPoller method to be processed */
    *hostname,           /* VMware vSphere server hostname */
    *name,		 /* Name of the vSphere object, e.g. VM name, ESXi name */
    *properties,	 /* vSphere properties to be collected */
    *key;                /* Provide additional data to vPoller as a 'key' */

  char *vpoller_result;  /* Holds the result from our vPoller request */
  
  int retries = CONFIG_VPOLLER_RETRIES;  /* Number of retries */
  int linger = 0;                        /* Set the ZeroMQ socket option ZMQ_LINGER to 0 */
  int msg_len = 0;                       /* Length of the received message */

  char msg_buf[MAX_BUFFER_LEN];          /* Buffer to hold the final message we send out to vPoller */

  method = hostname = name = properties = key = vpoller_result = NULL;

  /*
   * The `vpoller` key expects five parameters in the following order:
   *
   * vpoller[<method>, <hostname>, <name>, <properties>, <key>]
   */
  if (request->nparam != 5) {
    SET_MSG_RESULT(result, strdup("Invalid number of key parameters"));
    return (SYSINFO_RET_FAIL);
  }
  
  method = get_rparam(request, 0);
  hostname = get_rparam(request, 1);
  name = get_rparam(request, 2);
  properties = get_rparam(request, 3);
  key = get_rparam(request, 4);

  /* 
   * Create the task request which we send to vPoller
   */
  zbx_snprintf(msg_buf, sizeof(msg_buf), VPOLLER_TASK_TEMPLATE,
	       method, hostname, name, properties, key);

  zabbix_log(LOG_LEVEL_DEBUG, "Creating a ZeroMQ socket for connecting to vPoller");
  if ((zsocket = zmq_socket(zcontext, ZMQ_REQ)) == NULL) {
    SET_MSG_RESULT(result, strdup("Cannot create a ZeroMQ socket"));
    return (SYSINFO_RET_FAIL);
  }

  /* 
   * Connect to the vPoller Proxy
   */
  zabbix_log(LOG_LEVEL_DEBUG, "Connecting to vPoller endpoint at %s",
	     CONFIG_VPOLLER_PROXY);
  zmq_connect(zsocket, CONFIG_VPOLLER_PROXY);
  zmq_setsockopt(zsocket, ZMQ_LINGER, &linger, sizeof(linger));
  zmq_msg_init(&msg_in);

  /* 
   * Send the task request to vPoller, using a retry mechanism
   */
  while (retries > 0) {
    zabbix_log(LOG_LEVEL_DEBUG, "Sending task request to vPoller: %s", msg_buf);
    
    zmq_pollitem_t items[] = {
      { zsocket, 0, ZMQ_POLLIN, 0 },
    };
    
    zmq_send(zsocket, msg_buf, strlen(msg_buf), 0);
    zmq_poll(items, 1, CONFIG_VPOLLER_TIMEOUT);

    /* Do we have a reply? */
    if (items[0].revents & ZMQ_POLLIN) {
      zabbix_log(LOG_LEVEL_DEBUG, "Received reply from vPoller");
      if ((msg_len = zmq_msg_recv(&msg_in, zsocket, 0)) != -1) {
	/* 
	 * Allocate a buffer to hold the result message from vPoller.
	 */
	if ((vpoller_result = malloc(msg_len + 1)) == NULL) {
	  SET_MSG_RESULT(result, strdup("Cannot allocate memory"));
	  zmq_msg_close(&msg_in);
	  zmq_close(zsocket);
	  return (SYSINFO_RET_FAIL);
	}

	/* Get the result from vPoller and NULL-terminate it */
	vpoller_result = zmq_msg_data(&msg_in);
	vpoller_result[msg_len] = '\0';
	break;
      }
    } else {
      /* We didn't get a reply from the server, let's retry */
      retries--;

      zabbix_log(LOG_LEVEL_WARNING, "Did not receive response from vPoller, retrying...");
      
      /* Socket is confused, close and remove it */
      zabbix_log(LOG_LEVEL_DEBUG, "Closing socket and re-establishing connection to vPoller...");
      zmq_close(zsocket);
      
      if ((zsocket = zmq_socket(zcontext, ZMQ_REQ)) == NULL) {
	SET_MSG_RESULT(result, strdup("Cannot create a ZeroMQ socket"));
	zmq_msg_close(&msg_in);
	return (SYSINFO_RET_FAIL);
      }
      
      zmq_connect(zsocket, CONFIG_VPOLLER_PROXY);
      zmq_setsockopt(zsocket, ZMQ_LINGER, &linger, sizeof(linger));
    }
  }
  
  /* Do we have any result? */
  if (vpoller_result == NULL) {
    SET_MSG_RESULT(result, strdup("Did not receive response from vPoller"));
    return (SYSINFO_RET_FAIL);
  }

  zabbix_log(LOG_LEVEL_DEBUG, "Received response from vPoller was: %s", vpoller_result);

  zmq_msg_close(&msg_in);
  zmq_close(zsocket);

  SET_STR_RESULT(result, strdup(vpoller_result));
  
  return (SYSINFO_RET_OK);
}

/*
 * Function: 
 *    zbx_module_init()
 *
 * Purpose:
 *    The function is called on server/proxy/agent startup
 *    It should be used to call any initialization routines
 *
 * Return value:
 *     ZBX_MODULE_OK - success
 *     ZBX_MODULE_FAIL - module initialization failed
 *
 * Comment:
 *     The module won't be loaded in case of ZBX_MODULE_FAIL
 */
int
zbx_module_init(void)
{
  zabbix_log(LOG_LEVEL_DEBUG, "Creating ZeroMQ context for vPoller sockets");
  zcontext = zmq_ctx_new();

  zabbix_log(LOG_LEVEL_DEBUG, "vPoller Timeout: %d (ms)", CONFIG_VPOLLER_TIMEOUT);
  zabbix_log(LOG_LEVEL_DEBUG, "vPoller Retries: %d", CONFIG_VPOLLER_RETRIES);
  zabbix_log(LOG_LEVEL_DEBUG, "vPoller Proxy: %s", CONFIG_VPOLLER_PROXY);
  
  return (ZBX_MODULE_OK);
}

/*
 * Function:
 *    zbx_module_uninit()
 *
 * Purpose:
 *    The function is called on server/proxy/agent shutdown
 *    It should be used to cleanup used resources if there are any
 *
 * Return value:
 *    ZBX_MODULE_OK - success
 *    ZBX_MODULE_FAIL - function failed
 */
int
zbx_module_uninit(void)
{
  zabbix_log(LOG_LEVEL_DEBUG, "Destroying ZeroMQ context for vPoller");
  zmq_ctx_destroy(zcontext);

  return (ZBX_MODULE_OK);
}
