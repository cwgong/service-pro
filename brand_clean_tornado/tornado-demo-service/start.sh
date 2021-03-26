#!/bin/sh
LOGS_DIR=logs

if [ ! -d "${LOGS_DIR}" ]
then
  mkdir "${LOGS_DIR}"
fi

python3 tornado-demo-service.py tornado-demo-service.conf
