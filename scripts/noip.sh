#!/bin/bash

USERNAME=
PASSWORD=
HOSTNAME=

res=$(curl "https://${USERNAME}:${PASSWORD}@dynupdate.no-ip.com/nic/update?hostname=${HOSTNAME}&myip=127.0.0.1" \
		2> /dev/null)
echo $res

sleep 5

res=$(curl "https://${USERNAME}:${PASSWORD}@dynupdate.no-ip.com/nic/update?hostname=${HOSTNAME}" \
		  2> /dev/null)

echo $res