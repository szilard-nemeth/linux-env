#!/bin/bash

ps aux | grep '[o]rg.apache.hadoop' | tr -s " " | cut -d" " -f2 | xargs kill
