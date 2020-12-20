#!/bin/bash

sls_dirname=$(ssh root@snemeth-fips2-1.vpc.cloudera.com "ls -td -- ./slsrun* | head -n 1")
scp -r root@snemeth-fips2-1.vpc.cloudera.com:$sls_dirname $HOME/Downloads/YARN-10427/analysis
