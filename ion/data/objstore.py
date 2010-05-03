#!/usr/bin/env python

"""
@file ion/data/dataobject.py
@author Michael Meisinger
@author David Stuebe
@brief storing structured mutable objects mapped to graphs of immutable values
"""

import logging
import hashlib
import json
import types

from twisted.internet import defer
from magnet.spawnable import Receiver

import ion.util.procutils as pu
from ion.core.base_process import ProtocolFactory, RpcClient
from ion.services.base_service import BaseService, BaseServiceClient


class ValueRef(object):
    """Refers to a unique immutable value but 
    """
    def __init__(self, identity):
        # Save
        self.identity = identity
        
class ValueObject(ValueRef):
    """An instance of ValueObject represents an immutable value with an
    identifier, which is generated by secure hashing the value. This instance
    is not the actual value itself, but the "container" for the immutable,
    uniquely identified value.
    """
    def __init__(self, value, childrefs=None, basedon=None):
        """Initializes an immutable value, which consists of an actual value
        structure and 0 or more refs to child values; each value is logically
        based on other values.
        
        @param value the actual value content (must exist and be JSON'able)
        @param childrefs None, ValueRef or tuple of identities of child values
        @param basedon None, ValueRef or tuple of identities of preceeding values
        """
        
        if not childrefs: childrefs = ()
        elif not type(childrefs) is tuple: childrefs = (childrefs,)
        if not basedon: basedon = ()
        elif not type(basedon) is tuple: basedon = (basedon,)
        
        assert value != None
        assert type(childrefs) is tuple
        assert type(basedon) is tuple

        # Convert child ref into a string (hopefully with identity hash)
        def _reftostr(ref):
            if isinstance(ref,ValueRef): return ref.identity
            else: return str(ref)
            
        # Make a state dict out of all hash relevant fields
        self.state = {}
            
        # Save value (for efficiency purposes)
        self.state['value'] = value

        # Save childrefs, basedon (immutable tuple of str)
        self.state['childrefs'] = [_reftostr(child) for child in childrefs]
        self.state['basedon'] = [_reftostr(child) for child in basedon]
     
        # Encode the state value (this might fail) and save
        self.blob = json.dumps(self.state)

        # Create a secure unique hash of value and child references
        hash = hashlib.sha1(self.blob).hexdigest()
        
        # Init the underlying valueref; use hash as identity
        ValueRef.__init__(self, hash)

class EntityObject(object):
    """An instance of EntityObject "entity" represents a mutable object
    with a given identity. The actual state of the entity exists as reference
    to an immutable value. Entity keeps track of the succession of states over
    time.
    """


class ObjectStoreService(BaseService):
    """Service to store and retrieve structured objects. Updating an object
    will modify the object's state but keep the state history in place. It is
    always possible to
    The GIT distributed repository model is a strong design reference.
    Think local and distributed object store, commits, merges, HEADs, tags.
    """
    def slc_init(self):
        # KVS with entity ID -> most recent value ID
        self.entityidx = {}
        # KVS with value ID -> value 
        self.objstore = {}
        logging.info("ObjectStoreService initialized")
        
    @defer.inlineCallbacks
    def op_put(self, content, headers, msg):
        """Service operation: Puts a structured object into the data store.
        Equivalent to a git-push, with an already locally commited object
        """
        logging.info("op_put: "+str(content))
        val = content['value']
        childrefs = content['childrefs'] if 'childrefs' in content else None
        basedon = content['basedon'] if 'basedon' in content else None
        if isinstance(val,ValueObject):
            v1 = ValueObject(**val.state)
            assert val.identity == v1.identity
            v = val
        else:
            v = ValueObject(val,childrefs,basedon)

        # Use dict to store
        if v.identity in self.objstore:
            logging.info("op_put: value was already in obj store "+str(v.identity))

        # Put value in object store
        self.objstore[v.identity] = v
        
        # Update HEAD ref for entity
        self.entityidx[content['key']] = v
        
        logging.debug("ObjStore state: EI="+str(self.entityidx)+", OS="+str(self.objstore))
        
        # There is no need to return a value
        yield self.reply_message(msg, 'result', self._get_value(v), {})

    @defer.inlineCallbacks
    def op_get(self, content, headers, msg):
        """Service operation: Gets a structured object from the data store.
        Equivalent to a git-pull.
        """
        logging.info("op_get: "+str(content))
        
        v = self.entityidx.get(content['key'], None)
        
        yield self.reply_message(msg, 'result', self._get_value(v), {})

    @defer.inlineCallbacks
    def op_get_values(self, content, headers, msg):
        """Service operation: Gets values from the object store.
        """
        logging.info("op_get_values: "+str(content))
        
        keys = content['keys']
        if not (type(keys) is list or type(keys) is tuple):
            keys = (keys,)
            
        res = []
        for key in keys:
            v = self.objstore.get(key, None)
            res.append(self._get_value(v))

        yield self.reply_message(msg, 'result', res, {})

    @defer.inlineCallbacks
    def op_get_ancestors(self, content, headers, msg):
        """Service operation: Gets all ancestors of a value.
        """
        logging.info("op_get_ancestors: "+str(content))
        key = str(content['key'])
        resvalues = []
        v = self.objstore.get(key, None)
        self._get_ancestors(v, {}, resvalues)

        yield self.reply_message(msg, 'result', resvalues, {})

    def _get_ancestors(self, value, keys, resvalues):
        """Recursively get all ancestors of value, by traversing DAG"""
        if not value: return
        print "_get_ancestors ",value.state
        for anc in value.state['basedon']:
            if not anc in keys:
                keys[anc] = 1
                v = self.objstore.get(anc, None)
                assert v != None, "Ancestor value expected in store"
                resvalues.append(self._get_value(v))
                self._get_ancestors(v, keys, resvalues)

        
    def _get_value(self, vo):
        """Creates a return dict with ValueObject state and identity"""
        if not vo: return {}
        voc = vo.state.copy()
        voc['identity'] = vo.identity
        return voc

# Spawn of the process using the module name
factory = ProtocolFactory(ObjectStoreService)


class ObjectStoreClient(BaseServiceClient):
    """Class for the client accessing the object store.
    """
    def __init__(self, svcName):
        self.svcName = str(svcName)
        self.rpc = RpcClient()

    @defer.inlineCallbacks
    def attach(self):
        yield self.rpc.attach()
    
    @defer.inlineCallbacks
    def put(self, key, value, basedon=None):
        cont = {'key':str(key), 'value':value}
        if basedon and basedon is list:
            cont['basedon'] = basedon
        elif basedon:
            cont['basedon'] = [basedon]
        (content, headers, msg) = yield self.rpc.rpc_send(self.svcName, 'put', cont, {})
        logging.info('Service reply: '+str(content))
        defer.returnValue(str(content['value']))

    @defer.inlineCallbacks
    def get(self, key):
        (content, headers, msg) = yield self.rpc.rpc_send(self.svcName, 'get', {'key':str(key)}, {})
        logging.info('Service reply: '+str(content))
        defer.returnValue(str(content['value']))
