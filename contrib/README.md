In this directory you find contributed scripts

in externalscripts: cvpoller-zabbix/vpoller-zabbix both scripts have additional checks
to ensure that when a vcenter server is down or the vpoller-proxy is down the items
get the status: "Not Supported"

This solves the issue of all zabbix agents become unreachable due to vcenter down and the
zabbix queue is getting full.

Requirements for these scripts is that a recent version of `curl` is installed.


