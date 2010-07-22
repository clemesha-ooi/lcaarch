import logging
from twisted.internet import defer

from magnet.spawnable import Receiver, spawn
from ion.test.iontest import IonTestCase
from ion.core.base_process import BaseProcess

from ion.services.cei.sensors.rabbitmq_sensor import RabbitMQSensor 
import ion.util.procutils as pu


class TestSensors(IonTestCase):
    """Test the RabbitMQ Sensor for now (more later).
    """

    @defer.inlineCallbacks
    def setUp(self):
        yield self._start_container()
        bproc = BaseProcess()
        # the 'test' work queue:
        self.queue_name_work = bproc.get_scoped_name("system", "test_cei_sensors_work")
        #for the sensor events queue:
        self.queue_name_events = bproc.get_scoped_name("system", "test_cei_sensors_events")
        self.total_messages = 5
        topic = {
            self.queue_name_work:{'name_type':'worker', 'args':{'scope':'global'}},
            self.queue_name_events:{'name_type':'fanout', 'args':{'scope':'global'}}
        }
        yield self._declare_messaging(topic)

        #create a test SA:
        self.test_sa = TestSensorAggregator(self.queue_name_events)
        #now spawn it:
        sa_id = yield spawn(self.test_sa.receiver) 
        yield self.test_sa.plc_init()

        services = [
            {'name':'rabbitmq_sensor','module':'ion.services.cei.sensors.rabbitmq_sensor', 
            'spawnargs':{'queue_name_work':self.queue_name_work, 'queue_name_events':self.queue_name_events}}
        ]
        self.sup = yield self._spawn_processes(services)
        self.rabbitmq_sensor = self.sup.get_child_id("rabbitmq_sensor")
        
        for i in range(self.total_messages):
            yield self.sup.send(self.queue_name_work, 'data', "test_message"+str(i))

    @defer.inlineCallbacks
    def tearDown(self):
        result = yield self.sup.rpc_send(self.rabbitmq_sensor, "stop", {})
        yield self._stop_container()

    @defer.inlineCallbacks
    def test_rabbitmq_sensor(self):
        yield pu.asleep(5) #async wait
        logging.info("test_rabbitmq_sensor => message_count='%s'"% self.test_sa.message_count)
        self.assertEqual(self.total_messages, self.test_sa.message_count)


class TestSensorAggregator(BaseProcess):
    """Class for the client accessing the object store.
    """
    def __init__(self, queue_name_events, *args):
        BaseProcess.__init__(self, *args)
        self.queue_name_events = queue_name_events
        self.message_count = 0

    @defer.inlineCallbacks
    def plc_init(self):
        # create new receiver ('listener'), for the events (just the receiver object)
        self.event_receiver = Receiver("event_receiver", self.queue_name_events)
        # set BaseProcesses receive method as the callback for the new receiver that was just created.
        self.event_receiver.handle(self.receive)
        # actually create queue consumer:
        receiver_id = yield spawn(self.event_receiver)
        
    def op_event(self, content, headers, msg):
        self.message_count = int(content['messages'])
