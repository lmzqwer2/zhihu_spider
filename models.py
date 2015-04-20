#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'lmzqwer2'

'''
Models for user, blog, comment.
'''

import time, uuid, random

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
            uid = random.randint(1, nid)
            print uid, nid
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
    createdAt = FloatField(updatable=False, default=time.time)
    tryTime = IntegerField(defult=0)
    last = FloatField(default=0)

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

        
