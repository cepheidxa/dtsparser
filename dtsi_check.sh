#!/usr/bin/env bash
#Author: zhangbo10073794

#dtsi_check.sh xxx.dts

#set -x

if [ $# -lt 1 ];then
	echo "please set dts file: $(basename $0) xxx.dts"
	exit
fi

DTS=$1

if [ ! -f $DTS ]; then
	echo "${DTS}: no such file"
	exit
fi

DIR=$(dirname $1)
echo "$(basename $DTS)"

function check()
{
	local a=$1
	local files=$(grep "^[[:space:]]*#include[[:space:]]*\".*\"" $a | sed -E 's/[[:space:]]*#include[[:space:]]*"(.*)".*/\1/' -)
	for item in $files
	do
		echo $item
		check ${DIR}/$item
	done
}

check $DTS
