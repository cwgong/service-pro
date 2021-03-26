# -*- coding: utf-8 -*-
from models.model1 import Model1
from models.model2 import Model2
from models.mysqlobj import Mysql_Con
import logging


class Ensemble_Model(object):

    def __init__(self):

        self.model1 = Model1()
        self.model2 = Model2()
        self.database_obj = Mysql_Con()
    def analysis_v1(self, uid, password):

        # 依赖 model1、model2 输出
        model1_output = self.model1.inference(uid,password)
        model2_output = self.model2.inference(uid,password)

        final_output = self.inference(model1_output, model2_output)

        return final_output

    def analysis(self, uid, password):
        '''
        updata in 2020.11.13 by gcw.
        :param uid:
        :param password:
        :return:
        '''
        # 依赖 Mysql_Con 输出
        user_info = self.database_obj.get_info_by_uid(uid,password)

        return user_info

    def inference(self, x1, x2):

        y = x1 + x2 + '<FINAL_INFERENCE>'

        return y