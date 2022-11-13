from PySide2.QtWidgets import QApplication,QComboBox,QMainWindow,QPushButton,QLabel,QPlainTextEdit,QMessageBox
import os,shutil
from tqdm import tqdm       # 进度条包
import logging
import time
import sys
import configparser
import tkinter.filedialog

default_ini_dir = 'C:\\CopyRAWFileByJpg'
default_ini_file = 'C:\\CopyRAWFileByJpg\\config.ini'
now = time.strftime("%Y-%m-%d-%H_%M_%S",time.localtime(time.time())) 
default_log_file = 'C:\\CopyRAWFileByJpg\\'+now+'.log'
default_rawformat_dir = {'Canon':'.CR2','Fuji':'.RAF','Nikon':'.NEF','Ricoh':'.DNG','Sony':'.ARW','Pentax':'.PEF','Olympus':'ORF','Panasonic':'RW2'}


def check_file_exist(filename):
    return os.access(filename, os.F_OK)  # 文件存在，返回True,否则返回False

logging.basicConfig(level=logging.DEBUG,
                format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                datefmt='%Y-%m-%d %a %H:%M:%S',
                filename=default_log_file,
                filemode='w')

    #############################################

    # Public Function #

    #############################################

def logprint(msg):
    logging.info(msg)

def log_screen_print(msg):
    print(msg)
    logging.info(msg)

def check_dir(path):
    folder = os.path.exists(path)
    # return folder
    if not folder:  # 判断是否存在文件夹如果不存在则创建为文件夹
        return 0
    else:
        return 1

def mkdir(path):
    folder = os.path.exists(path)
    if not folder:  # 判断是否存在文件夹如果不存在则创建为文件夹
        os.makedirs(path)  # makedirs 创建文件时如果路径不存在会创建这个路径
        logprint('the folder '+path+' has created') 

class PicFileList:

    #############################################

    # Picture File Class #

    #############################################
    def __init__(self, jpgfileslist, curdir, oridir,formatname):
        self.jpgfileslist = jpgfileslist
        self.curdir = curdir
        self.oridir = oridir
        self.check_file_in_oridir()
        self.formatname = formatname

    def main_process(self):
        item_num = len(self.jpgfileslist)
        copy_success_num = 0
        copy_failed_num = 0
        with tqdm(total=item_num) as pbar:
            for i in range(item_num):
                jpgname = self.jpgfileslist[i]
                valid_result = self.one_jpg_process(jpgname)
                if valid_result == 1:
                    copy_success_num    = copy_success_num + 1
                else:
                    copy_failed_num     = copy_failed_num + 1
                pbar.update(1)
                time.sleep(0.1)
        log_screen_print("success copy "+str(copy_success_num)+" files, failed "+str(copy_failed_num)+",please check folder\\name\\format !")

    def one_jpg_process(self, jpgname):
        self.numbername = os.path.splitext(jpgname)[0]
        file_fullname = self.numbername + self.formatname
        dstfile = self.curdir + "\\" + file_fullname
        srcfile = self.oridir + "\\" + file_fullname
        if (check_file_exist(srcfile)):
            shutil.copy(srcfile, dstfile)  # 复制文件
            logprint('copy file' + file_fullname)
            return 1
        else:
            logprint(srcfile + ' not exist in the folder')
            return 0

    def check_file_in_oridir(self):
        # TODO 分析扩展名，猜测品牌，给出提示
        return

class PicApp(QMainWindow):
    
    #############################################

    # UI #

    #############################################
    
    def __init__(self):
        super(PicApp, self).__init__()
        self.resize(300, 350)
        self.setWindowTitle("RAW文件懒人复制")
        self.init()
        self.setup_ui()
        self.set_connect()

    def setup_ui(self):
        #设置ui界面
        self.curdir_label = QLabel(self)
        self.curdir_label.setText('当前工作目录')
        label_width = self.curdir_label.width()
        self.curdir_label.move(150-label_width/2, 0)

        self.workingfolder_te = QPlainTextEdit(self)
        self.workingfolder_te.setPlainText(self.working_dir)
        self.workingfolder_te.setEnabled(False)
        self.workingfolder_te.resize(250, 25)
        self.workingfolder_te.move(25, 25)
        
        self.unlockdir_btn = QPushButton(self)
        self.unlockdir_btn.setText("解锁")
        self.unlockdir_btn.resize(100, 30)
        self.unlockdir_btn.move(100, 62)

        self.source_folder_te = QPlainTextEdit(self)
        self.source_folder_te.setPlaceholderText("请输入RAW文件源路径")
        self.source_folder_te.resize(250, 50)
        self.source_folder_te.move(25, 100)
        
        self.brand_label = QLabel(self)
        self.brand_label.setText('当前适用品牌')
        brand_label_width = self.brand_label.width()
        # brand_label_height = self.brand_label.height()
        self.brand_label.move(150-brand_label_width/2, 150)

        self.brand_cbb = QComboBox(self)
        brandlist = self.brand_list_gen()
        self.brand_cbb.addItems(brandlist)        
        self.brand_cbb.resize(100, 20)
        self.brand_cbb.move(100, 175)

        self.check_log_btn = QPushButton(self)
        self.check_log_btn.setText("查看日志")
        self.check_log_btn.resize(100, 30)
        self.check_log_btn.move(100, 225)

        self.onekey_copy_btn = QPushButton(self)
        self.onekey_copy_btn.setText("一键复制")
        self.onekey_copy_btn.resize(100, 50)
        self.onekey_copy_btn.move(100, 275)

    def init(self):
        self.working_dir = os.getcwd()
        self.cur_logfile = default_log_file
        self.check_ini_file()
        self.workingdir_lock_status = 1

    def set_connect(self):
        self.onekey_copy_btn.clicked.connect(self.one_key_copy)
        self.brand_cbb.currentIndexChanged[str].connect(self.change_brand) 
        self.unlockdir_btn.clicked.connect(self.unlockdir_btn_slot) 
        self.check_log_btn.clicked.connect(self.open_log_file)

    # modify working directory
    def unlockdir_btn_slot(self):
        working_dir = self.workingfolder_te.toPlainText()
        if self.workingdir_lock_status == 1:
            self.workingfolder_te.setEnabled(True)
            self.workingdir_lock_status = 0
            self.working_dir = self.workingfolder_te.toPlainText()
            self.unlockdir_btn.setText('锁定')
        else:
            self.workingfolder_te.setEnabled(False)
            self.workingdir_lock_status = 1
            self.working_dir = self.workingfolder_te.toPlainText()
            if check_dir(working_dir):
                logprint('working folder manually change to '+self.working_dir)
                self.unlockdir_btn.setText('解锁')
            else:
                MessageBox = QMessageBox(self)
                MessageBox.critical(self, "错误", "请输入正确的工作目录")
                return

    #############################################

                    #Function#

    #############################################

    def create_ini_file(self):
        self.config.read(default_ini_file)
        self.config.add_section("baseconf")
        self.write_ini_file()

    def write_ini_file(self):
        # 写入配置文件
        try:
            self.config.set("baseconf", "brand", self.oribrand)
            self.config.set("baseconf", "formatname", self.formatname)
            self.config.write(open(default_ini_file, "w"))
        except configparser.DuplicateSectionError:
            logprint('config wirte error')

    def check_ini_file(self):
        if check_file_exist(default_ini_file):
            self.config = configparser.ConfigParser()
            self.config.read(default_ini_file)
            self.oribrand = self.config.get('baseconf', 'brand')
            self.formatname = self.config.get('baseconf', 'formatname')
            logprint('brand info loaded')
        else:
            self.config = configparser.ConfigParser()
            self.mkdir(default_ini_dir)
            self.oribrand = 'Nikon'
            self.formatname = '.NEF'
            self.create_ini_file()

    def change_brand(self, brand_name):
        self.oribrand = brand_name
        self.formatname = default_rawformat_dir[brand_name]
        logprint('brand manual switch to ' + self.oribrand)


    def open_log_file(self):
        os.system('notepad '+ default_log_file)


    def get_jpgfiles_list_from_oridir(self):
        # 获取当前路径下所有JPG文件的列表
        dirs = os.listdir(self.working_dir)
        full_pic_list = []
        for file_name in dirs:
            endname = os.path.splitext(file_name)[1]
            if endname.lower() == '.jpg':
                full_pic_list.append(file_name)
        self.jpgfileslist = full_pic_list

    def one_key_copy(self):
        # 一键复制
        self.oridir = self.source_folder_te.toPlainText()
        MessageBox = QMessageBox(self)
        if not self.oridir:
            MessageBox.critical(self, "错误", "请输入源地址")
            return
        self.get_jpgfiles_list_from_oridir()
        picprocess = PicFileList(self.jpgfileslist,self.working_dir,self.oridir,self.formatname)
        logprint('start copy file photo by ' + self.oribrand + ' device')
        picprocess.main_process()

    def brand_list_gen(self):
        list = []
        list.append(self.oribrand)
        for keyValue in default_rawformat_dir.keys():
            if keyValue != self.oribrand:
                list.append(keyValue)
        return list

    def closeEvent(self, event):
        self.write_ini_file()   #固化为最后确定的品牌和格式
        logprint('brand change to ' + self.oribrand)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    picApp = PicApp()
    picApp.show()
    sys.exit(app.exec_())