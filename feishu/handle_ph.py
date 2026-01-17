#!/usr/bin/python
# encoding=utf-8
import requests
import sys
import json
import os
import time

API_TOKEN = 'xxx'
differential_diff_search = 'https://cr.test.com/api/differential.query'
user_query = 'https://cr.test.com/api/user.query'
project_query = 'https://cr.test.com/api/project.query'

corpid = 'xxx'
corpsecret = 'xxx'

agentid = '1000059'

APP_ID = "xxx"
APP_SECRET = "xxx"
APP_VERIFICATION_TOKEN = "xxx"


def gettoken(corpid, corpsecret):
    gettoken_url = 'https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid=' \
                   + corpid + '&corpsecret=' + corpsecret

    token_file = requests.get(gettoken_url, timeout=60)
    token_json = token_file.json()
    token = token_json['access_token']
    return token


def gettoken_feishu():
    url = "https://open.feishu.cn/open-apis/auth/v3/" \
          "tenant_access_token/internal/"
    headers = {
        "Content-Type": "application/json"
    }
    req_body = {
        "app_id": APP_ID,
        "app_secret": APP_SECRET
    }

    req = requests.post(url=url, data=json.dumps(req_body), headers=headers,
                        timeout=60)
    req_json = req.json()
    return req_json['tenant_access_token']


def get_username(userid):
    data = dict()
    data['api.token'] = API_TOKEN
    data['phids[0]'] = userid
    response = requests.post(user_query, data=data).json()
    # print(response)
    if response['result']:
        result = response['result'][0]
        return result['userName'] + '@test.com'
    return None


def shufei_send(access_token, email, content):
    url = "https://open.feishu.cn/open-apis/message/v4/send/"
    headers = {
        "Authorization": ' '.join(['Bearer', access_token]),
        "Content-Type": "application/json"
    }
    data = dict()
    data["email"] = email
    # data["email"] = 'robot@test.com'
    data["msg_type"] = "post"
    data["content"] = content

    req = requests.post(url=url, data=json.dumps(data), headers=headers,
                        timeout=60)
    req_json = req.json()


def we_chat_notify(user_list, statusName, uri, title, author, branch, summary,
                   dateCreated, accepter_line, tr_author, tr_type,
                   tr_comment_line, ignore_user):
    if tr_author.strip() == 'robot@test.com' or statusName == 'Draft':
        if author in ignore_user:
            return
        user_list = [author]

    access_token = gettoken_feishu()

    content = dict()
    content["post"] = dict()
    content["post"]["zh_cn"] = dict()
    content["post"]["zh_cn"][
        "title"] = '[CR] Action Type: ' + tr_type
    content["post"]["zh_cn"]["content"] = list()
    content["post"]["zh_cn"]["content"].append(
        [{"tag": "text", "text": "Changed by: " + tr_author}])
    content["post"]["zh_cn"]["content"].append([
        {"tag": "text", "text": "Link: "},
        {"tag": "a", "text": uri, "href": uri}
    ]
    )
    content["post"]["zh_cn"]["content"].append(
        [{"tag": "text", "text": "Status: " + statusName}])
    content["post"]["zh_cn"]["content"].append(
        [{"tag": "text", "text": "Accept History: " + accepter_line}])
    if len(tr_comment_line.strip()) > 0:
        content["post"]["zh_cn"]["content"].append(
            [{"tag": "text", "text": "Comments: " + tr_comment_line}])
    content["post"]["zh_cn"]["content"].append(
        [{"tag": "text", "text": "Author :" + author}])
    content["post"]["zh_cn"]["content"].append(
        [{"tag": "text", "text": "Title :" + title}])
    if branch:
        content["post"]["zh_cn"]["content"].append(
            [{"tag": "text", "text": "Branch :" + branch}])
    for email in user_list:
        try:
            shufei_send(access_token, email, content)
        except:
            pass

    return user_list


def get_reviewers(reviewers_ph):
    output = list()
    for i in reviewers_ph:
        if i.find('PHID-PROJ') == 0:
            data = dict()
            data['api.token'] = API_TOKEN
            data['phids[0]'] = i
            result = \
                requests.post(project_query, data=data).json()['result'][
                    'data'][
                    i]['members']
            for j in result:
                user = get_username(j)
                if user:
                    output.append(user)
        else:
            user = get_username(i)
            if user:
                output.append(user)
    return output


def change_username(user_list, reviewers):
    user_list = user_list + '|robot'
    return user_list


def process_transaction(revision_id, transaction_id):
    data = dict()
    data['api.token'] = API_TOKEN
    data['objectIdentifier'] = revision_id
    data['limit'] = 99999
    result = requests.post('https://cr.test.com/api/transaction.search',
                           data=data).json()['result']['data']
    get_transaction = False
    accepters = list()
    tr_type = list()
    comments = list()
    author = list()
    for i in result:
        if i['authorPHID'] == 'PHID-APPS-PhabricatorHarbormasterApplication':
            continue
        if i['phid'] in transaction_id:
            get_transaction = True
            tr_type.append(i['type'])
            for j in i['comments']:
                comments.append(j['content']['raw'])
            user = get_username(i['authorPHID'])
            if user:
                author.append(user)
        if i['type'] == 'accept':
            user = get_username(get_username(i['authorPHID']))
            if user:
                accepters.append(user)
    if not get_transaction:
        return False
    author = list(set(author))

    tr_type = list(set(tr_type))
    if None in tr_type:
        tr_type.remove(None)

    if len(tr_type) == 0:
        sys.exit(0)

    accepters = list(set(accepters))

    tr_type_line = ','.join(tr_type)
    author_line = ','.join(author)
    accepter_line = ','.join(accepters)
    comment_line = '\n'.join(comments)
    return accepter_line, author_line, tr_type_line, comment_line


def get_revision(revision_id):
    data = dict()
    data['api.token'] = API_TOKEN
    data['phids[0]'] = revision_id
    result = \
        requests.post(differential_diff_search, data=data).json()['result'][0]
    return result


def read_ignore_user():
    path = os.path.dirname(os.path.abspath(__file__))
    ignore_path = os.path.join(path, 'ignore.txt')
    with open(ignore_path, 'r') as f:
        user_str = f.read()
    users = user_str.split('\n')
    return [u.strip() for u in users]


def main(revision_id, transaction_id):
    res = process_transaction(
        revision_id, transaction_id)
    if isinstance(res, bool):
        return
    accepter_line, tr_author, tr_type, tr_comment_line = res
    result = get_revision(revision_id)
    uri = result['uri']
    author = get_username(result['authorPHID'])
    title = result['title']
    summary = result['summary']
    branch = result['branch']
    statusName = result['statusName']
    dateCreated = time.ctime(int(result['dateCreated']))
    if type(result['reviewers']) is dict:
        reviewers = get_reviewers(result['reviewers'].keys())
    else:
        reviewers = list()
    if author:
        reviewers.append(author)
    reviewers = list(set(reviewers))

    ignore_user = read_ignore_user()
    for ignore in ignore_user:
        if ignore in reviewers:
            reviewers.remove(ignore)
    users = we_chat_notify(reviewers, statusName, uri, title, author, branch,
                           summary,
                           dateCreated, accepter_line, tr_author, tr_type,
                           tr_comment_line, ignore_user)
    # log(json.dumps(data), 'ph_user')
    # log(json.dumps(users), 'ph_user')
    return users


if __name__ == '__main__':
    # main('PHID-DREV-6tc6wkbkanlsrsa7migm', 'PHID-XACT-DREV-3hqaklnl3juri5b')

    data = {
        "object": {"type": "DREV", "phid": "PHID-DREV-t6aa2mscxa6tc3crdboa"},
        "triggers": [{"phid": "PHID-HRUL-igzqog5sos2yqiauzavy"}],
        "action": {"test": False, "silent": False, "secure": False,
                   "epoch": 1655878485},
        "transactions": [{"phid": "PHID-XACT-DREV-kyobwnui7lavdsp"},
                         {"phid": "PHID-XACT-DREV-i5dlivhq4aajcvr"},
                         {"phid": "PHID-XACT-DREV-eldi3kgp6zqbwoh"}]}

    phid = data['object']['phid']
    tr_ids = list()
    for i in data['transactions']:
        tr_ids.append(i['phid'])
    t = time.time()
    users = main(phid, tr_ids)
    print(users)
    print(time.time()-t)
