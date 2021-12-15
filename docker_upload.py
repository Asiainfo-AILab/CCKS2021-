#!/usr/bin/env python
# coding: utf-8


# 版本变更记录
'''
1.12 base， 
    score：0.3662
1.13 注释掉fontName，
    修改 tid_tmp, title = sentence.split()，解决ValueError: too many values to unpack (expected 2)问题，
    修改tid_tmp = tid.split('.')，解决UnboundLocalError: local variable 'tid' referenced before assignment问题，
    score：0.3614
1.14 还原tid_tmp, title = sentence.split()，
    还原 tid_tmp = tid.split('.')，
    增加product名字输出，
    score：0.3650
1.15 修改 if sentence in ['产品基本条款','基本条款','条款'] : 代码，增加 '条款'。
    判断是否是product name中增加    and '，' not in sentence
    注释掉 traceback.print_exc()
    增加 if file_value['product'] ==  'not found':
            print('not found product name :',data_pdf.iloc[:50,:])
    score：0.3778
1.16 修改if file_value['product'] ==  'not found':
            print('not found product name :',data_pdf.iloc[:50,:])
    为： if file_value['product'] ==  'not found':
            print('not found product name !')
            for i in range(50):
                print(data_pdf.loc[i,'sentence'])
1.17 针对部分保险条款的product name获取做优化, 增加 special_product 内容，增加了查找product里面的else内容
    score:0.3932
1.18 无影响分数的调整
1.19 注释掉 closely_title 等30行
    score: 0.3624
1.20 去掉了print300-308行内容，减少报错。无其他影响分数的调整
    score: 0.3920
1.21 修改 continue_search_sentence = ["第.{1,3}页",  为  continue_search_sentence = ["第.{1,4}页"
     增加了third_format大量内容
     修改 if (data_pdf.loc[i,'x'] - left_x_boundry) > 50: 为 if (data_pdf.loc[i,'x'] - left_x_boundry) > 80:
    score：0.51
1.22 case2 增加这个if not re.match('[0-9]',sentence):，避免有编号的标题也采用了模板
1.23 .......(都是微调，不记录了)
    
'''

import pandas as pd
from collections import Counter
import os
import json
import re
from pdf_analyse import *
from global_setting import *


def get_details(data_pdf,left_x_boundry,most_common_x):
    '''
    提取各项信息
    '''
    
    file_value = {}
    file_value['annotation'] = []
    title_value = {}
    value_value = {}
    tid_value = []
    def fill_value(tid,title,value,i,data_pdf):
        tid_value.append(tid)
        title_value[tid] = title
        value_value[tid] = value
        tid_y = data_pdf.loc[i,'y'] 
        np_tid = 0                                   # 没有编号的标题重新计数
        if_tid = False 
        return tid_y, np_tid, if_tid
    def fill_value_only(tid,title,value):
        tid_value.append(tid)
        title_value[tid] = title
        value_value[tid] = value

    ## 获取product 名称
    file_value['product'] =  get_product_name(data_pdf)

    ## 判别保险条款格式，一共有三大类
    ## 判别保险正文开始位置
    case, flag = judge_pdf_class(data_pdf)
    
    ## 获取各层级信息
    start = False
    footnote = False   # 是否还停留在脚注中
    NO_NUMBER_TITLE_FLAG = False  # 标题识别乱码的情况
    big_tid = 9999
    for i in range(flag,len(data_pdf)):
        sentence = data_pdf.loc[i,'sentence'] 
        
        continue_flag, footnote = if_continue(sentence,footnote)
        if continue_flag:
            continue

        break_flag = if_break(sentence)
        if break_flag and 5 * i > len(data_pdf):         # 目录可能会出现break的词
            break


        if case == 'first_format':
            
            ## 满足 第xxx条 格式
            if re.match("第.{1,3}条",sentence):
                if len(sentence.split()) > 3:
                    continue
                tid, start, title, value = text_analyse_1(sentence)
                tid_y, np_tid, if_tid = fill_value(tid,title,value,i,data_pdf)
               
                
            ## 满足 第xxx条 格式 的次级标题, 句子以1.xxx：开头
            elif re.match("[1-9]*\.[\u4e00-\u9fa5]{1,}：",sentence):
                tid, title, value = text_analyse_2(sentence,tid)
                tid_y, np_tid, if_tid = fill_value(tid,title,value,i,data_pdf)
                
                

            ## 满足 第xxx条 格式 的次级标题, 句子格式为1.xxxx
            elif re.fullmatch("[1-9]*\.[\u4e00-\u9fa5]{1,}",sentence) and len(sentence) < 12:
                tid, title, value = text_analyse_3(sentence,tid)
                tid_y, np_tid, if_tid = fill_value(tid,title,value,i,data_pdf)
                
                
            ## 满足 一、xxx 格式的次级标题， 例如  一、住院津贴医疗保险责任
            elif re.fullmatch("[\u4e00-\u9fa5]{1,2}、[ ]?[\u4e00-\u9fa5]+",sentence) and len(sentence) < 15:
                try:
                    tid, title, value = text_analyse_4(sentence,tid)
                except:
                    continue
                tid_y, np_tid, if_tid = fill_value(tid,title,value,i,data_pdf)

            elif re.fullmatch("\([\u4e00-\u9fa5]{1,2}\) [\u4e00-\u9fa5]+",sentence) and len(sentence) < 15:
                # 有些缩进明显的并不适合作为标题
                if data_pdf.loc[i,'x'] - most_common_x < -15:

                    tid, title, value = text_analyse_7(sentence,tid)
                    tid_y, np_tid, if_tid = fill_value(tid,title,value,i,data_pdf)
                    
                else:
                    try:
                        value_value[tid] += sentence           ## 有些保险一开始也满足这个条件，但是这时还没有tid
                    except:
                        pass
                

            else:                                            # 正文和没有明显标识的标题  这两种情况

                if start:
                    value_tmp = sentence.split()
                    special_frame = ['人数变动手续费',         # 国寿销售精英团体养老年金保险（万能型） 特殊情况
                        
                    ]

                    if len(value_tmp) > 1 and all(re.fullmatch(r"[\u4e00-\u9fa50-9.%]{1,}",s) for s in value_tmp) and all(len(s) < 11 for s in value_tmp):
                        ## 对应表格的情况
                        try:
                            value_value[tid] += sentence
                        except:
                            print('对应表格的情况写入失败，句子为', sentence)
                    elif any(sentence == s for s in special_frame):
                        try:
                            value_value[tid] += sentence
                        except:
                            print('对应special_frame的情况写入失败，句子为', sentence)
                        

                    elif re.match("[\u4e00-\u9fa5]{1,} = ", sentence) or sentence == '入价' or re.match("[\u4e00-\u9fa5]{1,} － ", sentence):  #  该行为一个计算公式
                        try:
                            value_value[tid] += sentence
                        except:
                            print('对应计算公式的情况写入失败，句子为', sentence)


                    elif re.fullmatch(r"（见[0-9.]+）",value_tmp[0]) and len(value_tmp[0]) < 11:  # 没有编号的标题的特定情况
                        title_value[tid] += value_tmp[0]
                        tid_y = data_pdf.loc[i,'y']
                        if len(value_tmp) > 1:
                            value_value[tid] += ''.join(value_tmp[1:])

                    elif re.fullmatch(r"[\u4e00-\u9fa5/（）、]{1,}",value_tmp[0]) and len(value_tmp[0]) < 11:  ## 一个标题分两行或多行写的情况
                        # 特殊情况，形式为 一、 xxx 但是是正文的情况
                        if value_tmp[0] in ['一','二','三','四','五','六','七','八','九','十','一、','二、','三、','四、','五、','六、','七、','八、','九、','十、']:
                            value_value[tid] += sentence
                            continue

                        if any(re.fullmatch(s,value_tmp[0]) for s in closely_title): 
                            tid_y = data_pdf.loc[i,'y'] 
                            if re.match('[0-9]+[.]',value_tmp[0]):
                                np_tid = int(value_tmp[0].split('.')[0])
                                title = re.findall('[0-9]+[.](.*)',value_tmp[0])[0]
                            else:
                                np_tid += 1
                                title = value_tmp[0]
                            
                            if if_tid:
                                tid = '.'.join(tid.split('.')[:-1]) + '.' + str(np_tid)
                            else:   
                                tid = tid + '.' + str(np_tid)
                                if_tid = True
                            tid_value.append(tid)
                            
                            title_value[tid] = title
                            try:
                                if value_tmp[1] == '：':     # 未成年 ： 指不满十二周岁的儿童。
                                    value_value[tid] = ''.join(value_tmp[2:])
                                else:
                                    value_value[tid] = ''.join(value_tmp[1:])
                            except:
                                value_value[tid] = ''



                        elif abs(data_pdf.loc[i,'y'] - tid_y) > 25:   ## y的距离超过25认为是两个标题
                            tid_y = data_pdf.loc[i,'y'] 
                            np_tid += 1
                            if if_tid:
                                tid = '.'.join(tid.split('.')[:-1]) + '.' + str(np_tid)
                            else:   
                                tid = tid + '.' + str(np_tid)
                                if_tid = True
                            tid_value.append(tid)
                            title_value[tid] = value_tmp[0]
                            try:
                                if value_tmp[1] == '：':     # 未成年 ： 指不满十二周岁的儿童。
                                    value_value[tid] = ''.join(value_tmp[2:])
                                else:
                                    value_value[tid] = ''.join(value_tmp[1:])
                            except:
                                value_value[tid] = ''
                            
                        else:
                            title_value[tid] += value_tmp[0]
                            try:
                                if value_tmp[1] == '：':     # 未成年 ： 指不满十二周岁的儿童。
                                    value_value[tid] += ''.join(value_tmp[2:])
                                else:
                                    value_value[tid] += ''.join(value_tmp[1:])
                            except:
                                value_value[tid] += ''
                            tid_y = data_pdf.loc[i,'y']

                            
                    else:
                        if sentence.startswith('：') and sentence.endswith('：'):
                            value_value[tid] = sentence[1:] + value_value[tid]
                        else:
                            value_value[tid] += sentence
        elif case == 'second_format':  ## 第二种 保险格式 1.xxx
            if most_common_x - left_x_boundry  > 15:       # 绝大部分情况
                if data_pdf.loc[i,'x'] - most_common_x < -15:
                    # 解析出乱码的特殊情况
                    if not re.match('[0-9]',sentence):
                        for rule in NO_NUMBER_TITLE.keys():
                            if re.fullmatch(rule,sentence):
                                if big_tid != 9999:
                                    big_tid = str(int(big_tid) + 1)
                                else:
                                    big_tid = NO_NUMBER_TITLE[rule]
                                big_title = re.findall('[\u4e00-\u9fa5]+',rule)[0]
                                tid = big_tid
                                try:
                                    value = rule.split()[1]
                                except:
                                    value = ''
                                fill_value_only(tid=tid, title=big_title, value=value)
                                NO_NUMBER_TITLE_FLAG = True
                                break
                        if any(re.fullmatch(rule,sentence) for rule in NO_NUMBER_TITLE.keys()):
                            continue
                    if re.match('[0-9]',sentence):
                        for rule in title_value_with_no_space.keys():
                            if re.fullmatch(rule,sentence):
                                tid = title_value_with_no_space[rule][0]
                                title = title_value_with_no_space[rule][1]
                                value = title_value_with_no_space[rule][2]
                                tid_y, np_tid, if_tid = fill_value(tid,title,value,i,data_pdf)
                                break
                        if any(re.fullmatch(rule,sentence) for rule in title_value_with_no_space.keys()):
                            continue
                    if re.match("[0-9.．]{1,} ",sentence) and re.fullmatch("[BrugadJDCRT\u4e00-\u9fa5、（）\(\)ⅢＩ/\-]{1,}",sentence.split()[1]):
                        ### 有些标题较长，用长度来限制可能不太准确，改成上面这一行的样子

                        if (data_pdf.loc[i,'x'] - left_x_boundry) > 80:          # 有个别正文也是这种格式, 但是又大量缩进，用这种判断找出这种内容
                            try:                                                 # 有时起始位置定位到了目录，可能满足if的条件，但是没有tid，所以加个try
                                value_value[tid] += sentence
                                continue 
                            except:
                                pass
                        
                        tmp = sentence.split()[0]
                        if tmp.endswith('.') or tmp.endswith('．'):
                            tmp = tmp[:-1]
                        if re.fullmatch('[0-9]+',tmp) and NO_NUMBER_TITLE_FLAG:
                            try:
                                third_tid += 1
                            except:
                                third_tid = 1
                            try:
                                tid = second_tid + '.' + str(third_tid)
                            except:
                                continue
                            try:
                                title = sentence.split()[1]
                            except:
                                title = ''
                            if len(sentence.split()) > 2:
                                value = ''.join(sentence.split()[2:])
                            else:
                                value = ''
                        else:
                            tid, title, value, start = text_analyse_5(sentence)
                        
                        tid_y, np_tid, if_tid = fill_value(tid,title,value,i,data_pdf)
                        

                        

                    else:                  # 正文和没有明显标识的标题  这两种情况

                        if start:
                            value_tmp = sentence.split()

                            if len(value_tmp) > 1 and all(re.fullmatch(r"[\u4e00-\u9fa50-9.%]{1,}",s) for s in value_tmp) and all(len(s) < 11 for s in value_tmp):
                                ## 对应表格的情况
                                value_value[tid] += sentence
                            elif re.match('第[0-9]+类：',sentence) and NO_NUMBER_TITLE_FLAG:
                                # 针对大标题是乱码，内部有许多种疾病的特殊处理
                                second_tid = big_tid + '.' + re.findall("第(.*)类",sentence)[0]
                                second_title = value_tmp[-1]
                                third_tid = 0
                                fill_value_only(second_tid,second_title,'')
                                


                            elif re.match("[\u4e00-\u9fa5]{1,} = ", sentence) or sentence == '入价' or re.match("[\u4e00-\u9fa5]{1,} － ", sentence):  #  该行为一个计算公式
                                value_value[tid] += sentence


                            elif re.fullmatch(r"（见[0-9.]+）",value_tmp[0]) and len(value_tmp[0]) < 11:  # 没有编号的标题的特定情况
                                title_value[tid] += value_tmp[0]
                                tid_y = data_pdf.loc[i,'y']
                                if len(value_tmp) > 1:
                                    value_value[tid] += ''.join(value_tmp[1:])

                            elif re.fullmatch(r"[Ⅲ0-9.\u4e00-\u9fa5/（）\(\)、：ABSDPHVICU-]{1,}",value_tmp[0]) and len(value_tmp[0]) < 12:  ## 没有编号，一个标题分两行或多行写的情况
                                # 特殊情况，形式为 一、 xxx 但是是正文的情况
                                if value_tmp[0] in ['一','二','三','四','五','六','七','八','九','十','一、','二、','三、','四、','五、','六、','七、','八、','九、','十、']:
                                    value_value[tid] += sentence
                                    continue
                                
                                
                                
                                if any(re.fullmatch(s,value_tmp[0]) for s in closely_title): 
                                    tid_y = data_pdf.loc[i,'y'] 
                                    if re.match('[0-9]+[.]',value_tmp[0]):
                                        np_tid = int(value_tmp[0].split('.')[0])
                                        title = re.findall('[0-9]+[.](.*)',value_tmp[0])[0]
                                    else:
                                        np_tid += 1
                                        title = value_tmp[0]
                                    
                                    if if_tid:
                                        tid = '.'.join(tid.split('.')[:-1]) + '.' + str(np_tid)
                                    else:   
                                        tid = tid + '.' + str(np_tid)
                                        if_tid = True
                                    tid_value.append(tid)
                                    
                                    title_value[tid] = title
                                    try:
                                        value_value[tid] = value_tmp[1]
                                    except:
                                        value_value[tid] = ''
                                    
                                elif data_pdf.loc[i,'y'] < tid_y and data_pdf.loc[i,'y'] < 85:    ## 标题隔页了,但是必须在第一行
                                    title_value[tid] += value_tmp[0]
                                    tid_y = data_pdf.loc[i,'y']
                                    
                                elif abs(data_pdf.loc[i,'y'] - tid_y) > 25:   ## y的距离超过25认为是两个标题
                                    tid_y = data_pdf.loc[i,'y'] 
                                    if re.match('[0-9]+[.]',value_tmp[0]):
                                        np_tid = int(value_tmp[0].split('.')[0])
                                        title = re.findall('[0-9]+[.](.*)',value_tmp[0])[0]
                                    else:
                                        np_tid += 1
                                        title = value_tmp[0]
                                    if if_tid:
                                        tid = '.'.join(tid.split('.')[:-1]) + '.' + str(np_tid)
                                    else:   
                                        tid = tid + '.' + str(np_tid)
                                        if_tid = True
                                    
                                    fill_value_only(tid=tid, title= title, value= '')
                                    
                                else:
                                    
                                    title_value[tid] += value_tmp[0]
                                    tid_y = data_pdf.loc[i,'y']
                                if len(value_tmp) > 1:
                                    value_value[tid] += ''.join(value_tmp[1:])
                            else:
                                if sentence.startswith('：') and sentence.endswith('：'):
                                    value_value[tid] = sentence[1:] + value_value[tid]
                                else:
                                    value_value[tid] += sentence
                else:
                    try:
                        value_value[tid] += sentence           ## 有些保险一开始也满足这个条件，但是这时还没有tid
                    except:
                        pass
            else:       # 极少数情况
                if not re.match('[0-9]',sentence):
                    for rule in NO_NUMBER_TITLE.keys():
                        if re.fullmatch(rule,sentence):
                            if big_tid != 9999:
                                big_tid = str(int(big_tid) + 1)
                            else:
                                big_tid = NO_NUMBER_TITLE[rule]
                            big_title = re.findall('[\u4e00-\u9fa5]+',rule)[0]
                            tid = big_tid
                            try:
                                value = rule.split()[1]
                            except:
                                value = ''
                            fill_value_only(tid=tid, title=big_title, value=value)
                            NO_NUMBER_TITLE_FLAG = True
                            break
                    if any(re.fullmatch(rule,sentence) for rule in NO_NUMBER_TITLE.keys()):
                        continue

                if re.match('[0-9]',sentence):
                    for rule in title_value_with_no_space.keys():
                        if re.fullmatch(rule,sentence):
                            tid = title_value_with_no_space[rule][0]
                            title = title_value_with_no_space[rule][1]
                            value = title_value_with_no_space[rule][2]
                            tid_y, np_tid, if_tid = fill_value(tid,title,value,i,data_pdf)
                            break
                    if any(re.fullmatch(rule,sentence) for rule in title_value_with_no_space.keys()):
                        continue
                if re.match("[0-9.．]{1,} ",sentence) and re.fullmatch("[\u4e00-\u9fa5、（）\(\)ⅢＩ/]{1,}",sentence.split()[1]):
                    ### 有些标题较长，用长度来限制可能不太准确，改成上面这一行的样子

                    if (data_pdf.loc[i,'x'] - left_x_boundry) > 80:          # 有个别正文也是这种格式, 但是又大量缩进，用这种判断找出这种内容
                        try:                                                 # 有时起始位置定位到了目录，可能满足if的条件，但是没有tid，所以加个try
                            value_value[tid] += sentence
                            continue 
                        except:
                            pass
                    
                    tmp = sentence.split()[0]
                    if tmp.endswith('.') or tmp.endswith('．'):
                        tmp = tmp[:-1]
                    if re.fullmatch('[0-9]+',tmp) and NO_NUMBER_TITLE_FLAG:
                        try:
                            third_tid += 1
                        except:
                            third_tid = 1
                        try:
                            tid = second_tid + '.' + str(third_tid)
                        except:
                            continue
                        try:
                            title = sentence.split()[1]
                        except:
                            title = ''
                        if len(sentence.split()) > 2:
                            value = ''.join(sentence.split()[2:])
                        else:
                            value = ''
                    else:
                        tid, title, value, start = text_analyse_5(sentence)
                    
                    tid_y, np_tid, if_tid = fill_value(tid,title,value,i,data_pdf)
                    

                else:                  # 正文和没有明显标识的标题  这两种情况

                    if start:
                        value_tmp = sentence.split()

                        if len(value_tmp) > 1 and all(re.fullmatch(r"[\u4e00-\u9fa50-9.%]{1,}",s) for s in value_tmp) and all(len(s) < 11 for s in value_tmp):
                            ## 对应表格的情况
                            value_value[tid] += sentence
                        elif re.match('第[0-9]+类：',sentence) and NO_NUMBER_TITLE_FLAG:
                            # 针对大标题是乱码，内部有许多种疾病的特殊处理
                            second_tid = big_tid + '.' + re.findall("第(.*)类",sentence)[0]
                            second_title = value_tmp[-1]
                            third_tid = 0
                            fill_value_only(second_tid,second_title,'')
                            


                        elif re.match("[\u4e00-\u9fa5]{1,} = ", sentence) or sentence == '入价' or re.match("[\u4e00-\u9fa5]{1,} － ", sentence):  #  该行为一个计算公式
                            value_value[tid] += sentence


                        elif re.fullmatch(r"（见[0-9.]+）",value_tmp[0]) and len(value_tmp[0]) < 11:  # 没有编号的标题的特定情况
                            title_value[tid] += value_tmp[0]
                            tid_y = data_pdf.loc[i,'y']
                            if len(value_tmp) > 1:
                                value_value[tid] += ''.join(value_tmp[1:])

                        elif re.fullmatch(r"[Ⅲ0-9\u4e00-\u9fa5/（）\(\)、：HVICU-]{1,}",value_tmp[0]) and len(value_tmp[0]) < 11:  ## 没有编号，一个标题分两行或多行写的情况
                            # 特殊情况，形式为 一、 xxx 但是是正文的情况
                            if value_tmp[0] in ['一','二','三','四','五','六','七','八','九','十','一、','二、','三、','四、','五、','六、','七、','八、','九、','十、']:
                                value_value[tid] += sentence
                                continue
                            
                            
                            
                            if any(re.fullmatch(s,value_tmp[0]) for s in closely_title): 
                                tid_y = data_pdf.loc[i,'y'] 
                                if re.match('[0-9]+[.]',value_tmp[0]):
                                    np_tid = int(value_tmp[0].split('.')[0])
                                    title = re.findall('[0-9]+[.](.*)',value_tmp[0])[0]
                                else:
                                    np_tid += 1
                                    title = value_tmp[0]
                               
                                if if_tid:
                                    tid = '.'.join(tid.split('.')[:-1]) + '.' + str(np_tid)
                                else:   
                                    tid = tid + '.' + str(np_tid)
                                    if_tid = True
                                tid_value.append(tid)
                                

                                title_value[tid] = title
                                try:
                                    value_value[tid] = value_tmp[1]
                                except:
                                    value_value[tid] = ''
                                
                            elif data_pdf.loc[i,'y'] < tid_y and data_pdf.loc[i,'y'] < 85:    ## 标题隔页了,但是必须在第一行
                                title_value[tid] += value_tmp[0]
                                tid_y = data_pdf.loc[i,'y']
                                
                            elif abs(data_pdf.loc[i,'y'] - tid_y) > 25:   ## y的距离超过25认为是两个标题
                                tid_y = data_pdf.loc[i,'y'] 
                                if re.match('[0-9]+[.]',value_tmp[0]):
                                    np_tid = int(value_tmp[0].split('.')[0])
                                    title = re.findall('[0-9]+[.](.*)',value_tmp[0])[0]
                                else:
                                    np_tid += 1
                                    title = value_tmp[0]
                                
                                if if_tid:
                                    tid = '.'.join(tid.split('.')[:-1]) + '.' + str(np_tid)
                                else:   
                                    tid = tid + '.' + str(np_tid)
                                    if_tid = True
                                
                                fill_value_only(tid=tid, title= title, value= '')
                                
                                
                            else:
                                
                                title_value[tid] += value_tmp[0]
                                tid_y = data_pdf.loc[i,'y']
                            if len(value_tmp) > 1:
                                value_value[tid] += ''.join(value_tmp[1:])
                        else:
                            if sentence.startswith('：') and sentence.endswith('：'):
                                value_value[tid] = sentence[1:] + value_value[tid]
                            else:
                                value_value[tid] += sentence
                

        # 第三种情况
        else: 

            # 形式为 第xxx章/部分 的一级标题                     
            if re.match("第.{1,3}[章部分]",sentence):
                if '...' in sentence or len(sentence.split()) > 3:
                    continue
                tid, start, title, value = text_analyse_6(sentence)
                tid_y, np_tid, if_tid = fill_value(tid,title,value,i,data_pdf)
                
                special_tid = 0 # 针对第三种情况下第xxx条 格式的二级标题的重新编号
                if_special_tid = False # 是否一直是在第xxx章下面的第xxx条 格式的标题，决定小标题是加一位还是加1



            # 形式为 1. xxxx 的次级标题， 标题编号需要处理
            elif re.match("[0-9]{1,}[ .．]+[\u4e00-\u9fa5]+",sentence) and ' ' in sentence and re.fullmatch("[\u4e00-\u9fa5（）\(\)ⅢＩ/]{1,}",sentence.split()[1]):
                
                tmp = sentence.split()   
                try:
                    title = tmp[1]
                except:
                    print('case3获取形式为1. xxxx的句子的title出错，句子为', sentence)
                    title = ''

                if len(tmp) > 2:
                    value = ''.join(tmp[2:])
                else:
                    value = ''
                try:
                    special_tid += 1
                except:
                    special_tid = 1
                    print('case3中形式为 1. xxxx 的句子提前出现了，句子为：',sentence)
                try:
                    if if_special_tid:
                        tid = '.'.join(tid.split('.')[:-1]) + '.' + str(special_tid)
                    else:   
                        tid = tid + '.' + str(special_tid)
                        if_special_tid = True
                except:
                    continue
                tid_y, np_tid, if_tid = fill_value(tid,title,value,i,data_pdf)
                
                
            # 形式为 1.1 xxxx 的次级标题， 标题编号不需要处理
            elif re.match("[0-9]{1,}[.．][0-9]+",sentence) and ' ' in sentence and re.fullmatch("[\u4e00-\u9fa5：、（）\(\)ⅢＩ/]{1,}",sentence.split()[1]):
                ### 有些标题较长，用长度来限制可能不太准确，改成上面这一行的样子

                if (data_pdf.loc[i,'x'] - left_x_boundry) > 50:          # 有个别正文也是这种格式, 但是又大量缩进，用这种判断找出这种内容
                    try:                                                 # 有时起始位置定位到了目录，可能满足if的条件，但是没有tid，所以加个try
                        value_value[tid] += sentence
                        continue 
                    except:
                        pass
                tid, title, value, start = text_analyse_5(sentence)
                tid_y, np_tid, if_tid = fill_value(tid,title,value,i,data_pdf)
                


            ## 形式为第xxx条的二级标题, 但是需要修改标题编号
            elif re.match("第.{1,3}条 ",sentence):
                if '...' in sentence or len(sentence.split()) > 3:
                    continue
                tmp = sentence.split()
                try:
                    title = tmp[1]
                except:
                    print('case3获取形式为第xxx条的句子的title出错，句子为', sentence)
                    title = ''
                if len(tmp) > 2:
                    value = ''.join(tmp[2:])
                else:
                    value = ''
                try:
                    special_tid += 1
                except:
                    special_tid = 1
                    print('case3中形式为 1. xxxx 的句子提前出现了，句子为：',sentence)
                try:
                    if if_special_tid:
                        tid = '.'.join(tid.split('.')[:-1]) + '.' + str(special_tid)
                    else:   
                        tid = tid + '.' + str(special_tid)
                        if_special_tid = True
                except:
                    continue
                tid_y, np_tid, if_tid = fill_value(tid,title,value,i,data_pdf)
                

            ## 形式为 一、xxx 格式的三级标题， 例如  一、住院津贴医疗保险责任
            elif re.fullmatch("[\u4e00-\u9fa5]{1,2}、[ ]?[\u4e00-\u9fa5]+",sentence):

                

                tid, title, value = text_analyse_4(sentence,tid)
                tid_y, np_tid, if_tid = fill_value(tid,title,value,i,data_pdf)
                
               
            ## 形式为 （一） xxx格式的四级标题
            elif re.fullmatch("\([\u4e00-\u9fa5]{1,2}\) [\u4e00-\u9fa5]+",sentence) and len(sentence) < 15:
                # 有些缩进明显的并不适合作为标题
                if data_pdf.loc[i,'x'] - most_common_x < -15:

                    tid, title, value = text_analyse_7(sentence,tid)
                    tid_y, np_tid, if_tid = fill_value(tid,title,value,i,data_pdf)
                    
                else:
                    try:
                        value_value[tid] += sentence           ## 有些保险一开始也满足这个条件，但是这时还没有tid
                    except:
                        pass

            
              
            else:                  # 正文和没有明显标识的标题  这两种情况

                if start:
                    value_tmp = sentence.split()
                    if len(value_tmp) > 1 and all(re.fullmatch(r"[\u4e00-\u9fa50-9.%]{1,}",s) for s in value_tmp) and all(len(s) < 11 for s in value_tmp):
                        ## 对应表格的情况
                        value_value[tid] += sentence
                    elif re.match("[\u4e00-\u9fa5]{1,} = ", sentence) or sentence == '入价' or re.match("[\u4e00-\u9fa5]{1,} － ", sentence):  #  该行为一个计算公式
                        value_value[tid] += sentence

                    elif re.fullmatch(r"（见[0-9.]+）",value_tmp[0]) and len(value_tmp[0]) < 11:  # 没有编号的标题的特定情况
                        title_value[tid] += value_tmp[0]
                        tid_y = data_pdf.loc[i,'y']
                        if len(value_tmp) > 1:
                            value_value[tid] += ''.join(value_tmp[1:])

                    elif re.fullmatch(r"[\u4e00-\u9fa5/（）、]{1,}",value_tmp[0]) and len(value_tmp[0]) < 11:  ## 一个标题分两行或多行写的情况
                        # 特殊情况，形式为 一、 xxx 但是是正文的情况
                        if value_tmp[0] in ['一','二','三','四','五','六','七','八','九','十','十一','十二','十三','十四','一、','二、','三、','四、','五、','六、','七、','八、','九、','十、','十一、','十二、','十三、','十四、']:
                            value_value[tid] += sentence
                            continue
                        if abs(data_pdf.loc[i,'y'] - tid_y) > 25:   ## y的距离超过25认为是两个标题
                            tid_y = data_pdf.loc[i,'y'] 
                            np_tid += 1
                            if if_tid:

                                tid = '.'.join(tid.split('.')[:-1]) + '.' + str(np_tid)
                            else:   
                                tid = tid + '.' + str(np_tid)
                                if_tid = True
                            fill_value_only(tid=tid, title= value_tmp[0], value= '')
                            
                        else:
                            title_value[tid] += value_tmp[0]
                            tid_y = data_pdf.loc[i,'y']
                        if len(value_tmp) > 1:
                            value_value[tid] += ''.join(value_tmp[1:])
                    else:
                        if sentence.startswith('：') and sentence.endswith('：'):
                            value_value[tid] = sentence[1:] + value_value[tid]
                        else:
                            value_value[tid] += sentence
                
        
    new_tid_value = list(set(tid_value))
    new_tid_value.sort(key=tid_value.index)
    for item in new_tid_value:
        file_value['annotation'].append({'tid':item,'title':title_value[item],'value':value_value[item].strip()})

    return file_value
if __name__ == '__main__':
    ## 最终代码
    import traceback
    result = []
    for baoxian in os.listdir('/tcdata/test2'):
        print('folder name: ', baoxian)
        try:
            
            for txt in os.listdir('/tcdata/test2/' + baoxian): 
                if txt.endswith('txt'):
                    with open('/tcdata/test2/' + baoxian + '/' + txt) as f:
                        file = f.readlines()
                    data1 = get_data1(file)
                    data_pdf = get_pdf(data1)
                    

                    left_x_boundry = min(data_pdf['x'])
                    most_common_x = Counter(data_pdf.x).most_common()[0][0]

                    file_value = get_details(data_pdf,left_x_boundry,most_common_x)
                    result.append(file_value)
                    
                    
        except Exception as e:
            print('Error found : ', e)
            # traceback.print_exc()
            continue

    with open('/tcdata/result.json','w') as w:
        json.dump(result,w)






