#ifndef _VPOLLER_CCLIENT_H_
#define _VPOLLER_CCLIENT_H_

#define VERSION "0.3.9-dev"
#define MAX_TASK_MESSAGE 8192                     /* Max size of the task message */
#define DEFAULT_TIMEOUT  10000 			  /* Timeout is in msec */
#define DEFAULT_RETRIES  3    			  /* Number of retries before giving up */
#define DEFAULT_ENDPOINT "tcp://localhost:10123"  /* Default endpoint we connect to */

typedef enum {
  PARAM_METHOD = 0,
  PARAM_HOSTNAME,
  PARAM_NAME,
  PARAM_PROPERTIES,
  PARAM_KEY,
  PARAM_USERNAME,
  PARAM_PASSWORD,
  PARAM_COUNTER_ID,
  PARAM_INSTANCE,
  PARAM_PERF_INTERVAL,
  PARAM_MAX_SAMPLE,
  PARAM_HELPER,
  PARAM_NUM,
} task_params;

void usage(void);

#endif  /* !_VPOLLER_CCLIENT_H_ */
