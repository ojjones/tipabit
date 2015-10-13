
import random
import datetime

from google.appengine.api import memcache
from google.appengine.ext import ndb

import shard

#*********************************************************************
#************************** Tip Log **********************************
#*********************************************************************

TIP_LOG_KEY = 'tip-transaction-key-{}-{:d}'
TIP_LOG_TEMPLATE = 'Date:{:%Y-%m-%d %H:%M:%S}-User:{}-Amount:{:f}'
DATE_TEMPLATE = '{:%Y-%m-%d %H:%M:%S}'

class TipTransactionLogShardConfig(ndb.Model):
    """Tracks the number of shards for each named counter."""

    @classmethod
    def all_keys(cls, user):
        """Returns all possible keys for the users transaction logs.

        Args:
            name: The name of the counter.

        Returns:
            The full list of ndb.Key values corresponding to all the possible
                counter shards that could exist.
        """
        shard_key_strings = [TIP_LOG_KEY.format(user.name, index)
                             for index in range(user.tip_log_count+1)]
        return [ndb.Key(TipTransactionLogShard, shard_key_string)
                for shard_key_string in shard_key_strings]


class TipTransactionLog(ndb.Model):
    date = ndb.DateTimeProperty(auto_now_add=True)
    tip_receiver = ndb.StringProperty()
    amount = ndb.FloatProperty(default=0)

class TipTransactionLogShard(ndb.Model):
    """Shards for each transaction log"""
    logs = ndb.JsonProperty(repeated=True)

#*********************************************************************
#************************** Tip Transactions *************************
#*********************************************************************

@ndb.transactional(xg=True)
def coalesce_balance(user):
    print user
    all_keys = shard.GeneralCounterShardConfig.all_keys('balance_shard', user.name)
    for counter in ndb.get_multi(all_keys):
        if counter is not None:
            user.balance += counter.count
            counter.count = 0
            counter.put()

    user.put()

def tip(user, tip_receiver, amount):
    if (user.balance - amount) < 0:
        coalesce_balance(user)

    _tip_transaction(user, tip_receiver, amount)

@ndb.transactional(xg=True)
def _tip_transaction(user, tip_receiver, amount):
    user.balance -= amount 
    if user.balance < 0:
        raise StandardError("Insufficient Balance")
    user.put()

    log_key = TIP_LOG_KEY.format(user.name, user.tip_log_count)
    tip_logs_shard = TipTransactionLogShard.get_by_id(log_key)
    if tip_logs_shard is None:
        tip_logs_shard = TipTransactionLogShard(id=log_key)

    now = datetime.datetime.now()
    now = DATE_TEMPLATE.format(now)
    tip_entry = { "date" : now,
                  "tip_receiver" : tip_receiver.name,
                  "amount" : amount }
    tip_logs_shard.logs.append(tip_entry)
    tip_logs_shard.put()

    index = random.randint(0, shard.NUM_SHARDS - 1)
    shard_key_string = shard.SHARD_KEY_TEMPLATE.format('balance_shard', tip_receiver.name, index)
    counter = shard.GeneralCounterShard.get_by_id(shard_key_string)
    if counter is None:
        counter = shard.GeneralCounterShard(id=shard_key_string)
    counter.count += amount
    counter.put()
