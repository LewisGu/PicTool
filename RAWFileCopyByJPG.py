from PySide2.QtWidgets import QApplication,QMainWindow,QPushButton,QPlainTextEdit,QMessageBox
import os,shutil
from tqdm import tqdm

rawformatlist = [".RAF",".NEF"]

class Pic():
    def __init__(self):
        self.windows = QMainWindow()
        self.windows.resize(450, 300)
        self.windows.setWindowTitle("特定RAW照片复制")
        self.setup_ui()
        self.get_cur_dir()
        self.set_connect()

    def setup_ui(self):
        #设置ui界面的建立
        self.text = QPlainTextEdit(self.windows)
        self.text.setPlaceholderText("请输入源路径")
        self.text.resize(450, 100)
        self.button = QPushButton(self.windows)
        self.button.resize(100, 100)
        self.button.move(150, 150)
        self.button.setText("一键复制")

    def get_cur_dir(self):
        self.curdir = os.getcwd()

    def set_connect(self):
        #设置建立联系
        self.button.clicked.connect(self.one_key_copy)

    def get_jpgfiles_from_oridir(self):
        # 获取当前路径下所有JPG文件的列表
        dirs = os.listdir(self.curdir)
        full_pic_list = []
        for file_name in dirs:
            endname = os.path.splitext(file_name)[1]
            if endname == '.jpg':
                full_pic_list.append(file_name)
            if endname == '.JPG':
                full_pic_list.append(file_name)
        self.jpgfileslist = full_pic_list

    def check_file_exist(self,filename):
        return os.access(filename, os.F_OK) # 文件存在，返回True,否则返回False
    
    def copy_file(self,curdir,oridir,numbername):
        # 目标
        dstfile1 = curdir + "\\" + numbername + rawformatlist[0]
        dstfile2 = curdir + "\\" + numbername + rawformatlist[1]
        srcfile1 = oridir + "\\" + numbername + rawformatlist[0]
        srcfile2 = oridir + "\\" + numbername + rawformatlist[1]
        if self.check_file_exist(srcfile1):
            shutil.copy(srcfile1, dstfile1)          # 复制文件
        elif self.check_file_exist(srcfile2):
            shutil.copy(srcfile2, dstfile2)          # 复制文件

    # def mycopyfile(srcfile,dstfile):
        # if not os.path.isfile(srcfile):
        #     print "%s not exist!"%(srcfile)
        # else:
        #     fpath,fname=os.path.split(dstfile)    #分离文件名和路径
        #     if not os.path.exists(fpath):
        #         os.makedirs(fpath)                #创建路径
        #     shutil.copyfile(srcfile,dstfile)      #复制文件
        #     print "copy %s -> %s"%( srcfile,dstfile)

    def copy_raw_file(self):
        for i in tqdm(range(len(self.jpgfileslist))):
            jpgname = self.jpgfileslist[i]
        # for jpgname in self.jpgfileslist:
            numbername = os.path.splitext(jpgname)[0]
            self.copy_file(self.curdir,self.oridir,numbername)
            # print

    def one_key_copy(self):
        # 一键复制
        self.oridir = self.text.toPlainText()
        MessageBox = QMessageBox(self.windows)
        if not self.oridir:
            MessageBox.critical(self.windows, "错误", "请输入源地址")
            return
        self.get_jpgfiles_from_oridir()
        self.copy_raw_file()
        print("Finish!")
  
if __name__ == '__main__':
    app = QApplication()
    pic=Pic()
    pic.windows.show()
    app.exec_()
