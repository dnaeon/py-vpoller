#!/bin/bash

while IFS='' read -r line || [[ -n "$line" ]]; do
    IFS=';' read -ra VALUES <<< $line
    echo "${VALUES[1]}  ${VALUES[0]}" >> /etc/hosts
    vconnector-cli --debug -H ${VALUES[0]} -U ${VALUES[2]} -P ${VALUES[3]} add
    vconnector-cli --debug -H ${VALUES[0]} enable
done < "/var/lib/vconnector/hosts.file"
