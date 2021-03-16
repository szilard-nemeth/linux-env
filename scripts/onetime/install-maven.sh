#!/bin/sh

#https://maven.apache.org/install.html

#https://gist.github.com/miroslavtamas/cdca97f2eafdd6c28b844434eaa3b631
VERSION="3.6.3"
mkdir /tmp/mvn-install && cd /tmp/mvn-install
wget http://www.eu.apache.org/dist/maven/maven-3/$VERSION/binaries/apache-maven-$VERSION-bin.tar.gz
tar xzf apache-maven-$VERSION-bin.tar.gz
sudo mkdir /usr/local/maven
sudo chown snemeth /usr/local/maven
mv apache-maven-$VERSION/ /usr/local/maven/
ln -s /usr/local/maven/apache-maven-$VERSION/bin/mvn /usr/local/bin/mvn