#!/usr/bin/env bash

#Setup ant
ANT_HOME=/usr/share/ant
export ANT_HOME


#Setup java
JAVA_HOME=/usr/lib/jvm/java-8-oracle/
export JAVA_HOME

#Setup PATH
PATH=$PATH:${ANT_HOME}/bin
PATH=$PATH:$HOME/.npm-global/bin