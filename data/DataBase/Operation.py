"""
包含查询数据库的操作
"""
import sqlite3
from data.DataBase.Ontology import *

class DBOperationWrapper:
    def __init__(self, db):
        self.db = db
        self.conn = sqlite3.connect(self.db)
        self.cur = self.conn.cursor()

    def SearchingByConstraints(self, table, feed_dict):
        """
        informable slots 查找
        数字描述的一般是tuple, 表示大于等于多少且小于等于多少
        文字描述的slots 统一 按“高”“中”“低”搜索
        :param table: 领域表名
        :param feed_dict: 搜索条件
        :return: 搜索结果
        """
        if table == "国际港澳台":
            command = """
                SELECT * FROM 国际港澳台
                WHERE  
                """
            constraints = []
            if "开通天数" in feed_dict:
                constraints.append("开通天数 == %d" % feed_dict["开通天数"])
            for slot in ["开通国家", "开通地区"]:
                if slot in feed_dict:
                    constraints.append("{0} LIKE \'%{1}%\'".format(slot,feed_dict[slot]))
            command += " AND ".join(constraints)
            return self.cur.execute(command)
        elif table == "套餐":
            command = """
                            SELECT * FROM 套餐
                            WHERE  
                            """
            constraints = []
            for slot in ["功能费", "套餐内容_国内流量", "套餐内容_国内主叫"]:
                if slot in feed_dict:
                    constraints.append("%s >= %f AND %s <= %f" % (slot, feed_dict[slot][0], slot, feed_dict[slot][1]))
            if "功能费_文字描述" in feed_dict:
                if feed_dict["功能费_文字描述"] == "高":
                    constraints.append("功能费 >= 300.0 ")
                elif feed_dict["功能费_文字描述"] == "中":
                    constraints.append("功能费 >= 100.0 AND 功能费 < 300.0")
                else:
                    constraints.append("功能费 < 100.0")
            if "套餐内容_国内流量_文字描述" in feed_dict:
                if feed_dict["套餐内容_国内流量_文字描述"] == "高":
                    constraints.append("套餐内容_国内流量 >= 1500.0 ")
                elif feed_dict["套餐内容_国内流量_文字描述"] == "中":
                    constraints.append("套餐内容_国内流量 >= 400.0 AND 套餐内容_国内流量 < 1500.0")
                else:
                    constraints.append("套餐内容_国内流量 <= 400.0")

            if "套餐内容_国内主叫_文字描述" in feed_dict:
                if feed_dict["套餐内容_国内主叫_文字描述"] == "高":
                    constraints.append("套餐内容_国内主叫 >= 1500.0 ")
                elif feed_dict["套餐内容_国内主叫_文字描述"] == "中":
                    constraints.append("套餐内容_国内主叫 >= 400.0 AND 套餐内容_国内主叫 < 1500.0")
                else:
                    constraints.append("套餐内容_国内主叫 <= 400.0")

            command += " AND ".join(constraints)
            return self.cur.execute(command)
        elif table == "流量":
            command = """
                            SELECT * FROM 流量
                            WHERE  
                            """
            constraints = []
            for slot in ["功能费", "套餐内容_国内流量"]:
                if slot in feed_dict:
                    constraints.append("%s >= %f AND %s <= %f" % (slot, feed_dict[slot][0], slot, feed_dict[slot][1]))
            if "功能费_文字描述" in feed_dict:
                if feed_dict["功能费_文字描述"] == "高":
                    constraints.append("功能费 >= 300.0 ")
                elif feed_dict["功能费_文字描述"] == "中":
                    constraints.append("功能费 >= 100.0 AND 功能费 < 300.0")
                else:
                    constraints.append("功能费 < 100.0")
            if "套餐内容_国内流量_文字描述" in feed_dict:
                if feed_dict["套餐内容_国内流量_文字描述"] == "高":
                    constraints.append("套餐内容_国内流量 >= 1500.0 ")
                elif feed_dict["套餐内容_国内流量_文字描述"] == "中":
                    constraints.append("套餐内容_国内流量 >= 400.0 AND 套餐内容_国内流量 < 1500.0")
                else:
                    constraints.append("套餐内容_国内流量 <= 400.0")

            command += " AND ".join(constraints)
            return self.cur.execute(command)
        else:
            return None

    def SearchingByEntity(self, table, feed_dict):
        if table == "Card":
            command = """
                    SELECT * FROM %s
                    WHERE  
                    """%(table)
            constraints = []
            for slot in ["号卡"]:
                if slot in feed_dict:
                    constraints.append("{0} LIKE \'%{1}%\'".format(slot, feed_dict[slot]))
            command += " AND ".join(constraints)
            return self.cur.execute(command)
        else:
            command = """
            SELECT * FROM %s
            WHERE
            """%(table)
            constraints = []
            for slot in ["子业务", "主业务"]:
                if slot in feed_dict:
                    constraints.append("{0} LIKE \'%{1}%\'".format(slot, feed_dict[slot]))
            command += " AND ".join(constraints)
            return self.cur.execute(command)

    def close(self):
        self.conn.close()


if __name__ == '__main__':
    operation = DBOperationWrapper('../tmp/CMCC_NewDB.db')
    for ii in operation.SearchingByConstraints("流量", {"套餐内容_国内流量_文字描述": "高"}):
        print(dict(zip(LiuLiang_DB_slots, ii)))
