#Description

This is Stratum Proxy for Monero-pools (RPCv2) using asynchronous networking written in Python Twisted.

# # #

If you lost connections to your proxy and have a lot of users, check limits of your system in /etc/security/limits.conf

The best way to increase limits of open files:

 proxyuser hard nofile 1048576
 
 proxyuser soft nofile 1048576

# # #

**NOTE:** This fork is still in development. Some features may be broken. Please report any broken features or issues.

#Features

* XMR stratum proxy
* Central Wallet configuration, miners doesn't need wallet as username
* Support mining to exchange
* Support monitoring via email
* Bypass worker_id for detailed statistic and per rig monitoring
* Only one connection to the pool
* Individually Vardiff for workers.

#ToDo

* Automatically failover via proxy, also for non-supported miners (ccminer)

#Configuration

* all configs file config.py

#Example for miners

* ./minerd -a cryptonight -o stratum+tcp://127.0.0.1:8080 -u 123456 -p 1

#Donations 

* XMR:  466KoUjvbFE2SduDyiZQUb5QviKo6qnbyDGDB46C6UcTDi5XmVtSXuRYJDmgd6mhYPU92xJHsTQyrSjLbsxdzKQc3Z1PZQM

#Requirements

xmr-proxy is built in python. I have been testing it with 2.7.3, but it should work with other versions. The requirements for running the software are below.

* Python 2.7+
* python-twisted
* Pool with support for this proxy

#Installation

* just copy and start xmr-proxy.py

#Contact

* I am available via admin@dwarfpool.com


#Credits

* Original version by Slush0 (original stratum code)
* More Features added by GeneralFault, Wadee Womersley and Moopless

#License

* This software is provides AS-IS without any warranties of any kind. Please use at your own risk. 
