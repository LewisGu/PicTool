# PicTool
A Small Tool Collection for Easy Process My Photo

[中文版](https://github.com/LewisGu/PicTool/blob/main/README-zh.md)

## RAWFileCopyByJPG.py

```
Python: 3.10

other lib edition refer to requirements.txt
```

input jpg and raw file path, copy matched file from raw path into jpg path, which fulfill the condition of "same file name" and "brand fit"

### v3.1 LTSC

1. improve ui
2. Enable UI to adapt to screen resolutions.

### v3.0 LTSC

1. improve python edition to 3.10
2. add a icon
3. fix bug

**TODO List**

Enable UI to adapt to screen resolutions.

### v2.3 LTSC

1. analysis RAW folder file format to match and infer suitable brand
2. add input check function and info window, improve stability of software
3. remove default jpg folder, replace by a editable input
4. code reconstruction, improve code readability

**TODO List**

1. Improve UI
2. fix bug

### v2.0

1. add brand support of more mainstream camera device, including: **Canon**, **Sony**, **Nikon**, **Fujifilm**, **Ricoh**, **Pentax**, **Panasonic**.

2. add auto verify of directory/file existance

3. add log function both in timestamp-marked log file and CMD prompt

4. support modify working directory

5. support last setting memory to ini file

**TODO List**

~~Analysis RAW Folder File Format to Match and Infer Suitable Brand~~

### v1.0

fulfill the basic function of copy

## TIFF2PNG

Automatically converts TIFF files to PNG format for easier processing of lossless film files obtained from HS1800 scanning.

### v1.0

fulfill the basic function

## fakefuji.bat

modify exif info of RAF file by using exiftool(perl)

