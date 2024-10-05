import os, hashlib
import sqlite3, json
import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta

# local module
import _difflines as df    # type: ignore
import _aichat as aichat   # type: ignore

#current_directory = os.getcwd()
#st.write(current_directory)
DB_FILE = "diff3.db"


# global environment store into st.session_state
# set a easy way to access
class Env():
    def __init__(self):
        pass

    def __getattr__(self, key):
        if key not in st.session_state:
            raise AttributeError(f"Invalid access to st.session_state, key = {key}")
        else:
            return st.session_state[key]

    def __setattr__(self, key, value):
        st.session_state[key] = value

    def __getitem__(self, key):
        if key not in st.session_state:
            raise AttributeError(f"Invalid access to st.session_state, key = {key}")
        else:
            return st.session_state[key]

    def __setitem__(self, key, value):
        st.session_state[key] = value

    def __len__(self, key):
        return len(st.session_state[key])

    def has(self, key):
        if key not in st.session_state:
            return False
        else:
            return True

env = Env()

if not env.has("working_step"):
    env.working_step = 0   # 0 prepare, 1 revice, 2 finish revice, ony refined text editable
if not env.has("is_file_ready"):
    env.is_file_ready = False

if not env.has("is_workspace_ready"):
    env.is_workspace_ready = False
if not env.has("is_changed"):
    env.is_changed = False
if not env.has("refined_text"):      # !! refined_text bind with refined_area
    env.refined_text = ""
if not env.has("inline"):
    env.inline = False  # inline working data
if not env.has("op_inline"):
    env.op_inline = []  # inline op list
if not env.has("pos_inline"):
    env.pos_inline = 0  # inline position
if not env.has("workspace_id"):
    env.workspace_id = None
if not env.has("refined_text_changed_only"):
    env.refined_text_changed_only = False
if not env.has("last_save_time"):
    env.last_save_time = None


#CRLF更换为\n\n；单\n也优化为\n\n，支持st.write换行
def format_crlf(s:str) -> str:
    s = s.replace(" ","")
    s = s.replace("\r\n","\n")
    s = s.replace("\n","\n\n")
    s = s.replace("\n\n\n\n","\n\n")
    return s

def hint(msg:str):
    hint_area.empty()
    hint_area.warning(msg)

# 应用标题
col1, col2 = st.columns(2)
header = col1.markdown("**选择文本文档（不要Word哦）**")
last_save_time = col2.empty()

def show_last_save(t):
    last_save_time.write(f"最后保存时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(t))}")

#side bar for debug message output and other
with st.sidebar:
    st.subheader("帮助信息：")
    st.markdown("""
             - 只支持文本文件的比较
             - 系统每分钟自动保存，不必担心内容丢失
             - 保存以段落为单位，段落校对完成才会被保存
             - 每次加载同样的文件会可以继续之前的工作
             - 你上传的文件将被保留在服务器端，请不要上传你认为需要保密的文件
             - 我们不保证你的文件会永久保留，超过一段时间未访问的文件可能会被清除
             """)

# place for file uploader
file_area = st.empty()
fe = file_area.container()
f_area1  = fe.container(border = True)

# hint area
hint_container = st.container(border = True)  # for hint message
hint_area = hint_container.empty()            # create hint area
if env.working_step == 0:
    if not env.is_file_ready:
        hint("开始吧，请先选择需要校对的文档...")  # will  when first time run
    else:
        hint("文件准备好了...")  # will  when first time run
        

### read data from files
#
if not env.has("filename1"):
    env.filename1 = ""
if not env.has("filesize1"):
    env.filesize1 = 0
if not env.has("filesize2"):
    env.filensize2 = 0
if not env.has("f1_md5"):
    env.f1_md5 = None
if not env.has("f2_md5"):
    env.f2_md5 = None
if not env.has("f1_md5_hex"):
    env.f1_md5_hex = None
if not env.has("f2_md5_hex"):
    env.f2_md5_hex = None
if not env.has("bytes1"):
    env.bytes1 = None
if not env.has("bytes2"):
    env.bytes2 = None
if not env.has("content1"):
    env.content1 = None
if not env.has("content2"):
    env.content2 = None

if not env.is_file_ready:
    file1 = f_area1.file_uploader("选择一个文档", type = ["txt"])

    # Preliminary file check
    if file1 is not None:
        if file1.type.startswith('text'):
            env.filename1= file1.name
            env.filesize1= file1.size
            env.bytes1 =  file1.read()
            env.content1 = env.bytes1.decode('utf-8')

            env.f1_md5 = hashlib.md5()
            env.f1_md5.update(env.bytes1)
            env.f1_md5_hex = env.f1_md5.hexdigest()

            f_area1.success(f"原始文件：{file1.name}: 文件大小: {file1.size} 字节，文件类型: {file1.type}")
        else:
            f_area1.warning("出错了：需要校对的应该是一个文本文件")

    if file1 is None :
        hint("请先选择需要校对的文档")
        st.stop()

    hint("文件就绪，请确认开始校对...")
    env.is_file_ready = True
#end of file reading


# show [开始人工校对] button, goto next step
if env.working_step == 0:   # prepare 
    bu = st.empty()
    if bu.button("开始人工校对"):
        bu.empty()  # we don't need the button any more
        env.working_step = 1
    else:
        st.stop()


# replace file uploader with file information
if env.working_step == 1 or env.working_step == 2:
    fe.empty()  # clear file uploader
    fe.markdown("**校对文件：**\n\n" +
                f"**文件**： {env.filename1} （{env.filesize1} 字节）")


def ai_refine_one_para(t:str, mml = "ark"):
    prompt = """
    下面内容是一个会议的录音的文字稿，内容是中医的中药学、伤寒论相关的课程。请阅读，然后根据以下指令进行文字校对：

    1 根据上下文校对可能因为语音识别错误导致的文字错误、错别字。请特别留意本文是中医相关的内容，很多词语是中医术语、中药名称、方剂名称等。
    2 请特别注意文本中包含语气词“这个”，请分析并去掉不需要的语气词“这个”。
    3 去除非必须的语气词，如“嗯”、“啊”。
    4 不做任何用词的改写和润色，如用正式词语替换口语话的文字等。
    5 不做任何句子的改写和润色。
    6 仅输出校对后的文字，不作任何其他说明。
    7 保留原文中的时间戳，不要额外加入时间戳。

    下面是需要处理的内容：

    """

    print(f"mml: {mml}")


    ai = aichat.LLM_ai(mml)
    print(vars(ai))

    def show_chunk(s):
        print(s)

    answer = ai.chat(prompt, t)

    st.write(f"{len(t)} -- {len(answer)}")
    return answer 

    # 对每个段落进行AI优化
def ai_refine_paras(paragraphs):
    refined_paragraphs = []
    length = len(paragraphs)
    for i, para in enumerate(paragraphs):
        refined_para = ai_refine_one_para(para)              # this will take long time run
        refined_paragraphs.append(refined_para)
        st.write(f"paragraph finish {i} of {length} in total")
    return refined_paragraphs

def ai_refine_article(c):
    # 将内容拆分为段落
    MAX_AI_PARA_LEN = 2000  # max length pass to AI
    def split_into_paragraphs(content, max_chars=MAX_AI_PARA_LEN):
        paragraphs = []
        current_paragraph = ""
        
        for line in content.split('\n'):
            if len(current_paragraph) + len(line) > max_chars:
                paragraphs.append(current_paragraph.strip())
                current_paragraph = line + "\n"
            else:
                current_paragraph += line + "\n"
        
        if current_paragraph:
            paragraphs.append(current_paragraph.strip())
        
        return paragraphs

    ps = split_into_paragraphs(c)
    ps2 = ai_refine_paras(ps)

    c2 = "".join(ps2)
    return c2  # content refined

### setup new workspace or restore workspace data from db
if not env.is_workspace_ready:
    # 连接到数据库
    conn = sqlite3.connect(DB_FILE)
    if conn is None:
        print("error")
        exit
    cursor = conn.cursor()

    # 创建 files 表（如果不存在）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            filesize INTEGER NOT NULL,
            content TEXT NOT NULL,
            md5 TEXT NOT NULL
        )
    ''')
    # 检查文件1的MD5是否已存在
    cursor.execute('SELECT * FROM files WHERE md5 = ?', (env.f1_md5_hex,))
    if cursor.fetchone() is None:
        # 如果MD5不存在，则插入文件1的信息
        cursor.execute('''
            INSERT INTO files (filename, filesize, content, md5)
            VALUES (?, ?, ?, ?)
        ''', (env.filename1, env.filesize1, env.content1, env.f1_md5_hex))

    # 创建 workspace 表（如果不存在）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workspace (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename1 TEXT NOT NULL,
            f1MD5 TEXT NOT NULL,
            text_refined TEXT,
            last_save_time INTEGER
        )
    ''')

    # 创建 op_list 表（如果不存在）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS op_list (
            workspace_id INTEGER,
            op TEXT,
            line TEXT,
            inline_ops TEXT,
            FOREIGN KEY (workspace_id) REFERENCES workspace (id)
        )
    ''')


    # 检查workspace中是否有包含前面两个MD5的项
    cursor.execute('''
        SELECT id, filename1, text_refined, last_save_time FROM workspace
        WHERE (f1MD5 = ? ) 
    ''', (env.f1_md5_hex,))

    existing_workspace = cursor.fetchone()

    # setup work space
    #
    if existing_workspace is None:

        env.last_save_time = time.time()

        # new work space
        r = cursor.execute('''
            INSERT INTO workspace (filename1, f1MD5, text_refined, last_save_time)
            VALUES (?, ?, ?, ?)
        ''', (env.filename1, env.f1_md5_hex, "", env.last_save_time))
        
        if r.rowcount <= 0:
            raise RuntimeError("Error operate database")

        env.workspace_id = cursor.lastrowid

        env.content1 = format_crlf(env.content1)
        hint("AI文件处理中，需要等待一段时间...")
        env.content2 = ai_refine_article(env.content1)     ### use AI to refine, take long time

        aa = env.content1.split("\n")
        bb = env.content2.split("\n")

        # 务必去掉空行
        aa = [s for s in aa if s.strip()]
        bb = [s for s in bb if s.strip()]

        diff_ab = df.diff_lines(aa, bb)
        op_list = df.combine_changed_lines(aa, bb, diff_ab)

        # 将op_list内容插入到数据库op_list表中
        for item in op_list:
            j_op = json.dumps(item[2])    # dump to json format save to db
            cursor.execute('''
                INSERT INTO op_list (workspace_id, op, line, inline_ops)
                VALUES (?, ?, ?, ?)
            ''', (env.workspace_id, item[0], item[1], j_op))

        st.session_state.refined_text = ""
        st.session_state.op_list = op_list

        hint(f"已建立新的工作环境：{env['filename1']}")
    else:
        # 如果找到匹配的workspace，恢复原来的工作环境
        env.workspace_id, env.filename1, refined_text, env.last_save_time = existing_workspace
        
        # 从op_list表中恢复op_list数据
        cursor.execute('''
            SELECT op, line, inline_ops FROM op_list
            WHERE workspace_id = ?
            ORDER BY rowid
        ''', (env.workspace_id,))
        
        op_list = []
        for row in cursor.fetchall():
            op, line, j_op = row
            s_op = json.loads(j_op)
            op_list.append([op, line, s_op])

        st.session_state.op_list = op_list
        st.session_state.refined_text = refined_text

        hint(f"已恢复工作环境：{env.filename1}\
             最后保存时间{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(env.last_save_time))}")

    # 提交更改并关闭连接
    conn.commit()
    conn.close()

    st.session_state.is_workspace_ready = True
# end restore workspace from db


# auto save workspace every 60 seconds
AUTO_SAVE_INTERVAL = 60
@st.fragment(run_every = AUTO_SAVE_INTERVAL)
def save_workspace():
    print(f"inside save workspace: working_step={env["working_step"]} : changed={st.session_state.is_changed}")
    if env["working_step"] == 0:
        return
        
    if not st.session_state.is_changed:
        return
    
    # 连接到数据库
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    if not env["refined_text_changed_only"]:
        # delete old op_list in db, insert new
        cursor.execute('''
            DELETE FROM op_list
            WHERE workspace_id = ?
        ''', (env["workspace_id"],))

        for item in op_list:
            j_op = json.dumps(item[2])    # dump to json format save to db
            cursor.execute('''
                INSERT INTO op_list (workspace_id, op, line, inline_ops)
                VALUES (?, ?, ?, ?)
            ''', (env["workspace_id"], item[0], item[1], j_op))

    # update refined_text to db
    env["last_save_time"] = time.time()
    cursor.execute('''
        UPDATE workspace
        SET text_refined = ?, last_save_time = ?
        WHERE id = ?
    ''', (st.session_state.refined_text, env["last_save_time"], env["workspace_id"]))
    
    # 提交更改
    conn.commit()
    conn.close()
    
    show_last_save(env["last_save_time"])
    st.session_state.is_changed = False
    env["refined_text_changed_only"] = False
#end of save_workspace
save_workspace()  # active auto save

# constructe working area, restore from session_state

op_list = st.session_state.op_list      # recove op_list from session

op_num = len(op_list)
if op_num == 0:         # empty
    hint("好像是一个空文件哦。")
    st.stop()

pos = 0
while pos < op_num:
    if op_list[pos][0] == "e":
        pos += 1
    else:
        break
if pos == op_num: # touch the end, the file processed
    env["working_step"] = 2  # revice finish, only refined-text editable
    hint("文件已经完成校对。")

# recove working data
inline = st.session_state.inline            # inline working or not
op_inline = st.session_state.op_inline      # inline op list
pos_inline = st.session_state.pos_inline    # inline position

refined_text = st.session_state.refined_text
op_list = st.session_state.op_list

### start to layout and process confirm activate
###

# user changed the text, update to refined_text
def ref_edited():
    global refined_text
    refined_text = st.session_state.refined_text
    st.session_state.is_changed = True
    env["refined_text_changed_only"] = True

# construction refined_text area
rac = st.container(height = 300, border = True)    # refined_text area
rae = rac.empty()
rae.text_area(label = "**已确认校对的文字：**", height = 240, key = "refined_text", on_change = ref_edited)

# update to text_area, called as refined-text changed cause "accept" or "reject"
def refresh_refined_textarea():
    st.session_state.refined_text = refined_text
    rae.empty()
    rae.text_area(label = "**已确认校对的文字：**", height = 240, key = "refined_text", on_change = ref_edited)

@st.fragment
def show_revice_button():    # accept and reject button
    if env["working_step"] == 0:    #do not show the button when prepare
        return   

    col1, col2 = st.columns(2)
    if env["working_step"] == 1:
        col1.button("确认修改", on_click = on_accept)
        col2.button("拒绝修改", on_click = on_reject)
    elif env["working_step"] == 2:
        col1.button("确认修改", on_click = on_accept, disabled=True)
        col2.button("拒绝修改", on_click = on_reject, disabled=True)
    else:
        raise RuntimeError(f"working_step={env["working_step"]}")  # should never be here


def on_accept():
    global pos, op_list, inline, op_inline, pos_inline, refined_text

    if env["working_step"] != 1:  # not revice
        raise RuntimeError(f"working_step={env["working_step"]}")  # should never be here

    if not inline:
        if op_list[pos][0] == "e":
            refined_text = refined_text + op_list[pos][1] + "\n"
            pos += 1
        elif op_list[pos][0] == "d":
            del op_list[pos]
        elif op_list[pos][0] == "i":
            op_list[pos][0] = "e"
            refined_text = refined_text + op_list[pos][1] + "\n"
            pos += 1
        elif op_list[pos][0] == "s":
            inline = True
            op_inline = op_list[pos][2]
            pos_inline = 0
            while op_inline[pos_inline][0] == "e":  # skip to first non-"e" elment
                pos_inline += 1
    if inline:
        if op_inline[pos_inline][0] == "e":
            pos_inline += 1
        elif op_inline[pos_inline][0] == "d":
            del op_inline[pos_inline]
        elif op_inline[pos_inline][0] == "i":
            op_inline[pos_inline][0] = "e"
            pos_inline += 1
        else:
            raise RuntimeError
        
        while pos_inline < len(op_inline) and op_inline[pos_inline][0] == "e":  # skip "e" following，hilight next d/i
            pos_inline += 1
        
        # 完成本行确认
        if pos_inline >= len(op_inline):
            op_list[pos][0] = "e"
            a = [row[1] for row in op_inline]
            op_list[pos][1] = "".join(a)
            inline = False
            #pos += 1
    st.session_state.is_changed = True

    # end of the list
    if pos == len(op_list):
        save_workspace()  # all finished, save
        env["working_step"] = 2   # only refined-text area editable

    # refresh
    refresh_refined_textarea()
    refresh_working()
    #end of button clicked

def on_reject():
    global pos, op_list, inline, op_inline, pos_inline, refined_text

    if env["working_step"] != 1:  # not revice
        raise RuntimeError(f"working_step={env["working_step"]}")  # should never be here

    if not inline:
        if op_list[pos][0] == "e":
            refined_text = refined_text + op_list[pos][1] + "\n"
            pos += 1
        elif op_list[pos][0] == "d":  # reject delete
            op_list[pos][0] = "e"
            refined_text = refined_text + op_list[pos][1] + "\n"
            pos += 1
        elif op_list[pos][0] == "i":
            del op_list[pos]
        elif op_list[pos][0] == "s":
            inline = True
            op_inline = op_list[pos][2]
            pos_inline = 0
            while op_inline[pos_inline][0] == "e":  # skip to first non-"e" elment
                pos_inline += 1
    if inline:
        if op_inline[pos_inline][0] == "e":
            pos_inline += 1
        elif op_inline[pos_inline][0] == "d":
            op_inline[pos_inline][0] = "e"
            pos_inline += 1
        elif op_inline[pos_inline][0] == "i":
            del op_inline[pos_inline]
        else:
            raise RuntimeError
        
        while pos_inline < len(op_inline) and op_inline[pos_inline][0] == "e":  # skip "e" following，hilight next d/i
            pos_inline += 1
        
        # 完成本行确认
        if pos_inline >= len(op_inline):
            op_list[pos][0] = "e"
            a = [row[1] for row in op_inline]
            op_list[pos][1] = "".join(a)
            inline = False
            #pos += 1
    st.session_state.is_changed = True

    # end of the list
    if pos == len(op_list):
        save_workspace()  # all finished, save
        env["working_step"] = 2   # only refined-text area editable

    # refresh
    refresh_refined_textarea()
    refresh_working()
    #end of button clicked
    #     pass  # not finish yet

# layout 2 buttons
show_revice_button()

# lay out text tobe confirm(working area)
wac = st.container(border = True)    # working area
wac.markdown("**正在校对的内容：**")
wa = wac.empty()
def refresh_working():
    if env["working_step"] == 0:
        return

    MAX_LINE_SHOW = 20
    s = ""
    if env["working_step"] == 1:
        maxitem = min(pos+MAX_LINE_SHOW, len(op_list))
        work_items = op_list[pos: maxitem]
            
        i = 0
        for l in work_items:  # layout delete and insert
            s = s + df.change_oneline_to_html(l, i == 0)
            s = s + "<br/>"
            i += 1
    elif env["working_step"] == 2:
        s = "恭喜，这里的内容已经都校对完了"
    else:
        raise RuntimeError(f"working_step={env["working_step"]}")  # should never be here
    
    wa.empty()
    wa.html(s)

refresh_working()
