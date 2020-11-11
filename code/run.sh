#!/bin/bash

if [ "$#" -ne 1 ]; then
	echo "Pass the py file you want to run"
fi

echo "Running $1"

/spark/bin/spark-submit --py-files 'dist/xmap-0.1.0-py3.6.egg' \
	--master spark://spark-master:7077 \
	--conf spark.driver.memory=20G \
	--conf spark.executor.memory=8G \
	$1
	
