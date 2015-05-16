#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'lmzqwer2'

'''
Models for user, blog, comment.
'''

import time, uuid, random, thread

from lsqlite import db
from lsqlite.orm import Model, StringField, BooleanField, FloatField, TextField, IntegerField

class Uid(object):
    tot = 0;
    @classmethod
    def next_id(cls):
        return cls.tot
    @classmethod
    def inc_id(cls):
        cls.tot += 1

class User(Model):
    __table__ = 'users'

    hashId = StringField(primary_key=True, ddl='char(32)')
    name = StringField(ddl='nvarchar(30)')
    bio = StringField(ddl='nvarchar(80)')
    spaceName = StringField(ddl='varchar(40)')
    myId = IntegerField(default=Uid.next_id)

    def check_insert(self):
        u = User.find_first('where hashId=?', self.hashId)
        if u is None:
            self.insert()
            Uid.inc_id()
            return 0
        return 1

    @classmethod
    def randomGet(cls):
        nid = Uid.next_id()
        if nid>0:
            uid = random.randint(1, nid) -1
            return cls.find_first('where myId=?', uid)
        else:
            return None

    @classmethod
    def init(cls):
        Uid.tot = cls.count_all()
        return Uid.tot

class UserList(Model):
    __table__ = 'userlist'

    spaceName = StringField(primary_key=True,ddl='varchar(40)')
    createdAt = FloatField(default=time.time)
    tryTime = IntegerField(defult=0)
    last = FloatField(default=0)

    listbuffer = []
    querystr = ''
    querylist = [0]
    querylimit = 0
    lock = thread.allocate_lock()
    @classmethod
    def queryset(cls, query, *args):
        cls.querystr = query
        cls.querylist = [x for x in args]

    @classmethod
    def limitset(cls, limit):
        cls.querylimit = limit

    @classmethod
    def bufferinit(cls):
        cls.lock.acquire()
        l = [ x for x in cls.querylist]
        l.append(cls.querylimit)
        cls.listbuffer = cls.find_by(cls.querystr + ' limit ?', *l)
        cls.lock.release()

    @classmethod
    def queryget(cls):
        if len(cls.listbuffer)==0:
            cls.bufferinit()
        if len(cls.listbuffer)==0:
            return None
        cls.lock.acquire()
        ans = cls.listbuffer.pop()
        cls.lock.release()
        return ans

if __name__ == '__main__':
    import sys
    reload(sys)
    sys.setdefaultencoding('utf-8')
    db.create_engine('zdb.db')
    L = []
    L.append(User)
    L.append(UserList)
    for m in L:
        drop = u'drop table if exists %s' % m.__table__
        db.update(drop)
        sql = u'%s' % m().__sql__()
        print sql
        db.update(sql)
    L = []
    L.append(UserList(spaceName='fanazhe'))
    L.append(UserList(spaceName='zhou-yu-chen-33-18'))
    for m in L:
        print m.__table__, m
        m.insert()

        
