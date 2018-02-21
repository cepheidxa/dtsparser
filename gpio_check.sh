#!/usr/bin/env bash
#Author zhangbo10073794
#set -x

#gpio_check.sh xxx.dts

if [ $# -lt 1 ]; then
	echo "please set dts file: $(basename $0) xxx.dts"
	exit
fi

FILE=$1

if [ ! -f $FILE ]; then
	echo "${FILE}: no such file"
	exit
fi

DIR=$(dirname $1)
files=$(${DIR}/dtsi_check.sh $FILE)

#gpio_check.sh xxx.dts
GPIO_NUM=112
gpio=0
while [ $gpio -le ${GPIO_NUM} ]; do
	echo "checking gpio $gpio"
	for file in $files
	do
		grep -rn -H "msm_gpio[[:space:]]*${gpio}[[:space:]]" ${DIR}/$file
	done
	grep -rn -H "gp[[:space:]]*${gpio}[^0-9]" ${DIR}/msm8909-pinctrl.dtsi
	gpio=$(($gpio+1))
done
