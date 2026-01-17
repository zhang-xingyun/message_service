# -*- coding:utf8 -*-
"""
Created on 2022/1/26 17:18
@author: robot
"""

from django.urls import re_path
from . import views

app_name = 'ph_app'
urlpatterns = [
    re_path(r'^ph_message/$', views.ph_message, name='ph_message'),
    re_path(r'^ph_accept_check/$', views.ph_accept_check, name='ph_accept_check'),
    re_path(r'^add_jira_into_summary/$', views.add_jira_into_summary, name='add_jira_into_summary'),
    re_path(r'^feishu$', views.feishu, name='feishu'),

]
