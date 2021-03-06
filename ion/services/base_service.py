#!/usr/bin/env python

"""
@file ion/services/base_service.py
@author Michael Meisinger
@brief base classes for all service interfaces, and clients.
"""

import logging
from twisted.internet import defer
from magnet.container import Container
from magnet.spawnable import Receiver
from magnet.spawnable import spawn

from ion.core import base_process
from ion.core.base_process import BaseProcess, BaseProcessClient
import ion.util.procutils as pu

class BaseService(BaseProcess):
    """
    This is the superclass for all service processes.  A service process is a
    Capability Container process that can be spawned  anywhere in the network
    and that provides a service under a defined service name. The service
    subclass must have declaration with service name and dependencies.
    """
    declare = {}

    def __init__(self, receiver=None, spawnArgs=None):
        """
        Initializes base service. The service name is taken from the service
        declaration
        """
        BaseProcess.__init__(self, receiver, spawnArgs)

        # Determine service known messging name either from spawn args or
        # if not given from service declaration
        self.svc_name = self.spawnArgs.get('servicename', self.declare['name'])
        assert self.svc_name, "Service must have a declare with a valid name"

        msgName = self.get_scoped_name('system', self.svc_name)
        svcReceiver = Receiver(self.svc_name+'.'+self.receiver.label, msgName)
        if hasattr(self.receiver, 'group'):
            svcReceiver.group = self.receiver.group
        self.svc_receiver = svcReceiver
        self.svc_receiver.handle(self.receive)
        self.add_receiver(self.svc_receiver)

    @defer.inlineCallbacks
    def plc_init(self):
        yield self._declare_service_name()
        svcid = yield spawn(self.svc_receiver)
        logging.info('Service process bound to name=%s as pid=%s' % (self.svc_receiver.name, svcid))
        yield defer.maybeDeferred(self.slc_init)

    @defer.inlineCallbacks
    def _declare_service_name(self):
        # Ad hoc service exchange name declaration
        msgName = self.get_scoped_name('system', self.svc_name)
        messaging = {'name_type':'worker', 'args':{'scope':'system'}}
        yield Container.configure_messaging(msgName, messaging)

    def slc_init(self):
        """
        Service life cycle event: initialization of service process. This is
        called once after the receipt of the process init message.
        """
        logging.debug('slc_init()')

    @classmethod
    def _add_messages(cls):
        pass

    @classmethod
    def _add_conv_type(cls):
        pass

    @classmethod
    def service_declare(cls, **kwargs):
        """
        Helper method to create a declaration of service.
        @param kwargs keyword attributes for service. Common ones must be present.
        @retval a dict with service attributes
        """
        logging.info("Service-declare: "+str(kwargs))
        decl = {}
        decl.update(kwargs)
        return decl

class BaseServiceClient(BaseProcessClient):
    """
    This is the base class for service client libraries. Service client libraries
    can be used from any process or standalone (in which case they spawn their
    own client process). A service client makes accessing the service easier and
    can perform client side optimizations (such as caching and transformation
    of certain service results).
    """
