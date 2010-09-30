import logging
from socket import gethostname

from ion.services.cei.sensors.sensor import SensorProcess

from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.task import LoopingCall

from ion.core.base_process import ProtocolFactory

from ion.services.cei import cei_events

class RabbitMQSensor(SensorProcess):
    """Obtain specific RabbitMQ data.

    Uses the 'txrabbitmq' library to communicate with RabbitMQ.
    """

    def plc_init(self):
        SensorProcess.plc_init(self)
        self.queue_name_work = self.get_scoped_name("system", self.spawn_args["queue_name_work"])
        self.queue_name_events = self.get_scoped_name("system", self.spawn_args["queue_name_events"])
        self.epu_controller = self.get_scoped_name("system", "epu_controller")

        erlang_cookie = self.spawn_args.get("erlang_cookie", None)
        if erlang_cookie is None:
            cookiefile = open(os.path.expanduser("~/.erlang.cookie"))
            erlang_cookie = cookiefile.read().strip()
            cookiefile.close()
        
        remote_node = self.spawn_args.get("rabbitmq_node", "rabbit@localhost") 
        local_node = gethostname()
        
        self.sensor_client = self._create_sensor_client(erlang_cookie, local_node, remote_node)
        
        self.sensor_loop = LoopingCall(self.messages_in_queue)
        if self.start_immediately:
            self.sensor_loop.start(self.sensor_interval)

    def _create_sensor_client(self, erlang_cookie, local_node, remote_node):
        from txrabbitmq.service import RabbitMQControlService
        from twotp.node import Process, buildNodeName
        logging.debug("RMQ client, remote_node: %s" % remote_node)
        logging.debug("RMQ client, local_node: %s" % local_node)
        nodeName = buildNodeName(local_node)
        process = Process(nodeName, erlang_cookie)
        return RabbitMQControlService(process, remote_node)

    @inlineCallbacks
    def op_stop(self, content, headers, msg):
        """Stop the LoopingCall"""
        self.sensor_loop.stop()
        yield self.reply_ok(msg)

    @inlineCallbacks
    def messages_in_queue(self):
        """
        Returns the number of existing messages in queue 'queue_name'.
        Returns -1 if 'queue_name' does not exist.
        """
        allqueues = yield self.sensor_client.list_queues()
        logging.info("=== messages_in_queue ===")
        for q in allqueues["result"]:
            if q[0] == self.queue_name_work:
                queuelen = q[1]["messages"]
                #logging.info("In queue '%s' there are '%s' messages"% (self.queue_name_work, queuelen))
                extradict = {"queuelen": queuelen, "queue_name": self.queue_name_work}
                cei_events.event("queue_sensor", "queuelen", logging, extra=extradict)
                content = {"queue_id":self.queue_name_work, "queuelen":queuelen}
                yield self.send(self.epu_controller, "sensor_info", content)

# Direct start of the service as a process with its default name
factory = ProtocolFactory(RabbitMQSensor)
