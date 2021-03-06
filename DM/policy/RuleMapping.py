"""
基于规则的policy
"""
import os
import sys
import random
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, '../..'))

from data.DataBase.Ontology import *
from data.DataManager import DataManager
import copy

DialogStateSample = {
    'TurnNum':int,
    # 用户主动提及业务实体集合
    'EntityMentioned': {'curr_turn': [],
                        'prev_turn': []},
    'UserPersonal': {
            "已购业务": ["180元档幸福流量年包", "18元4G飞享套餐升级版"], # 这里应该是完整的业务的信息dict
            "套餐使用情况": "剩余流量 11.10 GB，剩余通话 0 分钟，话费余额 110.20 元，本月已产生话费 247.29 元",
            "号码": "18811369685",
            "归属地" : "北京",
            "品牌": "动感地带",
            "是否转品牌过渡期": "否",
            "话费查询": "话费余额 110.20 元",
            "流量查询": "剩余流量 11.10 GB",
            "订购时间": "订购时间 2017-04-04， 生效时间 2017-05-01",
            "是否停机": "否",
            "话费充值": "请登录网上营业厅、微厅或 APP 充值",
            "流量充值": "请登录网上营业厅、微厅或 APP 充值",
            "账单查询": "请登录网上营业厅、微厅或 APP 查询"
        }, # 个人信息，dict
    'QueryResults': [], # 查询数据库得到的list of 业务信息dict
    # 一轮就提供一个套餐
    'OfferedResult': {'prev_turn':{'子业务': '188元畅享套餐', '主业务': None, '功能费': 188, '套餐内容_国内主叫': 700, '套餐内容_国内流量': 12288},
                    'preprev_turn': {'子业务': '188元畅享套餐', '主业务': None, '功能费': 188, '套餐内容_国内主叫': 700, '套餐内容_国内流量': 12288}},
    'SystemAct': {'curr_turn': {'offer': {'子业务': '158元畅享套餐', '主业务': None, '功能费': 158, '套餐内容_国内主叫': 700, '套餐内容_国内流量': 6144},
                                      'inform':['适用品牌', '产品介绍']},
                     'prev_turn': {}},
    'BeliefState': {'curr_turn':{"功能费": [150, 300]},
                    'prev_turn':{"功能费": [150, 300]}},
    'RequestedSlot': {'curr_turn': ["套餐内容_国内流量", "副卡客户限制"],
                      'prev_turn': []},
    'DetectedDomain': {'curr_turn': "套餐",
                         'prev_turn': None},
    'UserAct': {'curr_turn': "告知",
                'prev_turn': None}
}


class RulePolicy:
    def __init__(self):
        self.not_mentioned_informable_slots = \
            ["功能费", "套餐内容_国内流量", "套餐内容_国内主叫", "开通方向"]
        self.DislikeResults = [] # 用户明确说不要某业务，就存到这里
        # 用于 要求更多 要求更少 时做filter

    def reset_not_mentioned_informable_slots(self):
        self.not_mentioned_informable_slots = \
            ["功能费", "套餐内容_国内流量", "套餐内容_国内主叫", "开通方向"]

    def select_offer(self, strategy, KB_results):
        if not KB_results:
            return None
        if strategy == 'random_offer':
            random.shuffle(KB_results)
            new_offer = KB_results[0]
        elif strategy == 'offer_first':
            new_offer = KB_results[0]
        # TODO：最便宜的
        return new_offer

    def Ask_more_or_less(self, required_slots, KB_results, UsrAct):
        """
        根据用户要求，从搜索结果 QueryResults 中找出一个符合要求的
        """
        slot = random.choice(list(required_slots))
        if UsrAct == "要求更多":
            KB_results.sort(key=lambda x: x[slot], reverse=False)
            for entity in KB_results:
                if entity not in self.DislikeResults:
                    return entity
            return None
        else:
            KB_results.sort(key=lambda x: x[slot], reverse=True)
            for entity in KB_results:
                if entity not in self.DislikeResults:
                    return entity
            return None
    # def Ask_more_or_less(self, required_slots, KB_results, KB_pointer, UsrAct):
        # """
        # 根据用户要求，从搜索结果 QueryResults 中找出一个符合要求的
        # """
        # if UsrAct == "要求更多" and "套餐内容_国内流量" in required_slots:
        #     slot = "套餐内容_国内流量"
        # else:
        #     slot = "功能费"
        # if len(KB_results) == 0:
        #     return None
        # if UsrAct == "要求更多":
        #     KB_results.sort(key=lambda x: x[slot], reverse=True)
        #     try:
        #         idx = KB_results.index(KB_pointer)
        #     except:
        #         idx = -1
        #     while idx >= 0:
        #         if KB_pointer[slot] < KB_results[idx][slot] and KB_results[idx] not in self.DislikeResults:
        #             return KB_results[idx]
        #         idx -= 1
        #     return None
        # else:
        #     KB_results.sort(key=lambda x: x[slot], reverse=False)
        #     try:
        #         idx = KB_results.index(KB_pointer)
        #     except:
        #         idx = -1
        #     while idx >= 0:
        #         if KB_pointer[slot] > KB_results[idx][slot] and KB_results[idx] not in self.DislikeResults:
        #             return KB_results[idx]
        #         idx -= 1
        #     return None

    def Reply(self, CurrrentDialogState):
        """
        return System Action for NLG
        :param CurrrentDialogState: 对话状态
        :return: dict
        """
        # 根据 BeliefState 更新 未提及的 informable slots
        self.informable_slots = CurrrentDialogState["BeliefState"]["curr_turn"]
        if CurrrentDialogState["BeliefState"]["curr_turn"] ==\
                CurrrentDialogState["BeliefState"]["prev_turn"]:
            self.IsInformableSlotChanged = False
        else:
            self.IsInformableSlotChanged = True
        if ("功能费" in self.informable_slots  or
            "功能费_文字描述" in self.informable_slots) and \
                "功能费" in self.not_mentioned_informable_slots:
            self.not_mentioned_informable_slots.remove("功能费")
        if ("套餐内容_国内主叫" in self.informable_slots
            or "套餐内容_国内主叫_文字描述" in self.informable_slots)  and\
                "套餐内容_国内主叫" in self.not_mentioned_informable_slots:
            self.not_mentioned_informable_slots.remove("套餐内容_国内主叫")
        if ("套餐内容_国内流量" in self.informable_slots or
            "套餐内容_国内流量_文字描述" in self.informable_slots)  and\
                "套餐内容_国内流量" in self.not_mentioned_informable_slots:
            self.not_mentioned_informable_slots.remove("套餐内容_国内流量")
        if "开通方向" in self.informable_slots and \
                "开通方向" in self.not_mentioned_informable_slots:
            self.not_mentioned_informable_slots.remove("开通方向")

        self.domain = CurrrentDialogState["DetectedDomain"]["curr_turn"][0]
        self.UsrAct = CurrrentDialogState['UserAct']['curr_turn'][0]
        self.last_SysAct = CurrrentDialogState['SystemAct']['curr_turn'].keys()
        self.requestable_slots = list(set(CurrrentDialogState["RequestedSlot"]["curr_turn"]))
        self.ER = copy.deepcopy(CurrrentDialogState["EntityMentioned"]["curr_turn"])
        self.KB_results = copy.deepcopy(CurrrentDialogState["QueryResults"])
        self.KB_pointer = copy.deepcopy(CurrrentDialogState["OfferedResult"]["prev_turn"])

        for item in self.ER:
            if item in self.DislikeResults:
                self.DislikeResults.remove(item)

        if len(self.DislikeResults)>=len(self.KB_results):
            self.DislikeResults = []

        for entity in self.KB_results[:]:
            if entity in self.DislikeResults:
                self.KB_results.remove(entity)
        # print("== DislikeResults:", self.DislikeResults)

        # 第一类UsrAct：告知
        if self.UsrAct == "告知":
            if self.ER:
                # 如果直接告知实体，就返回这个实体的基本介绍
                if len(self.ER) == 1:
                    # 提到一个实体，正常处理
                    self.new_offer = self.ER[0]
                    SysAct = {'offer': self.new_offer,
                              'inform': ["产品介绍"],
                              'reqmore': None,  # None 是因为 reqmore 没有参数
                              'domain': self.domain}
                    return SysAct
                else:
                    # 提到多个实体，虽然正常返回介绍，但不认为本轮有offer的实体
                    SysAct = {'offer': self.ER,
                              'inform': ["产品介绍"],
                              'reqmore': None,  # None 是因为 reqmore 没有参数
                              'domain': self.domain}
                    return SysAct
            elif len(self.KB_results) == 0:
                # 告知意味着查找业务，如果没找到业务，可以直接返回重新查找了
                SysAct = {'sorry': "很抱歉，没有找到符合您要求的业务，您能重新描述您对费用、流量、通话时长的要求吗？",
                          'clear_state': True,
                          'domain': self.domain}
                self.reset_not_mentioned_informable_slots()
                return SysAct
            elif len(self.KB_results) > 5:
                # 逻辑：符合条件的结果过多，通过进一步提问缩小范围
                # request部分，不需要提供实体
                # 系统问询一到两个 informable slot
                if self.domain == "套餐":
                    if "功能费" in self.not_mentioned_informable_slots:
                        SysAct = {'request': ["功能费"],
                                  'domain': self.domain} # 例如 "想要多少钱的套餐，对价位有要求吗？"
                        return SysAct
                    if "套餐内容_国内流量" in self.not_mentioned_informable_slots and \
                       "套餐内容_国内主叫" in self.not_mentioned_informable_slots:
                        if random.random() > 0.5:
                            SysAct = {'request': ["套餐内容_国内流量"],
                                      'domain': self.domain}
                            return SysAct
                        else:
                            SysAct = {'request': ["套餐内容_国内主叫"],
                                      'domain': self.domain}
                            return SysAct
                elif self.domain == "流量":
                    if "功能费" in self.not_mentioned_informable_slots:
                        SysAct = {'request': ["功能费"],
                                  'domain': self.domain}
                        return SysAct
                    if "套餐内容_国内流量" in self.not_mentioned_informable_slots:
                        SysAct = {'request': ["套餐内容_国内流量"],
                                  'domain': self.domain}
                        return SysAct
                elif self.domain == "国际港澳台":
                    if "开通方向" in self.not_mentioned_informable_slots:
                        SysAct = {'request': ["开通方向"],
                                  'domain': self.domain}
                        return SysAct
                elif self.domain == "WLAN":
                    if "功能费" in self.not_mentioned_informable_slots:
                        SysAct = {'request': ["功能费"],
                                  'domain': self.domain}
                        return SysAct

            # 若系统没有选择接着问，需要确定一个实体反馈给用户
            # 策略：选KB_results中的第一个
            self.new_offer = self.select_offer('offer_first', self.KB_results)
            SysAct = {'offer': self.new_offer,
                      'inform': ["产品介绍"],
                      'reqmore': None,  # None 是因为 reqmore 没有参数
                      'domain': self.domain}
            return SysAct

        # 第二类UsrAct：问询
        elif self.UsrAct == "问询":
            if self.domain == "个人":
                # 问个人信息的情况最简单直接，优先处理
                SysAct = {'inform': list(self.requestable_slots),
                                'domain': self.domain}
                return SysAct
            # 问业务实体，要先确定问的是什么
            if self.ER:
                # 如果本轮有提及的entity，基本就是在问这个entity
                self.new_offer = self.ER[0] if len(self.ER) == 1 else self.ER
            elif self.KB_pointer:
                # 如果本轮没有提到的entity，默认问询对象不变
                self.new_offer = self.KB_pointer
            elif not self.KB_results:
                # 如果上一轮也没有offer的entity，询问用户在问哪个entity
                SysAct = {'ask_entity': None,
                          'domain':self.domain }
                return SysAct
            else:
                self.new_offer = self.KB_results[0]
            # 根据领域检测的结果对requestable_slots进行一些修正
            if self.domain == "家庭多终端":
                if "能否分享" in self.requestable_slots:
                    self.requestable_slots.remove("能否分享")
                    self.requestable_slots.add("套餐内容_通话共享规则")
                    self.requestable_slots.add("套餐内容_短信共享规则")
                    self.requestable_slots.add("套餐内容_流量共享规则")
                if "互斥业务" in self.requestable_slots:
                    self.requestable_slots.remove("互斥业务")
                    self.requestable_slots.add("主卡互斥业务")
                    self.requestable_slots.add("副卡互斥业务")
                    self.requestable_slots.add("套餐内容_流量共享规则")
                if "开通客户限制" in self.requestable_slots:
                    self.requestable_slots.remove("开通客户限制")
                    self.requestable_slots.add("主卡开通客户限制")
                    self.requestable_slots.add("副卡客户限制")
                    self.requestable_slots.add("主卡套餐限制")
                    self.requestable_slots.add("其他开通限制")
            # 对某些特殊 slot 增加一些补充
            if "限速说明" in self.requestable_slots:
                self.requestable_slots.add("封顶说明")
            if "适用品牌" in self.requestable_slots:
                self.requestable_slots.add("互斥业务")
            # TODO: 这里应该多维护一个history requestable slot，
            #             根据这个删减requestable_slots 里的内容，避免重复告知
            # 返回对应的系统动作
            if not self.requestable_slots :
            # or '产品介绍' in self.requestable_slots:
                # 1. 如果未检测出requested slot，默认回复产品介绍
                SysAct = {'offer': self.new_offer,
                          'inform': ["产品介绍"],
                          'reqmore': None,  # None 是因为 reqmore 没有参数
                          'domain': self.domain}
                return SysAct
            else:
                SysAct = {'offer': self.new_offer,
                          'inform': list(self.requestable_slots),
                          'domain':self.domain }  # 例如 "***套餐的***是***" 语句要尽量自然
                return SysAct

        elif self.UsrAct == "比较":
            # 比较不同的套餐
            # 先考虑用户主动提及集合
            if len(self.ER) > 1:
                self.compared_entities = self.ER
            # 再考虑对话系统提供的业务实体集
            elif self.KB_pointer != CurrrentDialogState["OfferedResult"]["prev_turn"]:
                self.compared_entities = [self.KB_pointer,
                                                         CurrrentDialogState["OfferedResult"]["prev_turn"]]
            else: # 最后是个人业务
                self.compared_entities = CurrrentDialogState["UserPersonal"]["已购业务"]
            SysAct = {'offer_comp': self.compared_entities,
            # 比较这里的offer是entity的list，和offer不同，定义成一个新的sysact: offer_comp
                      'inform': ["套餐内容"],
                      'reqmore': None,
                      'domain':self.domain}  # 把这几个业务都介绍一下
                      # zyc: 这里inform定死为套餐内容，但实际可能只对比流量或者通话时长之类的
            return SysAct
        elif self.UsrAct in ["要求更多", "要求更少"]:
            if not self.KB_pointer:
                SysAct = {'sorry': "对不起，您能重新描述您对费用、流量、通话时长的要求吗？",
                              'clear_state':True,
                              'domain': self.domain}
                self.reset_not_mentioned_informable_slots()
                return SysAct
            self.new_offer = self.Ask_more_or_less(self.requestable_slots,
                                            self.KB_results, self.UsrAct)
            # new_offer 可能是None，
                # 这时需要主动提问用户更改 belief states 范围
            if self.new_offer == None:
                SysAct = {'sorry': "对不起，未能找到符合要求的套餐，请您重新描述"
                                            "对费用、流量和通话时长的要求~",
                          'clear_state':True,
                          'domain': self.domain}
                return SysAct
            else:
                SysAct = {'offer': self.new_offer,
                          # 'inform': ['产品介绍'],
                          'inform': self.requestable_slots,
                          'domain': self.domain}
                return SysAct
        elif self.UsrAct == "更换":
        # print("dislike results num: ", str(len(self.DislikeResults)))
            if len(self.KB_results) > 1:
                self.DislikeResults.append(self.KB_pointer)
                if self.KB_pointer in self.KB_results:
                    self.KB_results.remove(self.KB_pointer)
                self.new_offer = self.select_offer('random_offer', self.KB_results)

                SysAct = {'offer': self.new_offer,
                          'inform': ['产品介绍'],
                          'domain': self.domain}
                return SysAct
            else:
                SysAct = {'sorry': "对不起未能找到符合要求的业务，您能重新描述您的要求吗？",
                            'domain': self.domain}
                self.reset_not_mentioned_informable_slots()
                return SysAct
        elif self.UsrAct == "问询说明":
            SysAct = {'offerhelp':None,
                      'domain': self.domain} # 回复问询说明
            return SysAct
        elif self.UsrAct == "闲聊":
            SysAct = {'chatting': None,
                      'domain': self.domain}  # 引导用户进入任务
            return SysAct
        elif self.UsrAct == "同时办理":
            # 现在只会回复提到的两个业务的“互斥业务”slot
            # TODO: 需要对家庭多终端进行特别判断
            SysAct = {'offer': self.ER ,
                      'inform': ['互斥业务'],
                      'domain': self.domain}
            return SysAct
        else:
            SysAct = {'sorry': "宝宝找不到满意的答案，您可登录中国移动网上营业厅查找相关最新信息",
                      'domain': self.domain}
            return SysAct



if __name__ == '__main__':
    import pprint
    rule_policy = RulePolicy()
    pprint.pprint(rule_policy.Reply(DialogStateSample))
