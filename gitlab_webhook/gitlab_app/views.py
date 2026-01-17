from django.apps import apps
from django.db import connection
from django.views import View
import json
import logging
from django.http import HttpResponse, JsonResponse
from gitlab_app.gitlab_mr import MR


def push_message(request):
    if request.method == 'POST' or request.method == 'GET':
        try:
            # Only for test: 读取git_push.json模拟接收的请求数据，接收者：robot
            # with open(file="gitlab_app/git_push.json", mode='r',
            #           encoding='utf-8') as f:
            #     data = f.read()
            # message = json.loads(data)
            message = json.loads(request.body)
            logging.debug(message)
        except Exception as err:
            logging.error("get request data with error:" + str(err))
            message = None
        try:
            if message:
                mr = MR()
                mr.parse_webhook(message)
        except Exception as err:
            logging.error("parse_webhook with error: " + str(err))
        result = {
            "code": 0,
            "msg": "Success"
        }
        return JsonResponse(result)
    return JsonResponse({"msg": "Success"})
