/*-
 * Copyright (c) 2013-2015 Marin Atanasov Nikolov <dnaeon@gmail.com>
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


/* 
 * vpoller-cclient is the vPoller Client application written in C
 *
 * It is used for sending client requests to vPoller Proxy/Workers for
 * discovering and polling of vSphere Object properties.
 *
 */


#include <stdio.h>
#include <stdbool.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <sysexits.h>
#include <unistd.h>

#include <zmq.h>

#include "vpoller-cclient.h"

void
usage(void)
{
  fprintf(stderr, "Usage:\n");
  fprintf(stderr, "    vpoller-cclient [options] -m <method> -V <host>\n\n");
  fprintf(stderr, "Options:\n");
  fprintf(stderr, "    -h                   Display this usage info\n");
  fprintf(stderr, "    -V <host>            The vSphere host to send the request to\n");
  fprintf(stderr, "    -m <method>          The method to be processed during the client request\n");
  fprintf(stderr, "    -n <name>            Name of the object, e.g. ESXi hostname, datastore URL, etc.\n");
  fprintf(stderr, "    -p <properties>      Name of the property as defined by the vSphere Web SDK\n");
  fprintf(stderr, "    -r <retries>         Number of times to retry if a request times out [default: 3]\n");
  fprintf(stderr, "    -t <timeout>         Timeout after that period of milliseconds [default: 3000]\n");
  fprintf(stderr, "    -e <endpoint>        Endpoint of vPoller Proxy/Worker the client connects to\n");
  fprintf(stderr, "                         [default: tcp://localhost:10123]\n");
  fprintf(stderr, "    -k <key>             Provide additional key for data filtering\n");
  fprintf(stderr, "    -s <max-sample>      Max number of performance samples to retrieve\n");
  fprintf(stderr, "    -c <counter-id>      Retrieve performance metrics with this counter ID\n");
  fprintf(stderr, "    -i <instance>        Performance metric instance name\n");
  fprintf(stderr, "    -T <interval>        Historical performance interval key\n");
  fprintf(stderr, "    -U <username>        Username to use for authentication in guest system\n");
  fprintf(stderr, "    -P <password>        Password to use for authentication in guest system\n");
  fprintf(stderr, "    -H <helper>          Specify a helper module to use for processing of the\n");
  fprintf(stderr, "                         result message, e.g. 'vpoller.helper.zabbix'\n\n");
  fprintf(stderr, "Examples:\n");
  fprintf(stderr, "     vpoller-cclient -m vm.discover -V vc01.example.org\n");
  fprintf(stderr, "     vpoller-cclient -m vm.discover -V vc01.example.org -p runtime.powerState\n");
  fprintf(stderr, "     vpoller-cclient -m vm.get -V vc01.example.org -n vm01.example.org -p summary.overallStatus\n");
  fprintf(stderr, "     vpoller-cclient -m vm.disk.get -V vc01.example.org -n vm01.example.org -k /var\n");
  fprintf(stderr, "     vpoller-cclient -m vm.process.get -V vc01.example.org -n vm01.example.org -U admin -P p4ssw0rd\n\n");
  fprintf(stderr, "Version:\n");
  fprintf(stderr, "     vpoller-cclient version %s\n", VERSION);
}

int
main(int argc, char *argv[])
{
  void *zcontext = NULL;
  void *zsocket  = NULL;
  zmq_msg_t msg_in;
  unsigned int i;
  char *params[PARAM_NUM];
  bool got_reply = false;
  const char *endpoint = DEFAULT_ENDPOINT;
  int rc = EX_OK;
  int timeout = DEFAULT_TIMEOUT;
  int retries = DEFAULT_RETRIES;
  int linger  = 0;
  int msg_len = 0;
  char msg_buf[MAX_TASK_MESSAGE];
  char ch;

  /* 
   * Template task message
   */
  const char *msg_out_template = ""
    "{"
    "\"method\":        \"%s\", "
    "\"hostname\":      \"%s\", "
    "\"name\":          \"%s\", "
    "\"properties\":   [\"%s\"], "
    "\"key\":           \"%s\", "
    "\"username\":      \"%s\", "
    "\"password\":      \"%s\", "
    "\"counter-id\":    \"%s\", "
    "\"instance\":      \"%s\", "
    "\"perf-interval\": \"%s\", "
    "\"max-sample\":    \"%s\", "
    "\"helper\":        \"%s\" "
    "}";

  for (i = 0; i < PARAM_NUM; i++)
    params[i] = NULL;

  /* By default we request the vpoller.helpers.cclient helper */
  params[PARAM_HELPER] = "vpoller.helpers.cclient";

  /* Get the command-line options and arguments */
  while ((ch = getopt(argc, argv, "m:e:r:t:n:p:k:c:i:s:T:U:P:V:H:")) != -1) {
    switch (ch) {
    case 'm':
      params[PARAM_METHOD] = optarg;
      break;
    case 'n':
      params[PARAM_NAME] = optarg;
      break;
    case 'p':
      params[PARAM_PROPERTIES] = optarg;
      break;
    case 'r':
      retries = atol(optarg);
      break;
    case 't':
      timeout = atol(optarg);
      break;
    case 'e':
      endpoint = optarg;
      break;
    case 'k':
      params[PARAM_KEY] = optarg;
      break;
    case 'c':
      params[PARAM_COUNTER_ID] = optarg;
      break;
    case 'i':
      params[PARAM_INSTANCE] = optarg;
      break;
    case 's':
      params[PARAM_MAX_SAMPLE] = optarg;
      break;
    case 'T':
      params[PARAM_PERF_INTERVAL] = optarg;
      break;
    case 'U':
      params[PARAM_USERNAME] = optarg;
      break;
    case 'P':
      params[PARAM_PASSWORD] = optarg;
      break;
    case 'V':
      params[PARAM_HOSTNAME] = optarg;
      break;
    case 'H':
      params[PARAM_HELPER] = optarg;
      break;
    default:
      usage();
      return (EX_USAGE);
    }
  }
  argc -= optind;
  argv += optind;
  
  /* Sanity check the provided options and arguments */
  if (params[PARAM_METHOD] == NULL || params[PARAM_HOSTNAME] == NULL) {
    usage();
    return (EX_USAGE);
  }

  /* Create the message to send out */
  snprintf(msg_buf, MAX_TASK_MESSAGE - 1, msg_out_template,
	   params[PARAM_METHOD],
	   params[PARAM_HOSTNAME],
	   params[PARAM_NAME],
	   params[PARAM_PROPERTIES],
	   params[PARAM_KEY],
	   params[PARAM_USERNAME],
	   params[PARAM_PASSWORD],
	   params[PARAM_COUNTER_ID],
	   params[PARAM_INSTANCE],
	   params[PARAM_PERF_INTERVAL],
	   params[PARAM_MAX_SAMPLE],
	   params[PARAM_HELPER]
	   );

  /* Create a new ZeroMQ Context and Socket */
  zcontext = zmq_ctx_new();
  
  if ((zsocket = zmq_socket(zcontext, ZMQ_REQ)) == NULL) {
    fprintf(stderr, "Cannot create a ZeroMQ socket\n");
    zmq_ctx_destroy(zcontext);
    return (EX_PROTOCOL);
  }

  /* Connect to the vPoller Proxy/Worker */
  zmq_connect(zsocket, endpoint);
  zmq_setsockopt(zsocket, ZMQ_LINGER, &linger, sizeof(linger));

  /* Init the ZeroMQ message we will be receiving */
  zmq_msg_init(&msg_in);

  /* Send our request message out, retry mechanism in place */
  while (retries > 0) {
    zmq_pollitem_t items[] = {
       { zsocket, 0, ZMQ_POLLIN, 0 },	/* ZeroMQ Poller Items */
     };

     zmq_send(zsocket, msg_buf, strlen(msg_buf), 0);
     zmq_poll(items, 1, timeout);

     /* Do we have a reply? */
     if (items[0].revents & ZMQ_POLLIN) {
       if ((msg_len = zmq_msg_recv(&msg_in, zsocket, 0)) != -1) {
	 got_reply = true;
	 break;
       }
     } else {
       /* We didn't get a reply from the server, let's retry */
       retries--;
       
       /* Socket is confused, close and remove it */
       zmq_close(zsocket);

       if ((zsocket = zmq_socket(zcontext, ZMQ_REQ)) == NULL) {
	 fprintf(stderr, "Cannot create a ZeroMQ socket\n");
	 zmq_msg_close(&msg_in);
	 zmq_ctx_destroy(zcontext);
	 return (EX_PROTOCOL);
       }

       zmq_connect(zsocket, endpoint);
       zmq_setsockopt(zsocket, ZMQ_LINGER, &linger, sizeof(linger));
     }
  }
  
  /* Do we have any result? */
  if (got_reply == false) {
    rc = EX_UNAVAILABLE;
    printf("{ \"success\": 1, \"msg\": \"Did not receive reply from server, aborting...\" }\n");
  } else {
    printf("%s\n", (char *)zmq_msg_data(&msg_in));
  }

  zmq_msg_close(&msg_in);
  zmq_close(zsocket);
  zmq_ctx_destroy(zcontext);

  return (rc);
}
