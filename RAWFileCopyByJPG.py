from fileinput import close
from pickle import TRUE
from PySide2.QtCore import Qt
from PySide2.QtWidgets import QApplication,QComboBox,QMainWindow,QWidget,QPushButton,QLabel,QPlainTextEdit,QMessageBox,QDialog,QDialogButtonBox,QVBoxLayout
import os,shutil
from tqdm import tqdm       # 进度条包
import logging
import time
import sys
import configparser

default_ini_dir = 'C:\\CopyRAWFileByJpg'
default_ini_file = 'C:\\CopyRAWFileByJpg\\config.ini'
now = time.strftime("%Y-%m-%d-%H_%M_%S",time.localtime(time.time())) 
default_log_file = 'C:\\CopyRAWFileByJpg\\'+now+'.log'
default_rawformat_dir = {'Canon':'.CR2','Fuji':'.RAF','Nikon':'.NEF','Ricoh':'.DNG','Sony':'.ARW','Pentax':'.PEF','Olympus':'.ORF','Panasonic':'.RW2'}

# 日志记录格式
logging.basicConfig(level=logging.DEBUG,
                format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                datefmt='%Y-%m-%d %a %H:%M:%S',
                filename=default_log_file,
                filemode='w')

    #############################################

    # Public Function #

    #############################################

def logprint(msg):
    # 仅在日志中打印
    logging.info(msg)

def log_screen_print(msg):
    # 同时在日志和屏幕中打印
    print(msg)
    logging.info(msg)

def same_dir(path1,path2):
    if path1 == path2:
        return True
    else:
        return False

def check_dir(path):
    # 检查路径是否存在
    folder = os.path.exists(path)
    if not folder:
        return False
    else:
        return True

def exist_jpg_file(local_file_list):
    # 遍历文件列表，获取文件名列表
    file_suffix_list,file_suffix_dict = get_all_file_suffix_list_dir(local_file_list,False)
    exist_flag = False
    for item in file_suffix_list:
        if item.lower() == 'jpg':
            exist_flag = True
    return exist_flag

def jpg_raw_file_precise_match(jpg_file_list,raw_file_list,rawformat):
    # 根据JPG文件名 RAW文件名 后缀名精确匹配
    file_prefix_list = get_all_file_prefix_list(jpg_file_list)
    for prefix in file_prefix_list:
        raw_file = prefix + str(rawformat)
        if raw_file in raw_file_list:
            return True
    return False

def mkdir(path):
    # 创建路径
    folder = os.path.exists(path)
    if not folder:  # 判断是否存在文件夹如果不存在则创建为文件夹
        os.makedirs(path)  
        logprint('the folder '+path+' has created') 

def check_file_exist(filename):
    # 检查文件是否存在
    return os.access(filename, os.F_OK)  # 文件存在，返回True,否则返回False

def get_full_filenamelist(filePath):
    # 获取本路径下所有单文件的完整文件名
    realfile_list = []
    filelist =  os.listdir(filePath)
    for item in filelist:
        split = item.split(".")
        if len(split) == 2:
            realfile_list.append(item)
    listlength = len(realfile_list)
    if listlength == 0:
        return realfile_list,True
    else:
        return realfile_list,False

def get_all_file_prefix_list(local_file_list):
    # 遍历文件列表，获取不带后缀的文件名列表
    file_prefix_list = []
    for file in local_file_list:
        file_split = file.split(".")
        file_prefix = file_split[0]
        file_prefix_list.append(file_prefix)
    return file_prefix_list

def get_all_file_suffix_list_dir(local_file_list,jpg_exclude_flag):
    # 遍历文件列表，不重复的后缀名列表及后缀字典(jpg_exclude_flag为1时，后缀名不包括jpg)
    file_suffix_list = []
    file_suffix_dict = {}
    for filename in local_file_list:
        file_split = filename.split(".")
        file_suffix = file_split[1]
        file_suffix_lower = file_suffix.lower()
        if jpg_exclude_flag:
            if file_suffix_lower != 'jpg':
                if file_suffix not in file_suffix_list:
                    file_suffix_list.append(file_suffix)
                if  file_suffix not in file_suffix_dict:
                    file_suffix_dict[file_suffix] = 1
                else :
                    file_suffix_dict[file_suffix] += 1
        else:
            if file_suffix not in file_suffix_list:
                file_suffix_list.append(file_suffix)
            if  file_suffix not in file_suffix_dict:
                file_suffix_dict[file_suffix] = 1
            else :
                file_suffix_dict[file_suffix] += 1
    return file_suffix_list,file_suffix_dict

def construct_auto_analyze_msg(list,dict):
    # 根据列表和字典，找出最大值，构造提示字符串
    msg = "RAW文件共 " + str(len(list)) + " 类格式,分别为\n"
    for item in list:
        msg = msg + str(item) + " 文件 " + str(dict[item]) + " 个\n"
    if len(list) == 1:
        max_key = list[0]
    else:
        for key,value in dict.items():
            if(value == max(dict.values())):
                max_key = key
    max_key = "."+max_key
    new_dict = {v : k for k, v in default_rawformat_dir.items()}
    brand = new_dict[max_key]
    msg = msg+"建议匹配 " + str(brand) 
    return msg,brand

class PicFileList:

    #############################################

    # Picture File List Class #
    # 读取文件列表后，对该列表进行操作

    #############################################
    def __init__(self, jpgfileslist, curdir, oridir,formatname):
        self.jpgfileslist = jpgfileslist
        self.curdir = curdir
        self.oridir = oridir
        # self.raw_file_auto_analyze()
        self.formatname = formatname

    def main_process(self):
        # 主方法
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
        msg = "success copy "+str(copy_success_num)+" files, failed "+str(copy_failed_num)
        if copy_failed_num > 0:
            msg = msg + ",please check log !"
        log_screen_print(msg)

    def one_jpg_process(self, jpgname):
        # 每个文件具体方法
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

class Dialog(QDialog):

    #############################################

    # 弹出框对象

    #############################################

    def __init__(self,Msg,parent=None):
        super(Dialog, self).__init__(parent)
        layout=QVBoxLayout(self)
        self.msg = Msg
        self.set_flag = False
        self.label=QLabel(self)
        self.label.setText(self.msg)
        layout.addWidget(self.label)

        self.buttonBox=QDialogButtonBox()
        self.buttonBox.addButton("接受",QDialogButtonBox.AcceptRole)
        self.buttonBox.addButton("放弃",QDialogButtonBox.RejectRole)

        self.buttonBox.accepted.connect(self.applybrand)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)

    def applybrand(self):
        # 接受建议
        self.set_flag = True
        self.accept()

    def getResult(self,parent=None):
        dialog=Dialog(parent)
        self.set_flag=dialog.exec_()
        return self.set_flag
class PicApp(QMainWindow):
    
    #############################################

    # UI Class #

    #############################################
    
    def __init__(self):
        super(PicApp, self).__init__()
        self.resize(300, 400)
        self.setWindowTitle("RAW文件懒人复制")
        self.init()
        self.setup_ui()
        self.set_connect()

    def setup_ui(self):
        # 设置ui界面
        self.jpgfiledir_label = QLabel(self)
        self.jpgfiledir_label.setAlignment(Qt.AlignCenter) 
        self.jpgfiledir_label.setText('JPG文件路径')
        label_width = self.jpgfiledir_label.width()
        self.jpgfiledir_label.move(150-label_width/2, 0)

        self.jpgdir_te = QPlainTextEdit(self)
        self.jpgdir_te.setPlaceholderText("请输入JPG文件源路径")
        self.jpgdir_te.setEnabled(True)
        self.jpgdir_te.resize(250, 50)
        self.jpgdir_te.move(25, 35)

        self.rawfiledir_label = QLabel(self)
        self.rawfiledir_label.setAlignment(Qt.AlignCenter) 
        self.rawfiledir_label.setText('RAW文件路径')
        label_width = self.rawfiledir_label.width()
        self.rawfiledir_label.move(150-label_width/2, 85)

        self.rawdir_te = QPlainTextEdit(self)
        self.rawdir_te.setPlaceholderText("请输入待匹配的RAW文件源路径")
        self.rawdir_te.resize(250, 50)
        self.rawdir_te.move(25, 120)

        self.auto_analyze_btn = QPushButton(self)
        self.auto_analyze_btn.setText("品牌自动分析")
        self.auto_analyze_btn.resize(100, 25)
        self.auto_analyze_btn.move(100, 180)
        
        self.brand_label = QLabel(self)
        self.brand_label.setAlignment(Qt.AlignCenter) 
        self.brand_label.setText('当前适用品牌')
        brand_label_width = self.brand_label.width()
        self.brand_label.move(150-brand_label_width/2, 205)

        self.brand_cbb = QComboBox(self)
        brandlist = self.brand_list_gen(self.oribrand)
                
        self.brand_cbb.resize(100, 20)
        self.brand_cbb.move(100, 235)

        self.onekey_copy_btn = QPushButton(self)
        self.onekey_copy_btn.setText("一键复制")
        self.onekey_copy_btn.resize(100, 50)
        self.onekey_copy_btn.move(100, 265)
                
        self.check_log_btn = QPushButton(self)
        self.check_log_btn.setText("查看日志")
        self.check_log_btn.resize(100, 30)
        self.check_log_btn.move(100, 325)

        self.copyright_label = QLabel(self)
        self.copyright_label.setText("RAW文件懒人复制v2.3 Copyright By Lewisgu")
        self.copyright_label.adjustSize()
        copyright_label_width = self.copyright_label.width()
        self.copyright_label.move(150-copyright_label_width/2, 380)

    def init(self):
        # 初始化
        self.filecopy_valid = False
        self.cur_logfile = default_log_file
        self.input_rawdir = ""
        self.input_jpgdir = ""
        self.check_ini_file()

    def set_connect(self):
        # 信号-槽链接
        self.onekey_copy_btn.clicked.connect(self.one_key_copy_slot)
        self.auto_analyze_btn.clicked.connect(self.auto_analyze_slot)
        self.brand_cbb.currentIndexChanged[str].connect(self.change_brand) 
        self.check_log_btn.clicked.connect(self.check_log_slot)

    def WarrningWindow(self,Msg):
        # 警告弹窗
        MessageBox = QMessageBox(self)
        MessageBox.warning(self, "错误", Msg)

    def CriticalWindow(self,Msg):
        # 提示弹窗
        MessageBox = QMessageBox(self)
        MessageBox.critical(self, "提示", Msg)

    #############################################

                    #Function#

    #############################################
    def create_ini_file(self):
        # 创建ini文件
        self.config.read(default_ini_file)
        self.config.add_section("baseconf")
        self.write_ini_file()

    def write_ini_file(self):
        # 写入配置文件
        try:
            self.config.set("baseconf", "brand", self.oribrand)
            self.config.set("baseconf", "formatname", self.rawformat)
            self.config.write(open(default_ini_file, "w"))
        except configparser.DuplicateSectionError:
            logprint('config wirte error')

    def check_ini_file(self):
        # 检查ini文件
        if check_file_exist(default_ini_file):
            self.config = configparser.ConfigParser()
            self.config.read(default_ini_file)
            self.oribrand = self.config.get('baseconf', 'brand')
            self.rawformat = self.config.get('baseconf', 'formatname')
            logprint('brand info loaded')
        else:
            self.config = configparser.ConfigParser()
            self.mkdir(default_ini_dir)
            self.oribrand = 'Nikon'
            self.rawformat = '.NEF'
            self.create_ini_file()

    def change_brand(self):
        # 修改品牌名
        self.oribrand = self.brand_cbb.currentText()
        self.rawformat = default_rawformat_dir[self.oribrand]
        logprint('brand manual switch to ' + self.oribrand)

    def check_log_slot(self):
        # 通过记事本打开日志文件
        os.system('notepad '+ default_log_file)

    def check_jpg_raw_dir(self):
        # 检查jpg路径和raw路径是否合法,是否完全相同,源路径存在JPG文件，且有文件名一致
        if check_dir(self.input_rawdir) and check_dir(self.input_jpgdir):#路径合法
            if same_dir(self.input_rawdir,self.input_jpgdir):#路径一致
                self.WarrningWindow("输入的路径相同，请检查")
            else:
                if self.jpg_raw_file_match():#两路径有符合格式要求的”JPG-RAW“文件对，且有源路径有JPG
                    self.filecopy_valid = True
                else:
                    self.WarrningWindow("两路径下没有名称一致的文件,或JPG路径下没有JPG文件")
        else:
            self.WarrningWindow("JPG或RAW路径非法，请检查")

    def jpg_raw_file_match(self):
        # 获取源和目的所有文件名的列表，检查是否有重复元素
        jpg_file_list,flag = get_full_filenamelist(self.input_jpgdir)
        if exist_jpg_file(jpg_file_list): # 存在JPG文件
            raw_file_list,flag = get_full_filenamelist(self.input_rawdir)
            result = jpg_raw_file_precise_match(jpg_file_list,raw_file_list,self.rawformat)
            return result
        else:
            return False

    def get_jpgfiles_list(self):
        # 获取源路径下所有JPG文件的列表
        dstdirs = os.listdir(self.input_jpgdir)
        full_pic_list = []
        for file_name in dstdirs:
            endname = os.path.splitext(file_name)[1]
            if endname.lower() == '.jpg':
                full_pic_list.append(file_name)
        self.jpgfileslist = full_pic_list

    def one_key_copy_slot(self):
        # 一键复制主函数
        self.input_jpgdir = self.jpgdir_te.toPlainText()
        self.input_rawdir = self.rawdir_te.toPlainText()
        self.check_jpg_raw_dir()
        if self.filecopy_valid:
            self.get_jpgfiles_list()
            picprocess = PicFileList(self.jpgfileslist,self.input_jpgdir,self.input_rawdir,self.rawformat)
            logprint('start copy file photo by ' + self.oribrand + ' device')
            picprocess.main_process()

    def brand_list_gen(self,brand):
        # 重新排列品牌列表,输入的brand排最先
        list = []
        list.append(brand)
        for keyValue in default_rawformat_dir.keys():
            if keyValue != brand:
                list.append(keyValue)
        self.brand_cbb.clear()
        self.brand_cbb.addItems(list)
        self.oribrand = brand

    def brand_advice(self,local_file_list):
        # 给出建议的品牌
        file_suffix_list,file_suffix_dict = get_all_file_suffix_list_dir(local_file_list,True)
        Msg,suggest_brand = construct_auto_analyze_msg(file_suffix_list,file_suffix_dict)
        set_flag = Dialog.getResult(self,Msg)
        if set_flag:
            self.brand_list_gen(suggest_brand)

    def auto_analyze_slot(self):
        # 分析扩展名，猜测品牌，给出提示
        self.input_jpgdir = self.jpgdir_te.toPlainText()
        self.input_rawdir = self.rawdir_te.toPlainText()
        if check_dir(self.input_rawdir) and check_dir(self.input_jpgdir):
            local_file_list,empty_flag = get_full_filenamelist(self.input_rawdir)
            if empty_flag:
                self.WarrningWindow("本路径下不含任何文件，请检查路径")
            else:
                self.brand_advice(local_file_list)
        else:
            self.WarrningWindow("路径非法，请检查")

    def closeEvent(self, event):
        # 固化为最后确定的品牌和格式
        self.write_ini_file()   
        logprint('brand change to ' + self.oribrand)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    picApp = PicApp()
    picApp.show()
    sys.exit(app.exec_())