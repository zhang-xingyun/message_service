# -*- coding: utf-8 -*-
import json
import logging
import time

import requests

token_info = {
    'token': None,
    'timestamp': 0,
    'expire':3600
}


class FeiShu(object):

    def __init__(self):
        self.APP_ID = "xxx"
        self.APP_SECRET = "xxx"

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
        token_info['expire'] = req_json['expire']
        return req_json['tenant_access_token']

    def feishu_notify(self, user_list, message: str):
        current_time = time.time()
        # 判断当前时间与上次获取token的时间戳之差是否大于一个小时
        if current_time - token_info['timestamp'] + 10 > token_info['expire']:
            # 如果大于一个小时，则重新获取token
            token_info['token'] = self.gettoken_feishu()
            # 更新时间戳
            token_info['timestamp'] = current_time
        for email in user_list:
            try:
                logging.info("send to:" + email)
                self.send_markdown(token_info['token'], email, message)
            except Exception as err:
                logging.error("send feishu with errir:" + str(err))

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
        logging.debug(email + r.text)
