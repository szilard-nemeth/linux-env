#0. Stop all Nodemanagers, except on host: ccycloud-2.snemeth-netty.root.hwx.site
#0. SSH to host: ccycloud-2.snemeth-netty.root.hwx.site

# 1. Generate public / private keys + certificate into the server's keystore: 
keytool -v -genkeypair -dname "CN=Server cert,OU=Compute Platform,O=Cloudera,C=HU" -keystore /home/systest/keystores/server-keystore.jks -storepass ssl_server_ks_pass  -keyalg RSA -keysize 2048 -alias server2 -validity 3650 -ext KeyUsage=digitalSignature,dataEncipherment,keyEncipherment,keyAgreement -ext ExtendedKeyUsage=serverAuth,clientAuth -ext SubjectAlternativeName:c=DNS:$HOSTNAME



# 1.1 Issue 1: DerInputStream.getLength(): lengthTag=109, too big
# http://support.ptc.com/help/thingworx/azure_connector_scm/en/index.html#page/thingworx_scm_azure/azure_connector/c_azure_trbl_input_stream_getlength_too_big.html
# 1.1. Solution: Had to fix the command, -deststoretype pkcs12 should be removed

# 1.2. Removed all -ext arguments from command

# 1.3. Issue 2: Permission denied for keystore
# 1.3 Solution: sudo chmod 777 /home/systest/keystores/server-keystore.jks

# CORRECT OUTPUT of keytool command: 
# Generating 2,048 bit RSA key pair and self-signed certificate (SHA256withRSA) with a validity of 3,650 days
# 	for: CN=Server cert, OU=Compute Platform, O=Cloudera, C=HU
# Enter key password for <server>
# 	(RETURN if same as keystore password):  
# [Storing /home/systest/keystores/server-keystore.jks]

# Warning:
# The JKS keystore uses a proprietary format. It is recommended to migrate to PKCS12 which is an industry standard format using "keytool -importkeystore -srckeystore /home/systest/keystores/server-keystore.jks -destkeystore /home/systest/keystores/server-keystore.jks -deststoretype pkcs12".
# [systest@ccycloud-2 ~]$ 




#1.1 Verify keystore
keytool -list -keystore /home/systest/keystores/server-keystore.jks -storepass ssl_server_ks_pass



# 2. Restart NM
yarn --daemon stop nodemanager && yarn --daemon start nodemanager


# Do above steps on all machines that have NM running: 
# ccycloud-3.snemeth-netty.root.hwx.site
# ccycloud-3.snemeth-netty.root.hwx.site




# 3. Try to launch sleep job again, see what kind of error message is generated
# 3.1 Issue 1: Caused by: java.lang.RuntimeException: Unexpected error: java.security.InvalidAlgorithmParameterException: the trustAnchors parameter must be non-empty
# https://www.baeldung.com/java-trustanchors-parameter-must-be-non-empty
# This is most likely because the truststore of the client can't trust the server's certificate because the truststore is empty.


# 4. Export server certificates + add them to all client truststores

# 4.1 Export server's certificate to a certificate file on all hosts (NEED TO RUN THESE FROM CLIENT MACHINE)
ssh ccycloud-2.snemeth-netty.root.hwx.site "mkdir -p /home/systest/certs/ && keytool -v -exportcert -file /home/systest/certs/server2.cert -alias server2 -keystore /home/systest/keystores/server-keystore.jks -storepass ssl_server_ks_pass -rfc && ls -la /home/systest/certs"

ssh ccycloud-3.snemeth-netty.root.hwx.site "mkdir -p /home/systest/certs/ && keytool -v -exportcert -file /home/systest/certs/server3.cert -alias server3 -keystore /home/systest/keystores/server-keystore.jks -storepass ssl_server_ks_pass -rfc && ls -la /home/systest/certs"

ssh ccycloud-4.snemeth-netty.root.hwx.site "mkdir -p /home/systest/certs/ && keytool -v -exportcert -file /home/systest/certs/server4.cert -alias server4 -keystore /home/systest/keystores/server-keystore.jks -storepass ssl_server_ks_pass -rfc && ls -la /home/systest/certs"


# 4.2 Scp all server certificates into all hosts that will be acting a client
ssh ccycloud-2.snemeth-netty.root.hwx.site "scp -o StrictHostKeyChecking=no systest@ccycloud-3.snemeth-netty.root.hwx.site:/home/systest/certs/server3.cert /home/systest/certs/ && ls -la /home/systest/certs"
ssh ccycloud-2.snemeth-netty.root.hwx.site "scp -o StrictHostKeyChecking=no systest@ccycloud-4.snemeth-netty.root.hwx.site:/home/systest/certs/server4.cert /home/systest/certs/ && ls -la /home/systest/certs"

ssh ccycloud-3.snemeth-netty.root.hwx.site "scp -o StrictHostKeyChecking=no systest@ccycloud-2.snemeth-netty.root.hwx.site:/home/systest/certs/server2.cert /home/systest/certs/ && ls -la /home/systest/certs"
ssh ccycloud-3.snemeth-netty.root.hwx.site "scp -o StrictHostKeyChecking=no systest@ccycloud-4.snemeth-netty.root.hwx.site:/home/systest/certs/server4.cert /home/systest/certs/ && ls -la /home/systest/certs"

ssh ccycloud-4.snemeth-netty.root.hwx.site "scp -o StrictHostKeyChecking=no systest@ccycloud-2.snemeth-netty.root.hwx.site:/home/systest/certs/server2.cert /home/systest/certs/ && ls -la /home/systest/certs"
ssh ccycloud-4.snemeth-netty.root.hwx.site "scp -o StrictHostKeyChecking=no systest@ccycloud-3.snemeth-netty.root.hwx.site:/home/systest/certs/server3.cert /home/systest/certs/ && ls -la /home/systest/certs"


# 4.2 Import server certificates into client truststore on all hosts (NEED TO RUN THESE ON ALL MACHINES)
client_truststore="/home/systest/keystores/truststore.jks"
client_truststore_pass="truststore_pass"
for cert in `find /home/systest/certs/*.cert`; do 
	echo "file: $cert";
	sudo chmod 777 $client_truststore
	alias=$(basename $cert | cut -d '.' -f1);
	echo "cert alias: $alias"
	keytool -v -importcert -file $f -alias $alias -keystore $client_truststore -storepass $client_truststore_pass -noprompt

	echo "Listing certificates in client truststore: "
	keytool -list -keystore $client_truststore -storepass $client_truststore_pass
done


### TRY TO RUN JOBS AGAIN
#Exception in reducer containers, syslog.shuffle: 
# java.io.IOException: HTTPS hostname wrong:  should be <ccycloud-2.snemeth-netty.root.hwx.site>
# 	at sun.net.www.protocol.https.HttpsClient.checkURLSpoofing(HttpsClient.java:649)
# 	at sun.net.www.protocol.https.HttpsClient.afterConnect(HttpsClient.java:573)
# 	at sun.net.www.protocol.https.AbstractDelegateHttpsURLConnection.setNewClient(AbstractDelegateHttpsURLConnection.java:100)
# 	at sun.net.www.protocol.https.AbstractDelegateHttpsURLConnection.setNewClient(AbstractDelegateHttpsURLConnection.java:80)
# 	at sun.net.www.protocol.http.HttpURLConnection.writeRequests(HttpURLConnection.java:706)
# 	at sun.net.www.protocol.http.HttpURLConnection.getInputStream0(HttpURLConnection.java:1591)
# 	at sun.net.www.protocol.http.HttpURLConnection.getInputStream(HttpURLConnection.java:1498)
# 	at java.net.HttpURLConnection.getResponseCode(HttpURLConnection.java:480)
# 	at sun.net.www.protocol.https.HttpsURLConnectionImpl.getResponseCode(HttpsURLConnectionImpl.java:352)
# 	at org.apache.hadoop.mapreduce.task.reduce.Fetcher.verifyConnection(Fetcher.java:436)
# 	at org.apache.hadoop.mapreduce.task.reduce.Fetcher.setupConnectionsWithRetry(Fetcher.java:402)
# 	at org.apache.hadoop.mapreduce.task.reduce.Fetcher.openShuffleUrl(Fetcher.java:272)
# 	at org.apache.hadoop.mapreduce.task.reduce.Fetcher.copyFromHost(Fetcher.java:331)
# 	at org.apache.hadoop.mapreduce.task.reduce.Fetcher.run(Fetcher.java:199)
## https://stackoverflow.com/questions/1802051/https-hostname-wrong-should-be-sub-domain-com-what-causes-this
### --> Possible reason: 
#: Argument: '-ext SubjectAlternativeName:c=DNS:$HOSTNAME' was missing when public / private key pair was generated for the servers

