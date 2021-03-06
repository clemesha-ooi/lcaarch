#!/usr/bin/env python

"""
@file ion/services/coi/authorization.py
@author Michael Meisinger
@brief service authorizing access and managing policy within an Org
"""

import logging
from twisted.internet import defer
from magnet.spawnable import Receiver

import ion.util.procutils as pu
from ion.core.base_process import ProtocolFactory
from ion.services.base_service import BaseService, BaseServiceClient

class AuthorizationService(BaseService):
    """Authorization service interface
    """

    # Declaration of service
    declare = BaseService.service_declare(name='authorization', version='0.1.0', dependencies=[])

    def op_authorize(self, content, headers, msg):
        """Service operation: 
        """

# Spawn of the process using the module name
factory = ProtocolFactory(AuthorizationService)

