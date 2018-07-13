import tensorflow as tf
import copy, pprint, os
from data.DataManager import DataManager
from NLU.SlotFilling.model.input_data import InformableSlotDataset, RequestableSlotDataset
from NLU.SlotFilling.model.model import InformableSlotDector, RequestableSlotDector

# requestable slots 对应的 DialogData20180613 的 id, 用于指导生成训练数据
All_requestable_slots = {
    '已购业务':['id1', 'id14'],
    '订购时间':['id2', 'id14'],
    '使用情况':['id3'],
    '号码':['id4'],
    '归属地':['id5'],
    '品牌':['id6'],
    '是否转品牌过渡期':['id7'],
    '是否停机':['id8'],
    '账单查询':['id9'],
    '话费充值':['id10','id15','id16'],
    '流量充值':['id11','id15','id17'],
    '话费查询':['id12','id16','id18'],
    '流量查询':['id13','id17','id18'],
    '功能费':['id22','id24','id28','id30','id71'],
    '套餐内容_国内主叫':['id20','id26','id72','id149'],
    '套餐内容_国内流量':['id19','id23','id25','id29','id75','id152'],
    '产品介绍':['id76'],
    '计费方式':['id77'],
    '适用品牌':['id70'],
    '套餐内容_国内短信':['id21','id27','id73','id150'],
    '套餐内容_国内彩信':['id74','id151'],
    '套餐内容_其他功能':['id78'],
    '套餐内容':['id79'],
    '超出处理_国内主叫':['id80','id153'],
    '超出处理_国内流量':['id81'],
    '超出处理':['id82','id115'],
    '结转规则_国内主叫':['id83'],
    '结转规则_国内流量':['id84'],
    '结转规则_赠送流量':['id85'],
    '结转规则':['id86'],
    '是否全国接听免费':['id87'],
    '能否结转滚存':['id88'],
    '能否分享':['id89','id91','id126','id127','id128'],
    '能否转赠':['id90','id92'],
    '转户转品牌管理':['id93'],
    '停机销号管理':['id94'],
    '赠送优惠活动':['id95'],
    '使用限制':['id96','id113'],
    '使用有效期':['id97'],
    '使用方式设置':['id98','id114'],
    '封顶规则':['id99'],
    '限速说明':['id100'],
    '受理时间':['id101'],
    '互斥业务':['id102','id129','id130'],
    '开通客户限制':['id103','id131','id132'],
    '累次叠加规则':['id104'],
    '开通方式':['id105'],
    '开通生效规则':['id106'],
    '是否到期自动取消':['id107'],
    '能否变更或取消':['id108'],
    '取消方式':['id109'],
    '取消变更生效规则':['id110'],
    '变更方式':['id111'],
    '密码重置方式':['id112'],
    '激活方式':['id116'],
    '副卡数量上限':['id125'],
    '主卡添加成员':['id134'],
    '主卡删除成员':['id135'],
    '副卡成员主动退出':['id136'],
    '主卡查询副卡':['id137'],
    '副卡查询主卡':['id138'],
    '恢复流量功能':['id139'],
    '开通方向':['id148']
}
All_requestable_slots_order = dict(zip(All_requestable_slots.keys(), range(len(All_requestable_slots.keys()))))

def extract_informable_data(DialogData, dict):
    dialog_data = copy.deepcopy(DialogData)
    high_data = []
    for id in dict['高']:
        high_data.extend(dialog_data[id]["用户回复示例"])
        del dialog_data[id]
    medium_data = []
    for id in dict['中']:
        medium_data.extend(dialog_data[id]["用户回复示例"])
        del dialog_data[id]
    low_data = []
    for id in dict['低']:
        low_data.extend(dialog_data[id]["用户回复示例"])
        del dialog_data[id]
    none_data = []
    for id, item in dialog_data.items():
        none_data.extend(item["用户回复示例"])
    return high_data, medium_data, low_data, none_data

def extract_requestable_data(DialogData, list):
    dialog_data = copy.deepcopy(DialogData)
    positive_data = []
    negative_data = []
    for id in list:
        positive_data.extend(dialog_data[id]["用户回复示例"])
        del dialog_data[id]
    for id, item in dialog_data.items():
        negative_data.extend(item["用户回复示例"])
    return positive_data, negative_data

def generate_dataset(DialogData):
    """
    生成informable slots 和 requestable slots 的训练数据集
    """
    # 生成 功能费 相关的训练数据
    informable_slot_dataset_cost = InformableSlotDataset(
        *extract_informable_data(DialogData,
                                 {"高": ["id36", "id51"],
                                  "中": ["id35", "id50"],
                                  "低": ["id34", "id49"]}))
    # 通话时长 相关的训练数据
    informable_slot_dataset_time = InformableSlotDataset(
        *extract_informable_data(DialogData,
                                 {"高": ["id39", "id52"],
                                  "中": ["id40", "id53"],
                                  "低": ["id41", "id54"]}))
    # 流量 相关的训练数据
    informable_slot_dataset_data = InformableSlotDataset(
        *extract_informable_data(DialogData,
                                 {"高": ["id44", "id55"],
                                  "中": ["id45", "id56"],
                                  "低": ["id46", "id57"]}))
    informable_slot_datasets = {
        "功能费":informable_slot_dataset_cost,
        "流量": informable_slot_dataset_data,
        "通话时长":informable_slot_dataset_time
    }
    requestable_slot_datasets = {}
    for k,v in All_requestable_slots.items():
        requestable_slot_datasets[k] = \
            RequestableSlotDataset(*extract_requestable_data(DialogData, v))
    return informable_slot_datasets,requestable_slot_datasets

def train(data_tmp_path):
    """
    用于训练模型，先训练完存好了才能用
    :param data_tmp_path:  data tmp 文件夹位置
    """
    print('载入数据管理器...')
    data_manager = DataManager(data_tmp_path)

    print('载入训练数据...')
    informable_slot_datasets, requestable_slot_datasets = generate_dataset(data_manager.DialogData)

    print('载入 SlotFilling 模型...')
    informable_slots_models = {
        "功能费":InformableSlotDector('cost'),
        "流量":InformableSlotDector('data'),
        "通话时长":InformableSlotDector('time')
    }
    requestable_slots_models = {}
    for k, v in All_requestable_slots_order.items():
        requestable_slots_models[k] = RequestableSlotDector(str(v))

    with tf.Session(config=tf.ConfigProto(
            allow_soft_placement=True)) as sess:
        sess.run(tf.group(tf.global_variables_initializer()))
        saver = tf.train.Saver()
        # saver.restore(sess, "./ckpt/model.ckpt")

        # 训练 informable slots
        for slot , model in informable_slots_models.items():
            average_loss = 0
            average_accu = 0
            final_accu = average_accu
            display_step = 10
            for step in range(1000):
                step += 1
                batch_data, batch_output = informable_slot_datasets[slot].next_batch()
                char_emb_matrix, word_emb_matrix, seqlen = data_manager.sent2num(batch_data, 40, 6)
                _, training_loss, training_accu = sess.run([model.train_op, model.final_loss, model.accuracy],
                                            feed_dict={
                                                model.char_emb_matrix: char_emb_matrix,
                                                model.word_emb_matrix: word_emb_matrix,
                                                model.output: batch_output
                                               })
                average_loss += training_loss / display_step
                average_accu += training_accu / display_step
                if step % display_step == 0:
                    # print("step % 4d, loss %0.4f, accu %0.4f" % (step, average_loss, average_accu))
                    final_accu = average_accu
                    average_loss = 0
                    average_accu = 0
            print("informable slot: %s, accu %0.4f" % (slot, final_accu))
        # 训练 requestable slots
        for slot, model in requestable_slots_models.items():
            average_loss = 0
            average_accu = 0
            final_accu = average_accu
            display_step = 10
            for step in range(1000):
                step += 1
                batch_data, batch_output = requestable_slot_datasets[slot].next_batch()
                char_emb_matrix, word_emb_matrix, seqlen = data_manager.sent2num(batch_data, 40, 6)

                _, training_loss, training_accu = sess.run([model.train_op, model.final_loss, model.accuracy],
                                                           feed_dict={
                                                               model.char_emb_matrix: char_emb_matrix,
                                                               model.word_emb_matrix: word_emb_matrix,
                                                               model.output: batch_output
                                                           })
                average_loss += training_loss / display_step
                average_accu += training_accu / display_step
                if step % display_step == 0:
                    # print("step % 4d, loss %0.4f, accu %0.4f" % (step, average_loss, average_accu))
                    final_accu = average_accu
                    average_loss = 0
                    average_accu = 0
            print("requestable slot: %s, accu %0.4f" % (slot, final_accu))
        # 保存模型
        saver.save(sess, "./ckpt/model.ckpt")

if __name__ == '__main__':
    train('../../../data/tmp')


