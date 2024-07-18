/*-
 * Copyright (c) 2014-2015 Marin Atanasov Nikolov <dnaeon@gmail.com>
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


#include <stdbool.h>

#include <zmq.h>

#include "threads.h"
#include "zbxcfg.h"
#include "zbxsysinc.h"
#include "module.h"
#include "zbxlog.h"
#include "zbxstr.h"

#define VPOLLER_MODULE_VERSION "0.6.0"
#define MODULE_CONFIG_FILE "/etc/zabbix/vpoller_module.conf"

#define VPOLLER_TASK_TEMPLATE "{ \
			           \"method\": \"%s\", \
			           \"hostname\": \"%s\", \
                                   \"name\": \"%s\", \
			           \"properties\": [ \"%s\" ], \
			           \"key\": \"%s\", \
                                   \"username\": \"%s\", \
                                   \"password\": \"%s\", \
                                   \"counter-name\": \"%s\", \
                                   \"instance\": \"%s\", \
                                   \"perf-interval\": \"%s\", \
                                   \"max-sample\": \"1\", \
			           \"helper\": \"vpoller.helpers.czabbix\" \
                               }"

int zbx_module_vpoller(AGENT_REQUEST *request, AGENT_RESULT *result);
int zbx_module_vpoller_echo(AGENT_REQUEST *request, AGENT_RESULT *result);

typedef enum {
  PARAM_METHOD = 0,
  PARAM_HOSTNAME,
  PARAM_NAME,
  PARAM_PROPERTIES,
  PARAM_KEY,
  PARAM_USERNAME,
  PARAM_PASSWORD,
  PARAM_COUNTER_NAME,
  PARAM_INSTANCE,
  PARAM_PERF_INTERVAL,
  PARAM_NUM,
} item_params;

/* The variable keeps timeout setting for item processing */
static int item_timeout = 0;

/* Default vPoller settings */
static unsigned CONFIG_VPOLLER_TIMEOUT = 10000;
static unsigned CONFIG_VPOLLER_RETRIES = 1;
static char    *CONFIG_VPOLLER_PROXY   = NULL;

/* ZeroMQ context used for creating sockets that connect to vPoller */ 
static void *zcontext = NULL;

/* Zabbix keys provided by this module */
static ZBX_METRIC keys[] = {
  /* KEY,       FLAG,          FUNCTION,           TEST PARAMS */
  { "vpoller",	        CF_HAVEPARAMS, zbx_module_vpoller,      NULL },
  { "vpoller.echo",	CF_HAVEPARAMS, zbx_module_vpoller_echo, NULL },
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
   * The zbx_cfg_line_t entries below are in the following format/order:
   *
   * PARAMETER, VAR, TYPE, MANDATORY, MIN, MAX
   */
  static zbx_cfg_line_t cfg[] = {
    { "vPollerTimeout", &CONFIG_VPOLLER_TIMEOUT, ZBX_CFG_TYPE_INT, ZBX_CONF_PARM_OPT, 1000, 60000 },
    { "vPollerRetries", &CONFIG_VPOLLER_RETRIES, ZBX_CFG_TYPE_INT, ZBX_CONF_PARM_OPT, 1, 100 },
    { "vPollerProxy", &CONFIG_VPOLLER_PROXY, ZBX_CFG_TYPE_STRING, ZBX_CONF_PARM_OPT, 0, 0 },
    { NULL },
  };
  
  /*
   * A new paramter was added in zabbix 6.0 to reread the zabbix agent configuration without restarting it.
   * see ZBXNEXT-6936
   */
  zbx_parse_cfg_file(MODULE_CONFIG_FILE, cfg, ZBX_CFG_FILE_OPTIONAL, ZBX_CFG_STRICT, ZBX_CFG_NO_EXIT_FAILURE);
}

/*
 * Function:
 *    zbx_module_set_defaults()
 * 
 * Purpose:
 *     Set default settings for vPoller
 */
void
zbx_module_set_defaults(void)
{
  if (CONFIG_VPOLLER_PROXY == NULL)
    CONFIG_VPOLLER_PROXY = "tcp://localhost:10123";
}

/*
 * Function:
 *     zbx_module_api_version()
 *
 * Purpose: 
 *     Returns version number of the module interface
 *
 * Return value: 
 *     ZBX_MODULE_API_VERSION - the only version supported by
 *     Zabbix currently.
 */
int
zbx_module_api_version(void)
{
  return (ZBX_MODULE_API_VERSION);
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
ZBX_METRIC *zbx_module_item_list(void)
{
  return (keys);
}

/*
 * Function: 
 *    zbx_module_vpoller()
 *
 * Purpose:
 *    Sends task requests to vPoller for processing
 *
 *    The `vpoller` key expects the following parameters
 *    when called through Zabbix:
 *
 *    vpoller[method, hostname, name, properties, <key>, <username>, <password>, <counter-name>, <instance>, <perf-interval>]
 * 
 *    And the parameters that it expects are these:
 *
 *    method - vPoller method to be processed
 *    hostname - VMware vSphere server hostname
 *    name - Name of the vSphere object (e.g. VM name, ESXi name)
 *    properties - vSphere properties to be collected
 *    <key> - Additional information passed as a 'key' to vPoller
 *    <username> - Username to use when logging into the guest system
 *    <password> - Password to use when logging into the guest system
 *    <counter-name> - Performance counter name
 *    <instance> - Performance counter instance
 *    <perf-interval> - Historical performance interval
 */
int
zbx_module_vpoller(AGENT_REQUEST *request, AGENT_RESULT *result)
{
  unsigned int i;
  void *zsocket = NULL;    /* ZeroMQ socket */
  zmq_msg_t msg_in;        /* Incoming ZeroMQ message from vPoller */

  char *params[PARAM_NUM]; /* Params received from Zabbix */
  char *key_esc;
  bool got_reply = false;   /* A flag to indicate whether a reply from vPoller was received or not */

  int retries = CONFIG_VPOLLER_RETRIES; /* Number of retries */
  int linger = 0;                       /* Set the ZeroMQ socket option ZMQ_LINGER to 0 */
  int msg_len = 0;                      /* Length of the received message */
  char msg_buf[MAX_BUFFER_LEN];         /* Buffer to hold the final message we send out to vPoller */

  for (i = 0; i < PARAM_NUM; i++)
    params[i] = "(null)";

  /*
   * The Zabbix `vpoller` key expects these parameters
   * in the following order:
   *
   * vpoller[method, hostname, name, properties, <key>, <username>, <password>, <counter-name>, <instance>, <perf-interval>]
   */
  if ((request->nparam < 4) || (request->nparam > PARAM_NUM)) {
    SET_MSG_RESULT(result, strdup("Invalid number of arguments"));
    return (SYSINFO_RET_FAIL);
  }

  for (i = 0; i < request->nparam; i++)
    params[i] = get_rparam(request, i);

  /* 
   * Create the task request which we send to vPoller
   */
  key_esc = zbx_dyn_escape_string(params[PARAM_KEY], "\\");
  zbx_snprintf(msg_buf, sizeof(msg_buf), VPOLLER_TASK_TEMPLATE,
	       params[PARAM_METHOD],
	       params[PARAM_HOSTNAME],
	       params[PARAM_NAME],
	       params[PARAM_PROPERTIES],
	       key_esc,
	       params[PARAM_USERNAME],
	       params[PARAM_PASSWORD],
	       params[PARAM_COUNTER_NAME],
	       params[PARAM_INSTANCE],
	       params[PARAM_PERF_INTERVAL]);
  zbx_free(key_esc);

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
	got_reply = true;
	break;
      }
    } else {
      /* We didn't get a reply from the server, let's retry */
      retries--;

      if (retries > 0) {
	zabbix_log(LOG_LEVEL_WARNING, "Did not receive response from vPoller, retrying...");
      } else {
	zabbix_log(LOG_LEVEL_WARNING, "Did not receive response from vPoller, giving up.");
      }
      
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
  if (got_reply == false) {
    zmq_msg_close(&msg_in);
    zmq_close(zsocket);
    SET_MSG_RESULT(result, strdup("Did not receive response from vPoller"));
    return (SYSINFO_RET_FAIL);
  }

  SET_STR_RESULT(result, strdup(zmq_msg_data(&msg_in)));

  zmq_msg_close(&msg_in);
  zmq_close(zsocket);
  
  return (SYSINFO_RET_OK);
}

/*
 * Function:
 *    zbx_module_vpoller_echo()
 *
 * Purpose:
 *    Will echo back the first parameter you provide to it
 *
 * Return value:
 *    The first parameter it was invoked with
 */
int
zbx_module_vpoller_echo(AGENT_REQUEST *request, AGENT_RESULT *result)
{
  const char *param;

  if (request->nparam < 1) {
    SET_MSG_RESULT(result, strdup("Invalid number of key parameters"));
    return (SYSINFO_RET_FAIL);
  }

  param = get_rparam(request, 0);

  SET_STR_RESULT(result, strdup(param));

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
  zabbix_log(LOG_LEVEL_INFORMATION, "vPoller module version %s", VPOLLER_MODULE_VERSION);

  zbx_module_load_config();
  zbx_module_set_defaults();
  
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
