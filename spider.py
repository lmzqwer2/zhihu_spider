#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'lmzqwer2'

'''
Read the volcabulary from shanbay.com
'''

import cookielib, urllib2, urllib, Cookie, re
from lsqlite import db, orm
from models import User, Uid
from bs4 import BeautifulSoup as bs
from IPython import embed
try:
    import json
except ImportError:
    import simplejson as json

cookieJar = cookielib.CookieJar()
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookieJar))
headers = {
    'Host': 'www.zhihu.com',
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/41.0.2272.76 Chrome/41.0.2272.76 Safari/537.36',
    'Referer': 'http://www.zhihu.com/',
    'Accept-Encoding': 'deflate',
    'Accept-Language': 'zh-CN,zh;q=0.8',
    'Cookie': 'q_c1=050daf1212554da3bdd5801a41cb907f|1428635070000|1428635070000; z_c0="QUtCQXVFS2J6UWNYQUFBQVlRSlZUYl9LVGxVSVlid0xrWUZySjV6UHl2U3JwQjNQTjhreE9RPT0=|1428635071|9e86871527a7183b7894cec44755fda70aa1250b"; _xsrf=84e730b281ae1b2f00b65b95e7b04ba9'
}
#opener.handle_open["http"][0].set_http_debuglevel(1)

zhihu_people = 'http://www.zhihu.com/people/'

class searchList(object):
    l = []
    @classmethod
    def add(cls, name):
        cls.l.append(name)
    @classmethod
    def len(cls):
        return len(cls.l)
    @classmethod
    def pop(cls):
        if cls.len()>0:
            return cls.l.pop()
        return None

def getResponse(url, data={}, method=lambda: 'GET', **kw):
    jsdata = json.dumps(data)
    encodejsdata = urllib.urlencode(data)
    request = urllib2.Request(url, encodejsdata)
    request.get_method = method
    for name, values in headers.items():
        if name not in kw:
            request.add_header(name, values)
    for name, values in kw.items():
        request.add_header(name, values)
    response = opener.open(request)
    return response

uid_pattern = re.compile('^/inbox/(.*)$')

def UserInfo(space_name):
    people = zhihu_people + space_name
    try:
        response = getResponse(people)
    except:
        print 'What\'s wrong with your network?'
        return []
    html = bs(response.read())
    user_profile = html.find('div', class_='zm-profile-header')
    user = user_profile.find('div', class_='title-section ellipsis')
    user_name = user.find('span', class_='name' ).text
    user_bio = user.find('span', class_='bio' )
    if user_bio is None:
        user_bio = ''
    else:
        user_bio = ' '.join(user_bio.text.split('\r\n'))
    follow = html.find('button', {'data-follow':'m:button'})
    hash_id = follow['data-id']
    u = User(hashId=hash_id, name=user_name, bio=user_bio, spaceName=space_name)
    if u.check_insert()==0:
        print "INSERT: Space-Name: %s User-Name: %s User-Id:%d\nBio: %s" % (u.spaceName, u.name, u.myId, u.bio)
        searchList.add(u.spaceName)
    else:
        print 'NOTE: %s found in database' % u.name

space_pattern = re.compile('^/people/(.*)$')

def findAllPeople(html):
    followees = html.find_all('div', class_='zm-profile-section-item')
    for people in followees:
        linker = people.find('a', class_='zm-item-link-avatar')
        space_match = space_pattern.match(linker['href'])
        if space_match:
            space_name = space_match.group(1)
            UserInfo(space_name)
 
followee_headers = {
    'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1581.2 Safari/537.36',
    'Host':'www.zhihu.com',
    'Origin':'http://www.zhihu.com',
    'Connection':'keep-alive',
    'Content-Type':'application/x-www-form-urlencoded',
}

def searchUser(space_name):
    for url in ['followees','followers']:
        follow = zhihu_people + space_name + '/' + url
        listurl = 'http://www.zhihu.com/node/Profile'+url.capitalize()+'ListV2'
        try:
            response = getResponse(follow)
        except:
            print 'What\'s wrong with your network?'
            return L
        html = bs(response.read())
        findAllPeople(html)

        listdiv = html.find('div', class_='zh-general-list')
        if listdiv is None:
            continue
        data = json.loads(listdiv['data-init'])
        params = data['params']
        _xsrf = html.find('input', {'name':'_xsrf'})['value']

        items = html.find_all('a', class_='item')
        followee_status = items[6]
        num_followees = followee_status.find('strong').text
        load_times = int(num_followees) / 20 +1

        for i in range(1,load_times):
            params['offset'] = i * 20
            post_data = {
                'method': 'next',
                'params': json.dumps(params),
                '_xsrf': _xsrf,
            }
            post_header = followee_headers
            post_header['Referer'] = follow
            try:
                response = getResponse(listurl, post_data, lambda: 'POST', **post_header)
                data = json.loads(response.read())
                if data.get('r',1)==0:
                    html = bs(''.join(data['msg']))
                    findAllPeople(html)
                else:
                    break;
            except Exception, e:
                print e

def run():
    import sys
#    reload(sys)
#    sys.setdefaultencoding('utf-8')
#    headers['Cookie'] = ''
#    searchFromFollwee('zhao-yue-qi-88')
#    searchFromZhihu('zenozeng')
#    searchFromFollowee('edward-mj')
#    print searchFromFollowee('')
    db.create_engine('tdb.db')
    def dbdrop():
        db.update('drop table if exists users')
        print User().__sql__()
        db.update(User().__sql__())
#dbdrop()
    print User.init()

#searchList.add('lmzqwer2')
#searchList.add('zhou-yu-chen-33-18')
    searchList.add('liangbianyao')
    now = searchList.pop()
    while now is not None:
        print 'SEARCH: %s' % now
        searchUser(now)
        now = searchList.pop()

#searchUser('zhou-yu-chen-33-18')
#searchUser('lmzqwer2')
#searchUser('wang-fan-2-45')
#embed()
    print User.count_all()   

if (__name__ == '__main__'):
    run()
