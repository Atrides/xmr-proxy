# XMR Proxy


This is Stratum Proxy for Monero-pools (RPCv2) using asynchronous networking written in Python Twisted.

**NOTE:** This fork is still in development. Some features may be broken. Please report any broken features or issues.


## Features

* XMR stratum proxy
* Central Wallet configuration, miners doesn't need wallet as username
* Support mining to exchange
* Support monitoring via email
* Bypass worker_id for detailed statistic and per rig monitoring
* Only one connection to the pool
* Individually Vardiff for workers.

## Installation and Configuration

### 1. Get pre-reqs and clone repository

```
pip install python-twisted
git clone <this repo>
cd xmr-proxy
```

### 2. Configure Settings

Edit the ```config.py``` file.  Modify:

*  ```WALLET``` Enter your wallet address.  This is where your monero will be stored when you mine. 
*  ```MONITORING_EMAIL``` Enter your email if you wish to monitor your server.
*  ```POOL_HOST``` Change to a pool you wish to join. 

### 3. Start the Proxy

```
./xmr-proxy.py
```
This will start the proxy. 


### 4. Start miner

The proxy by default opens port ```8080``` to proxy tcp connections to https connections using twisted.  

You can use several different miners.  For example:

```
./minerd -a cryptonight -o stratum+tcp://127.0.0.1:8080 -u 123456 -p 1
```
Or you can use [cpuminer-easy](https://github.com/luisvasquez/cpuminer-easy)

```
./cpuminer -a cryptonight -o stratum+tcp://127.0.0.1:8080 -u 47kgvGgng2ZGjc7Ey3Vk9J3NTN2hEavkEixeUmgTh8NDJ1FQBCxXPM6Yi5VPmWf5WeTR712voQUvh6qwNUnrZJr9B7v4X66 -p myemail.com
```
This will then forward traffic through the proxy and allow you to start mining.  

## Donations 

* XMR:  ```466KoUjvbFE2SduDyiZQUb5QviKo6qnbyDGDB46C6UcTDi5XmVtSXuRYJDmgd6mhYPU92xJHsTQyrSjLbsxdzKQc3Z1PZQM```

## Requirements

xmr-proxy is built in python. I have been testing it with 2.7.3, but it should work with other versions. The requirements for running the software are below.

* Python 2.7+
* python-twisted
* Pool with support for this proxy


## Troubleshooting

If you lost connections to your proxy and have a lot of users, check limits of your system in ```/etc/security/limits.conf```

The best way to increase limits of open files:

```
<proxyuser> hard nofile 1048576 
<proxyuser> soft nofile 1048576
```
Where ```<proxyuser>``` is your user name.  e.g: ```ubuntu```.

## TODO

* Automatically failover via proxy, also for non-supported miners (ccminer)

## Contact

* I am available via admin@dwarfpool.com


## Credits

* Original version by Slush0 (original stratum code)
* More Features added by GeneralFault, Wadee Womersley and Moopless

## License

* This software is provides AS-IS without any warranties of any kind. Please use at your own risk. 
