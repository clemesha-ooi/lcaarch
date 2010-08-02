#!/usr/bin/env python

"""
@file ion/services/cei/dtrs.py
@author Alex Clemesha
@author David LaBissoniere
@brief Deployable Type Registry Service. Used to look up Deployable type data/metadata.
"""

import logging

from twisted.internet import defer

from ion.core.base_process import ProtocolFactory
from ion.services.base_service import BaseService, BaseServiceClient
from ion.core import ioninit

__all__ = ['DeployableTypeRegistryService', 'DeployableTypeRegistryClient']

#TODO ugggggggggghhhhhhhhh
_REGISTRY = {}
CONF = ioninit.config(__name__)
execfile(CONF['deployable_types'])
logging.debug('Loaded %s deployable types.', len(_REGISTRY))

class DeployableTypeRegistryService(BaseService):
    """Deployable Type Registry service interface
    """
    declare = BaseService.service_declare(name='dtrs', version='0.1.0', dependencies=[])

    def slc_init(self):
        pass

    def op_lookup(self, content, headers, msg):
        """Resolve a depoyable type
        """

        logging.debug('Recieved DTRS lookup. content: ' + str(content))
        # just using a file for this right now, to keep it simple
        dtId = content['deployable_type']
        nodes = content.get('nodes')
        try:
            dt = _REGISTRY[dtId]
        except KeyError:
            logging.error('Invalid deployable type specified: ' + dtId)
            return self.reply_err(msg)
        
        response_nodes = {}
        result = {'document' : dt['document'], 'nodes' : response_nodes}
        sites = dt['sites']

        for node_name, node in nodes.iteritems():

            try:
                node_site = node['site']
            except KeyError:
                logging.error('Node request missing site: ' + node_name)
                return self.reply_err(msg)
                
            try:
                site_node = sites[node_site][node_name]
            except KeyError:
                logging.error('Invalid deployable type site specified: ' + node_site)
                return self.reply_err(msg)

            response_nodes[node_name] = {
                    'iaas_image' : site_node.get('image'),
                    'iaas_allocation' : site_node.get('allocation'),
                    'iaas_sshkeypair' : site_node.get('sshkeypair'),
                    }

        logging.debug('Sending DTRS response: ' + str(result))

        return self.reply_ok(msg, result)

class DeployableTypeRegistryClient(BaseServiceClient):
    """Client for accessing DTRS
    """
    def __init__(self, proc=None, **kwargs):
        if not 'targetname' in kwargs:
            kwargs['targetname'] = "dtrs"
        BaseServiceClient.__init__(self, proc, **kwargs)
        
    @defer.inlineCallbacks
    def lookup(self, dt, nodes=None):
        """Lookup a deployable type
        """
        yield self._check_init()
        logging.debug("Sending DTRS lookup request")
        (content, headers, msg) = yield self.rpc_send('lookup', {
            'deployable_type' : dt,
            'nodes' : nodes
        })

        if content.get('status') == 'ERROR':
            raise KeyError()

        defer.returnValue({
            'document' : content.get('document'),
            'nodes' : content.get('nodes')
            })

# Direct start of the service as a process with its default name
factory = ProtocolFactory(DeployableTypeRegistryService)
