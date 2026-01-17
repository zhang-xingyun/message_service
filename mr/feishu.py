# -*- coding: utf-8 -*-
import json

import requests

from utils.log_utils import log


class FeiShu(object):

    def __init__(self):
        self.APP_ID = ""
        self.APP_SECRET = ""

    def gettoken_feishu(self):
        url = "https://open.feishu.cn/open-apis/auth/v3/" \
              "tenant_access_token/internal/"
        headers = {
            "Content-Type": "application/json"
        }
        req_body = {
            "app_id": self.APP_ID,
            "app_secret": self.APP_SECRET
        }
        req = requests.post(url=url, data=json.dumps(req_body),
                            headers=headers, timeout=60)
        req_json = req.json()
        return req_json['tenant_access_token']

    def feishu_notify(self, user_list, message: str):
        access_token = self.gettoken_feishu()
        for email in user_list:
            try:
                self.send_markdown(access_token, email, message)
            except Exception as err:
                log(err)

    def send_markdown(self, access_token, email, text):
        email += '@test.com'
        """发送富文本消息"""
        url = "https://open.feishu.cn/open-apis/message/v4/send/"
        headers = {"Content-Type": "text/plain",
                   "Authorization": ' '.join(['Bearer', access_token])}
        data = {
            "msg_type": "interactive",
            "email": email,
            "card": {
                "config": {
                    "wide_screen_mode": True
                },
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": "【GitLab】"
                    },
                    "template": "red"
                },
                "elements": [
                    {"tag": "div",
                     "text": {
                         "content": text,
                         "tag": "lark_md"
                     }}
                ]}
        }
        r = requests.post(url, headers=headers, json=data)
        print(r.text)
