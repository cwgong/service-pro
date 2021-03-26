import pymysql
import traceback

class Mysql_Con():
    def __init__(self):
        pass

    def get_info_by_uid(self,uid,password):
        try:
            db = pymysql.connect(host='121.36.100.3', \
                                 port=3306, user='gongchengwei', \
                                 passwd='qwe1372864243', db='mysql', \
                                 charset='utf8')

            cursor = db.cursor()
            sql_str = 'select user,host from mysql.user where user = "%s"' % (uid)
            cursor.execute(sql_str)

            data = cursor.fetchall()
            cursor.close()
            db.close()
            return data
        except:
            print(traceback.format_exc())