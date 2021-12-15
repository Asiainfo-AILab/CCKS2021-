import pandas as pd
from collections import Counter
import os
import json
import re


def get_data1(file):
    '''
    将给定TXT文件转为csv格式
    '''
    data = {}
    data['fontSize'] = []
    data['word'] = []
    data['x1'] = []
    data['x2'] = []
    data['y1'] = []
    data['y2'] = []
    for item in file:
        tmp = eval(item)
        data['fontSize'].append(tmp['fontSize'])
        data['word'].append(tmp['word'])
        data['x1'].append(tmp['x1'])
        data['x2'].append(tmp['x2'])
        data['y1'].append(tmp['y1'])
        data['y2'].append(tmp['y2'])
    return pd.DataFrame(data)



digit = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}
def _trans(s):
    num = 0
    if s:
        idx_q, idx_b, idx_s = s.find('千'), s.find('百'), s.find('十')
        if idx_q != -1:
            num += digit[s[idx_q - 1:idx_q]] * 1000
        if idx_b != -1:
            num += digit[s[idx_b - 1:idx_b]] * 100
        if idx_s != -1:
            # 十前忽略一的处理
            num += digit.get(s[idx_s - 1:idx_s], 1) * 10
        if s[-1] in digit:
            num += digit[s[-1]]
    return num

def trans(chn):
    '''
    汉字转数字
    '''
    if re.fullmatch('[0-9]+',chn):
        return chn
    chn = chn.replace('零', '')
    idx_y, idx_w = chn.rfind('亿'), chn.rfind('万')
    if idx_w < idx_y:
        idx_w = -1
    num_y, num_w = 100000000, 10000
    if idx_y != -1 and idx_w != -1:
        return trans(chn[:idx_y]) * num_y + _trans(chn[idx_y + 1:idx_w]) * num_w + _trans(chn[idx_w + 1:])
    elif idx_y != -1:
        return trans(chn[:idx_y]) * num_y + _trans(chn[idx_y + 1:])
    elif idx_w != -1:
        return _trans(chn[:idx_w]) * num_w + _trans(chn[idx_w + 1:])
    return _trans(chn)

def get_pdf(data1):
    '''将y坐标相同的字放到一起'''
    pdf = {}
    pdf['sentence'] = []
    pdf['y'] = []
    pdf['fontSize'] = []
    pdf['x'] = []
    sentence = ''
    y_sig = data1.loc[0,'y2']
    x_sig = 999                   # 随便找个比较大的数
    fontSize = 0                  # 初始化一个字体大小，防止找不到变量报错
    for index in data1.index:
        x1 = data1.loc[index,'x1']
        y2 = data1.loc[index,'y2']
        word = data1.loc[index,'word']
        try:
            if data1.loc[index,'fontSize'] < 6:  # 脚注前面的数字很小，y坐标比较小
                y2 = data1.loc[index+1,'y2'] if data1.loc[index+1,'fontSize'] > 6 else data1.loc[index+2,'y2']
        except:
            pass
        if abs(y2 - y_sig) < 10:
            x_sig = min(x_sig,x1)
            y_sig = y2            # 为了应对泰康宝育少儿年金保险1.3.5的情况,同一句话，前后的y不一样
            sentence += word
            if word != ' ':
                fontSize = data1.loc[index,'fontSize']
        elif word == ' ':         # 为了应对 泰康如意宝（2014）意外伤害保险 二级标题的编号和标题名称不在一行，导致标题编号错误
            end_flag = True
            continue
        else:
            pdf['sentence'].append(sentence.strip())
            pdf['x'].append(x_sig)
            pdf['y'].append(y_sig)
            pdf['fontSize'].append(fontSize)
            sentence = data1.loc[index,'word']
            x_sig = 999
            y_sig = data1.loc[index,'y2']
            end_flag = False
            
    if end_flag:
        pdf['sentence'].append(sentence.strip())
        pdf['y'].append(y_sig)
        pdf['fontSize'].append(data1.loc[index-1,'fontSize'])
        pdf['x'].append(x_sig)
    return pd.DataFrame(pdf)



def get_product_name(data_pdf):
    '''
    获取保险名称
    data_pdf: 处理为dataframe形式的PDF文件
    '''
    product = 'not found'
    special_product = [
                        "中英人寿.*（[A-Z]款）",
                        "友邦附加.*保险",
                        "华贵守护e家放心贷定期寿险条款                                              华贵人寿保险股份有限公司",
                        "中银三星附加康利双赢重大疾病保险条款   请扫描以查询验证条款",
                        "友邦金世无忧B款十年年金保险（分红型）",
                        '友邦附加全佑倍无忧B款重大疾病保险',
                        "交银康联逍遥贷意外伤害保险条款（2010年7月）",
                        "中宏宏福一生团体终身重大疾病保险",
                        "生命真心真意重大疾病保险条款",
                        '金富裕两全保险（分红型）',
    ]

    for i in data_pdf.index:
        sentence = data_pdf.loc[i,'sentence']
        fontSize = data_pdf.loc[i,'fontSize']
        if sentence.endswith('利益条款') and fontSize > 10 and ' ' not in sentence and '，' not in sentence:
            if not re.search('扫描',sentence):
                product = sentence[:-4]
                break
        elif sentence.endswith('条款') and fontSize > 10 and ' ' not in sentence and '，' not in sentence:
            if not re.search('扫描',sentence):
                if sentence in ['产品基本条款','基本条款','条款'] :         # 需要不断完善
                    product = data_pdf.loc[i-1,'sentence']
                    # print('product_name_last : ', data_pdf.loc[i-1,'sentence'])
                else:
                    product = sentence[:-2]
                    # print('product_name_2 : ',sentence)
                break
        else:
            for product_name in special_product:
                if re.fullmatch(product_name,sentence):
                    if sentence == '交银康联逍遥贷意外伤害保险条款（2010年7月）':
                        product = '交银康联逍遥贷意外伤害保险'
                        break
                    else:
                        sentence = sentence.split()[0]
                        product = sentence.replace('条款','')
                        break
            if product != 'not found':
                break
    return product


def judge_pdf_class(data_pdf):
    '''
    1. 判断保险文档格式属于哪一类
    2. 查找正文起始位置

    data_pdf: 处理为dataframe形式的PDF文件
    '''
    case1 = case2 = False
    case = 'second_format'
    for i in data_pdf.index:
        if re.match("第.{1,3}条",data_pdf.loc[i,'sentence']):
            case1 = True
            break
    for i in data_pdf.index:
        if re.match("第.{1,3}[章部分]",data_pdf.loc[i,'sentence']):
            case2 = True
            break
    if case2:
        case = 'third_format'
    else:
        if case1:
            case = 'first_format'
    print('case',case)
    flag = 2
    # for i in data_pdf.index:
    #     sentence = data_pdf.loc[i,'sentence']
    #     if sentence.endswith('公司') or sentence.startswith('在本条款中') or re.fullmatch(".?条.?款.?内.?容.?",sentence):
    #         flag = i
    #         break
    return case, flag

def if_continue(sentence,footnote):
    '''
    判断是否继续对该文档内容的查找
    sentence: str
    footnote: bool
    '''

    continue_search_sentence = ["第.{1,4}页",                         # 页脚不计入
                                "保险[1-9]{1,}号",                    # 保险编号，如  中国人寿〔2020〕疾病保险244号
                                "[此本]页正文完",                      # 本来应该是break的，但是有的PDF文件在中间页的结尾也有这个，就continue了
                                "条款全文结束",
                                "条款正文完",
                                '保险条款内容结束',
                                '（条款正文结束）',
                                '<本页内容结束>',
                                '瑞华康瑞保重大疾病保险',
                                '瑞华附加投保人豁免保险费重大疾病保险',
                                '（此页内容结束）',
                                '<本条款内容结束>',
    ]
    continue_match_sentence = ["[0-9 ]{1,}[\u4e00-\u9fa5]{1,}指",     # 是脚注
                                "[0-9 ]{1,}对于在",                    # 是另一种形式脚注
                                "[0-9 ]{1,}[\u4e00-\u9fa5]{1,}：",    # 是另一种形式脚注  
    ]
    continue_fullmatch_sentence = [" *",                            # 没有内容
                                    "[0-9]{1,}",                     # 页码 如 1
                                    "- [0-9]+ -",
                                    "[0-9]+-[0-9]+",                 # 页码 如 1-19
                                    '[0-9]+ / [0-9]+',               # 页码 如 3 / 10
                                    '泰康人寿保险有限责任公司',                      # 针对某一篇特定保险文档进行的判断，文档里有两个保险
                                    '中国人寿保险股份有限公司',                      # 针对某一篇特定保险文档进行的判断，文档里有两个保险
                                    '和谐健康保险股份有限公司',
                                    '泰康人寿个人税收递延型养老年金保险B2款（2018）',   # 针对某一篇特定保险文档进行的判断，文档里有两个保险  
                                    '民生航空旅客人身意外伤害保险 *民生人寿保险股份有限公司',
                                    '《金富裕两全保险（分红型）》2012年2月备案',
                                    '中美联泰大都会人寿保险有限公司',
                                    'MR06-C                                                                     中美联泰大都会人寿[2018]205号',
                                    '广电日生附加特别给付意外伤害保险[ ]+[0-9]+',
                                    '[\u4e00-\u9fa5]+条款',                                     # 文档不需要的说明，如  个人保险基本条款, 但是有些标题特定行有条款两个字，所以.+
    ]
    if any(re.search(rule,sentence) for rule in continue_search_sentence):
        return True, footnote
    if any(re.fullmatch(rule,sentence) for rule in continue_fullmatch_sentence):
        return True, footnote
    if any(re.match(rule,sentence) for rule in continue_match_sentence):
        if not sentence.endswith('。'):
            footnote = True     
        return True, footnote
    if not re.search("[0-9\u4e00-\u9fa5，。.a-zA-Z]",sentence):  # 只有奇怪的符号
        return True, footnote
    if footnote:                                             # 脚注可能有多行
        if sentence.endswith('。'):
            footnote = False
        return True, footnote
    return False, footnote

def if_break(sentence):
    '''
    判断是否停止对该文档内容的查找
    sentence: str
    '''
    break_fullmatch_sentence = ['附件',                 # 条款都找完了，到了附件就停止
                                '附表.?',               # 条款都找完了，到了附表就停止
                                '附表.?：',
                                '附表.?:',
                                '附录',                 # 条款都找完了，到了附录就停止
                                '条款特别提示',          # 条款都找完了，到了条款特别提示就停止
                                '附加[\u4e00-\u9fa5]{1,}比例表', # 条款都找完了，到了附件表就停止
                                '人身保险残疾程度与保险金给付比例表',

    ]
    break_endswith_sentence = ['月度保障成本费率表',    # 针对 泰康赢家人生终身寿险（投资连结型） 的特定优化

            
    ]
    if any(re.fullmatch(rule,sentence) for rule in break_fullmatch_sentence):  
        return True
    if any(sentence.endswith(s) for s in break_endswith_sentence):
        return True

    return False

def text_analyse_1(sentence):
    '''
    格式为  第xxxx条 xxxx ， 为一级大标题
    '''
    tmp = sentence.split()
    try:
        title = ''.join(tmp[1:])
    except:
        print('case1获取形式为第xxxx条 xxxx的title失败，句子为：', sentence)
        
    try:
        tid_tmp = re.findall("第(.*)条",sentence)[0]
    except:
        print('case1查找形式为第xxx条的句子的tid失败，句子为 :', sentence)
        tid_tmp = '一'
    
    tid = str(trans(tid_tmp))
    start = True
    value = ''
    return tid, start, title, value

def text_analyse_2(sentence, tid):
    '''
    格式为  1.xxxxx：  xxxxx  , 为次级标题
    '''
    second = sentence.split('：')
    tid_tmp = tid.split('.')
    if len(tid_tmp) > 1:
        tid_tmp = tid_tmp[:-1]
    tid = '.'.join(tid_tmp) + '.' + sentence.split('.')[0]
    title = second[0].split('.')[-1]
    if len(second) > 1:
        value = second[-1]
    else:
        value = ''
    return tid, title, value

def text_analyse_3(sentence, tid):
    '''
    格式为  1.xxxxx  , 为次级标题
    '''
    second = sentence.split('.')
    tid_tmp = tid.split('.')
    if len(tid_tmp) > 1:
        tid_tmp = tid_tmp[:-1]
    tid = '.'.join(tid_tmp) + '.' + second[0]
    title = second[-1]
   
    value = ''
    return tid, title, value

def text_analyse_4(sentence, tid):
    '''
    格式为  一、xxxxx   , 为次级标题
    '''

    second = sentence.split('、')
    tid_tmp = tid.split('.')

    if second[0] != '一':
        tid_tmp = tid_tmp[:-1]
    tid = '.'.join(tid_tmp) + '.' + str(trans(second[0]))
    title = second[-1].strip()
    value = ''
    return tid, title, value

def text_analyse_5(sentence):
    '''
    格式为  1. xxxx 或 1 xxxx 或 1． xxxx 或 1.1 xxxx  , 为一级大标题或者次级标题
    有些小标题是 1 xxxx 这种的，容易与大标题混淆，需要特殊处理
    '''

    tmp = sentence.split()
    tid = tmp[0]

    try:
        title = tmp[1]
    except:
        title = ''
    if title.endswith('：'):
        title = title[:-1]
    if tid.endswith('.') or tid.endswith('．'):
        tid = tid[:-1]

    if len(tmp) > 2:
        value = ''.join(tmp[2:])
    else:
        value = ''
    start = True
    return tid, title, value, start

def text_analyse_6(sentence):
    '''
    格式为  第xxxx章/部分 xxxx ， 为一级大标题
    '''
    tmp = sentence.split()
    try:
        title = tmp[1]
    except:
        title = ''
    try:
        tid_tmp = re.findall("第(.*)章",sentence)[0]
    except:
        tid_tmp = re.findall("第(.*)部分",sentence)[0]
        
    tid = str(trans(tid_tmp))
    if len(tmp) > 2:
        value = ''.join(tmp[2:])
    else:
        value = ''

    start = True
    return tid, start, title, value

def text_analyse_7(sentence, tid):
    '''
    格式为  (一） xxxxx   , 为次级标题
    '''

    second = sentence.split()
    tmp = second[0][1]
    tid_tmp = tid.split('.')

    if tmp != '一':
        tid_tmp = tid_tmp[:-1]
    tid = '.'.join(tid_tmp) + '.' + str(trans(tmp))
    title = second[-1].strip()
    value = ''
    return tid, title, value