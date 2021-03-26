#!/usr/bin/env python3
#coding=utf-8

import sys
import os
import datetime
from flask import Flask
from flask_restful import Api, Resource, reqparse
import traceback
import logging
import logging.config
from logging.handlers import TimedRotatingFileHandler
from pyhive import hive
#from impala.dbapi import connect

from inc_brand_reg import IncBrandReg
import tool
import bc_config
from mssql_opt import MsSqlOpt
from liwei_brand_clean import LiweiBrandClean

logging.basicConfig(level=logging.INFO,
    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
    datefmt='%a, %d %b %Y %H:%M:%S',
    filemode='a'
)

log_instance = logging.getLogger("brand_clean_logger")
log_file_name = 'log/brand_clean_log'
fileTimeHandler = TimedRotatingFileHandler(log_file_name, \
                                           when="D", \
                                           interval=1, \
                                           backupCount=10)
fileTimeHandler.suffix = "%Y-%m-%d.log"
formatter = logging.Formatter('%(name)-12s %(asctime)s level-%(levelname)-8s thread-%(thread)-8d %(message)s')
fileTimeHandler.setFormatter(formatter)
log_instance.addHandler(fileTimeHandler)

app = Flask(__name__)
api = Api(app)

errNo2Info_Dict = {
    0: {"status": 0, "info": 'successful'},
    -1: {"status": -1, "info": 'getting data from hive error!'},
    -100: {"status": -1, "info": 'getting data from hive error!'},
    -200: {"status": -1, "info": 'dp_brands_result.txt.brandreg is not exist!'},
    -300: {"status": -1, "info": 'inc_data/inc_data.txt is not exist!'},
    -400: {"status": -1, "info": 'inc-brand-dealing error!'}
}

class BrandClean(Resource):
    def __init__(self):
        parser = reqparse.RequestParser()
        parser.add_argument('cate_name')
        parser.add_argument('bc_date', type=str)

        args = parser.parse_args()
        self.cate_name = args["cate_name"].strip()
        self.bc_date = args["bc_date"].strip()
        self.mssql_opt = None

        log_instance.info("cate-name: %s bc_date: %s" % (self.cate_name, self.bc_date))
        pass

    def get(self):
        if self.cate_name == "":
            return {"status": -1, "info": 'cate_name is empty'}

        if self.cate_name in bc_config.cateName2Dir_Dict and self.cate_name in bc_config.cateName2WhereCondition_Dict:
            self.cate_clean()
            return {"status": 0, "info": "successful"}
        elif self.cate_name == "all":
            #for c_name, _ in {"yaodian": "", "xidihuli": ""} #bc_config.cateName2Dir_Dict.items():
            for c_name, _ in bc_config.cateName2Dir_Dict.items():
                self.cate_name = c_name.strip()
                self.cate_clean()
            return {"status": 0, "info": "successful"}
        else:
            return {"status": -1, "info": 'unkown cate_name: %s' % self.cate_name}


    def cate_clean(self):
        # checking
        if self.cate_name not in bc_config.cateName2Dir_Dict or \
                self.cate_name not in bc_config.cateName2WhereCondition_Dict:
            return {"status": -1, "info": 'unkown cate_name: %s' % self.cate_name}
        # dir-path checking
        inc_data_folder = bc_config.cateName2Dir_Dict[self.cate_name]
        if not os.path.exists(inc_data_folder):
            return {"status": -1, "info": '%s does not exist!' % inc_data_folder}
        try:
            self.mssql_opt = MsSqlOpt(self.cate_name, self.bc_date, log_instance)
        except Exception as e:
            log_instance.error(traceback.format_exc())
            return {"status": -1, "info": 'mssql connecting error!'}

        try:
            log_instance.info("working-start: %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            # stp1 del related-data
            log_instance.info("stp1: del related-data! %s" % \
                              datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            self.mssql_opt._del_related_data()

            # stp2 update db-status
            log_instance.info("stp2: setting working starting flag! %s" % \
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            self.mssql_opt.insert_starting_flag()

            log_instance.info("stp3: getting data from hive! %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            # getting data from hive
            r_no = self._getting_data_from_hive()
            if r_no != 0:
                return errNo2Info_Dict[r_no]

            # inc-brand-clean
            log_instance.info("stp4: brand inc dealing! %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            if self.cate_name in bc_config.liWeiBCCateName_Dict:
                log_instance.info("liwei_brand_clean!!")
                r_no = self._liwei_brand_clean()
            else:
                r_no = self._inc_brand_clean()
            if r_no != 0:
                return errNo2Info_Dict[r_no]
            # saving data to db
            log_instance.info("stp5: adding inc-data to mssql! %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            r_no = self.mssql_opt.add_inc_brand_data()

            log_instance.info("finish! %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            return errNo2Info_Dict[r_no]
        except Exception as e:
            log_instance.info("working failture! %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            log_instance.error(traceback.format_exc())
            self.mssql_opt.insert_failture_flag()
            return {"status": -1, "info": traceback.format_exc()}

    def post(self):
        return {"status": 0, "info": 'ok'}

    def _getting_data_from_hive(self):
        log_instance.info("hive-1")
        # getting data from hive
        s1 = "select distinct shop_id, t.shop_name from tmp.tmp_offline_dianping_shop_all_category t %s" % \
             bc_config.cateName2WhereCondition_Dict[self.cate_name]
        inc_data_file = bc_config.cateName2Dir_Dict[self.cate_name] + "/inc_data/inc_data.txt"
        conn = None
        cur = None
        try:
            conn = hive.connect(host='172.20.207.6', port=10000, username='supdev')
            #conn = connect(host='172.20.207.6', port=10000, auth_mechanism="PLAIN")
            cur = conn.cursor()
            log_instance.info("hive-2")
            log_instance.info("hive-sql: %s" % s1)
            cur.execute(s1)
            
            lst1 = []
            while True:
                data = cur.fetchmany(size=50000)
                if len(data) == 0:
                    break
                for d in data:
                    lst1.append("%s\t%s" % (d[0], d[1].replace("\t", " ")))
                log_instance.info("hive-data: %s" % len(lst1))
            '''
            lst1 = []
            results = cur.fetchall()
            log_instance.info("hive-3")
            for d in results:
                lst1.append("%s\t%s" % (d[0], d[1].replace("\t", " ")))
                if len(lst1) % 10000 == 0: 
                    log_instance.info("hive-data: %s" % len(lst1))
            '''
            with open(inc_data_file, "w") as f1:
                f1.write("\n".join(lst1))
                f1.flush()
            log_instance.info("hive-4")
        except Exception as e:
            log_instance.error(traceback.format_exc())
            raise e
        finally:
            if cur != None: cur.close()
            if conn != None: conn.close()

        return 0

    def _inc_brand_clean(self):
        # dict-file
        log_instance.info("bc-1")
        try:
            incObj = IncBrandReg(bc_config.cateName2Dir_Dict[self.cate_name], log_instance, self.bc_date)
            log_instance.info("bc-2")
            incObj.inc_data_brand_reg()
            incObj.inc_data_stat()
        except:
            return -400
        log_instance.info("bc-3")
        return 0

    def _liwei_brand_clean(self):
        try:
            legal_brand_dict = self.mssql_opt.getting_legal_brand()
            liwei_obj = LiweiBrandClean(legal_brand_dict, \
                                        bc_config.cateName2Dir_Dict[self.cate_name], \
                                        log_instance, self.bc_date)
            liwei_obj.inc_data_brand_reg()
            liwei_obj.inc_data_stat()
            return 0
        except Exception as e:
            raise e
api.add_resource(BrandClean, '/api/brand_clean')

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True, port=8000)
