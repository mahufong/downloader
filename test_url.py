"""
 * @2022-01-06 16:38:24
 * @Author       : mahf
 * @LastEditTime : 2022-01-06 16:39:56
 * @FilePath     : /epicgames-claimer/test_url.py
 * @Copyright 2022 mahf, All Rights Reserved.
"""
import os
import urllib.parse

url = 'http://cdn.video.picasso.dandanjiang.tv/sdf/sdfsdf/sdfw/3a9a1721e28c47a60459bd404b4d942e.mp4?newver=0.239987592509&sign=827000577d553c11f14a8674ad80d970&t=61d6c081'

flag = os.path.basename(urllib.parse.urlsplit(url).path)
#flag = urllib.parse.urlsplit(url).path

print(flag)