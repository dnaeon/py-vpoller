#!/usr/bin/env bash

# Max number of concurent requests
MAX_REQUESTS=16

# Total number of requests to be made
TOTAL_REQUESTS=1000

let i=0
while [[ ${i} -lt ${TOTAL_REQUESTS} ]]; do 
    running=$( ps -ef | grep vm-pollerd-client | grep -v grep | wc -l )

    # Fire up another request if needed
    if [[ ${running} -lt ${MAX_REQUESTS} ]]; then
	echo "I: Firing up request ${i} ..."
	./vm-pollerd-client -D -n esx1-evn1_local0 -p summary.capacity -u ds:///vmfs/volumes/4c68dc48-0db9ca38-f0e0-78e7d1e5782e/ -c poll -V vc1-sof2 > /dev/null 2>&1 &
	let i++
    fi
done
