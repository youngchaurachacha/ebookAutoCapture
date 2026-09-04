#from pywinauto.keyboard import send_keys
from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
import pyautogui
import mss
import mss.tools
import time
from datetime import datetime
import json
import os
import keyboard
import re
import ctypes

try:
    # 윈도우 배율(DPI) 설정을 무시하고 시스템 전체 기준으로 1:1 좌표를 맞춤 (듀얼 모니터 오류 방지)
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


class ebookToPDF:

    def __init__(self, root):

        #좌측 상단, 우측 하단 좌표를 저장하는 변수들
        self.x1 = 0
        self.y1 = 0
        self.x2 = 0
        self.y2 = 0

        #좌표를 UI에 표시해주는 변수들
        self.posDisplay1 = StringVar()
        self.posDisplay2 = StringVar()
        self.posDisplay1.set("0, 0")
        self.posDisplay2.set("0, 0")

        self.pages = IntVar()#캡쳐 페이지 수

        self.name = StringVar()#파일 이름

        self.dirPath = StringVar()#파일 저장 경로

        self.captureSpeed = IntVar()#캡쳐 간격
        self.captureSpeed.set(200)

        self.moveToNextPageOption = IntVar()#다음 페이지 이동 옵션(0: 키보드 오른쪽 방향키, 1: 마우스 좌클릭)

        self.progress = DoubleVar()#진행율 
        self.progress.set(0.0)

        root.title("eBookAutoCapture")
        root.geometry("")#이렇게 해야 내부 위젯들 사이즈에 맞게 창의 크기가 자동으로 조절됨. https://stackoverflow.com/questions/50955987/auto-resize-tkinter-window-to-fit-all-widgets
        root.resizable(width=False, height=False)      

        contents = ttk.Frame(root, padding="3 3 3 3")
        contents.grid(column=0, row=0, sticky=(N, W, E, S))
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        ttk.Label(contents, text="madeBy p0tat0-113", ).grid(column=1, row=1, columnspan=3, sticky=W)
        ttk.Label(contents, text="설정 버튼을 누른 후 space키를 눌러야 좌표가 기입됨").grid(column=1, row=2, columnspan=3, sticky=W)

        ttk.Label(contents, text="좌측 상단 좌표", ).grid(column=1, row=3, sticky=W)
        ttk.Label(contents, text="우측 하단 좌표", ).grid(column=1, row=4, sticky=W)
        ttk.Entry(contents, textvariable=self.posDisplay1, width=12).grid(column=2, row=3, sticky=(W, E))
        ttk.Entry(contents, textvariable=self.posDisplay2, width=12).grid(column=2, row=4, sticky=(W, E))
        ttk.Button(contents, text="좌표 설정", command=self.callGetPointerPosLeft).grid(column=3, row=3, sticky=(W, E))
        ttk.Button(contents, text="좌표 설정", command=self.callGetPointerPosRight).grid(column=3, row=4, sticky=(W, E))

        ttk.Label(contents, text="총 페이지 수").grid(column=1, row=5, sticky=W)
        ttk.Label(contents, text="파일 이름").grid(column=1, row=6, sticky=W)
        ttk.Entry(contents, width=10, textvariable=self.pages).grid(column=3, row=5, sticky=(W, E))
        ttk.Entry(contents, width=10, textvariable=self.name).grid(column=3, row=6, sticky=(W, E))

        ttk.Label(contents, text="캡쳐 간격(ms)").grid(column=1, row=7, sticky=W)
        ttk.Label(contents, textvariable=self.captureSpeed,width=3).grid(column=2, row=7, sticky=(W, E))
        ttk.Scale(contents, orient=HORIZONTAL, length=100, from_=1, to=1000, variable=self.captureSpeed, command=self.floatToInt).grid(column=3, row=7, sticky=(W,E))

        ttk.Label(contents, text="다음 페이지 이동").grid(column=1, row=8, sticky=W)
        ttk.Radiobutton(contents, text="키보드 방향키", variable=self.moveToNextPageOption, value=0).grid(column=2, row=8, sticky=W)
        ttk.Radiobutton(contents, text="마우스 클릭", variable=self.moveToNextPageOption, value=1).grid(column=3, row=8, sticky=W)

        ttk.Progressbar(contents, orient=HORIZONTAL,length=30, mode='determinate', maximum = 10000, variable=self.progress).grid(column=1, row=9, columnspan=3, sticky=(W,E))

        self.start_btn = ttk.Button(contents, text="작업 시작 (단축키: ])", command=self.toggle_capture)
        self.start_btn.grid(column=1, row=10,columnspan=3, sticky=(W,E))
        ttk.Button(contents, text="저장 경로 설정", command=self.getDirPath).grid(column=1, row=11,columnspan=3, sticky=(W,E))
        ttk.Label(contents, text="경로", textvariable=self.dirPath, width=51).grid(column=1, row=12,columnspan=3, sticky=W)

        for child in contents.winfo_children(): 
            child.grid_configure(padx=5, pady=5)
            
        self.is_running = False
        self.capture_instance = None
        self.load_settings()
        
        try:
            keyboard.add_hotkey(']', lambda: root.after(0, self.toggle_capture))
        except Exception as e:
            print(f"단축키 설정 실패: {e}")

    def load_settings(self):
        if os.path.exists("settings.json"):
            try:
                with open("settings.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.x1 = data.get("x1", 0)
                    self.y1 = data.get("y1", 0)
                    self.x2 = data.get("x2", 0)
                    self.y2 = data.get("y2", 0)
                    self.posDisplay1.set(f"{self.x1}, {self.y1}")
                    self.posDisplay2.set(f"{self.x2}, {self.y2}")
                    self.pages.set(data.get("pages", 0))
                    self.name.set(data.get("name", ""))
                    self.dirPath.set(data.get("dirPath", ""))
            except Exception:
                pass

    def save_settings(self):
        try:
            data = {
                "x1": self.x1, "y1": self.y1,
                "x2": self.x2, "y2": self.y2,
                "pages": self.pages.get(),
                "name": self.name.get(),
                "dirPath": self.dirPath.get()
            }
            with open("settings.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception:
            pass

    def toggle_capture(self, *args):
        if self.is_running:
            self.is_running = False
            if self.capture_instance:
                self.capture_instance.stop()
            self.start_btn.config(text="작업 시작 (단축키: ])")
        else:
            self.captureCall()
    
    def floatToInt(self, *args):#Scale바를 통해서 입력되는 값의 소숫점을 제거함.
        self.captureSpeed.set(round(self.captureSpeed.get(),0))

    def callGetPointerPosLeft(self,*args): #Tkinter를 통해서 호출되는 메서드는 매개변수로 반드시 *args를 가지고 있어야 함.
        print("callGetPointerPosLeft")
        root.bind("<Key-space>", lambda event: self.getPointerPos(event,1))#바인드된 함수에 인자를 넘기려면 이렇게 lambda로 우회적으로 넘겨야 함.
        root.focus_set()  # root로 포커스 강제 이동, 스페이스바를 눌렀을 때 버튼이 계속 눌리던 문제를 해결

    def callGetPointerPosRight(self,*args):
        print("callGetPointerPosRight")
        root.bind("<Key-space>", lambda event: self.getPointerPos(event,2))
        root.focus_set()  # root로 포커스 강제 이동

    def getPointerPos(self,event,position):
        posx,posy = pyautogui.position()
        if(position == 1):
            self.x1 = posx
            self.y1 = posy
            self.posDisplay1.set(f"{posx}, {posy}")
        if(position == 2):
            self.x2 = posx
            self.y2 = posy
            self.posDisplay2.set(f"{posx}, {posy}")
        #root.unbind("<Key-space>") 스페이스바를 여러번 눌러서 좌표를 수정할 수 있게함.

    def getDirPath(self, *args):
        self.dirPath.set(filedialog.askdirectory())
        print(self.dirPath.get())

    def parse_pos(self, pos_str):
        nums = re.findall(r'-?\d+', pos_str)
        if len(nums) >= 2:
            return int(nums[0]), int(nums[1])
        return None, None

    def captureCall(self, *args):
        x1, y1 = self.parse_pos(self.posDisplay1.get())
        x2, y2 = self.parse_pos(self.posDisplay2.get())
        if x1 is None or y1 is None or x2 is None or y2 is None:
            messagebox.showerror("좌표 오류", "좌표 형식이 올바르지 않습니다. 'x, y' 형태로 숫자를 입력해주세요.")
            return
        
        self.x1, self.y1, self.x2, self.y2 = x1, y1, x2, y2

        try:
            pages_val = self.pages.get()
            if pages_val <= 0:
                messagebox.showerror("입력 오류", "총 페이지 수는 1 이상이어야 합니다.")
                return
        except Exception:
            messagebox.showerror("입력 오류", "총 페이지 수를 올바른 숫자로 입력해주세요.")
            return

        if self.x2 - self.x1 <= 0 or self.y2 - self.y1 <= 0:
            messagebox.showerror("좌표 오류", "좌표가 올바르지 않습니다. 좌측 상단과 우측 하단을 순서대로 정확히 설정해주세요.")
            return

        if not self.dirPath.get():
            messagebox.showerror("경로 오류", "저장 경로를 설정해주세요.")
            return

        self.save_settings()
        self.is_running = True
        self.start_btn.config(text="작업 중지 (단축키: ])")

        self.capture_instance = Capture(self)
        self.capture_instance\
            .setRoot(root)\
            .setRegion(self.x1,self.y1,self.x2,self.y2)\
            .setPages(self.pages.get())\
            .setName(self.name.get())\
            .setDirpath(self.dirPath.get())\
            .setCaptureSpeed(self.captureSpeed.get())\
            .setProgres(self.progress)\
            .setMoveToNextPage(self.moveToNextPageOption.get())

        self.capture_instance.find_last_count()
        root.after(2000, self.capture_instance.process)

class Capture:
    def __init__(self, parent):
        self.parent = parent
        self.root = None
        self.region = None
        self.pages = None
        self.name = None
        self.dirpath = None
        self.captureSpeed = None
        self.progress = None
        self.moveToNextPage = None
        self.count = 1
        self.file_index = 1
        self.is_stopped = False

    def find_last_count(self):
        name_str = self.name if self.name else "img"
        max_num = 0
        try:
            for f in os.listdir(self.dirpath):
                match = re.match(re.escape(name_str) + r'-(\d+)\.png', f)
                if match:
                    num = int(match.group(1))
                    if num > max_num:
                        max_num = num
        except Exception:
            pass
        self.file_index = max_num + 1

    def stop(self):
        self.is_stopped = True

    def setRoot(self,root):
        self.root = root
        return self
    
    def setRegion(self,x1,y1,x2,y2):
        self.region = (x1,y1,x2-x1,y2-y1)
        return self
    
    def setPages(self,pages):
        self.pages = pages
        return self
    
    def setName(self,name):
        self.name = name
        return self
    
    def setDirpath(self,dirpath):
        self.dirpath = dirpath.replace("/","\\")
        return self
    
    def setCaptureSpeed(self,captureSpeed):
        self.captureSpeed = captureSpeed
        return self
    
    def setProgres(self,progress):
        '''ValueVar타입으로 받아야 함.'''
        self.progress = progress
        progress.set(0.0)
        return self
    
    def setMoveToNextPage(self,moveToNextPageOption):
        self.moveToNextPage = self.selectMoveToNextPageOption(moveToNextPageOption)
        return self

    def process(self):
        if self.is_stopped:
            print("작업 중지됨")
            return

        try:
            self.capture()
    
            self.progress.set(self.progress.get()+(10000/self.pages))
            self.moveToNextPage()
            self.count += 1
    
            if (self.count<=self.pages) and not self.is_stopped:
                root.after(self.captureSpeed,self.process)#Tkinter가 captureSpeed만큼의 ms가 지난 후 process()를 다시 호출함.
                #tkinter는 time.sleep을 쓰는게 좋지 않다고 함. 이렇게 해야 progressbar가 지속적으로 업데이트 됨.
                #https://stackoverflow.com/questions/51298758/tkinter-updating-progressbar-when-a-function-is-called
            else:
                if not self.is_stopped:
                    print("작업 완료")
                    self.parent.is_running = False
                    self.parent.start_btn.config(text="작업 시작 (단축키: ])")
                    messagebox.showinfo("완료", "캡처 작업이 완료되었습니다!")
        except Exception as e:
            self.parent.is_running = False
            self.parent.start_btn.config(text="작업 시작 (단축키: ])")
            messagebox.showerror("오류 발생", f"캡처 중 오류가 발생했습니다:\n{str(e)}")

    def capture(self):
        name_str = self.name if self.name else "img"
        filename = f"{name_str}-{self.file_index:04d}.png"
        save_dir = str(f"{self.dirpath}\\{filename}")
        print(save_dir)

        with mss.mss() as sct:
            monitor = {"top": self.region[1], "left": self.region[0], "width": self.region[2], "height": self.region[3]}
            screenshot = sct.grab(monitor)
            mss.tools.to_png(screenshot.rgb, screenshot.size, output=save_dir)
            
        self.file_index += 1
            
    def selectMoveToNextPageOption(self,num):
        if num == 0:
            return self.moveToNextPageWithKey
        elif num   == 1:
            return self.moveToNextPageWithClick
        
    #다음페이지로 넘겨주는 함수들
    def moveToNextPageWithKey(self):
        pyautogui.press("right")
        print("키보드 딸칵")

    def moveToNextPageWithClick(self):
        pyautogui.leftClick()
        print("마우스 딸칵")


root = Tk()
ebookToPDF(root)#FeetToMeters인스턴스를 생성하는 과정에서 생성자 함수가 호출되고, root에 모든 설정을 끝냄.
root.mainloop()