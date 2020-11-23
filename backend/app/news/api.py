import os
import time
import json
import requests
import datetime
import traceback
import configparser
from threading import Thread
from flask_cors import cross_origin
from flask import render_template, session, redirect, url_for, current_app, flash, request, jsonify

from ..limiter import limiter
from ..common_func import CommonFunc
from ..login.login_funtion import User
from ..response import Response as MyResponse
from ..privilege.privilege_control import privilegeFunction
from ..privilege.privilege_control import permission_required
from .get_news import parse_baidu, parse_zhihu_hot, parse_weibo, parse_v2ex, parse_36kr, parse_chouti, parse_jandan, parse_zhihu_daily, parse_hacpai, parse_douban, parse_guokr, parse_huxiu, parse_cnbeta, parse_zaobao, parse_weixin, parse_thepaper, parse_nytimes, parse_solidot, parse_bilibili, parse_sinatech, parse_hostloc, parse_smzdm_article, parse_zhihu_good

from . import news

rsp = MyResponse()
cf = configparser.ConfigParser()
cf.read('app/homepage.config')
NEWS_JSON_PATH = cf.get('config', 'BASE_PATH') + 'backend/app/news/json'
DOMAIN_NAME = cf.get('config', 'DOMAIN_NAME')
LIMITER_FREQUENCY_NEWS_GET = '10/minute'  # 接口限制的新闻获取访问频次
LIMITER_FREQUENCY_NEWS_FLUSH = '10/hour'  # 接口限制的新闻刷新访问频次


class MyThread(Thread):

    def __init__(self, target, args=()):
        super(MyThread, self).__init__()
        self.target = target
        self.args = args

    def run(self):
        self.result = self.target(*self.args)


news_dict = {
    '36kr': [MyThread(target=parse_36kr)],
    'v2ex': [MyThread(target=parse_v2ex)],
    'huxiu': [MyThread(target=parse_huxiu)],
    'guokr': [MyThread(target=parse_guokr)],
    'weibo': [MyThread(target=parse_weibo)],
    'weixin': [MyThread(target=parse_weixin)],
    'zaobao': [MyThread(target=parse_zaobao)],
    'cnbeta': [MyThread(target=parse_cnbeta)],
    'douban': [MyThread(target=parse_douban)],
    'jandan': [MyThread(target=parse_jandan)],
    'chouti': [MyThread(target=parse_chouti)],
    'hostloc': [MyThread(target=parse_hostloc)],
    'solidot': [MyThread(target=parse_solidot)],
    'nytimes': [MyThread(target=parse_nytimes)],
    'bilibili': [MyThread(target=parse_bilibili)],
    'sinatech': [MyThread(target=parse_sinatech)],
    'thepaper': [MyThread(target=parse_thepaper)],
    'zhihu_daily': [MyThread(target=parse_zhihu_daily)],
    'zhihu_hot': [MyThread(target=parse_zhihu_hot), MyThread(target=parse_zhihu_good)],
    'hacpai': [MyThread(target=parse_hacpai, args=("play", )), MyThread(target=parse_hacpai, args=("hot", ))],
    'baidu': [MyThread(target=parse_baidu, args=("now", )), MyThread(target=parse_baidu, args=("today", )),
              MyThread(target=parse_baidu, args=("week", ))],
    'smzdm_article': [MyThread(target=parse_smzdm_article, args=("today", )),
                      MyThread(target=parse_smzdm_article, args=("week", )),
                      MyThread(target=parse_smzdm_article, args=("month", ))]
}


@news.route('/get', methods=['POST'])
@limiter.limit(LIMITER_FREQUENCY_NEWS_GET)
def get():
    try:
        if not request.referrer.startswith(DOMAIN_NAME):
            return rsp.refuse(), 403
        csrf_token_send = request.get_json()['token']
        csrf_token = request.cookies.get('csrf_token')
        if csrf_token != csrf_token_send:
            return rsp.refuse(), 403

        temp = {}
        r = []
        files = os.listdir(NEWS_JSON_PATH)
        for file in files:
            file_path = os.path.join(NEWS_JSON_PATH, file)
            temp[file] = json.load(open(file_path))
        r.append({'title': '百度', 'data': [temp.pop('baidu_now.json'), temp.pop('baidu_today.json'), temp.pop('baidu_week.json')]})
        r.append({'title': '什么值得买', 'data': [temp.pop('smzdm_article_today.json'), temp.pop('smzdm_article_week.json'), temp.pop('smzdm_article_month.json')]})
        r.append({'title': '知乎', 'data': [temp.pop('zhihu_daily.json'), temp.pop('zhihu_good.json'), temp.pop('zhihu_hot.json')]})
        r.append({'title': '微信', 'data': [temp.pop('weixin.json'), temp.pop('weixin_hot.json')]})
        r.append({'title': '36Kr', 'data': [temp.pop('36kr_hot.json'), temp.pop('36kr_article.json')]})
        r.append({'title': '黑客派', 'data': [temp.pop('hacpai_hot.json'), temp.pop('hacpai_play.json')]})

        for key in temp:
            r.append({'title': temp[key]['title'], 'data': [temp[key]]})

        return rsp.success(r)
    except Exception as e:
        traceback.print_exc()
        return rsp.failed(e), 500


@news.route('/flush', methods=['POST'])
@limiter.limit(LIMITER_FREQUENCY_NEWS_FLUSH)
def flush():
    try:
        if not request.referrer.startswith(DOMAIN_NAME):
            return rsp.refuse(), 403
        csrf_token_send = request.get_json()['token']
        csrf_token = request.cookies.get('csrf_token')
        if csrf_token != csrf_token_send:
            return rsp.refuse(), 403

        target = request.get_json()['target']
        result = []
        for t in news_dict[target]:
            t.start()
        for t in news_dict[target]:
            t.join()
        for t in news_dict[target]:
            result.append(t.result)
        return rsp.success(result)
    except Exception as e:
        traceback.print_exc()
        return rsp.failed(e), 500
