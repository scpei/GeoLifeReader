import logging
logger = logging.getLogger("geolife.user")
import os
import pltfile
from collections import defaultdict
from record import LinkedRecords
from record import TimeModifiedGeoLifeRecord

class BaseGeoLifeUser:
  def __init__(self):
    self.id = None

  def __str__(self):
    return "<{0}(id={1}, size={2})>".format(
      self.__class__.__name__,
      self.id,
      len(self)
    )
  __repr__=__str__
  
  def __iter__(self):
    raise NotImplemented(
      "Class {0} must implement the __iter__() method.".format(
      self.__class__.__name__
    ))

  def __len__(self):
    raise NotImplemented(
      "Class {0} must implement the __len__() method.".format(
      self.__class__.__name__
    ))

  def __bool__(self):
    raise NotImplemented(
      "Class {0} must implement the __bool__() method.".format(
      self.__class__.__name__
    ))


class GeoLifeUserFromFile(BaseGeoLifeUser):
  def __init__(self, user_id, directory):
    self.id = int(user_id)
    self.files = pltfile.load_from_directory(
      directory=os.path.join(directory, user_id),
      user=self
    )

  def __iter__(self):
    for f in self.files:
      import os
      logger.debug("Reading from file {0}".format(os.path.basename(f.url)))
      for r in f:
        yield r


def from_directory(directory):
  users = []
  for d in os.listdir(directory):
    if os.path.isdir(os.path.join(directory, d)):
      logger.debug("Yielding user {0}".format(d))
      yield GeoLifeUserFromFile(user_id=d, directory=directory)


class GeoLifeUserFromDB(BaseGeoLifeUser):
  def __init__(self):
    BaseGeoLifeUser.__init__(self)
    self.records = []
    self.linked_list = None
    self.record_ptr = None

  def add(self, record):
    if self.id is None:
      self.id = record.user
    self.records.append(record)

  def sort(self):
    self.records.sort(key=lambda r: r.datetime)

  def __len__(self):
    return len(self.records)

  def __iter__(self):
    for i in self.records:
      yield i

  def __bool__(self):
    return bool(self.records)

  def __getitem__(self, key):
    return self.records[key]

  def add_record_if_not_present_for(self, time):
    # If a user exists, then he has at least one record.
    # Upon initialization, the record pointed to by self.record_ptr
    #  has a timestamp greater than or equal to the minimum timestamp
    #  across all records for all other users. Thus, upon initialization
    #  we will be adding records before it.
    
    if self.record_ptr is None:
      self.record_ptr = self.linked_list

    if self.record_ptr.record.datetime == time:
      # A record exists with the time. Nothing is needed.
      self.record_ptr = self.record_ptr.next

    else:
      if self.record_ptr.prev is None:
        # Set synth'd record based on user's true initial location
        reference_record = self.record_ptr.record

      else:
        # Set synth's record based on most recent user's location.
        reference_record = self.record_ptr.prev.record

      # A record does not exist for the given time. We need
      #  to add it to the linked list. It will be a replication
      #  of the current record_ptr.record, only the timing
      #  data will be changed.
      modified_record = TimeModifiedGeoLifeRecord(
        base_record=reference_record,
        timestamp=time
      )
      logger.info("Synthesized record")
      logger.info("Base record:    {0}".format(reference_record))
      logger.info("Synth'd record: {0}".format(modified_record))
      self.record_ptr.insertBefore(
        LinkedRecords([modified_record])
      )


  def link_listify_records(self):
    self.linked_list = LinkedRecords(self.records)


def from_Query(query):
  # Split up the results by user
  users = defaultdict(GeoLifeUserFromDB)
  for record in query:
    users[record.user].add(record)

  users_list = users.values()
  for u in users_list:
      u.sort()
      u.link_listify_records()

  return users_list

