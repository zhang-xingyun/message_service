from django.apps import apps
from django.db import connection
from django.views import View
from concurrent.futures import ThreadPoolExecutor
import json
import time
import logging
from django.http import HttpResponse, JsonResponse
from ph_app.handle_ph import handle_ph_request, check_accept_validation, \
    update_jira_link_to_summary, gettoken_feishu, shufei_send

executor = ThreadPoolExecutor(4)


def handle_received_data(request, execute_function):
    try:
        data = json.loads(request.body)
        logging.debug(data)
    except Exception as err:
        logging.error("Get request date with error: " + str(err))
        data = None
    # Only for test data: 模拟PH webhook数据，接收者：robot,cr-test.test.com测试环境输入
    # data = {
    #     'object': {'type': 'DREV', 'phid': 'PHID-DREV-4ng6ggffj5xvxiqepmsz'},
    #     'triggers': [{'phid': 'PHID-HRUL-igzqog5sos2yqiauzavy'}],
    #     'action': {'test': False, 'silent': False, 'secure': False,
    #                'epoch': 1694444723},
    #     'transactions': [{'phid': 'PHID-XACT-DREV-ay25psxbx3jokmu'},
    #                      {'phid': 'PHID-XACT-DREV-soluxrds5otzg3z'}]}
    try:
        if data:
            phid = data['object']['phid']
            tr_ids = list()
            for i in data['transactions']:
                tr_ids.append(i['phid'])
            try:
                executor.submit(execute_function, phid, tr_ids)
                # execute_function(phid, tr_ids)
            except Exception as err:
                logging.error("handle request with error: " + str(err))
    except Exception as err:
        logging.error("Parse data with error: " + str(err))
    result = {
        "code": 0,
        "msg": "Success"
    }
    return JsonResponse(result)


def ph_message(request):
    if request.method == 'POST' or request.method == 'GET':
        handle_received_data(request, handle_ph_request)
        return JsonResponse({"msg": "Success"})


def ph_accept_check(request):
    if request.method == 'POST' or request.method == 'GET':
        handle_received_data(request, check_accept_validation)
        return JsonResponse({"msg": "Success"})


def add_jira_into_summary(request):
    if request.method == 'POST' or request.method == 'GET':
        handle_received_data(request, update_jira_link_to_summary)
        return JsonResponse({"msg": "Success"})


def feishu(request):
    if request.method == 'POST' or request.method == 'GET':
        try:
            data = json.loads(request.body)
            logging.debug(data)
        except Exception as err:
            logging.error("Get request date with error: " + str(err))
            data = None
        # data = {
        #     'user': 'robot,robot',
        #     'msg_type': 'text',
        #     'content': {'text': '构建成功'}
        # }
        users = data.get('user', '')
        if isinstance(users, str):
            users = users.split(',')
        if len(users) == 0:
            return
        content = data.get('content', '')

        access_token= gettoken_feishu()

        msg_type = data.get('msg_type', '')
        for user in users:
            if '@test.com' not in user:
                user = f"{user}@test.com"
            try:
                shufei_send(access_token, user, content, msg_type)
            except Exception as e:
                logging.error("send feishu with error:" + str(e))
        return JsonResponse({"msg": "Success"})
