"""
对话状态跟踪、维护对话历史

四个业务实体集合：用户主动提及集合（保留两轮）、用户个人业务集合、数据库查询结果、系统提供结果集合（保留一轮）
所有领域的 belief states（累计） 和 requested slots(保留两轮)、领域检测结果（保留两轮）、 用户动作结果（保留两轮）

是否 DST 不变、是否用户重复表述同一句话、情感检测结果

"""
import os
import sys
import copy
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, '../..'))
# from collections import deque
from NLU.NLUManager import *
from DM.policy.RuleMapping import *
from data.DataBase.Ontology import *


card_dict = ['4G包年卡', '4G飞享卡', '4G任我用卡', '4G爱家卡', '8元卡', '万能副卡']

DB_tables = ['套餐', '流量', 'WLAN',  '国际港澳台', '家庭多终端']

Domain_DB_slots_mapping = {
    "套餐": TaoCan_DB_slots,
    "流量": LiuLiang_DB_slots,
    "WLAN": WLAN_DB_slots,
    "号卡": Card_DB_slots,
    "国际港澳台": Overseas_DB_slots,
    "家庭多终端": MultiTerminal_DB_slots,
    "个人": Personal_requestable_slots
}


DialogStateSample = {
    'TurnNum':int,
    # 用户主动提及业务实体集合
    'EntityMentioned': {'curr_turn': [],
                        'prev_turn': []},
    'UserPersonal': {'111':111
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


def rule_based_belief_state_update(usr_act, req_slots, prev_state, prev_offer):
    # 我设想的该函数输入输出和功能应为：
    # usr_act: "要求更多"或"要求更少"
    # req_slots: "要求更多"或"要求更少"的对象
    #           应为"功能费", "套餐内容_国内流量", "套餐内容_国内主叫"的组合
    # prev_state: 上一轮的belief state，目前的实现暂未用到
    # prev_offer: 上一轮的offered entity
    # 返回：new_state: 针对prev_offer满足要求req_slot更多/更少的新belief state

    if not prev_offer or isinstance(prev_offer, list):
        return prev_state

    max_v = {
        '功能费':1200,
        '套餐内容_国内流量':30720,
        '套餐内容_国内主叫':6000,
    }
    adjval = 200

    new_state = {}
    for slot in req_slots:
        if slot not in ["功能费", "套餐内容_国内流量", "套餐内容_国内主叫"]:
            continue
        base = prev_offer[slot]
        if usr_act == '要求更多':
            lower = base+1
            upper = base+adjval if base+adjval<max_v[slot] else max_v[slot]
            if slot in prev_state:
                prev_upper = prev_state[slot][1]
                upper = prev_upper if prev_upper>upper else upper
        else:
            upper = base-1
            lower = base-adjval if base-adjval>0 else 0
            if slot in prev_state:
                prev_lower = prev_state[slot][0]
                lower = prev_lower if prev_lower<lower else lower
        new_state[slot] = (lower, upper)

    return new_state


class DialogStateTracker:
    def __init__(self, usr_personal, print_details, logger):
        self.DialogState = {
             'TurnNum': 0,
             'EntityMentioned': {'curr_turn': [],  'prev_turn': []},
             'UserPersenal': usr_personal,
             'QueryResults': [],
             'OfferedResult': {'curr_turn': {},  'prev_turn': {}},
             'SystemAct': {'curr_turn': {},  'prev_turn': {}},
             'BeliefState':{'curr_turn': {},  'prev_turn': {}},
             'RequestedSlot':{'curr_turn': [],  'prev_turn': []},
             'DetectedDomain': {'curr_turn': None,  'prev_turn': None},
             'UserAct': {'curr_turn': None,  'prev_turn': None}
         }
        # status variables
        self.isDSTChange = True
        self.isOfferedEntityChange = True
        self.isUtterChange = True
        self.user_utter = None
        self.print_details = print_details
        self.logger = logger

    def update(self, NLU_results, rule_policy, data_manager):
        """
        NLU_results 包含
        Dom_results, ER_results, Senti_results, UserAct_results,
        Slot_filling_results, user_utter
        :param NLU_results: dict
        :param data_manager: data_manager
        """
        self.DialogState['TurnNum'] += 1
        self.isUtterChange = False if self.user_utter == NLU_results['userutter'] else True
        self.user_utter = NLU_results['userutter']
        # 复制上一轮的dialog state到prev_turn
        for key,value in self.DialogState.items():
            if isinstance(value,dict) and 'prev_turn' in value.keys():
                value['prev_turn'] = copy.deepcopy(value['curr_turn'])

        if self.print_details: self.logger.info("\n基于规则的DST更新：")

        # 优先更新识别准确率相对较高的UsrAct
        if self.DialogState['TurnNum'] == 1 and \
            NLU_results['useract'][0] in [ '要求更多', '要求更少', '更换']:
            self.DialogState['UserAct']['curr_turn'] = ('告知', 0.5)  # TODO: 告知是否合理？
            if self.print_details:
                self.logger.info(" - 第一轮不应出现'要求更多', '要求更少', '更换'等用户动作，"
                                         "强制修正为问询")
        else:
            self.DialogState['UserAct']['curr_turn'] = NLU_results['useract']

        # 更新domain
        prev_domain = self.DialogState['DetectedDomain']['prev_turn'][0] \
                                  if self.DialogState['DetectedDomain']['prev_turn'] else None
        if NLU_results['domain'][0] == '个人':
            if '我' in self.user_utter or '查' in self.user_utter:
                self.DialogState['DetectedDomain']['curr_turn'] = NLU_results['domain']
            elif  self.DialogState['TurnNum'] == 1:
                self.DialogState['DetectedDomain']['curr_turn'] = ('套餐', 0.5)
                if self.print_details:
                    self.logger.info(" - 第一轮误识为个人领域，强制修正为套餐领域")
            else:
                self.DialogState['DetectedDomain']['curr_turn'] = (prev_domain, 0.5)
                if self.print_details:
                    self.logger.info(" - 本轮误识为个人领域，修正为上一轮的领域")
        elif prev_domain == None:
            # 包含TurnNum== 1和上一轮执行了clear_state操作的情况
            self.DialogState['DetectedDomain']['curr_turn'] = NLU_results['domain']
        elif NLU_results['domain'][0] != prev_domain:
            if self.DialogState['UserAct']['curr_turn'][0] in ['更换','要求更多', '要求更少']:
                #pass, 即self.DialogState['DetectedDomain']['curr_turn'] 不变
                if self.print_details:
                    self.logger.info(" - 本轮用户动作有领域延续性，自动继承上一轮的领域")
            elif NLU_results['domain'][1] > 0.7:
                self.DialogState['DetectedDomain']['curr_turn'] = NLU_results['domain']
            else:
                #pass, 即self.DialogState['DetectedDomain']['curr_turn'] 不变
                if self.print_details:
                    self.logger.info(" - 本轮领域识别结果:"+str(NLU_results['domain'])+
                                             "置信度过低，自动继承上一轮的领域")
        else:
            self.DialogState['DetectedDomain']['curr_turn'] = NLU_results['domain']

        # 更新requested slot
        if self.DialogState['UserAct']['curr_turn'] in ['要求更多', '要求更少']:
            required_slots = ["功能费", "套餐内容_国内流量", "套餐内容_国内主叫"]
            for req_slot in required_slots:
                if req_slot not in NLU_results['requestable']:
                    required_slots.remove(req_slot)
            self.DialogState['RequestedSlot']['curr_turn'] = required_slots
        else:
            self.DialogState['RequestedSlot']['curr_turn'] = NLU_results['requestable']

        # 更新informable slot
        if self.DialogState['UserAct']['curr_turn'][0] in ['更换']:
            # pass，即self.DialogState['BeliefState']['curr_turn']不变
            if self.print_details:
                self.logger.info(" - 本轮的informable slot识别结果："+str(NLU_results['informable']))
                self.logger.info("   由于用户动作为“更换”，自动继承上一轮的belief state")
        elif self.DialogState['UserAct']['curr_turn'][0] in ['要求更多', '要求更少']:
            belief_state = rule_based_belief_state_update(
                                        self.DialogState['UserAct']['curr_turn'][0],
                                        self.DialogState['RequestedSlot']['curr_turn'],
                                        self.DialogState['BeliefState']['prev_turn'],
                                        self.DialogState['OfferedResult']['prev_turn'])
            self.DialogState['BeliefState']['curr_turn'] = belief_state
            if self.print_details:
                self.logger.info(' - 根据用户动作：要求更多/更少，调整belief state：')
                self.logger.info('   from: '+str(self.DialogState['BeliefState']['prev_turn']))
                self.logger.info('     to: ' + str(self.DialogState['BeliefState']['curr_turn']))
                self.logger.info("   本轮的informable slot识别结果："+str(NLU_results['informable']))
        else:
            for slot, value in NLU_results['informable'].items():
                self.DialogState['BeliefState']['curr_turn'][slot] = value

        # TODO: sentiment
        # self.detected_sentiment = ?
        self.DialogState['EntityMentioned']['curr_turn']= []
        if NLU_results['entity']:
            if self.print_details: self.logger.info(" - NLU实体识别结果："+str(NLU_results['entity']))
            QueryResults = []
            for entity_name in NLU_results['entity']:
                if entity_name in main_bussiness_dict:
                    for table in DB_tables:
                        ent = data_manager.SearchingByEntity(
                            table=table, feed_dict={'主业务':entity_name})
                        QueryResults += ent
                        self.DialogState['EntityMentioned']['curr_turn'] += ent
                elif entity_name in card_dict:
                    ent = data_manager.SearchingByEntity(
                        table='Card', feed_dict={'号卡':entity_name})
                    QueryResults += ent
                    self.DialogState['EntityMentioned']['curr_turn'] += ent
                else:
                    for table in DB_tables:
                        ent = data_manager.SearchingByEntity(
                            table=table, feed_dict={'子业务':entity_name})
                        QueryResults += ent
                        self.DialogState['EntityMentioned']['curr_turn'] += ent
        else:
            QueryResults = data_manager.SearchingByConstraints(
                table=self.DialogState['DetectedDomain']['curr_turn'][0],
                feed_dict=self.DialogState['BeliefState']['curr_turn'])
        self.DialogState['QueryResults'] = QueryResults

        #self.DialogState['UserPersenal'] = self.UserPersenal  #个人信息不变

        # 最后更新system act
        self.DialogState['SystemAct']['curr_turn'] = rule_policy.Reply(self.DialogState)
        if self.DialogState['SystemAct']['curr_turn'] == None:
            self.DialogState['SystemAct']['curr_turn'] = {}

        # TODO: 添加rule_based_offer()
        sysact = self.DialogState['SystemAct']['curr_turn']
        if 'offer' in sysact:
            self.DialogState['OfferedResult']['curr_turn'] = \
            self.DialogState['SystemAct']['curr_turn']['offer']
        else:
            self.DialogState['OfferedResult']['curr_turn'] = {}

        # 过滤掉一些不必要的requested slots
        self.sysact_filter()

        # 状态判断量的更新
        self.isDSTChange = False
        for key,value in self.DialogState.items():
            if isinstance(value, dict) and 'prev_turn' in value.keys():
                if value['prev_turn'] != value['curr_turn']:
                    self.isDSTChange = True
        self.isOfferedEntityChange=False if self.DialogState['OfferedResult']['curr_turn']==\
                                                     self.DialogState['OfferedResult']['prev_turn'] else True

        # 打印对话状态
        if self.print_details: self.dialog_state_print()

        # if 'backtrack' in self.DialogState['SystemAct']['curr_turn']:
        # # 复制上一轮的dialog state到curr_turn
        #     for key,value in self.DialogState.items():
        #         if isinstance(value,dict) and 'prev_turn' in value.keys():
        #             value['curr_turn'] = copy.deepcopy(value['prev_turn'])

        if 'clear_state' in self.DialogState['SystemAct']['curr_turn']:
            self.DialogState['BeliefState']['curr_turn'] = {}
            self.DialogState['DetectedDomain']['curr_turn'] = None
            if self.print_details: self.logger.info(' - belief state已重置')

    def dialog_state_print(self):
        # dialog state printer
        def print_entity(self, dst_key_name):
            temp = ' - ' + dst_key_name + '\n'
            for turn in ['prev_turn', 'curr_turn']:
                entity = self.DialogState[dst_key_name][turn]
                temp += '   '+turn+': '
                if isinstance(entity, list):
                    for ent in entity:
                        if '子业务' in ent and ent['子业务'] is not None:
                            temp += str(ent['子业务']) + ', '
                        elif '主业务' in ent and ent['主业务'] is not None:
                            temp +=str(ent['主业务']) + ', '
                        else:
                            temp += 'None, '
                    temp = temp[:-2] + '\n'
                elif isinstance(entity, dict):
                    ent = entity
                    if '子业务' in ent and ent['子业务'] is not None:
                        temp += str(ent['子业务']) + '\n'
                    elif '主业务' in ent and ent['主业务'] is not None:
                        temp +=str(ent['主业务']) + '\n'
                    else:
                        temp += 'None\n'
                elif entity is None:
                    temp += 'None\n'
                else:
                    raise ValueError('invalid entity type')
            return temp[:-1]

        def print_QR(self):
            QR = self.DialogState['QueryResults']
            temp = ' - QueryResults\n'
            for ent in QR:
                if isinstance(ent, dict):
                    if '子业务' in ent and ent['子业务'] is not None:
                        temp += '   '+str(ent['子业务']) + '\n'
                    elif '主业务' in ent and ent['主业务'] is not None:
                        temp += '   '+str(ent['主业务']) + '\n'
            return temp[:-1]

        def print_NLU(self, dst_key_name):
            temp = ' - ' + dst_key_name + '\n'
            for turn in ['prev_turn', 'curr_turn']:
                result = self.DialogState[dst_key_name][turn]
                temp += '   '+turn+': ' + str(result) + '\n'
            return temp[:-1]

        def print_sysact(self):
            SysAct = self.DialogState['SystemAct']
            temp = ' - SystemAct\n'
            for turn in ['prev_turn', 'curr_turn']:
                temp += '   '+turn+': \n'
                for sysact, content in SysAct[turn].items():
                    temp += '      '+sysact+'  '
                    if sysact == 'offer':
                        if isinstance(content, dict):
                            if '子业务' in content and content['子业务'] is not None:
                                temp += str(content['子业务']) + '\n'
                            elif '主业务' in content and content['主业务'] is not None:
                                temp +=str(content['主业务']) + '\n'
                        elif isinstance(content, list):
                            for ent in content:
                                if '子业务' in ent and ent['子业务'] is not None:
                                    temp += str(ent['子业务']) + ', '
                                elif '主业务' in ent and ent['主业务'] is not None:
                                    temp +=str(ent['主业务']) + ', '
                                else:
                                    temp += 'None, '
                            temp = temp[:-2] + '\n'
                        else:
                            temp += 'None\n'
                    elif sysact == 'offer_comp':
                        for ent in content:
                            if isinstance(ent, dict):
                                if '子业务' in ent and ent['子业务'] is not None:
                                    temp += str(ent['子业务']) + ', '
                                elif '主业务' in ent and ent['主业务'] is not None:
                                    temp +=str(ent['主业务']) + ', '
                            else:
                                temp += 'None, '
                        temp = temp[:-2] + '\n'
                    else:
                        temp += str(content)+'\n'
            return temp[:-1]

        self.logger.info('Dialog State in turn %d:' %self.DialogState['TurnNum'])
        self.logger.info(print_entity(self, 'EntityMentioned'))
        self.logger.info(print_QR(self))
        self.logger.info(print_entity(self, 'OfferedResult'))
        self.logger.info(print_NLU(self, 'DetectedDomain'))
        self.logger.info(print_NLU(self, 'UserAct'))
        self.logger.info(print_NLU(self, 'RequestedSlot'))
        self.logger.info(print_NLU(self, 'BeliefState'))
        self.logger.info(print_sysact(self))
        self.logger.info(' - isDSTChange:' + str(self.isDSTChange))
        self.logger.info(' - isUtterChange:' + str(self.isUtterChange))
        self.logger.info(' - isOfferedEntityChange:' + str(self.isOfferedEntityChange) + '\n')


    def sysact_filter(self):
        # 对系统动作中提到的required slot的过滤函数，滤除一些不合理的slots
        def domain_filter(req_slots, domain):
            # 删除非该domain的slot
            # TODO: 是否必要：domain detection未必靠谱？
            domain_slots = Domain_DB_slots_mapping[domain]
            for slot in req_slots[:]:
                if slot not in domain_slots:
                    req_slots.remove(slot)
                    if self.print_details: self.logger.info(' - 删去与本领域无关的slot: '+slot)
            for slot in domain_slots:
                if slot in self.user_utter:
                    req_slots.append(slot)
                    if self.print_details: self.logger.info(' - 增加直接提到的本领域slot: '+slot)
            req_slots = list(set(req_slots))
            return req_slots

        def cost_filter(req_slots):
            # 问询费用，只提供计费方式和功能费中的一个
            if '功能费' in req_slots and '计费方式' in req_slots:
                req_slots.remove('功能费')
                if self.print_details: self.logger.info(' - 删去功能费，只询问计费方式')
            elif '功能费' in req_slots:
                offered_entity = self.DialogState['OfferedResult']['curr_turn']
                if isinstance(offered_entity, list): offered_entity=offered_entity[0]
                if '功能费' in offered_entity and offered_entity['功能费'] is None:
                    req_slots.insert(0, '计费方式')
                    if self.print_details: self.logger.info(' - 功能费为None，提供计费方式')
            return req_slots

        def content_filter(req_slots):
            # 问询套餐内容、超出处理、结转规则时删去子slot
            if '产品介绍' in req_slots:
                for slot in req_slots[:]:
                    if '套餐内容' in slot:
                        req_slots.remove('产品介绍')
                        if self.print_details:
                            self.logger.info(" - 用户同时问询“产品介绍”和“套餐内容”，"
                                "只保留“套餐内容“")
                        break
            if '套餐内容' in req_slots:
                for slot in req_slots[:]:
                    if '套餐内容_' in slot:
                        if slot !='套餐内容_其他功能':
                            req_slots.remove('套餐内容')
                            if self.print_details:
                                self.logger.info(" - 用户同时问询“套餐内容”及其子内容，只保留子内容")
                        else:
                            req_slots.remove('套餐内容_其他功能')
                            if self.print_details:
                                self.logger.info(" - 用户同时问询其他内容及套餐内容，只保留套餐内容")
                        break
            if '超出处理' in req_slots:
                for slot in req_slots[:]:
                    if '超出处理_' in slot:
                        req_slots.remove('超出处理')
                        if self.print_details:
                            self.logger.info(" - 用户同时问询“超出处理”及其子内容，只保留子内容")
                        break
            if '结转规则' in req_slots:
                for slot in req_slots[:]:
                    if '结转规则_' in slot:
                        req_slots.remove('结转规则')
                        if self.print_details:
                            self.logger.info(" - 用户同时问询“结转规则”及其子内容，只保留子内容")
                        break
            return req_slots

        SysAct = self.DialogState['SystemAct']['curr_turn']
        domain = self.DialogState['DetectedDomain']['curr_turn'][0]
        if 'inform' in SysAct.keys():
            req_slots = SysAct['inform']
            req_slots = domain_filter(req_slots, domain)
            req_slots = cost_filter(req_slots)
            req_slots = content_filter(req_slots)
            self.DialogState['SystemAct']['curr_turn']['inform'] = req_slots

if __name__ == '__main__':
    dst = DialogStateTracker(DialogStateSample['UserPersonal'])
    data_manager = DataManager('../../data/tmp')
    rule_policy = RulePolicy()
    NLU_results = {
    'domain': ('套餐', 0.67),
    'useract': ('问询',  0.99),
    'informable': {"功能费": [500, 700]},
    'requestable': ['套餐内容', '产品介绍'],
    'entity': ['188元畅享套餐'],
    'sentiment':None,
    'userutter': '畅享套餐，188元那个，介绍一下'
    }
    NLU_results2 = {
    'domain': ('套餐', 0.17),
    'useract': ('问询',  0.89),
    'informable': {"功能费": [100, 400]},
    'requestable': ['套餐内容'],
    'entity': [],
    'sentiment':None,
    'userutter': 'hhhhhhhh'
    }
    NLU_results3 = {
    'domain': ('套餐', 0.19),
    'useract': ('比较',  0.44),
    'informable': {"功能费": [100, 150]},
    'requestable': ['套餐内容'],
    'entity': ['88元畅享套餐', '288元畅享套餐'],
    'sentiment':None,
    'userutter': 'hhhhhhhh'
    }
    dst.update(NLU_results, rule_policy, data_manager)
    dst.dialog_state_print()
    dst.update(NLU_results2, rule_policy, data_manager)
    dst.dialog_state_print()
    dst.update(NLU_results3, rule_policy, data_manager)
    dst.dialog_state_print()
