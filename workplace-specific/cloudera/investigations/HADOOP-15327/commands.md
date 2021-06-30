#Maven build
mvn clean install -Pdist -DskipTests  -Dmaven.javadoc.skip=true -e | tee /tmp/maven_out
mvn clean install -Pdist -DskipTests  -Dmaven.javadoc.skip=true -DskipShade

My commits: 
* 765ba31d595 - (HEAD -> HADOOP-15327-snemeth, upstream_fork/HADOOP-15327-snemeth) Update (13 hours ago) <Szilard Nemeth>
* 6147c89fb3d - [WIP] This is the first version that compiles. (13 hours ago) <Szilard Nemeth>

Wei-Chiu's commits:  
2d647cebfc8 - (weichiu/shuffle_handler_netty4, HADOOP-15327-weichiu) Update (9 weeks ago) <Wei-Chiu Chuang>
* 14761633c95 - [WIP] This is the first version that compiles. (9 weeks ago) <Wei-Chiu Chuang>


# Diff commits
##Wei-Chiu vs. snemeth, 1st commit diff:
git show 14761633c95 > /tmp/commit-weichiu
git show 6147c89fb3d > /tmp/commit-snemeth
diff /tmp/commit-weichiu /tmp/commit-snemeth > ~/Downloads/HADOOP-15327/commitdiff_1

##Wei-Chiu vs. snemeth, 2nd commit diff:
git show 2d647cebfc8 > /tmp/commit-weichiu
git show 765ba31d595 > /tmp/commit-snemeth
diff /tmp/commit-weichiu /tmp/commit-snemeth > ~/Downloads/HADOOP-15327/commitdiff_2


REGEX REPLACE LOG PREFIX
^\d+-\d+-\d+ \d+:\d+:\d+,\d+ DEBUG (.*)


sudo tcpdump -i lo0 -v -A -s0 port 8088 > ~/Downloads/HADOOP-15327/tcpdumps/tmp3



# Configure mitmproxy

mitmdump --listen-port 8888
mitmproxy --listen-port 8888

Java test run config VM options: -ea -Dhttp.proxyHost=127.0.0.1 -Dhttp.proxyPort=8888