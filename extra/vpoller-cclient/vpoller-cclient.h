#ifndef _VPOLLER_CCLIENT_H_
#define _VPOLLER_CCLIENT_H_

#define DEFAULT_TIMEOUT  3000 			  /* Timeout is in msec */
#define DEFAULT_RETRIES  3    			  /* Number of retries before giving up */
#define DEFAULT_ENDPOINT "tcp://localhost:10123"  /* Default endpoint we connect to */

void usage(void);

#endif  /* !_VPOLLER_CCLIENT_H_ */
