#!/usr/bin/env bash

# Max number of concurent requests
MAX_REQUESTS=16

# Total number of requests to be made
TOTAL_REQUESTS=1000

let i=0
while [[ ${i} -lt ${TOTAL_REQUESTS} ]]; do 
    running=$( ps -ef | grep vpoller-client | grep -v grep | wc -l )

    # Fire up another request if needed
    if [[ ${running} -lt ${MAX_REQUESTS} ]]; then
	echo "I: Firing up request ${i} ..."
	vpoller-client -m host.discover -V vc01.example.org -e tcp://localhost:10123 > /dev/null 2>&1 &
	vpoller-client -m datastore.discover -V vc01.example.org -e tcp://localhost:10123 > /dev/null 2>&1 &
	vpoller-client -m datastore.poll -p summary.capacity -u ds:///vmfs/volumes/4c68dc48-0db9ca38-f0e0-78e7d1e5782e/ -V vc01.example.org > /dev/null 2>&1 &
	let i++
    fi
done
