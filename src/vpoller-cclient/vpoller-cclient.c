/*-
 * Copyright (c) 2013-2014 Marin Atanasov Nikolov <dnaeon@gmail.com>
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
  fprintf(stderr, "    vpoller-cclient [-r <retries>] [-t <timeout>] [-e <endpoint>]\n");
  fprintf(stderr, "                    -m <method> -V <host>\n");
  fprintf(stderr, "    vpoller-cclient [-r <retries>] [-t <timeout>] [-e <endpoint>]\n");
  fprintf(stderr, "                    -m <method> -n <name> -p <property> -V <host>\n");
  fprintf(stderr, "    vpoller-cclient [-r <retries>] [-t <timeout>] [-e <endpoint>]\n");
  fprintf(stderr, "                    -m <method> -u <datastore-url> -p <property> -V <host>\n");
  fprintf(stderr, "    vpoller-cclient -h\n\n");
  fprintf(stderr, "Options:\n");
  fprintf(stderr, "    -h                   Display this usage info\n");
  fprintf(stderr, "    -V <host>            The vSphere host server to send the request to\n");
  fprintf(stderr, "    -m <method>          The method to be processed during the client request\n");
  fprintf(stderr, "    -n <name>            Name of the ESXi host, only applicable to hosts object type\n");
  fprintf(stderr, "    -p <property>        Name of the property as defined by the vSphere Web SDK\n");
  fprintf(stderr, "    -u <datastore-url>   Datastore URL, only applicable to datastores object type\n");
  fprintf(stderr, "    -r <retries>         Number of times to retry if a request times out [default: 3]\n");
  fprintf(stderr, "    -t <timeout>         Timeout after that period of milliseconds [default: 3000]\n");
  fprintf(stderr, "    -e <endpoint>        Endpoint of ZeroMQ Proxy/Broker the client connects to\n");
  fprintf(stderr, "                         [default: tcp://localhost:10123]\n\n");
  fprintf(stderr, "Example usage for discovering datastores on a vSphere host:\n\n");
  fprintf(stderr, "     $ vpoller-cclient -m datastore.discover -V vc1.example.org\n\n");
  fprintf(stderr, "Example usage for retrieving a property of an ESXi host:\n\n");
  fprintf(stderr, "     $ vpoller-cclient -m host.poll -V vc01-test.example.org -p runtime.bootTime -n esxi1.example.org\n");
}

int
main(int argc, char *argv[])
{
  void *zcontext = NULL; /* ZeroMQ Context */
  void *zsocket  = NULL; /* ZeroMQ Socket */
  zmq_msg_t msg_in;      /* Incoming ZeroMQ Message */

  /* 
   * Template message before formatting and sending out.
   * The message we send is in JSON format
   */
  const char *msg_out_template = ""
    "{"
    "\"method\":      \"%s\", "
    "\"hostname\":    \"%s\", "
    "\"name\":        \"%s\", "
    "\"info.url\":    \"%s\", "
    "\"property\":    \"%s\""
    "}";

  const char *method,	  /* The method to be processed during client request */
    *name,		  /* Name of the object, e.g. "datastore1", "esx1-host", .. */
    *property,		  /* The property we want as defined in the vSphere Web Services SDK */
    *url,		  /* Datastore URL, only applicable to datastores object type */
    *vsphere_host;	  /* The vSphere host we send the request message to */
  
  char *result;	  	  /* A pointer to hold the result from our request */
  
  /* The ZeroMQ Broker/Proxy endpoint we connect to */
  const char *endpoint = DEFAULT_ENDPOINT;

  int rc      = EX_OK;            /* Return code */
  int timeout = DEFAULT_TIMEOUT;  /* Timeout in msec */
  int retries = DEFAULT_RETRIES;  /* Number of retries */
  int linger  = 0;                /* Set the ZeroMQ socket option ZMQ_LINGER to 0 */
  int msg_len = 0;		  /* Length of the received message */

  char msg_buf[1024];		  /* Message buffer to hold the final message we send out */
  char ch;

  /* Initialize the message properties */
  name = property = url = "None";
  method = vsphere_host = result = NULL;
  
  /* Get the command-line options and arguments */
  while ((ch = getopt(argc, argv, "m:e:r:t:n:p:u:V:")) != -1) {
    switch (ch) {
    case 'm':
      method = optarg;
      break;
    case 'n':
      name = optarg;
      break;
    case 'p':
      property = optarg;
      break;
    case 'u':
      url = optarg;
      break;
    case 'V':
      vsphere_host = optarg;
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
    default:
      usage();
      return (EX_USAGE);
    }
  }
  argc -= optind;
  argv += optind;
  
  /* Sanity check the provided options and arguments */
  if (method == NULL || vsphere_host == NULL) {
    usage();
    return (EX_USAGE);
  }
  
  /* Create the message to send out */
  snprintf(msg_buf, 1023, msg_out_template, method, vsphere_host, name, url, property);
    
  /* Create a new ZeroMQ Context and Socket */
  zcontext = zmq_ctx_new();
  
  if ((zsocket = zmq_socket(zcontext, ZMQ_REQ)) == NULL) {
    fprintf(stderr, "Cannot create a ZeroMQ socket\n");
    zmq_ctx_destroy(zcontext);
    return (EX_PROTOCOL);
  }

  /* Connect to the ZeroMQ Proxy */
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
	 /* 
	  * Allocate a buffer to hold our resulting message
	  * The resulting message needs to be NULL-terminated as well
	  */
	 if ((result = malloc(msg_len + 1)) == NULL) {
	   fprintf(stderr, "Cannot allocate memory\n");
	   zmq_msg_close(&msg_in);
	   zmq_ctx_destroy(zcontext);
	   return (EX_OSERR);
	 }
	 
	 result = zmq_msg_data(&msg_in);
	 result[msg_len] = '\0';
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
  if (result == NULL) {
    printf("{ \"success\": -1, \"msg\": \"Did not receive reply from server, aborting...\"\n");
  } else {
    printf("%s\n", result);
  }

  zmq_msg_close(&msg_in);
  zmq_close(zsocket);
  zmq_ctx_destroy(zcontext);

  return (rc);
}
