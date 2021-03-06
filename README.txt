==================================================
LCAarch - OOI Release 1 LCA architecture prototype
==================================================

April 2010 - May 2010

This project provides a service framwork and auxilliary functions for running
architecturally complete, but functionally limited versions of all the
services of the OOI release 1 system with their full architectural dependencies.
In "shore" a data distribution network based on pub-sub messaging with underlying
infrastructure services (security, persistence) and provisioning.

The "core" part of LCAarch provides base classes and a framework for spawnable,
message communicating processes, for services with defined names, for
bootstrapping the system, for managing logging and configuration etc.

For more information, please see:
http://www.oceanobservatories.org/spaces/display/CIDev/LCAARCH+Development+Project

LCAarch is compatible with Python 2.5 and higher, but not Python 3.x
This project has as dependencies Magnet, Carrot, txAMQP, Twisted and pycassa,
(see below)

Get LCAarch with
::
    git clone git@amoeba.ucsd.edu:lcaarch.git

Usage
=====

(all subsequent steps assume start from lcaarch/ dir)

Start empty CC ("Magnet" Python Capability Container) shell with:
::
    twistd -n magnet -h amoeba.ucsd.edu

(to end a magnet container shell, press Ctrl-D Ctrl-C)

Start system by executing within the CC shell:
><>
    from ion.core import bootstrap
    bootstrap.start()

Alternatively from shell executing a script:
::
    twistd -n magnet -h amoeba.ucsd.edu res/scripts/bootstrap.py
    twistd -n magnet -h amoeba.ucsd.edu res/scripts/newcc.py

Run trial test cases (recursively)
::
    trial ion
    trial ion.core
    trial ion.services.coi.test.test_resource_registry

A good learning example is the HelloService
::
    trial ion.play.test.test_hello

Or in the CC shell:
><>
    from ion.play import hello_service
    spawn(hello_service)
    send(1, {'op':'hello','content':'Hello you there!'})

    from ion.play.hello_service import HelloServiceClient
    hc = HelloServiceClient()
    hc.hello()


Install the dependencies: Magnet (see Magnet's Readme)
======================================================
Recommendation:
    Create a virtualenv for installing Magnet and its dependencies.

Twisted Framework
-----------------
::
    easy_install twisted

txAMQP
------
::
    easy_install txamqp

Pycassa
-------
::
    easy_install -U --find-links http://ooici.net/packages pycassa

SimpleJSON (only when running Python2.5)
----------------------------------------
::
    easy_install simplejson

carrot (use txamqp branch)
--------------------------
::
    git clone git://amoeba.ucsd.edu/carrot.git
    (cd carrot; git checkout -b txamqp origin/txamqp)
    (cd carrot; python setup.py install)

Install the Magnet package [NEED Magent 0.3.4 on master branch]
------------------------------------------------------------------
Get the latest version of the repository, if you haven't already.
::
    git clone git://amoeba.ucsd.edu/magnet.git # no ooi credential
    # OR
    git clone git@amoeba.ucsd.edu:magnet.git # need ooi credential
    (cd magnet; python setup.py install)


Note:
=====
This project dependes closely on magnet. Whenever you do a "git pull" on
this project, there is a chance that you need to update and install magnet
again (see above). Please review the branch logs for any hints.


---------------------------------------------------------------------------
Change log:
===========

2010-05-24:
- Modified the IStore interface to support a create_store factory method. This
  method can yield and return a deferred. Modified and fixed IStore impls.
2010-05-22:
- Added timeout to BaseProcess.rpc_send. Use with kwarg timeout=<secs>
- CC-Agent detects missing known containers and removes them from the list
- Enhanced CC-Agent operations and CC shell helpers
- Added sequence numbers for messages
- Added glue functions BaseProcess.reply_ok and reply_err and changes some
  RPC style service operations.
2010-05-20:
- The system now looks for a local config file ionlocal.config and if exists,
  overrides entries in ion.config.
- Test cases use the config file to determine the broker host to use. If local
  config override exists, a different broker (e.g. localhost) can be given.
- Added BaseProcessClient and changed BaseServiceClient and all clients and
  all test cases (again).
- Added container shell helpers under 'cc', such as cc.spawn('hello')
2010-05-16:
- Removed support for BaseProcess.send_message and reply_message. Always use
  send, reply and rpc_send now.
- Any BaseProcess instance can now spawn_child() other processes.
- Removed RpcClient class, because every process can do rpc_send()
- Service processes now also listen to their service name's queue. The service
  name is determined from the service declaration. Two processes will listen
  to the same queue and take messages round robin from the queue.
- Startup arguments evaluated, for instance to start with system name set:
  twistd -n magnet -a sysname=mysys
  twistd -n magnet -a "{'sysname':'mysys'}"
- Added capability container agent process. Start with:
  twistd -n magnet res/scripts/newcc.py
  Agents announce themselves to others in the same system and can spawn procs.
- Name scope 'local' for messaging names means now really local to one container.
  Use scope 'system' for names unique for each bootstrapped system. Do not use
  global names, because they will clash.
- Less verbose trace output for process init messages and changes to other
  trace output as well.
- Changed BaseServiceClient and tests. Initializer arguments different.
- Using master branch of magnet now
2010-05-10:
- Based on entries in config files, service process modules are sought and
  loaded in order to collect the service process declarations. This enables
  a registration of services with versions and dependencies on startup
2010-05-06:
- Refactored the BaseProcess class.
  - You can now do RPC directly from the process, via self.rpc_send without
    the need for an RpcClient. Works even with other messages coming in at the
    same time (using the conv-id)
  - Added aliases: self.send, self.reply (use these now)
  - Process instance can be spawned via self.spawn()
- Provided an easier to use BaseServiceClient, which uses a default service
  name lookup. Accepts BaseProcess instance as argument to use for sending/
  receiving service calls.
