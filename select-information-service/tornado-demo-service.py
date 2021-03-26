# -*- coding: utf-8 -*-
# 自定义版本
from _version import __version__
import sys
# python
import io
import json
# tornado
import logging
import tornado.escape
import tornado.ioloop
import tornado.web
import tornado.httpserver
import tornado.options
from tornado.escape import json_decode
import datetime

# business logical
from models.ensemble_model import Ensemble_Model
import traceback

# version
VERSION = "0.1"

# config
def parse_conf_file(config_file):
    
    config = {}
    with io.open(config_file, 'r', encoding='utf8') as f:
        config = json.load(f)
    return config


class Handler1(tornado.web.RequestHandler):

    def post(self):

        try:
            begin = datetime.datetime.now()

            post_data = json_decode(self.request.body)

            # service 获取参数
            uid = post_data['uid']
            password = post_data['password']
            logging.info('title: {}'.format(uid))
            logging.info('content: {}'.format(password))

            # 模型调用
            result = self.application.model.analysis(uid,password)
            logging.info('result: {}'.format(result))

            # result（模型输出） 可以是任何结构，如 String、List、Dict
            Restful_Result = {"data": result,
                              "message": {"code": 0,
                                          "message": "success"}}

            # service 返回 json 结果
            self.write(json.dumps(Restful_Result, ensure_ascii=False))

            end = datetime.datetime.now()
            logging.info("post success! " + "  end - begin = " + str(end - begin))

        except Exception as e:
            logging.error(traceback.format_exc())
            Restful_Result = {"data": [],
                              "message": {"code": -1,
                                          "message": str(e)}}
            self.write(json.dumps(Restful_Result, ensure_ascii=False))


    def get(self):

        try:
            begin = datetime.datetime.now()

            post_data = json_decode(self.request.body)

            # service 获取参数
            uid = post_data['uid']
            password = post_data['password']
            logging.info('title: {}'.format(uid))
            logging.info('content: {}'.format(password))

            # 模型调用
            result = self.application.model.analysis(uid, password)
            logging.info('result: {}'.format(result))

            # result（模型输出） 可以是任何结构，如 String、List、Dict
            Restful_Result = {"data": result,
                              "message": {"code": 0,
                                          "message": "success"}}

            # service 返回 json 结果
            self.write(json.dumps(Restful_Result, ensure_ascii=False))

            end = datetime.datetime.now()
            logging.info("post success! " + "  end - begin = " + str(end - begin))

        except Exception as e:
            logging.error(traceback.format_exc())
            Restful_Result = {"data": [],
                              "message": {"code": -1,
                                          "message": str(e)}}
            self.write(json.dumps(Restful_Result, ensure_ascii=False))


class Application(tornado.web.Application):
    
    def __init__(self, config, model):

        self.model = model

        # 此部分可以进行多个 url 与 Handler 配置
        handlers = [
            (config['url_1'], Handler1),
        ]
        settings = dict(
            debug = bool(config['debug']),
        )
        tornado.web.Application.__init__(self, handlers, **settings)


def main(argv):
    
    if sys.version_info < (3,):
        reload(sys)
        sys.setdefaultencoding("utf-8")

    # 服务版本号验证
    if VERSION != __version__:
        print("version error!")
        logging.info("version error!")
        exit(-1)

    # 服务启动参数验证
    if len(argv) < 2:
        print('arg error!')
        logging.info("arg error!")
        exit(-2)  

    # 加载 config
    config = parse_conf_file(argv[1])
    tornado.options.parse_config_file(config['log_config_file'])

    # initial model
    model = Ensemble_Model()

    # tornado Application 加载 Model
    app = Application(config, model)

    server = tornado.httpserver.HTTPServer(app)
    # 配置服务端口号
    server.bind(config['port'])
    # 配置服务启动进程数量
    server.start(config['process_num'])

    logging.info("Server Inititial Success! ")
    print("Server Inititial Success! ")

    tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
    
    main(sys.argv)
