import sys
import json
import datetime
import time
from copy import deepcopy
from typing import TypeVar, Dict, Any

from django.conf import settings
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
from .event import Event
from .utils import get_storage

is_python3 = sys.version_info >= (3,)

# minutes before purging an event from the database
EVENT_TIMEOUT = 60 * 24

# attempt to trim this many events per pass
EVENT_TRIM_BATCH = 50

T = TypeVar("T")


class EventDoesNotExist(Exception):
    def __init__(self, message, current_id):
        super(Exception, self).__init__(message)
        self.current_id = current_id


class RedisPackageIsNotAvailable(Exception):
    def __init__(self, message):
        super(Exception, self).__init__(message)


class IncompatibleSettings(Exception):
    def __init__(self, message):
        super(Exception, self).__init__(message)


class StorageBase(object):
    def append_event(self, channel, event_type, data):
        raise NotImplementedError()

    def get_events(self, channel, last_id, limit=100):
        raise NotImplementedError()

    def get_current_id(self, channel):
        raise NotImplementedError()


class RedisStorage(StorageBase):
    def __init__(self) -> None:
        """
        Initializes the RedisModelStorage instance by getting Redis connection details
        from settings and setting storage timeout.
        """
        self.connection_details = self._get_redis_connection_details()
        self.redis_client = None

    @staticmethod
    def _get_redis_connection_details() -> Dict[str, any]:
        """
        Static method to retrieve Redis connection details from settings.

        Returns:
            dict: Redis connection details including host, port, and other configuration parameters.
        """
        connection_details = getattr(settings, "EVENTSTREAM_STORAGE_CONNECTION")
        if not isinstance(connection_details, dict):
            raise IncompatibleSettings(
                "To use Redis as event stream storage, please set the connection details of Redis in settings.py EVENTSTREAM_STORAGE_CONNECTION"
            )
        return deepcopy(connection_details)

    def _connect(self):
        """
        Connects to the Redis server using the provided connection details.

        Returns:
            Redis: A Redis client instance.

        Raises:
            RedisPackageIsNotAvailable: If the Redis package is not available.
        """
        try:
            import redis

            return redis.Redis(**self.connection_details)
        except ModuleNotFoundError:
            raise RedisPackageIsNotAvailable(
                "Redis package is not available. Please install it using !pip install redis"
            )

    @property
    def redis(self):
        """
        Lazily initializes the Redis client.

        Returns:
            Redis: A Redis client instance.
        """
        if self.redis_client is None:
            self.redis_client = self._connect()
        return self.redis_client

    def append_event(self, channel: str, event_type: str, data: dict):
        """
        Appends a new event to the storage for the specified channel.

        Args:
            channel (str): The name of the channel to append the event to.
            event_type (str): The type of the event.
            data (dict): The data associated with the event.

        Returns:
            Event: An Event object representing the appended event.
        """
        with self.redis.pipeline() as pipe:
            try:
                event_id = pipe.incr("event_counter:" + channel)
                event_data = json.dumps({"type": event_type, "data": data})
                pipe.setex(
                    "event:" + channel + ":" + str(event_id),
                    EVENT_TIMEOUT * 60,
                    event_data,
                )
                pipe.execute()
                return Event(channel, event_type, data, id=event_id)
            except ConnectionError as e:
                raise ConnectionError("Failed to append event to Redis.") from e

    def get_events(self, channel: str, last_id: int, limit: int = 100):
        """
        Retrieves events from the storage for the specified channel,
        starting from the last known event ID.

        Args:
            channel (str): The name of the channel to retrieve events from.
            last_id (int): The ID of the last event retrieved.
            limit (int, optional): The maximum number of events to retrieve. Defaults to 100.

        Returns:
            list[Event]: A list of Event objects retrieved from the storage.
        """
        events = []
        current_id = self.get_current_id(channel)
        if last_id >= current_id:
            return events
        for i in range(last_id + 1, min(last_id + limit + 1, current_id + 1)):
            event_data = self.redis.get("event:" + channel + ":" + str(i))
            if event_data:
                event = json.loads(event_data)
                events.append(Event(channel, event["type"], event["data"], id=i))
        return events

    def get_current_id(self, channel: str):
        """
        Gets the current event ID for the specified channel.

        Args:
            channel (str): The name of the channel to get the current event ID for.

        Returns:
            int: The current event ID for the specified channel.
        """
        current_id = self.redis.get("event_counter:" + channel)
        return int(current_id) if current_id else 0


class DjangoModelStorage(StorageBase):
    def append_event(self, channel, event_type, data):
        from . import models

        db_event = models.Event(
            channel=channel,
            type=event_type,
            data=json.dumps(data, cls=DjangoJSONEncoder),
        )
        db_event.save()

        self.trim_event_log()

        e = Event(db_event.channel, db_event.type, data, id=db_event.eid)

        return e

    def get_events(self, channel, last_id, limit=100):
        from . import models

        if is_python3:
            assert isinstance(last_id, int)
        else:
            assert isinstance(last_id, (int, long))

        try:
            ec = models.EventCounter.objects.get(name=channel)
            cur_id = ec.value
        except models.EventCounter.DoesNotExist:
            cur_id = 0

        if last_id == cur_id:
            return []

        # look up the referenced event first, to avoid a range query when
        #   the referenced event doesn't exist
        try:
            models.Event.objects.get(channel=channel, eid=last_id)
        except models.Event.DoesNotExist:
            raise EventDoesNotExist("No such event %d" % last_id, cur_id)

        # increase limit by 1 since we'll exclude the first result
        db_events = models.Event.objects.filter(
            channel=channel, eid__gte=last_id
        ).order_by("eid")[: limit + 1]

        # ensure the first result matches the referenced event
        if len(db_events) == 0 or db_events[0].eid != last_id:
            raise EventDoesNotExist("No such event %d" % last_id, cur_id)

        # exclude the first result
        db_events = db_events[1:]

        out = []
        for db_event in db_events:
            e = Event(
                db_event.channel,
                db_event.type,
                json.loads(db_event.data),
                id=db_event.eid,
            )
            out.append(e)

        return out

    def get_current_id(self, channel):
        from . import models

        try:
            ec = models.EventCounter.objects.get(name=channel)
            return ec.value
        except models.EventCounter.DoesNotExist:
            return 0

    def trim_event_log(self):
        from . import models

        now = timezone.now()
        cutoff = now - datetime.timedelta(minutes=EVENT_TIMEOUT)
        while True:
            events = models.Event.objects.filter(created__lt=cutoff)[:EVENT_TRIM_BATCH]
            if len(events) < 1:
                break
            for e in events:
                try:
                    e.delete()
                except models.Event.DoesNotExist:
                    # someone else deleted. that's fine
                    pass
