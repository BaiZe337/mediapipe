import time
from ctypes import cast, POINTER

import cv2
import numpy as np
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

import HandTrackingModule as htm
from util import *

devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume = cast(interface, POINTER(IAudioEndpointVolume))
volumeRange = volume.GetVolumeRange()  # (-63.5, 0.0, 0.03125)
minVol = volumeRange[0]
maxVol = volumeRange[1]

#############################
wCam, hCam = 1080, 720
#############################
cap = cv2.VideoCapture(0)
cap.set(3, wCam)
cap.set(4, hCam)
pTime = 0
detector = htm.handDetector()

no_act_thres = 15  # 可以容忍的错误帧数
stop_thres = 15  # 判断为停滞的移动距离
stable_thres = 20  # 判断为稳定触发的时间
stop_time = [0]
old_lmList = None

while True:
    ret, img = cap.read()
    img = detector.findHands(img)
    lmList = detector.findPosition(img)
    if old_lmList is None and len(lmList):
        old_lmList = lmList

    if len(lmList):
        # 下面实现长度到音量的转换
        # 判断食指是否稳定
        # 判定为停止开始稳定读秒
        length = compute_distance(lmList[8][1], lmList[8][2], old_lmList[8][1], old_lmList[8][2])
        print(length)
        if length < stop_thres:
            if stop_time[0] < stable_thres:
                stop_time[0] += 1

            fill_cnt = stop_time[0] / stable_thres * 360
            cv2.circle(img, (lmList[8][1], lmList[8][2]), 15, (0, 255, 0), cv2.FILLED)
            if 0 < fill_cnt < 360:
                cv2.ellipse(img, (lmList[8][1], lmList[8][2]), (30, 30), 0, 0, fill_cnt, (255, 255, 0),
                            2)
                # 进入功能开始调节音量
            else:
                cv2.ellipse(img, (lmList[8][1], lmList[8][2]), (30, 30), 0, 0, fill_cnt, (0, 150, 255),
                            4)
                # 下面实现长度到音量的转换
                # np.interp为插值函数，简而言之，看line_len的值在[15，200]中所占比例，然后去[min_volume,max_volume]中线性寻找相应的值，作为返回值
                vol = np.interp(length, [0, 20], [minVol, maxVol])
                # 用之前得到的vol值设置电脑音量
                volume.SetMasterVolumeLevel(vol, None)
                volBar = np.interp(length, [0, 20], [350, 150])
                volPer = np.interp(length, [0, 20], [0, 100])

                cv2.rectangle(img, (20, 150), (50, 350), (255, 0, 255), 2)
                cv2.rectangle(img, (20, int(volBar)), (50, 350), (255, 0, 255), cv2.FILLED)
                cv2.putText(img, f'{int(volPer)}%', (10, 380), cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 255), 2)
        # 判定为移动，刷新时间
        else:
            stop_time[0] = 0
        old_lmList = lmList

    cTime = time.time()
    fps = 1 / (cTime - pTime)
    pTime = cTime
    cv2.putText(img, f'fps: {int(fps)}', (10, 40), cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 2)

    cv2.imshow("Image", img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break