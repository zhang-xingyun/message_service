#!/usr/bin/python
# encoding=utf-8
import requests
import sys
import json
import os
import time
import re
import logging
from ph_app.models import PhUser

API_TOKEN = 'xxx'
differential_diff_search = 'https://cr.test.com/api/differential.query'
user_query = 'https://cr.test.com/api/user.query'
project_query = 'https://cr.test.com/api/project.query'

corpid = ''
corpsecret = ''

agentid = '1000059'

APP_ID = ""
APP_SECRET = ""
APP_VERIFICATION_TOKEN = ""
token_info = {
    'token': None,
    'timestamp': 0,
    'expire':3600
}


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

    current_time = time.time()
    # 判断当前时间与上次获取token的时间戳之差是否大于一个小时
    if current_time - token_info['timestamp'] + 10 > token_info['expire']:
        req = requests.post(url=url, data=json.dumps(req_body), headers=headers,
                            timeout=60)
        req_json = req.json()
        token_info['expire'] = req_json['expire']
        # 如果大于一个小时，则重新获取token
        token_info['token'] = req_json['tenant_access_token']
        # 更新时间戳
        token_info['timestamp'] = current_time


    return token_info['token']


# def get_username(userid):
#     data = dict()
#     data['api.token'] = API_TOKEN
#     data['phids[0]'] = userid
#     response = requests.post(user_query, data=data).json()
#     # print(response)
#     if response['result']:
#         result = response['result'][0]
#         return result['userName'] + '@test.com'
#     return None

def get_username(ph_user_id):
    try:
        ph_user = PhUser.objects.filter(ph_id=ph_user_id)
    except Exception as e:
        logging.error("get ph_user error:" + str(e))
        ph_user = None
    if ph_user:
        logging.info("Found the user from DB")
        return ph_user.first().user_name + '@test.com'
    else:
        data = dict()
        data['api.token'] = API_TOKEN
        data['phids[0]'] = ph_user_id
        response = requests.post(user_query, data=data).json()
        # print(response)
        if response['result']:
            result = response['result'][0]
            try:
                PhUser.objects.update_or_create(
                    ph_id=ph_user_id,
                    user_name=result['userName']
                )
            except Exception as e:
                error_msg = 'Insert ph user error: ' + str(e)
                logging.error(error_msg)
            logging.info("Found the user from API")
            return result['userName'] + '@test.com'
        return None


def shufei_send(access_token, email, content, msg_type='post'):
    url = "https://open.feishu.cn/open-apis/message/v4/send/"
    headers = {
        "Authorization": ' '.join(['Bearer', access_token]),
        "Content-Type": "application/json"
    }
    data = dict()
    data["email"] = email
    # data["email"] = 'robot@test.com'
    if msg_type == "text":
        data["msg_type"] = "text"
        data["content"] = content
    elif msg_type == "mark_down":
        data["msg_type"] = "interactive"
        data["card"] = content
    else:
        data["msg_type"] = msg_type
        data["content"] = content
    try:
        req = requests.post(url=url, data=json.dumps(data), headers=headers,
                            timeout=60)
        # req_json = req.json()
    except Exception as e:
        logging.error("post send feishu failed:" + str(e))


def set_ph_summary(revision, summary):
    import json
    logging.debug("summary:" + summary)
    update_summary_data = {
        "api.token": API_TOKEN,
        "transactions[0][type]": "summary",
        "transactions[0][value]": summary,
        "objectIdentifier": revision
    }
    response = requests.post(
        'https://cr.test.com/api/differential.revision.edit',
        data=update_summary_data).json()
    if response['error_code']:
        logging.error("set_ph_summary error:" + str(response['error_code']))
        return False
    return True


def remove_ac(revision, reviewers):
    data = {"api.token": API_TOKEN, "objectIdentifier": revision,
            'transactions[reviewers.remove][type]': 'reviewers.remove'}
    for index, username in enumerate(reviewers):
        data[f'transactions[reviewers.remove][value][{index}]'] = username
    data['transactions[reviewers.add][type]'] = 'reviewers.add'
    for index, username in enumerate(reviewers):
        data[f'transactions[reviewers.add][value][{index}]'] = username
    print(data)
    response = requests.post(
        'https://cr.test.com/api/differential.revision.edit',
        data=data).json()
    if response['error_code']:
        logging.error("remove_ac error:" + str(response['error_code']))
        return False
    return True


def add_ac(revision, reviewers):
    data = {"api.token": API_TOKEN, "objectIdentifier": revision,
            'transactions[reviewers.add][type]': 'reviewers.add'}
    for index, username in enumerate(reviewers):
        data[f'transactions[reviewers.add][value][{index}]'] = username
    print(data)
    response = requests.post(
        'https://cr.test.com/api/differential.revision.edit',
        data=data).json()
    if response['error_code']:
        logging.error("add_ac error:" + str(response['error_code']))
        return False
    return True


def rollback_accept(revision, reviewers):
    try:
        remove_ac(revision, reviewers)
        add_ac(revision, reviewers)
    except Exception as e:
        logging.error("rollback_accept error:" + str(e))


def update_jira_link_to_summary(revision, transaction_id):
    result = get_revision(revision)
    title = result['title']
    summary = result['summary']
    jira_pattern = re.compile(
        '^(feat|fix|bugfix|hotfix|docs|style|refactor|perf|test|chore)\('
        '.*\): \[([a-zA-Z][a-zA-Z0-9_]+-[1-9][0-9]*)\] [A-Z]+.*')
    jira_content_pattern = re.compile(
        '功能描述: https://jira.test.com:8443/browse/.*')
    if jira_pattern.search(title):
        # logging.debug(jira_pattern.search(title).group(2))
        jira_id = jira_pattern.search(title).group(2)
        logging.debug("jira id:" + str(jira_id))
    else:
        logging.info(title + " has no jira id")
        return
    jira_context = "功能描述: " + "https://jira.test.com:8443/browse/" + jira_id
    summary_match_jira = jira_content_pattern.search(summary)
    logging.debug(summary_match_jira)
    if not summary_match_jira:
        jira_summary = jira_context + '\n' + summary
        logging.debug(jira_summary)
        try:
            set_ph_summary(revision, jira_summary)
        except Exception as e:
            logging.error("set ph summary with error:" + str(e))
    else:
        logging.debug(title + " 无需更新summay")


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
            # raise Exception("New Exception")
            shufei_send(access_token, email, content)
        except Exception as e:
            logging.error("Feishu shen with error: " + str(e))
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
    logging.info(revision_id)
    logging.info(transaction_id)
    data = dict()
    data['api.token'] = API_TOKEN
    data['objectIdentifier'] = revision_id
    data['limit'] = max(5,len(transaction_id))
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
            user = get_username(i['authorPHID'])
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


def get_user_comments_by_trans(revision_id, transaction_id):
    print("dafa")
    logging.info(revision_id)
    logging.info(transaction_id)
    data = dict()
    data['api.token'] = API_TOKEN
    data['objectIdentifier'] = revision_id
    data['limit'] = 5
    result = requests.post('https://cr.test.com/api/transaction.search',
                           data=data).json()['result']['data']
    comments = dict()
    author = list()
    for res in result:
        if res['phid'] in transaction_id and res['type'] == 'accept':
            author.append(res['authorPHID'])
            comments[res['authorPHID']] = list()
    if not author:
        return False
    for i in result:
        if i['authorPHID'] == 'PHID-APPS-PhabricatorHarbormasterApplication':
            continue
        for j in i['comments']:
            if j['authorPHID'] in author:
                comments[j['authorPHID']].append(j['content']['raw'])
    # print(author)
    # print(comments)
    return author, comments


def get_revision(revision_id):
    data = dict()
    data['api.token'] = API_TOKEN
    data['phids[0]'] = revision_id
    result = \
        requests.post(differential_diff_search, data=data).json()['result'][0]
    return result


def get_diff_result(diff_id):
    """请求增量接口"""
    url = "https://cr.test.com/api/differential.getrawdiff"
    token = 'api.token=xxx&diffID={id}'
    payload = token.format(id=diff_id)
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }
    try:
        response = requests.request("POST", url, headers=headers,
                                    data=payload)
        # print(response.content)
        return json.loads(response.content)['result']
    except Exception as e:
        logging.error("get_diff with error:" + str(e))
        return None


def get_code_snippet_num(content):
    """获取改动文件路径和改动代码行"""
    if not content:
        return 0
    data_dict = dict()
    pattern_1 = re.compile('---\\ (a/)?.*')
    pattern_2 = re.compile('\\+\\+\\+\\s+b/(.*)')
    pattern_3 = re.compile(
        '@@\\ -[0-9]+(,[0-9]+)?\\ \\+([0-9]+)(,[0-9]+)?\\ @@.*')
    pattern_4 = re.compile('^($esc\\[[0-9;]*m)*([\\ +-])')
    logging.debug('start get file line')
    snippet_num = 0
    try:
        file_name = ''
        line = 0
        for code in content.split("\n"):
            if code == '':
                break
            if pattern_1.search(code):
                logging.debug('----find')
                continue
            # 获取文件路径
            elif pattern_2.search(code):
                logging.debug('+++find')
                file_name = pattern_2.search(code).group(1)
                logging.debug(file_name)
                # data_dict[file_name] = list()
            # 获取变动代码行数  @@ -3046,6 +3049,135 @@
            elif pattern_3.search(code):
                line = pattern_3.search(code).group(2)
                line = int(line)
                snippet_num = snippet_num + 1
                logging.debug("代码段个数：" + str(snippet_num))
                logging.debug('line is:' + str(line))
            elif pattern_4.search(code):
                print(code)
                ff = pattern_4.search(code).group(2)
                logging.debug(ff)
                if ff == '+':
                    pass
                if ff != '-':
                    line = line + 1

        # logging.debug(data_dict)
    except Exception as e:
        logging.debug(e)
        return 0
    # print(data_dict)
    logging.debug('end get file line')
    return snippet_num


def read_ignore_user():
    path = os.path.dirname(os.path.abspath(__file__))
    ignore_path = os.path.join(path, 'ignore.txt')
    with open(ignore_path, 'r') as f:
        user_str = f.read()
    users = user_str.split('\n')
    return [u.strip() for u in users]


def handle_ph_request(revision_id, transaction_id):
    res = process_transaction(
        revision_id, transaction_id)
    if isinstance(res, bool):
        return
    accepter_line, tr_author, tr_type, tr_comment_line = res
    result = get_revision(revision_id)
    uri = result['uri']
    logging.debug(uri)
    author = get_username(result['authorPHID'])
    title = result['title']
    summary = result['summary']
    branch = result['branch']
    statusName = result['statusName']
    dateCreated = time.ctime(int(result['dateCreated']))
    reviewers_exclude_groups = list()
    if type(result['reviewers']) is dict:
        for reviewer in result['reviewers'].keys():
            if not reviewer.startswith("PHID-PROJ"):
                reviewers_exclude_groups.append(reviewer)
        reviewers = get_reviewers(reviewers_exclude_groups)
    else:
        reviewers = list()
    if author:
        reviewers.append(author)
    reviewers = list(set(reviewers))
    #ignore_user = read_ignore_user()
    ignore_user = ['robot@test.com']
    for ignore in ignore_user:
        if ignore in reviewers:
            reviewers.remove(ignore)
    try:
        logging.debug("start to send: " + str(reviewers))
        users = we_chat_notify(reviewers, statusName, uri, title, author,
                               branch, summary,
                               dateCreated, accepter_line, tr_author, tr_type,
                               tr_comment_line, ignore_user)
        logging.debug("sent success:" + str(users))
    except Exception as e:
        logging.error("sent " + uri + " with error: " + str(e))


def check_accept_validation(revision_id, transaction_id):
    need_rollback_reviewers = list()
    res = get_user_comments_by_trans(
        revision_id, transaction_id)
    # logging.info(res)
    if isinstance(res, bool):
        return
    author_list, comments = res
    result = get_revision(revision_id)
    diffs = result['diffs']
    snippet_num = get_code_snippet_num(get_diff_result(diffs[0]))
    for author in author_list:
        comments_num = len(comments[author])
        logging.info(result['uri'])
        logging.info("snippet_num:" + str(snippet_num))
        logging.info("comments:" + str(comments[author]))
        logging.info("comments_num:" + str(comments_num))
        if snippet_num > comments_num:
            need_rollback_reviewers.append(author)
    if need_rollback_reviewers:
        logging.info("rollback_accept:" + str(need_rollback_reviewers))
        rollback_accept(revision_id, need_rollback_reviewers)


# 此入口函数只做本地调试单步运行使用
if __name__ == '__main__':
    # main('PHID-DREV-6tc6wkbkanlsrsa7migm', 'PHID-XACT-DREV-3hqaklnl3juri5b')

    # data = {'object': {'type': 'DREV', 'phid':
    # 'PHID-DREV-f23a2mznptay2fwq6ej2'}, 'triggers': [{'phid':
    # 'PHID-HRUL-igzqog5sos2yqiauzavy'}], 'action': {'test': False,
    # 'silent': False, 'secure': False, 'epoch': 1694095516},
    # 'transactions': [{'phid': 'PHID-XACT-DREV-yh7s7js5gxzzhxt'}]}
    #
    # phid = data['object']['phid']
    # tr_ids = list()
    # for i in data['transactions']:
    #     tr_ids.append(i['phid'])
    # t = time.time()
    # users = check_accept_validation(phid, tr_ids)
    # print(users)
    # print(time.time()-t)

    # update_jira_link_to_summary("PHID-DREV-uyq6cxqzcypp4qrcovwr")

    # print(get_code_snippet_num(get_diff_result("1396223")))

    # remove_ac(
    #     'PHID-DREV-uyq6cxqzcypp4qrcovwr',
    #     ["PHID-USER-mtd43yms7s45zbqwjmvj",
    #      "PHID-USER-anxziyfk6n7zb3gvuc53"]
    # )
    # add_ac(
    #     'PHID-DREV-uyq6cxqzcypp4qrcovwr',
    #     ["PHID-USER-mtd43yms7s45zbqwjmvj",
    #      "PHID-USER-anxziyfk6n7zb3gvuc53"]
    # )
    # data = {'object': {'type': 'DREV', 'phid': 'PHID-DREV-mjg7ysuih672sq5sb5db'}, 'triggers': [{'phid': 'PHID-HRUL-igzqog5sos2yqiauzavy'}, {'phid': 'PHID-HRUL-sapzcg27rbjnibo4nuqb'}], 'action': {'test': False, 'silent': False, 'secure': False, 'epoch': 1694227336}, 'transactions': [{'phid': 'PHID-XACT-DREV-e34buzosddapzty'}, {'phid': 'PHID-XACT-DREV-qfsqffwnvc4kbt2'}]}
    get_user_comments_by_trans(
        "PHID-DREV-mjg7ysuih672sq5sb5db",
        ['PHID-XACT-DREV-e34buzosddapzty', 'PHID-XACT-DREV-qfsqffwnvc4kbt2']
    )
    # handle_ph_request(
    #     "PHID-DREV-mjg7ysuih672sq5sb5db",
    #     ['PHID-XACT-DREV-e34buzosddapzty', 'PHID-XACT-DREV-qfsqffwnvc4kbt2']
    # )
