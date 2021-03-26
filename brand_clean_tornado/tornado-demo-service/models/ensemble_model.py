# -*- coding: utf-8 -*-
from models.model1 import Model1
from models.model2 import Model2
from inc_brand_reg import IncBrandReg
import tool
import bc_config
from mssql_opt import MsSqlOpt
from liwei_brand_clean import LiweiBrandClean
import logging
from logging.handlers import TimedRotatingFileHandler
import traceback
import datetime
import os
from pyhive import hive


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

errNo2Info_Dict = {
    0: {"status": 0, "info": 'successful'},
    -1: {"status": -1, "info": 'getting data from hive error!'},
    -100: {"status": -1, "info": 'getting data from hive error!'},
    -200: {"status": -1, "info": 'dp_brands_result.txt.brandreg is not exist!'},
    -300: {"status": -1, "info": 'inc_data/inc_data.txt is not exist!'},
    -400: {"status": -1, "info": 'inc-brand-dealing error!'}
}

class Ensemble_Model(object):

    def __init__(self):

        self.model1 = Model1()
        self.model2 = Model2()

    def cate_clean(self,cate_name,bc_date,mssql_opt):
        # checking
        if cate_name not in bc_config.cateName2Dir_Dict or \
                cate_name not in bc_config.cateName2WhereCondition_Dict:
            return {"status": -1, "info": 'unkown cate_name: %s' % cate_name}
        # dir-path checking
        inc_data_folder = bc_config.cateName2Dir_Dict[cate_name]
        if not os.path.exists(inc_data_folder):
            return {"status": -1, "info": '%s does not exist!' % inc_data_folder}
        try:
            mssql_opt = MsSqlOpt(cate_name, bc_date, log_instance)
        except Exception as e:
            log_instance.error(traceback.format_exc())
            return {"status": -1, "info": 'mssql connecting error!'}

        try:
            log_instance.info("working-start: %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            # stp1 del related-data
            log_instance.info("stp1: del related-data! %s" % \
                              datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            mssql_opt._del_related_data()

            # stp2 update db-status
            log_instance.info("stp2: setting working starting flag! %s" % \
                              datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            mssql_opt.insert_starting_flag()

            log_instance.info(
                "stp3: getting data from hive! %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            # getting data from hive
            r_no = self._getting_data_from_hive(cate_name,bc_date)
            if r_no != 0:
                return errNo2Info_Dict[r_no]

            # inc-brand-clean
            log_instance.info("stp4: brand inc dealing! %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            if cate_name in bc_config.liWeiBCCateName_Dict:
                log_instance.info("liwei_brand_clean!!")
                r_no = self._liwei_brand_clean(cate_name,bc_date,mssql_opt)
            else:
                r_no = self._inc_brand_clean(cate_name,bc_date)
            if r_no != 0:
                return errNo2Info_Dict[r_no]
            # saving data to db
            log_instance.info(
                "stp5: adding inc-data to mssql! %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            r_no = mssql_opt.add_inc_brand_data()

            log_instance.info("finish! %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            return errNo2Info_Dict[r_no]
        except Exception as e:
            log_instance.info("working failture! %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            log_instance.error(traceback.format_exc())
            mssql_opt.insert_failture_flag()
            return {"status": -1, "info": traceback.format_exc()}

    def _getting_data_from_hive(self,cate_name,bc_date):
        log_instance.info("hive-1")
        # getting data from hive
        s1 = "select distinct shop_id, t.shop_name from tmp.tmp_offline_dianping_shop_all_category t %s" % \
             bc_config.cateName2WhereCondition_Dict[cate_name]
        inc_data_file = bc_config.cateName2Dir_Dict[cate_name] + "/inc_data/inc_data.txt"
        conn = None
        cur = None
        try:
            conn = hive.connect(host='172.20.207.6', port=10000, username='supdev')
            # conn = connect(host='172.20.207.6', port=10000, auth_mechanism="PLAIN")
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

    def _inc_brand_clean(self,cate_name,bc_date):
        # dict-file
        log_instance.info("bc-1")
        try:
            incObj = IncBrandReg(bc_config.cateName2Dir_Dict[cate_name], log_instance, bc_date)
            log_instance.info("bc-2")
            incObj.inc_data_brand_reg()
            incObj.inc_data_stat()
        except:
            return -400
        log_instance.info("bc-3")
        return 0

    def _liwei_brand_clean(self,cate_name,bc_date,mssql_opt):
        try:
            legal_brand_dict = mssql_opt.getting_legal_brand()
            liwei_obj = LiweiBrandClean(legal_brand_dict,
                                        bc_config.cateName2Dir_Dict[cate_name],
                                        log_instance, bc_date)
            liwei_obj.inc_data_brand_reg()
            liwei_obj.inc_data_stat()
            return 0
        except Exception as e:
            raise e

    def analysis(self, content):

        # 依赖 model1、model2 输出
        model1_output = self.model1.inference(content)
        model2_output = self.model2.inference(content)

        final_output = self.inference(model1_output, model2_output)

        return final_output

    def inference(self, x1, x2):

        y = x1 + x2 + '<FINAL_INFERENCE>'

        return y