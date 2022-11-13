# PicTool
个人使用的照片处理小工具集合

[English Edition](https://github.com/LewisGu/PicTool/blob/main/README.md)

## RAWFileCopyByJPG.py
技术选型：
Python: 3.6.4
库及版本详见requirements.txt

选定源路径，通过遍历现路径中所有JPG文件名，并将源路径中对应的RAW文件复制到现路径中

### v2.0
#### 新增功能

1. RAW格式支持更多的设备品牌，包括**佳能**, **索尼**, **尼康**, **富士**, **理光**, **宾得**, **松下**

2. 增加文件夹及文件的自动校验

3. 增加带时间戳的日志和cmd命令行打印功能

4. 支持修改工作目录

5. 支持记忆上次所使用的品牌设置

#### TODO list

遍历源路径，根据文件扩展名匹配推断所适用的设备品牌及RAW格式

### v1.0

完成基本功能

## fakefuji.bat

通过使用基于Perl的EXIFTool工具，魔改富士RAW格式照片中的EXIF信息，以实现在Capture One中自由套用胶片滤镜的作用（X-T2亲测可用）

