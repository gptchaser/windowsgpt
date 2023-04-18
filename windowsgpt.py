# 这是一个使用 OpenAI 的 GPT-3.5-turbo 模型的 Python 程序，用于创建一个命令行界面，允许用户输入命令并获得代码片段或执行代码。程序主要包括以下功能： 
# 设置和初始化环境变量、颜色和样式。
# 定义函数以打印不同类型的消息（状态、成功、错误）。
# 定义函数以清理和格式化从 GPT-3.5-turbo 模型返回的代码片段。
# 定义一个函数 LLM，用于与 GPT-3.5-turbo 模型进行交互，发送消息并获取响应。
# 定义一个函数 containerize_code，用于在一个安全的环境中执行代码片段。
# 定义一个函数 run_python，用于执行从 GPT-3.5-turbo 模型返回的代码片段，并处理可能的错误和调试。
# 定义一个函数 clear_memory，用于清除与 GPT-3.5-turbo 模型的交互历史。
# 在程序的主要部分，处理命令行参数（例如，是否显示生成的代码、是否进行调试）。
# 创建一个循环，让用户输入命令并与 GPT-3.5-turbo 模型进行交互，根据用户输入执行代码或提供代码片段。 

import tkinter as tk
from tkinter import ttk
import sv_ttk
import time
import threading
import openai
import time
from colorama import Fore, Style
import os
from cnprompts import *
from keys import *
import io
import contextlib
import pyperclip
import json

openai.api_key = OPENAI_KEY
MAX_PROMPT = 20480
CONTEXT_LEFT, CONTEXT_RIGHT = '{', '}'
engshell_PREVIX = lambda: Style.RESET_ALL + os.getcwd() + ' ' + Style.RESET_ALL + Fore.MAGENTA + "engshell" + Style.RESET_ALL + '>'
API_CALLS_PER_MIN = 50
VERBOSE = False
MAX_DEBUG_ATTEMPTS = 2
RETRY_ERRORS = ["在处理您的请求时，服务器发生了错误。非常抱歉！"]
memory = []
conversation = []
showprompt = False
run_code = True
user_prompt = ''
returned_code = ''
final_code = ''

def print_console_prompt():
    print(engshell_PREVIX(), end="")

def print_status(status):
    print_console_prompt()
    print(Style.RESET_ALL + Fore.YELLOW + status + Style.RESET_ALL)

def print_success(status):
    print_console_prompt()
    print(Style.RESET_ALL + Fore.GREEN + status + Style.RESET_ALL)

def print_err(status):
    print_console_prompt()
    print(Style.RESET_ALL + Fore.RED + status + Style.RESET_ALL)

def clean_code_string(response_content):
    lines = response_content.split("\n")
    if lines[0].startswith("!"):
        lines.pop(0)
    response_content = "\n".join(lines)

    split_response_content = response_content.split('```')
    if len(split_response_content) > 1:
        response_content = split_response_content[1]
    for code_languge in ['python', 'bash']:
        if response_content[:len(code_languge)]==code_languge: response_content = response_content[len(code_languge)+1:] # remove python+newline blocks
    return response_content.replace('`','')

def clean_install_string(response_content):
    split_response_content = response_content.split('`')
    if len(split_response_content) > 1:
        response_content = split_response_content[1]
    return response_content.replace('`','')

def LLM(prompt, mode='text'):
    global memory
    global showprompt
    time.sleep(1.0/API_CALLS_PER_MIN)
    moderation_resp = openai.Moderation.create(input=prompt)
    if moderation_resp.results[0].flagged:
        raise ValueError(f'提示({prompt})被审核端过滤')
    time.sleep(1.0/API_CALLS_PER_MIN)
    if mode == 'text':
        messages=[
            {"role": "system", "content": LLM_SYSTEM_CALIBRATION_MESSAGE},
            {"role": "user", "content": prompt},
        ]
    elif mode == 'code':
        messages=memory
    elif mode == 'debug':
        messages=[
            {"role": "system", "content": DEBUG_SYSTEM_CALIBRATION_MESSAGE},
            {"role": "user", "content": prompt},
        ]
    elif mode == 'install':
        messages=[
            {"role": "system", "content": INSTALL_SYSTEM_CALIBRATION_MESSAGE},
            {"role": "user", "content": prompt},
        ]
    response = openai.ChatCompletion.create(
      #model="gpt-4",
      model="gpt-3.5-turbo-0301",
      messages=messages,
      temperature = 0.0
    )
    response_content = response.choices[0].message.content
    if mode == 'code' or mode == 'debug': response_content = clean_code_string(response_content)
    elif mode == 'install': response_content = clean_install_string(response_content)
    return response_content

def containerize_code(code_string):
    code_string = code_string.replace('your_openai_api_key_here', OPENAI_KEY)
    # uncomment this if you wish to easily use photos from Unsplash API
    # code_string = code_string.replace('your_unsplash_access_key_here', UNSPLASH_ACCESS_KEY)
    try:
        output_buffer = io.StringIO()
        with contextlib.redirect_stdout(output_buffer):
            exec(code_string,globals())
    except Exception as e:
        error_msg = str(e)
        print((lambda: Style.RESET_ALL + Fore.RED + '收到错误消息:')(), error_msg)
        return False, error_msg
    code_printout = output_buffer.getvalue()
    return True, code_printout

def clear_memory(_):
    global memory
    global t1_Msg
    memory = [
            {"role": "system", "content": CODE_SYSTEM_CALIBRATION_MESSAGE},
            {"role": "user", "content": CODE_USER_CALIBRATION_MESSAGE},
            {"role": "assistant", "content": CODE_ASSISTANT_CALIBRATION_MESSAGE},
            {"role": "system", "content": CONSOLE_OUTPUT_CALIBRATION_MESSAGE},
    ]
    t1_Msg.delete('0.0', "end")
    t1_Msg.config(state=tk.DISABLED)
    return memory

def copy_text(event):
    event.widget.clipboard_clear()
    text = event.widget.get("sel.first", "sel.last")
    event.widget.clipboard_append(text)

def paste_text(event):
    text = event.widget.selection_get(selection='CLIPBOARD')
    event.widget.insert('insert', text)

def copy():
    global memory
    pyperclip.copy(json.dumps(memory, ensure_ascii=False))
    t1_Msg.insert("end", '已复制对话记录\n', "green")

def enter(event):
    sendMsg()

def clear():
    t1_Msg.config(state=tk.NORMAL)
    clear_th = threading.Thread(target=clear2, args=(app,))
    clear_th.start()

def clear2(master):
    master.after(0, clear_memory, '')
    

def copy_code():
    global final_code
    pyperclip.copy(final_code)
    t1_Msg.insert("end", '已复制最终代码\n', "green")

# 创建窗口
app = tk.Tk()
app.title('Windows GPT')

#
w = 890
h = 660
sw = app.winfo_screenwidth()
sh = app.winfo_screenheight()
x = 200
y = (sh - h) / 2
app.geometry("%dx%d+%d+%d" % (w, h, x, y+30))
app.resizable(0, 0)

llmonly = False
def toggle_switch():
    global llmonly
    if llmonly:
        llmonly=False
    else:
        llmonly=True
switch_btn = tk.Checkbutton(app, text='仅询问ChatGPT', command=toggle_switch)
switch_btn.place(x=370, y=2)

copy_code_btn = ttk.Button(text="复制代码", command=copy_code)
copy_code_btn.place(x=630, y=2)
copy_code_btn.config(state=tk.DISABLED)

copy_btn = ttk.Button(text="复制对话", command=copy)
copy_btn.place(x=760, y=2)
copy_btn.config(state=tk.DISABLED)

clear_btn = ttk.Button(text="清除对话", command=clear)
clear_btn.place(x=500, y=2)
clear_btn.config(state=tk.DISABLED)

# 聊天消息预览窗口
t1_Msg = tk.Text(width=113, height=32, padx=10, pady=7)
t1_Msg.tag_config('green', foreground='#008C00')  # 创建tag
t1_Msg.tag_config('blue', foreground='blue')
t1_Msg.tag_config('red', foreground='red')
t1_Msg.place(x=2, y=35)
t1_Msg.bind('<Control-c>', copy_text)
t1_Msg.config(state=tk.DISABLED)

def run_python(returned_code, debug = False):
    global t1_Msg
    print_status("编译中...")
    t1_Msg.insert("end", "编译中...\n")
    print_status("执行中...")
    t1_Msg.insert("end", "执行中...\n")
    returned_code = clean_code_string(returned_code)
    success, output = containerize_code(returned_code)
    attempts = 0
    should_debug = debug and (attempts < MAX_DEBUG_ATTEMPTS) and (not success)
    should_install = (output is not None) and ('No module named' in output)
    should_retry = should_debug or should_install or ((output is not None) and any([(err in output) for err in RETRY_ERRORS]))
    while should_retry:
        if should_install:
            print_status('安装中: ' + output)
            t1_Msg.insert("end", '安装中: ' + output.lstrip("No module named") +"\n")
            prompt = INSTALL_USER_MESSAGE(output)
            returned_command = LLM(prompt, mode='install')
            os.system(returned_command)
        elif should_debug:
            print_status('调试中: ' + output)
            t1_Msg.insert("end", '调试中: ' + output +"\n")
            prompt = DEBUG_MESSAGE(returned_code, output)
            returned_code = LLM(prompt, mode='debug')
        returned_code = clean_code_string(returned_code)
        success, output = containerize_code(returned_code)
        attempts += 1
        should_debug = debug and (attempts < MAX_DEBUG_ATTEMPTS) and (not success)
        should_retry = should_debug or any([(err in output) for err in RETRY_ERRORS])
    if not success:
        t1_Msg.insert("end", "代码执行失败, 请重新再试。\n", "red")
        sendMsg_btn.config(state=tk.NORMAL)
        clear_btn.config(state=tk.NORMAL)
        raise ValueError(f"failed ({output})")
    return output


def insert_separator(text_widget):
    text_widget.tag_config('grey', foreground='grey')
    text_widget.insert('end', '-' * 50 + '\n', 'grey')
    text_widget.tag_add('line', 'end-51c', 'end')
    text_widget.tag_config('line', underline=False)
# 发送消息
def sendMsg():
    global user_prompt
    global memory
    global debug
    global run_code
    global t1_Msg
    global llmonly
    t1_Msg.configure(state=tk.NORMAL)
    strMsg = f"""用户：{USERNAME}, 目录：{CURDIR}, """ + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + '\n'
    t1_Msg.insert("end", strMsg, 'green')
    sendMsg = t2_sendMsg.get('0.0', 'end')
    t1_Msg.insert("end", sendMsg, "blue")  
    t2_sendMsg.delete('0.0', "end")
    if (llmonly):
        t1_Msg.insert("end", " (仅询问ChatGPT)", "blue")
        sendMsg += CONGNITIVE_USER_MESSAGE
    else:
        memory = [item for item in memory if CONGNITIVE_USER_MESSAGE not in item.get("content")]
    user_prompt = USER_MESSAGE(sendMsg, current_dir = os.getcwd())
    memory.append({"role": "user", "content": user_prompt})
    conversation.append(user_prompt)
    copy_btn.config(state=tk.NORMAL)
    sendMsg_btn.config(state=tk.DISABLED)
    clear_btn.config(state=tk.NORMAL)
    run_code = True
    threading.Thread(target=Begin).start()
    
def Begin():
    global run_code
    global final_code
    final_code = ''
    copy_code_btn.config(state=tk.DISABLED)
    copy_btn.config(state=tk.DISABLED)
    t1_Msg.insert("end", "\n询问中...\n")
    ask_thread = threading.Thread(target=AskGPTAsync)
    ask_thread.start()
    ask_thread.join()
    try:
        run_thread = threading.Thread(target=RunCodeAsync, args=(app,))
        run_thread.start()
        run_thread.join() 
    except Exception as e:
        error_message = str(e)
        print(e)
        console_output = error_message
        run_code = any([err in error_message for err in RETRY_ERRORS])
def AskGPTAsync():
    global memory
    global user_prompt
    global returned_code
    returned_code = LLM(user_prompt, mode='code')
    memory.append({"role": "assistant", "content": returned_code})
    conversation.append(returned_code)
def RunCodeAsync(master):
    global returned_code
    global final_code
    console_output = run_python(returned_code, True)
    final_code = returned_code
    master.after(0, updateGUI, console_output)
def updateGUI(console_output):
    global run_code
    global t1_Msg
    global memory
    if console_output.strip() == '': console_output = '执行结束.'
    print_success(console_output)
    t1_Msg.insert("end", console_output + '\n', "green")
    insert_separator(t1_Msg)
    t1_Msg.config(state=tk.DISABLED)
    if len(console_output) < MAX_PROMPT:
        memory.append({"role": "system", "content": console_output})
        conversation.append(console_output)
    run_code = False
    copy_code_btn.config(state=tk.NORMAL)
    copy_btn.config(state=tk.NORMAL)
    sendMsg_btn.config(state=tk.NORMAL)
    clear_btn.config(state=tk.NORMAL)


# 聊天消息发送
t2_sendMsg = tk.Text(width=112, height=10)
t2_sendMsg.place(x=2, y=485)
t2_sendMsg.bind('<Control-c>', copy_text)
t2_sendMsg.bind('<Control-v>', paste_text)
t2_sendMsg.bind('<Return>', lambda event: enter(event))
 # 发送按钮
sendMsg_btn = ttk.Button(text="发送(Send)", style="Accent.TButton", command=sendMsg)
sendMsg_btn.place(x=760, y=618)
# 主事件循环
clear_memory('')
sv_ttk.set_theme("light")
app.mainloop()