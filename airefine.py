import sys
import sqlite3
import mimetypes
import time
import streamlit as st

# local package
my_package_path = 'd:\\home\\other\\py'
if my_package_path not in sys.path:
    sys.path.append(my_package_path)
from c_package import difflines as df    # type: ignore
from c_package import aichat             # type: ignore

DB_FILE = "d:\\home\\other\\py\\ai_refine.db"



# 初始化数据库
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 创建文件表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        filesize INTEGER NOT NULL,
        upload_time INTEGER NOT NULL
    )
    ''')

    # 创建段落表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS paragraphs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_id INTEGER,
        content TEXT NOT NULL,
        ai_review1 TEXT,
        ai_review2 TEXT,
        ai_review3 TEXT,
        FOREIGN KEY (file_id) REFERENCES files (id)
    )
    ''')

    conn.commit()
    conn.close()

# 将文件拆分为段落并保存
def save_file_and_paragraphs(filename, content):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 保存文件信息
    filesize = len(content)
    upload_time = time.time()
    cursor.execute('INSERT INTO files (filename, filesize, upload_time) VALUES (?, ?, ?)',
                   (filename, filesize, upload_time))
    file_id = cursor.lastrowid

    # 拆分段落并保存
    paragraphs = split_into_paragraphs(content)
    for paragraph in paragraphs:
        cursor.execute('INSERT INTO paragraphs (file_id, content) VALUES (?, ?)',
                       (file_id, paragraph))

    conn.commit()
    conn.close()

# 将内容拆分为段落
def split_into_paragraphs(content, max_chars=2000):
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

# 初始化数据库
init_db()


def upload_and_process_file():
    uploaded_file = st.file_uploader("请选择一个文件上传", type=["txt"])
    
    if uploaded_file is not None:
        # 检查文件类型
        file_type = mimetypes.guess_type(uploaded_file.name)[0]
        if file_type != 'text/plain':
            st.error("错误：请上传文本文件。")
            return

        # 读取文件内容
        content = uploaded_file.getvalue().decode("utf-8")
        filename = uploaded_file.name

        # 处理文件并保存到数据库
        paragraphs = split_into_paragraphs(content)
        save_file_and_paragraphs(filename, content)

        # 打印分段信息
        st.write(f"文件已成功处理并保存到数据库。")
        st.write(f"总共分成 {len(paragraphs)} 段")
        for i, para in enumerate(paragraphs, 1):
            lines = para.count('\n') + 1
            chars = len(para)
            st.write(f"第 {i} 段：{lines} 行，{chars} 字")
        return paragraphs
    else:
        return None
    
# 在Streamlit应用中调用此函数
paras = upload_and_process_file()
if paras is None:
    st.stop()

def refine_with_ai(t:str, mml = "ark"):
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


# paragraph include multi lines
# change p(paragraph) and r(refined-paragraph) to compare html(delete and insert) 
def diff_para_to_html(p: str, r: str):
    ps = p.split("\n")
    rs = r.split("\n")
    dif_op = df.diff_lines(ps, rs)
    lines_op = df.combine_changed_lines(ps, rs, dif_op)

    result = df.change_lines_to_html(lines_op)
    return result


    # 对每个段落进行AI优化
def refine_paras(paragraphs):

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    refined_paragraphs = []
    for i, para in enumerate(paragraphs):
        refined_para = refine_with_ai(para)              # this will take long time run
        refined_paragraphs.append(refined_para)
        st.write(f"paragraph finish {i}")

        cursor.execute('''
                UPDATE paragraphs
                SET ai_review1 = ?
                WHERE id = ?
            ''', (refined_para, i+1))
    
    conn.commit()
    conn.close()

    for i, para in enumerate(paragraphs):
        diffs = diff_para_to_html(para, refined_paragraphs[i])

        st.markdown(f"### 优化前后的差异：{i}")
        st.markdown(diffs, unsafe_allow_html=True)

refine_paras(paras)

