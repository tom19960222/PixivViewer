#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)


def _login(username, password):
    LOGINURL = "https://oauth.secure.pixiv.net/auth/token"
    data = {'username': username, 'password': password, "grant_type": "password",
            "client_id": "bYGKuGVw91e0NMfPGp44euvGt59s", "client_secret": "HP3RmkgAmEGro0gn1x9ioawQE8WMfvLXDz3ZqxpK"}
    r = requests.post(LOGINURL, data=data)
    r.encoding = 'utf-8'
    PHPSESSID = r.cookies['PHPSESSID']
    return PHPSESSID


def _doSearch(PHPSESSID, keyword, pages):
    resultList = list()
    cookie = {"PHPSESSID": PHPSESSID}

    for i in range(1, pages):
        URL = "http://www.pixiv.net/search.php?word=" + keyword + "&s_mode=s_tag_full&order=date_d&p="+str(i)
        r = requests.get(URL, cookies=cookie)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text)

        liList = soup.find_all('li', attrs={"class": "image-item"})
        for li in liList:
            resultdata = dict()
            resultdata['picsrc'] = li.a.div.img.get('src')
            resultdata['title'] = li.a.next_sibling.h1.text
            resultdata['link'] = "http://www.pixiv.net" + li.a.get('href')
            resultdata['illust_id'] = getWorkID(resultdata['link'])
            resultdata['author'] = li.a.next_sibling.next_sibling.text
            resultdata['author_link'] = "http://www.pixiv.net" + li.a.next_sibling.next_sibling.get('href')
            resultdata['author_id'] = getWorkID(resultdata['author_link'])

            print(li.a.div.img.get('src'))
            print(li.a.next_sibling.h1.text)
            if li.ul is not None:
                resultdata['stars'] = int(li.ul.li.a.text)
            else:
                resultdata['stars'] = 0
            print(resultdata['stars'])

            resultList.append(resultdata)
    return resultList


def getWorkID(link):
    b = str()
    a = link.split('&')
    for i in a:
        if i.__contains__('illust_id'):
            b = i.split('=')[1]
    return b


def saveToDatabase(data):
    dbClient = MongoClient('nas.hsexpert.net', 27017)
    db = dbClient.PixivViewer
    searchDB = db.PixivSearchResult

    savedata = {
        "illust_id": data['illust_id'],
        "link": data['link'],
        "picsrc": data['picsrc'],
        "title": data['title'],
        "stars": data['stars'],
        "time": time.time()
    }

    query = list()
    for key in savedata.keys():
        q = {'$set': {key: savedata[key]}}
        query.append(q)
    query.append({'$addToSet': {'keyword': data['keyword']}})

    for q in query:
        print("Processing query %s" % q)
        searchDB.update_one({'illust_id': data['illust_id']}, q, upsert=True)


def main():
    import sys
    reload(sys)
    sys.setdefaultencoding('utf8')
    app.run(host='0.0.0.0', debug=True)


@app.route('/search', methods=['GET'])
def search():
    keyword = request.args.get('keyword')
    pages = int(request.args.get('pages'))
    PHPSESSID = request.cookies.get('PHPSESSID')
    resultList = sorted(_doSearch(PHPSESSID, keyword, pages), key=lambda x: x['stars'], reverse=True)
    return render_template('pixiv.html', keyword=keyword, search_count=resultList.__len__(), dataList=resultList)

@app.route('/login', methods=['GET'])
def login():
    username = request.args.get('username')
    password = request.args.get('password')

    PHPSESSID = _login(username, password)
    response = jsonify({'PHPSESSID': PHPSESSID})
    response.set_cookie('PHPSESSID', value=PHPSESSID)
    return response

if __name__ == '__main__':
    main()