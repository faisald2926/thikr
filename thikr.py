#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ذِكْر - برنامج التذكير بذكر الله
Thikr - Islamic Remembrance Reminder

برنامج احترافي للتذكير بالأذكار والسور القرآنية
يعمل في خلفية النظام مع واجهة سايبربنك أنيقة

الإصدار: 1.0.0
"""

import sys
import os
import json
import random
import time
from datetime import datetime, timedelta
from pathlib import Path

# التحقق من المتطلبات
try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QSlider, QComboBox, QSpinBox, QCheckBox,
        QTabWidget, QGroupBox, QFrame, QLineEdit,
        QListWidget, QSystemTrayIcon,
        QMenu, QMessageBox, QTimeEdit, QProgressBar,
        QGraphicsDropShadowEffect
    )
    from PyQt6.QtCore import (
        Qt, QTimer, QPropertyAnimation, QEasingCurve,
        QThread, pyqtSignal, QTime, QObject
    )
    from PyQt6.QtGui import (
        QFont, QColor, QIcon, QPixmap, QPainter, QBrush,
        QPen, QRadialGradient, QAction, QCursor,
        QFontDatabase, QGuiApplication
    )
except ImportError:
    print("جاري تثبيت PyQt6...")
    os.system(f"{sys.executable} -m pip install PyQt6 --break-system-packages -q")
    from PyQt6.QtWidgets import *
    from PyQt6.QtCore import *
    from PyQt6.QtGui import *


# ============================================
# الثوابت والمسارات
# ============================================

APP_NAME = "ذِكْر"
APP_VERSION = "1.0.0"
APP_DIR = Path(__file__).parent.resolve()
DATA_DIR = APP_DIR / "data"
SOUNDS_DIR = APP_DIR / "sounds"

# إنشاء المجلدات
for directory in [DATA_DIR, SOUNDS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


# ============================================
# الأذكار الافتراضية
# ============================================

DEFAULT_ATHKAR = [
    {"id": 1, "text": "سُبْحَانَ اللَّهِ", "category": "تسبيح", "virtue": "من قال سبحان الله مائة مرة غفرت له ذنوبه"},
    {"id": 2, "text": "الْحَمْدُ لِلَّهِ", "category": "تحميد", "virtue": "الحمد لله تملأ الميزان"},
    {"id": 3, "text": "لَا إِلَٰهَ إِلَّا اللَّهُ", "category": "تهليل", "virtue": "أفضل ما قلت أنا والنبيون من قبلي"},
    {"id": 4, "text": "اللَّهُ أَكْبَرُ", "category": "تكبير", "virtue": "كلمة عظيمة ثقيلة في الميزان"},
    {"id": 5, "text": "سُبْحَانَ اللَّهِ وَبِحَمْدِهِ", "category": "تسبيح", "virtue": "من قالها مائة مرة حين يصبح وحين يمسي لم يأت أحد يوم القيامة بأفضل مما جاء به"},
    {"id": 6, "text": "سُبْحَانَ اللَّهِ الْعَظِيمِ وَبِحَمْدِهِ", "category": "تسبيح", "virtue": "كلمتان خفيفتان على اللسان ثقيلتان في الميزان حبيبتان إلى الرحمن"},
    {"id": 7, "text": "لَا حَوْلَ وَلَا قُوَّةَ إِلَّا بِاللَّهِ", "category": "حوقلة", "virtue": "كنز من كنوز الجنة"},
    {"id": 8, "text": "أَسْتَغْفِرُ اللَّهَ الْعَظِيمَ وَأَتُوبُ إِلَيْهِ", "category": "استغفار", "virtue": "من لزم الاستغفار جعل الله له من كل هم فرجا"},
    {"id": 9, "text": "اللَّهُمَّ صَلِّ وَسَلِّمْ عَلَى نَبِيِّنَا مُحَمَّدٍ", "category": "صلاة على النبي", "virtue": "من صلى علي صلاة صلى الله عليه بها عشرا"},
    {"id": 10, "text": "لَا إِلَٰهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ، لَهُ الْمُلْكُ وَلَهُ الْحَمْدُ وَهُوَ عَلَىٰ كُلِّ شَيْءٍ قَدِيرٌ", "category": "تهليل", "virtue": "من قالها عشر مرات كان كمن أعتق أربعة أنفس من ولد إسماعيل"},
    {"id": 11, "text": "سُبْحَانَ اللَّهِ، وَالْحَمْدُ لِلَّهِ، وَلَا إِلَٰهَ إِلَّا اللَّهُ، وَاللَّهُ أَكْبَرُ", "category": "الباقيات الصالحات", "virtue": "أحب الكلام إلى الله"},
    {"id": 12, "text": "رَبِّ اغْفِرْ لِي وَتُبْ عَلَيَّ إِنَّكَ أَنْتَ التَّوَّابُ الرَّحِيمُ", "category": "استغفار", "virtue": "دعاء التوبة"},
    {"id": 13, "text": "اللَّهُمَّ إِنِّي أَسْأَلُكَ الْعَفْوَ وَالْعَافِيَةَ", "category": "دعاء", "virtue": "ما سُئل الله شيئاً أحب إليه من العافية"},
    {"id": 14, "text": "حَسْبُنَا اللَّهُ وَنِعْمَ الْوَكِيلُ", "category": "توكل", "virtue": "قالها إبراهيم حين ألقي في النار"},
    {"id": 15, "text": "يَا حَيُّ يَا قَيُّومُ بِرَحْمَتِكَ أَسْتَغِيثُ", "category": "دعاء", "virtue": "دعاء الكرب"},
    {"id": 16, "text": "رَبَّنَا آتِنَا فِي الدُّنْيَا حَسَنَةً وَفِي الْآخِرَةِ حَسَنَةً وَقِنَا عَذَابَ النَّارِ", "category": "دعاء قرآني", "virtue": "أكثر دعاء النبي ﷺ"},
    {"id": 17, "text": "اللَّهُمَّ أَعِنِّي عَلَى ذِكْرِكَ وَشُكْرِكَ وَحُسْنِ عِبَادَتِكَ", "category": "دعاء", "virtue": "وصية النبي ﷺ لمعاذ"},
    {"id": 18, "text": "رَبِّ زِدْنِي عِلْمًا", "category": "دعاء قرآني", "virtue": "دعاء طلب العلم"},
    {"id": 19, "text": "بِسْمِ اللَّهِ الَّذِي لَا يَضُرُّ مَعَ اسْمِهِ شَيْءٌ فِي الْأَرْضِ وَلَا فِي السَّمَاءِ وَهُوَ السَّمِيعُ الْعَلِيمُ", "category": "حماية", "virtue": "من قالها ثلاثاً لم تصبه فجأة بلاء"},
    {"id": 20, "text": "اللَّهُمَّ إِنِّي أَعُوذُ بِكَ مِنَ الْهَمِّ وَالْحَزَنِ", "category": "تعوذ", "virtue": "دعاء الهم والحزن"},
]

DEFAULT_SURAHS = [
    {"id": 1, "name": "سورة الإخلاص", "number": 112, "verses": ["بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ", "قُلْ هُوَ اللَّهُ أَحَدٌ", "اللَّهُ الصَّمَدُ", "لَمْ يَلِدْ وَلَمْ يُولَدْ", "وَلَمْ يَكُن لَّهُ كُفُوًا أَحَدٌ"], "virtue": "تعدل ثلث القرآن"},
    {"id": 2, "name": "سورة الفلق", "number": 113, "verses": ["بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ", "قُلْ أَعُوذُ بِرَبِّ الْفَلَقِ", "مِن شَرِّ مَا خَلَقَ", "وَمِن شَرِّ غَاسِقٍ إِذَا وَقَبَ", "وَمِن شَرِّ النَّفَّاثَاتِ فِي الْعُقَدِ", "وَمِن شَرِّ حَاسِدٍ إِذَا حَسَدَ"], "virtue": "المعوذتان"},
    {"id": 3, "name": "سورة الناس", "number": 114, "verses": ["بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ", "قُلْ أَعُوذُ بِرَبِّ النَّاسِ", "مَلِكِ النَّاسِ", "إِلَٰهِ النَّاسِ", "مِن شَرِّ الْوَسْوَاسِ الْخَنَّاسِ", "الَّذِي يُوَسْوِسُ فِي صُدُورِ النَّاسِ", "مِنَ الْجِنَّةِ وَالنَّاسِ"], "virtue": "المعوذتان"},
    {"id": 4, "name": "سورة الفاتحة", "number": 1, "verses": ["بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ", "الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ", "الرَّحْمَٰنِ الرَّحِيمِ", "مَالِكِ يَوْمِ الدِّينِ", "إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ", "اهْدِنَا الصِّرَاطَ الْمُسْتَقِيمَ", "صِرَاطَ الَّذِينَ أَنْعَمْتَ عَلَيْهِمْ غَيْرِ الْمَغْضُوبِ عَلَيْهِمْ وَلَا الضَّالِّينَ"], "virtue": "أعظم سورة في القرآن"},
    {"id": 5, "name": "آية الكرسي", "number": 255, "verses": ["اللَّهُ لَا إِلَٰهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ ۚ لَا تَأْخُذُهُ سِنَةٌ وَلَا نَوْمٌ ۚ لَّهُ مَا فِي السَّمَاوَاتِ وَمَا فِي الْأَرْضِ ۗ مَن ذَا الَّذِي يَشْفَعُ عِندَهُ إِلَّا بِإِذْنِهِ ۚ يَعْلَمُ مَا بَيْنَ أَيْدِيهِمْ وَمَا خَلْفَهُمْ ۖ وَلَا يُحِيطُونَ بِشَيْءٍ مِّنْ عِلْمِهِ إِلَّا بِمَا شَاءَ ۚ وَسِعَ كُرْسِيُّهُ السَّمَاوَاتِ وَالْأَرْضَ ۖ وَلَا يَئُودُهُ حِفْظُهُمَا ۚ وَهُوَ الْعَلِيُّ الْعَظِيمُ"], "virtue": "أعظم آية في القرآن"},
    {"id": 6, "name": "سورة الكوثر", "number": 108, "verses": ["بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ", "إِنَّا أَعْطَيْنَاكَ الْكَوْثَرَ", "فَصَلِّ لِرَبِّكَ وَانْحَرْ", "إِنَّ شَانِئَكَ هُوَ الْأَبْتَرُ"], "virtue": "أقصر سورة في القرآن"},
    {"id": 7, "name": "سورة العصر", "number": 103, "verses": ["بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ", "وَالْعَصْرِ", "إِنَّ الْإِنسَانَ لَفِي خُسْرٍ", "إِلَّا الَّذِينَ آمَنُوا وَعَمِلُوا الصَّالِحَاتِ وَتَوَاصَوْا بِالْحَقِّ وَتَوَاصَوْا بِالصَّبْرِ"], "virtue": "لو تدبرها الناس لكفتهم"},
]

# ============================================
# أذكار الصباح والمساء
# ============================================

MORNING_ATHKAR = [
    {"id": 1, "text": "أَصْبَحْنَا وَأَصْبَحَ الْمُلْكُ لِلَّهِ، وَالْحَمْدُ لِلَّهِ، لَا إِلَٰهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ، لَهُ الْمُلْكُ وَلَهُ الْحَمْدُ وَهُوَ عَلَىٰ كُلِّ شَيْءٍ قَدِيرٌ", "repeat": 1, "virtue": ""},
    {"id": 2, "text": "اللَّهُمَّ بِكَ أَصْبَحْنَا، وَبِكَ أَمْسَيْنَا، وَبِكَ نَحْيَا، وَبِكَ نَمُوتُ، وَإِلَيْكَ النُّشُورُ", "repeat": 1, "virtue": ""},
    {"id": 3, "text": "اللَّهُمَّ أَنْتَ رَبِّي لَا إِلَٰهَ إِلَّا أَنْتَ، خَلَقْتَنِي وَأَنَا عَبْدُكَ، وَأَنَا عَلَىٰ عَهْدِكَ وَوَعْدِكَ مَا اسْتَطَعْتُ، أَعُوذُ بِكَ مِنْ شَرِّ مَا صَنَعْتُ، أَبُوءُ لَكَ بِنِعْمَتِكَ عَلَيَّ، وَأَبُوءُ بِذَنْبِي فَاغْفِرْ لِي فَإِنَّهُ لَا يَغْفِرُ الذُّنُوبَ إِلَّا أَنْتَ", "repeat": 1, "virtue": "سيد الاستغفار"},
    {"id": 4, "text": "اللَّهُمَّ إِنِّي أَصْبَحْتُ أُشْهِدُكَ، وَأُشْهِدُ حَمَلَةَ عَرْشِكَ، وَمَلَائِكَتَكَ، وَجَمِيعَ خَلْقِكَ، أَنَّكَ أَنْتَ اللَّهُ لَا إِلَٰهَ إِلَّا أَنْتَ وَحْدَكَ لَا شَرِيكَ لَكَ، وَأَنَّ مُحَمَّدًا عَبْدُكَ وَرَسُولُكَ", "repeat": 4, "virtue": "من قالها أعتقه الله من النار"},
    {"id": 5, "text": "اللَّهُمَّ مَا أَصْبَحَ بِي مِنْ نِعْمَةٍ أَوْ بِأَحَدٍ مِنْ خَلْقِكَ فَمِنْكَ وَحْدَكَ لَا شَرِيكَ لَكَ، فَلَكَ الْحَمْدُ وَلَكَ الشُّكْرُ", "repeat": 1, "virtue": "من قالها أدى شكر يومه"},
    {"id": 6, "text": "اللَّهُمَّ عَافِنِي فِي بَدَنِي، اللَّهُمَّ عَافِنِي فِي سَمْعِي، اللَّهُمَّ عَافِنِي فِي بَصَرِي، لَا إِلَٰهَ إِلَّا أَنْتَ", "repeat": 3, "virtue": ""},
    {"id": 7, "text": "اللَّهُمَّ إِنِّي أَعُوذُ بِكَ مِنَ الْكُفْرِ، وَالْفَقْرِ، وَأَعُوذُ بِكَ مِنْ عَذَابِ الْقَبْرِ، لَا إِلَٰهَ إِلَّا أَنْتَ", "repeat": 3, "virtue": ""},
    {"id": 8, "text": "حَسْبِيَ اللَّهُ لَا إِلَٰهَ إِلَّا هُوَ عَلَيْهِ تَوَكَّلْتُ وَهُوَ رَبُّ الْعَرْشِ الْعَظِيمِ", "repeat": 7, "virtue": "من قالها كفاه الله ما أهمه"},
    {"id": 9, "text": "بِسْمِ اللَّهِ الَّذِي لَا يَضُرُّ مَعَ اسْمِهِ شَيْءٌ فِي الْأَرْضِ وَلَا فِي السَّمَاءِ وَهُوَ السَّمِيعُ الْعَلِيمُ", "repeat": 3, "virtue": "لم يضره شيء"},
    {"id": 10, "text": "رَضِيتُ بِاللَّهِ رَبًّا، وَبِالْإِسْلَامِ دِينًا، وَبِمُحَمَّدٍ صَلَّى اللَّهُ عَلَيْهِ وَسَلَّمَ نَبِيًّا", "repeat": 3, "virtue": "حق على الله أن يرضيه يوم القيامة"},
    {"id": 11, "text": "سُبْحَانَ اللَّهِ وَبِحَمْدِهِ", "repeat": 100, "virtue": "حُطت خطاياه وإن كانت مثل زبد البحر"},
    {"id": 12, "text": "لَا إِلَٰهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ، لَهُ الْمُلْكُ وَلَهُ الْحَمْدُ، وَهُوَ عَلَىٰ كُلِّ شَيْءٍ قَدِيرٌ", "repeat": 10, "virtue": "كمن أعتق أربع رقاب"},
    {"id": 13, "text": "اللَّهُمَّ صَلِّ وَسَلِّمْ عَلَى نَبِيِّنَا مُحَمَّدٍ", "repeat": 10, "virtue": "من صلى علي صلاة صلى الله عليه بها عشرا"},
]

EVENING_ATHKAR = [
    {"id": 1, "text": "أَمْسَيْنَا وَأَمْسَى الْمُلْكُ لِلَّهِ، وَالْحَمْدُ لِلَّهِ، لَا إِلَٰهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ، لَهُ الْمُلْكُ وَلَهُ الْحَمْدُ وَهُوَ عَلَىٰ كُلِّ شَيْءٍ قَدِيرٌ", "repeat": 1, "virtue": ""},
    {"id": 2, "text": "اللَّهُمَّ بِكَ أَمْسَيْنَا، وَبِكَ أَصْبَحْنَا، وَبِكَ نَحْيَا، وَبِكَ نَمُوتُ، وَإِلَيْكَ الْمَصِيرُ", "repeat": 1, "virtue": ""},
    {"id": 3, "text": "اللَّهُمَّ أَنْتَ رَبِّي لَا إِلَٰهَ إِلَّا أَنْتَ، خَلَقْتَنِي وَأَنَا عَبْدُكَ، وَأَنَا عَلَىٰ عَهْدِكَ وَوَعْدِكَ مَا اسْتَطَعْتُ، أَعُوذُ بِكَ مِنْ شَرِّ مَا صَنَعْتُ، أَبُوءُ لَكَ بِنِعْمَتِكَ عَلَيَّ، وَأَبُوءُ بِذَنْبِي فَاغْفِرْ لِي فَإِنَّهُ لَا يَغْفِرُ الذُّنُوبَ إِلَّا أَنْتَ", "repeat": 1, "virtue": "سيد الاستغفار"},
    {"id": 4, "text": "اللَّهُمَّ إِنِّي أَمْسَيْتُ أُشْهِدُكَ، وَأُشْهِدُ حَمَلَةَ عَرْشِكَ، وَمَلَائِكَتَكَ، وَجَمِيعَ خَلْقِكَ، أَنَّكَ أَنْتَ اللَّهُ لَا إِلَٰهَ إِلَّا أَنْتَ وَحْدَكَ لَا شَرِيكَ لَكَ، وَأَنَّ مُحَمَّدًا عَبْدُكَ وَرَسُولُكَ", "repeat": 4, "virtue": "من قالها أعتقه الله من النار"},
    {"id": 5, "text": "اللَّهُمَّ مَا أَمْسَى بِي مِنْ نِعْمَةٍ أَوْ بِأَحَدٍ مِنْ خَلْقِكَ فَمِنْكَ وَحْدَكَ لَا شَرِيكَ لَكَ، فَلَكَ الْحَمْدُ وَلَكَ الشُّكْرُ", "repeat": 1, "virtue": "من قالها أدى شكر ليلته"},
    {"id": 6, "text": "اللَّهُمَّ عَافِنِي فِي بَدَنِي، اللَّهُمَّ عَافِنِي فِي سَمْعِي، اللَّهُمَّ عَافِنِي فِي بَصَرِي، لَا إِلَٰهَ إِلَّا أَنْتَ", "repeat": 3, "virtue": ""},
    {"id": 7, "text": "اللَّهُمَّ إِنِّي أَعُوذُ بِكَ مِنَ الْكُفْرِ، وَالْفَقْرِ، وَأَعُوذُ بِكَ مِنْ عَذَابِ الْقَبْرِ، لَا إِلَٰهَ إِلَّا أَنْتَ", "repeat": 3, "virtue": ""},
    {"id": 8, "text": "حَسْبِيَ اللَّهُ لَا إِلَٰهَ إِلَّا هُوَ عَلَيْهِ تَوَكَّلْتُ وَهُوَ رَبُّ الْعَرْشِ الْعَظِيمِ", "repeat": 7, "virtue": "من قالها كفاه الله ما أهمه"},
    {"id": 9, "text": "بِسْمِ اللَّهِ الَّذِي لَا يَضُرُّ مَعَ اسْمِهِ شَيْءٌ فِي الْأَرْضِ وَلَا فِي السَّمَاءِ وَهُوَ السَّمِيعُ الْعَلِيمُ", "repeat": 3, "virtue": "لم يضره شيء"},
    {"id": 10, "text": "رَضِيتُ بِاللَّهِ رَبًّا، وَبِالْإِسْلَامِ دِينًا، وَبِمُحَمَّدٍ صَلَّى اللَّهُ عَلَيْهِ وَسَلَّمَ نَبِيًّا", "repeat": 3, "virtue": "حق على الله أن يرضيه يوم القيامة"},
    {"id": 11, "text": "أَعُوذُ بِكَلِمَاتِ اللَّهِ التَّامَّاتِ مِنْ شَرِّ مَا خَلَقَ", "repeat": 3, "virtue": "لم يضره شيء تلك الليلة"},
    {"id": 12, "text": "سُبْحَانَ اللَّهِ وَبِحَمْدِهِ", "repeat": 100, "virtue": "حُطت خطاياه وإن كانت مثل زبد البحر"},
    {"id": 13, "text": "لَا إِلَٰهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ، لَهُ الْمُلْكُ وَلَهُ الْحَمْدُ، وَهُوَ عَلَىٰ كُلِّ شَيْءٍ قَدِيرٌ", "repeat": 10, "virtue": "كمن أعتق أربع رقاب"},
    {"id": 14, "text": "اللَّهُمَّ صَلِّ وَسَلِّمْ عَلَى نَبِيِّنَا مُحَمَّدٍ", "repeat": 10, "virtue": "من صلى علي صلاة صلى الله عليه بها عشرا"},
]


# ============================================
# الثيمات
# ============================================

THEMES = {
    "cyberpunk_dark": {
        "name": "سايبربنك داكن",
        "background": "#0a0a0f",
        "bg_gradient": ["#0a0a0f", "#1a1a2e", "#0f0f1a"],
        "text": "#00ffff",
        "accent": "#ff00ff",
        "secondary": "#00ff88",
        "border": "#00ffff",
        "glow": "#00ffff"
    },
    "cyberpunk_neon": {
        "name": "نيون متوهج",
        "background": "#0d0221",
        "bg_gradient": ["#0d0221", "#150734", "#0d0221"],
        "text": "#f72585",
        "accent": "#7209b7",
        "secondary": "#4cc9f0",
        "border": "#f72585",
        "glow": "#f72585"
    },
    "islamic_gold": {
        "name": "ذهبي إسلامي",
        "background": "#1a1a2e",
        "bg_gradient": ["#1a1a2e", "#16213e", "#0f0f23"],
        "text": "#ffd700",
        "accent": "#daa520",
        "secondary": "#f4e4bc",
        "border": "#ffd700",
        "glow": "#ffd700"
    },
    "ocean_depth": {
        "name": "أعماق المحيط",
        "background": "#0c1821",
        "bg_gradient": ["#0c1821", "#1b2838", "#0c1821"],
        "text": "#4fc3f7",
        "accent": "#0288d1",
        "secondary": "#81d4fa",
        "border": "#4fc3f7",
        "glow": "#4fc3f7"
    },
    "emerald_night": {
        "name": "ليل زمردي",
        "background": "#0a1612",
        "bg_gradient": ["#0a1612", "#1a2f28", "#0a1612"],
        "text": "#50fa7b",
        "accent": "#00d26a",
        "secondary": "#98fb98",
        "border": "#50fa7b",
        "glow": "#50fa7b"
    },
    "royal_purple": {
        "name": "بنفسجي ملكي",
        "background": "#1a0a2e",
        "bg_gradient": ["#1a0a2e", "#2d1b4e", "#1a0a2e"],
        "text": "#bb86fc",
        "accent": "#9c27b0",
        "secondary": "#e1bee7",
        "border": "#bb86fc",
        "glow": "#bb86fc"
    },
    "sunset_warm": {
        "name": "غروب دافئ",
        "background": "#1a0f0a",
        "bg_gradient": ["#1a0f0a", "#2d1810", "#1a0f0a"],
        "text": "#ff7043",
        "accent": "#ff5722",
        "secondary": "#ffab91",
        "border": "#ff7043",
        "glow": "#ff7043"
    },
    "minimal_light": {
        "name": "فاتح بسيط",
        "background": "#f5f5f5",
        "bg_gradient": ["#ffffff", "#f5f5f5", "#eeeeee"],
        "text": "#1a1a1a",
        "accent": "#2196f3",
        "secondary": "#666666",
        "border": "#cccccc",
        "glow": "#2196f3",
        "is_light": True
    },
    "clean_white": {
        "name": "أبيض نظيف",
        "background": "#ffffff",
        "bg_gradient": ["#ffffff", "#fafafa", "#f5f5f5"],
        "text": "#212121",
        "accent": "#1976d2",
        "secondary": "#757575",
        "border": "#e0e0e0",
        "glow": "#1976d2",
        "is_light": True
    },
    "soft_cream": {
        "name": "كريمي ناعم",
        "background": "#fffef5",
        "bg_gradient": ["#fffef5", "#faf8f0", "#f5f3eb"],
        "text": "#3e2723",
        "accent": "#8d6e63",
        "secondary": "#6d4c41",
        "border": "#d7ccc8",
        "glow": "#8d6e63",
        "is_light": True
    },
    "mint_fresh": {
        "name": "نعناعي منعش",
        "background": "#f1f8f6",
        "bg_gradient": ["#f1f8f6", "#e8f5e9", "#e0f2f1"],
        "text": "#1b5e20",
        "accent": "#2e7d32",
        "secondary": "#4caf50",
        "border": "#a5d6a7",
        "glow": "#4caf50",
        "is_light": True
    },
    "sky_blue": {
        "name": "سماوي صافي",
        "background": "#f0f8ff",
        "bg_gradient": ["#f0f8ff", "#e3f2fd", "#e1f5fe"],
        "text": "#0d47a1",
        "accent": "#1565c0",
        "secondary": "#1976d2",
        "border": "#90caf9",
        "glow": "#2196f3",
        "is_light": True
    },
    "rose_light": {
        "name": "وردي فاتح",
        "background": "#fff5f5",
        "bg_gradient": ["#fff5f5", "#fce4ec", "#f8bbd9"],
        "text": "#880e4f",
        "accent": "#c2185b",
        "secondary": "#e91e63",
        "border": "#f48fb1",
        "glow": "#e91e63",
        "is_light": True
    }
}


# ============================================
# مدير الإعدادات
# ============================================

class SettingsManager:
    def __init__(self):
        self.settings_file = DATA_DIR / "user_settings.json"
        self.settings = self.load_settings()
    
    def load_settings(self):
        defaults = {
            "reminder": {
                "enabled": True,
                "interval_minutes": 60,
                "random_order": True,
                "show_virtue": True,
                "quiet_hours": {"enabled": False, "start": "23:00", "end": "06:00"}
            },
            "surah_reminder": {
                "enabled": True,
                "interval_days": 3,
                "last_shown": None
            },
            "popup": {
                "theme": "cyberpunk_dark",
                "position": "bottom_right",
                "width": 450,
                "height": 220,
                "duration_seconds": 8,
                "font_size": 20,
                "opacity": 0.95,
                "border_radius": 15
            },
            "sound": {
                "enabled": True,
                "volume": 30
            },
            "stats": {
                "daily_count": 0,
                "total_count": 0,
                "last_reset": None
            },
            "custom_athkar": []
        }
        
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                    return self._merge(defaults, saved)
            except:
                pass
        return defaults
    
    def _merge(self, defaults, saved):
        result = defaults.copy()
        for key, value in saved.items():
            if key in result and isinstance(value, dict) and isinstance(result[key], dict):
                result[key] = self._merge(result[key], value)
            else:
                result[key] = value
        return result
    
    def save(self):
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving: {e}")
    
    def get(self, path, default=None):
        keys = path.split('.')
        val = self.settings
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        return val
    
    def set(self, path, value):
        keys = path.split('.')
        s = self.settings
        for k in keys[:-1]:
            s = s.setdefault(k, {})
        s[keys[-1]] = value
        self.save()
    
    def get_theme(self):
        name = self.get('popup.theme', 'cyberpunk_dark')
        return THEMES.get(name, THEMES['cyberpunk_dark'])
    
    def get_random_thikr(self):
        all_athkar = DEFAULT_ATHKAR + self.get('custom_athkar', [])
        return random.choice(all_athkar) if all_athkar else DEFAULT_ATHKAR[0]
    
    def get_random_surah(self):
        return random.choice(DEFAULT_SURAHS) if DEFAULT_SURAHS else None
    
    def increment_counter(self):
        today = datetime.now().strftime("%Y-%m-%d")
        if self.get('stats.last_reset') != today:
            self.set('stats.daily_count', 0)
            self.set('stats.last_reset', today)
        
        daily = self.get('stats.daily_count', 0) + 1
        total = self.get('stats.total_count', 0) + 1
        self.set('stats.daily_count', daily)
        self.set('stats.total_count', total)
        return daily, total


# ============================================
# نافذة التذكير المنبثقة
# ============================================

class ReminderPopup(QWidget):
    closed = pyqtSignal()
    
    def __init__(self, settings):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | 
                        Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.settings = settings
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setup_ui()
        
        self.close_timer = QTimer(self)
        self.close_timer.timeout.connect(self.start_close)
        
        self.progress_timer = QTimer(self)
        self.progress_timer.timeout.connect(self.update_progress)
        self.progress_value = 100
    
    def setup_ui(self):
        w = self.settings.get('popup.width', 450)
        h = self.settings.get('popup.height', 220)
        self.setFixedSize(w, h)
        
        self.container = QFrame(self)
        self.container.setGeometry(0, 0, w, h)
        self.container.setObjectName("container")
        
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(8)
        
        # Header
        header = QHBoxLayout()
        self.title = QLabel("ذِكْر")
        self.title.setObjectName("title")
        
        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("closeBtn")
        self.close_btn.setFixedSize(28, 28)
        self.close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.close_btn.clicked.connect(self.start_close)
        
        header.addWidget(self.title)
        header.addStretch()
        header.addWidget(self.close_btn)
        
        # Content
        self.thikr_label = QLabel()
        self.thikr_label.setObjectName("thikr")
        self.thikr_label.setWordWrap(True)
        self.thikr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.virtue_label = QLabel()
        self.virtue_label.setObjectName("virtue")
        self.virtue_label.setWordWrap(True)
        self.virtue_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.progress = QProgressBar()
        self.progress.setObjectName("progress")
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(3)
        self.progress.setMaximum(100)
        self.progress.setValue(100)
        
        layout.addLayout(header)
        layout.addWidget(self.thikr_label, 1)
        layout.addWidget(self.virtue_label)
        layout.addWidget(self.progress)
        
        self.apply_theme()
        
        # Animations
        self.show_anim = QPropertyAnimation(self, b"windowOpacity")
        self.show_anim.setDuration(300)
        self.show_anim.setStartValue(0.0)
        self.show_anim.setEndValue(self.settings.get('popup.opacity', 0.95))
        self.show_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.hide_anim = QPropertyAnimation(self, b"windowOpacity")
        self.hide_anim.setDuration(300)
        self.hide_anim.setEndValue(0.0)
        self.hide_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self.hide_anim.finished.connect(self.on_closed)
    
    def apply_theme(self):
        t = self.settings.get_theme()
        fs = self.settings.get('popup.font_size', 20)
        br = self.settings.get('popup.border_radius', 15)
        
        bg = t['bg_gradient']
        gradient = f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {bg[0]}, stop:0.5 {bg[1]}, stop:1 {bg[2]})"
        
        self.setStyleSheet(f"""
            #container {{
                background: {gradient};
                border: 2px solid {t['border']};
                border-radius: {br}px;
            }}
            #title {{
                color: {t['accent']};
                font-size: 14px;
                font-weight: bold;
            }}
            #closeBtn {{
                background: transparent;
                color: {t['secondary']};
                border: none;
                font-size: 16px;
                border-radius: 14px;
            }}
            #closeBtn:hover {{
                background: rgba(255,255,255,0.1);
                color: {t['text']};
            }}
            #thikr {{
                color: {t['text']};
                font-size: {fs}px;
                padding: 10px;
            }}
            #virtue {{
                color: {t['secondary']};
                font-size: {fs-4}px;
                font-style: italic;
            }}
            #progress {{
                background: rgba(255,255,255,0.1);
                border: none;
                border-radius: 2px;
            }}
            #progress::chunk {{
                background: {t['accent']};
                border-radius: 2px;
            }}
        """)
        
        # Glow effect
        glow = QGraphicsDropShadowEffect(self)
        glow.setBlurRadius(25)
        glow.setColor(QColor(t['glow']))
        glow.setOffset(0, 0)
        self.container.setGraphicsEffect(glow)
    
    def show_thikr(self, data, is_surah=False):
        if is_surah:
            self.title.setText(f"📖 {data.get('name', 'سورة')}")
            verses = data.get('verses', [])
            self.thikr_label.setText('\n'.join(verses[:4]) + ('...' if len(verses) > 4 else ''))
            self.virtue_label.setText(data.get('virtue', ''))
        else:
            self.title.setText("ذِكْر")
            self.thikr_label.setText(data.get('text', ''))
            virtue = data.get('virtue', '')
            self.virtue_label.setText(virtue)
            self.virtue_label.setVisible(bool(virtue) and self.settings.get('reminder.show_virtue', True))
        
        self.position_popup()
        self.setWindowOpacity(0)
        self.show()
        self.show_anim.start()
        
        duration = self.settings.get('popup.duration_seconds', 8) * 1000
        self.close_timer.start(duration)
        self.progress_value = 100
        self.progress.setValue(100)
        self.progress_timer.start(duration // 100)
    
    def position_popup(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        pos = self.settings.get('popup.position', 'bottom_right')
        margin = 20
        
        positions = {
            'top_left': (margin, margin),
            'top_right': (screen.width() - self.width() - margin, margin),
            'top_center': ((screen.width() - self.width()) // 2, margin),
            'bottom_left': (margin, screen.height() - self.height() - margin),
            'bottom_right': (screen.width() - self.width() - margin, screen.height() - self.height() - margin),
            'bottom_center': ((screen.width() - self.width()) // 2, screen.height() - self.height() - margin),
            'center': ((screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2)
        }
        
        x, y = positions.get(pos, positions['bottom_right'])
        self.move(int(x), int(y))
    
    def update_progress(self):
        self.progress_value -= 1
        self.progress.setValue(max(0, self.progress_value))
        if self.progress_value <= 0:
            self.progress_timer.stop()
    
    def start_close(self):
        self.close_timer.stop()
        self.progress_timer.stop()
        self.hide_anim.setStartValue(self.windowOpacity())
        self.hide_anim.start()
    
    def on_closed(self):
        self.hide()
        self.closed.emit()
    
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
    
    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self.drag_pos)


# ============================================
# خيط التذكير
# ============================================

class ReminderThread(QThread):
    show_reminder = pyqtSignal(dict, bool)
    
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.running = True
        self.paused = False
    
    def run(self):
        while self.running:
            if not self.paused and self.settings.get('reminder.enabled', True):
                if not self.is_quiet_time():
                    if self.should_show_surah():
                        surah = self.settings.get_random_surah()
                        if surah:
                            self.show_reminder.emit(surah, True)
                            self.settings.set('surah_reminder.last_shown', datetime.now().isoformat())
                    else:
                        thikr = self.settings.get_random_thikr()
                        self.show_reminder.emit(thikr, False)
            
            interval = self.settings.get('reminder.interval_minutes', 60) * 60
            for _ in range(interval):
                if not self.running:
                    break
                time.sleep(1)
    
    def is_quiet_time(self):
        q = self.settings.get('reminder.quiet_hours', {})
        if not q.get('enabled'):
            return False
        
        now = datetime.now().time()
        start = datetime.strptime(q.get('start', '23:00'), '%H:%M').time()
        end = datetime.strptime(q.get('end', '06:00'), '%H:%M').time()
        
        if start <= end:
            return start <= now <= end
        return now >= start or now <= end
    
    def should_show_surah(self):
        if not self.settings.get('surah_reminder.enabled', True):
            return False
        
        last = self.settings.get('surah_reminder.last_shown')
        if not last:
            return True
        
        try:
            last_date = datetime.fromisoformat(last)
            days = self.settings.get('surah_reminder.interval_days', 3)
            return datetime.now() - last_date >= timedelta(days=days)
        except:
            return True
    
    def stop(self):
        self.running = False
    
    def pause(self):
        self.paused = True
    
    def resume(self):
        self.paused = False


# ============================================
# نافذة الإعدادات
# ============================================

class SettingsWindow(QMainWindow):
    settings_changed = pyqtSignal()
    
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.setup_ui()
        self.load_values()
    
    def setup_ui(self):
        self.setWindowTitle("ذِكْر - الإعدادات")
        self.setMinimumSize(700, 550)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header = QFrame()
        header.setFixedHeight(70)
        header.setObjectName("header")
        h_layout = QHBoxLayout(header)
        title = QLabel("⚙️ إعدادات ذِكْر")
        title.setObjectName("headerTitle")
        h_layout.addWidget(title)
        main_layout.addWidget(header)
        
        # Tabs
        tabs = QTabWidget()
        tabs.setObjectName("tabs")
        tabs.addTab(self.create_reminder_tab(), "🔔 التذكيرات")
        tabs.addTab(self.create_appearance_tab(), "🎨 المظهر")
        tabs.addTab(self.create_sound_tab(), "🔊 الصوت")
        tabs.addTab(self.create_athkar_tab(), "📿 الأذكار")
        tabs.addTab(self.create_stats_tab(), "📊 الإحصائيات")
        main_layout.addWidget(tabs)
        
        # Buttons
        btn_frame = QFrame()
        btn_frame.setObjectName("btnFrame")
        btn_layout = QHBoxLayout(btn_frame)
        
        self.preview_btn = QPushButton("👁️ معاينة")
        self.preview_btn.clicked.connect(self.preview)
        self.cancel_btn = QPushButton("❌ إلغاء")
        self.cancel_btn.clicked.connect(self.close)
        self.save_btn = QPushButton("💾 حفظ")
        self.save_btn.setObjectName("saveBtn")
        self.save_btn.clicked.connect(self.save_settings)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.preview_btn)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        main_layout.addWidget(btn_frame)
        
        self.apply_style()
    
    def create_reminder_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(15)
        
        # التشغيل التلقائي
        g0 = QGroupBox("التشغيل التلقائي")
        l0 = QVBoxLayout(g0)
        
        self.autostart_cb = QCheckBox("تشغيل البرنامج مع بدء Windows")
        l0.addWidget(self.autostart_cb)
        
        # زر للتحقق من الحالة
        self.autostart_status = QLabel("")
        self.autostart_status.setObjectName("statusLabel")
        l0.addWidget(self.autostart_status)
        self.update_autostart_status()
        
        layout.addWidget(g0)
        
        # Main reminders
        g1 = QGroupBox("التذكيرات الأساسية")
        l1 = QVBoxLayout(g1)
        
        self.reminder_cb = QCheckBox("تفعيل التذكيرات")
        l1.addWidget(self.reminder_cb)
        
        h = QHBoxLayout()
        h.addWidget(QLabel("الفترة (دقيقة):"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 1440)
        h.addWidget(self.interval_spin)
        h.addStretch()
        l1.addLayout(h)
        
        self.random_cb = QCheckBox("ترتيب عشوائي")
        self.virtue_cb = QCheckBox("إظهار الفضيلة")
        l1.addWidget(self.random_cb)
        l1.addWidget(self.virtue_cb)
        layout.addWidget(g1)
        
        # Quiet hours
        g2 = QGroupBox("وقت الهدوء")
        l2 = QVBoxLayout(g2)
        
        self.quiet_cb = QCheckBox("تفعيل وقت الهدوء")
        l2.addWidget(self.quiet_cb)
        
        h2 = QHBoxLayout()
        h2.addWidget(QLabel("من:"))
        self.quiet_start = QTimeEdit()
        self.quiet_start.setDisplayFormat("HH:mm")
        h2.addWidget(self.quiet_start)
        h2.addWidget(QLabel("إلى:"))
        self.quiet_end = QTimeEdit()
        self.quiet_end.setDisplayFormat("HH:mm")
        h2.addWidget(self.quiet_end)
        h2.addStretch()
        l2.addLayout(h2)
        layout.addWidget(g2)
        
        # Surah reminder
        g3 = QGroupBox("تذكير السور")
        l3 = QVBoxLayout(g3)
        
        self.surah_cb = QCheckBox("تفعيل تذكير السور")
        l3.addWidget(self.surah_cb)
        
        h3 = QHBoxLayout()
        h3.addWidget(QLabel("كل (يوم):"))
        self.surah_spin = QSpinBox()
        self.surah_spin.setRange(1, 30)
        h3.addWidget(self.surah_spin)
        h3.addStretch()
        l3.addLayout(h3)
        layout.addWidget(g3)
        
        layout.addStretch()
        return w
    
    def create_appearance_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(15)
        
        # Theme
        g1 = QGroupBox("الثيم")
        l1 = QVBoxLayout(g1)
        self.theme_combo = QComboBox()
        for k, v in THEMES.items():
            self.theme_combo.addItem(v['name'], k)
        l1.addWidget(self.theme_combo)
        layout.addWidget(g1)
        
        # Popup settings
        g2 = QGroupBox("النافذة المنبثقة")
        l2 = QVBoxLayout(g2)
        
        h1 = QHBoxLayout()
        h1.addWidget(QLabel("الموضع:"))
        self.pos_combo = QComboBox()
        positions = [("أعلى اليسار", "top_left"), ("أعلى اليمين", "top_right"),
                    ("أعلى الوسط", "top_center"), ("أسفل اليسار", "bottom_left"),
                    ("أسفل اليمين", "bottom_right"), ("أسفل الوسط", "bottom_center"),
                    ("وسط الشاشة", "center")]
        for n, v in positions:
            self.pos_combo.addItem(n, v)
        h1.addWidget(self.pos_combo)
        h1.addStretch()
        l2.addLayout(h1)
        
        h2 = QHBoxLayout()
        h2.addWidget(QLabel("حجم الخط:"))
        self.font_spin = QSpinBox()
        self.font_spin.setRange(14, 36)
        h2.addWidget(self.font_spin)
        h2.addStretch()
        l2.addLayout(h2)
        
        h3 = QHBoxLayout()
        h3.addWidget(QLabel("المدة (ثانية):"))
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(3, 60)
        h3.addWidget(self.duration_spin)
        h3.addStretch()
        l2.addLayout(h3)
        
        h4 = QHBoxLayout()
        h4.addWidget(QLabel("العرض:"))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(300, 800)
        h4.addWidget(self.width_spin)
        h4.addWidget(QLabel("الارتفاع:"))
        self.height_spin = QSpinBox()
        self.height_spin.setRange(150, 400)
        h4.addWidget(self.height_spin)
        h4.addStretch()
        l2.addLayout(h4)
        
        h5 = QHBoxLayout()
        h5.addWidget(QLabel("الشفافية:"))
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(50, 100)
        self.opacity_label = QLabel("95%")
        self.opacity_slider.valueChanged.connect(lambda v: self.opacity_label.setText(f"{v}%"))
        h5.addWidget(self.opacity_slider)
        h5.addWidget(self.opacity_label)
        l2.addLayout(h5)
        
        layout.addWidget(g2)
        layout.addStretch()
        return w
    
    def create_sound_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        
        g = QGroupBox("الصوت")
        l = QVBoxLayout(g)
        
        self.sound_cb = QCheckBox("تفعيل الصوت")
        l.addWidget(self.sound_cb)
        
        h = QHBoxLayout()
        h.addWidget(QLabel("مستوى الصوت:"))
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_label = QLabel("30%")
        self.volume_slider.valueChanged.connect(lambda v: self.volume_label.setText(f"{v}%"))
        h.addWidget(self.volume_slider)
        h.addWidget(self.volume_label)
        l.addLayout(h)
        
        layout.addWidget(g)
        layout.addStretch()
        return w
    
    def create_athkar_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        
        g = QGroupBox("الأذكار المخصصة")
        l = QVBoxLayout(g)
        
        self.athkar_list = QListWidget()
        self.athkar_list.setMinimumHeight(150)
        l.addWidget(self.athkar_list)
        
        h1 = QHBoxLayout()
        self.add_btn = QPushButton("➕ إضافة")
        self.add_btn.clicked.connect(self.add_thikr)
        self.del_btn = QPushButton("🗑️ حذف")
        self.del_btn.clicked.connect(self.del_thikr)
        h1.addWidget(self.add_btn)
        h1.addWidget(self.del_btn)
        h1.addStretch()
        l.addLayout(h1)
        
        l.addWidget(QLabel("نص الذكر:"))
        self.thikr_input = QLineEdit()
        self.thikr_input.setPlaceholderText("أدخل الذكر...")
        l.addWidget(self.thikr_input)
        
        l.addWidget(QLabel("الفضيلة (اختياري):"))
        self.virtue_input = QLineEdit()
        self.virtue_input.setPlaceholderText("أدخل الفضيلة...")
        l.addWidget(self.virtue_input)
        
        layout.addWidget(g)
        return w
    
    def create_stats_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        
        g = QGroupBox("الإحصائيات")
        l = QVBoxLayout(g)
        
        self.daily_label = QLabel("أذكار اليوم: 0")
        self.daily_label.setObjectName("statLabel")
        self.total_label = QLabel("الإجمالي: 0")
        self.total_label.setObjectName("statLabel")
        
        l.addWidget(self.daily_label)
        l.addWidget(self.total_label)
        
        reset_btn = QPushButton("🔄 إعادة تعيين")
        reset_btn.clicked.connect(self.reset_stats)
        l.addWidget(reset_btn)
        
        layout.addWidget(g)
        layout.addStretch()
        return w
    
    def load_values(self):
        # Reminders
        self.reminder_cb.setChecked(self.settings.get('reminder.enabled', True))
        self.interval_spin.setValue(self.settings.get('reminder.interval_minutes', 60))
        self.random_cb.setChecked(self.settings.get('reminder.random_order', True))
        self.virtue_cb.setChecked(self.settings.get('reminder.show_virtue', True))
        
        self.quiet_cb.setChecked(self.settings.get('reminder.quiet_hours.enabled', False))
        self.quiet_start.setTime(QTime.fromString(self.settings.get('reminder.quiet_hours.start', '23:00'), 'HH:mm'))
        self.quiet_end.setTime(QTime.fromString(self.settings.get('reminder.quiet_hours.end', '06:00'), 'HH:mm'))
        
        self.surah_cb.setChecked(self.settings.get('surah_reminder.enabled', True))
        self.surah_spin.setValue(self.settings.get('surah_reminder.interval_days', 3))
        
        # Appearance
        idx = self.theme_combo.findData(self.settings.get('popup.theme', 'cyberpunk_dark'))
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        
        idx = self.pos_combo.findData(self.settings.get('popup.position', 'bottom_right'))
        if idx >= 0:
            self.pos_combo.setCurrentIndex(idx)
        
        self.font_spin.setValue(self.settings.get('popup.font_size', 20))
        self.duration_spin.setValue(self.settings.get('popup.duration_seconds', 8))
        self.width_spin.setValue(self.settings.get('popup.width', 450))
        self.height_spin.setValue(self.settings.get('popup.height', 220))
        self.opacity_slider.setValue(int(self.settings.get('popup.opacity', 0.95) * 100))
        
        # Sound
        self.sound_cb.setChecked(self.settings.get('sound.enabled', True))
        self.volume_slider.setValue(self.settings.get('sound.volume', 30))
        
        # Custom athkar
        for a in self.settings.get('custom_athkar', []):
            self.athkar_list.addItem(a.get('text', ''))
        
        # Stats
        self.update_stats()
    
    def update_stats(self):
        self.daily_label.setText(f"أذكار اليوم: {self.settings.get('stats.daily_count', 0)}")
        self.total_label.setText(f"الإجمالي: {self.settings.get('stats.total_count', 0)}")
    
    def save_settings(self):
        # حفظ إعداد التشغيل التلقائي
        self.set_autostart(self.autostart_cb.isChecked())
        
        self.settings.set('reminder.enabled', self.reminder_cb.isChecked())
        self.settings.set('reminder.interval_minutes', self.interval_spin.value())
        self.settings.set('reminder.random_order', self.random_cb.isChecked())
        self.settings.set('reminder.show_virtue', self.virtue_cb.isChecked())
        
        self.settings.set('reminder.quiet_hours.enabled', self.quiet_cb.isChecked())
        self.settings.set('reminder.quiet_hours.start', self.quiet_start.time().toString('HH:mm'))
        self.settings.set('reminder.quiet_hours.end', self.quiet_end.time().toString('HH:mm'))
        
        self.settings.set('surah_reminder.enabled', self.surah_cb.isChecked())
        self.settings.set('surah_reminder.interval_days', self.surah_spin.value())
        
        self.settings.set('popup.theme', self.theme_combo.currentData())
        self.settings.set('popup.position', self.pos_combo.currentData())
        self.settings.set('popup.font_size', self.font_spin.value())
        self.settings.set('popup.duration_seconds', self.duration_spin.value())
        self.settings.set('popup.width', self.width_spin.value())
        self.settings.set('popup.height', self.height_spin.value())
        self.settings.set('popup.opacity', self.opacity_slider.value() / 100)
        
        self.settings.set('sound.enabled', self.sound_cb.isChecked())
        self.settings.set('sound.volume', self.volume_slider.value())
        
        self.settings_changed.emit()
        QMessageBox.information(self, "تم", "تم حفظ الإعدادات!")
        self.close()
    
    def add_thikr(self):
        text = self.thikr_input.text().strip()
        if text:
            custom = self.settings.get('custom_athkar', [])
            custom.append({'text': text, 'virtue': self.virtue_input.text().strip(), 'category': 'مخصص'})
            self.settings.set('custom_athkar', custom)
            self.athkar_list.addItem(text)
            self.thikr_input.clear()
            self.virtue_input.clear()
    
    def del_thikr(self):
        row = self.athkar_list.currentRow()
        if row >= 0:
            self.athkar_list.takeItem(row)
            custom = self.settings.get('custom_athkar', [])
            if row < len(custom):
                custom.pop(row)
                self.settings.set('custom_athkar', custom)
    
    def reset_stats(self):
        if QMessageBox.question(self, "تأكيد", "إعادة تعيين الإحصائيات؟") == QMessageBox.StandardButton.Yes:
            self.settings.set('stats.daily_count', 0)
            self.settings.set('stats.total_count', 0)
            self.update_stats()
    
    def preview(self):
        self.settings.set('popup.theme', self.theme_combo.currentData())
        self.settings.set('popup.position', self.pos_combo.currentData())
        self.settings.set('popup.font_size', self.font_spin.value())
        self.settings.set('popup.duration_seconds', self.duration_spin.value())
        self.settings.set('popup.width', self.width_spin.value())
        self.settings.set('popup.height', self.height_spin.value())
        self.settings.set('popup.opacity', self.opacity_slider.value() / 100)
        
        popup = ReminderPopup(self.settings)
        popup.show_thikr({'text': 'سُبْحَانَ اللَّهِ وَبِحَمْدِهِ', 'virtue': 'كلمتان خفيفتان على اللسان'})
    
    def get_startup_path(self):
        """الحصول على مسار مجلد Startup في Windows"""
        if sys.platform == 'win32':
            import winreg
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
                startup_path = winreg.QueryValueEx(key, "Startup")[0]
                winreg.CloseKey(key)
                return Path(startup_path)
            except:
                # مسار بديل
                return Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        return None
    
    def get_shortcut_path(self):
        """الحصول على مسار ملف الاختصار"""
        startup = self.get_startup_path()
        if startup:
            return startup / "ذكر.bat"
        return None
    
    def is_autostart_enabled(self):
        """التحقق من تفعيل التشغيل التلقائي"""
        shortcut = self.get_shortcut_path()
        if shortcut:
            return shortcut.exists()
        return False
    
    def update_autostart_status(self):
        """تحديث حالة التشغيل التلقائي"""
        if self.is_autostart_enabled():
            self.autostart_cb.setChecked(True)
            self.autostart_status.setText("✅ مفعّل - سيعمل مع بدء Windows")
            self.autostart_status.setStyleSheet("color: #00ff88;")
        else:
            self.autostart_cb.setChecked(False)
            self.autostart_status.setText("❌ غير مفعّل")
            self.autostart_status.setStyleSheet("color: #ff6b6b;")
    
    def set_autostart(self, enable):
        """تفعيل أو إلغاء التشغيل التلقائي"""
        if sys.platform != 'win32':
            QMessageBox.warning(self, "تنبيه", "هذه الميزة متاحة فقط على Windows")
            return
        
        shortcut_path = self.get_shortcut_path()
        if not shortcut_path:
            return
        
        if enable:
            # إنشاء ملف BAT للتشغيل
            app_path = Path(__file__).parent.resolve()
            bat_content = f'''@echo off
chcp 65001 >nul
cd /d "{app_path}"
start "" pythonw thikr.py
exit
'''
            try:
                with open(shortcut_path, 'w', encoding='utf-8') as f:
                    f.write(bat_content)
                self.autostart_status.setText("✅ تم التفعيل!")
                self.autostart_status.setStyleSheet("color: #00ff88;")
            except Exception as e:
                QMessageBox.warning(self, "خطأ", f"فشل تفعيل التشغيل التلقائي:\n{e}")
        else:
            # حذف ملف الاختصار
            try:
                if shortcut_path.exists():
                    shortcut_path.unlink()
                self.autostart_status.setText("❌ تم الإلغاء")
                self.autostart_status.setStyleSheet("color: #ff6b6b;")
            except Exception as e:
                QMessageBox.warning(self, "خطأ", f"فشل إلغاء التشغيل التلقائي:\n{e}")
    
    def apply_style(self):
        t = self.settings.get_theme()
        is_light = t.get('is_light', False)
        
        # ألوان الخلفية حسب نوع الثيم
        if is_light:
            bg = t['bg_gradient']
            main_bg = f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {bg[0]}, stop:0.5 {bg[1]}, stop:1 {bg[2]})"
            overlay_bg = "rgba(255,255,255,0.7)"
            input_bg = "rgba(255,255,255,0.9)"
            item_border = "rgba(0,0,0,0.1)"
            dropdown_bg = "#ffffff"
            tab_selected_text = "#fff"
        else:
            main_bg = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0a0a0f, stop:0.5 #1a1a2e, stop:1 #0f0f1a)"
            overlay_bg = "rgba(0,0,0,0.3)"
            input_bg = "rgba(0,0,0,0.3)"
            item_border = "rgba(255,255,255,0.1)"
            dropdown_bg = "#1a1a2e"
            tab_selected_text = "#000"
        
        self.setStyleSheet(f"""
            QMainWindow {{
                background: {main_bg};
            }}
            #header {{
                background: {overlay_bg};
                border-bottom: 2px solid {t['border']};
            }}
            #headerTitle {{
                color: {t['text']};
                font-size: 22px;
                font-weight: bold;
            }}
            QTabWidget::pane {{
                border: 1px solid {t['border']};
                background: {overlay_bg};
                border-radius: 8px;
                margin: 8px;
            }}
            QTabBar::tab {{
                background: {overlay_bg};
                color: {t['secondary']};
                padding: 10px 18px;
                margin: 2px;
                border-radius: 6px;
            }}
            QTabBar::tab:selected {{
                background: {t['accent']};
                color: {tab_selected_text};
            }}
            QGroupBox {{
                color: {t['text']};
                font-size: 14px;
                font-weight: bold;
                border: 1px solid {t['border']};
                border-radius: 8px;
                margin-top: 12px;
                padding: 12px;
                background: {overlay_bg};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top right;
                padding: 4px 8px;
                color: {t['accent']};
            }}
            QLabel {{
                color: {t['secondary']};
                font-size: 13px;
            }}
            #statLabel {{
                color: {t['text']};
                font-size: 16px;
                font-weight: bold;
            }}
            QCheckBox {{
                color: {t['secondary']};
                font-size: 13px;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {t['border']};
                border-radius: 4px;
                background: {input_bg};
            }}
            QCheckBox::indicator:checked {{
                background: {t['accent']};
                border-color: {t['accent']};
            }}
            QSpinBox, QTimeEdit, QComboBox {{
                background: {input_bg};
                color: {t['text']};
                border: 1px solid {t['border']};
                border-radius: 4px;
                padding: 6px;
                min-width: 80px;
            }}
            QComboBox QAbstractItemView {{
                background: {dropdown_bg};
                color: {t['text']};
                selection-background-color: {t['accent']};
            }}
            QSlider::groove:horizontal {{
                height: 6px;
                background: {input_bg};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                width: 16px;
                height: 16px;
                background: {t['accent']};
                border-radius: 8px;
                margin: -5px 0;
            }}
            QSlider::sub-page:horizontal {{
                background: {t['accent']};
                border-radius: 3px;
            }}
            QLineEdit {{
                background: {input_bg};
                color: {t['text']};
                border: 1px solid {t['border']};
                border-radius: 4px;
                padding: 8px;
            }}
            QListWidget {{
                background: {input_bg};
                color: {t['text']};
                border: 1px solid {t['border']};
                border-radius: 4px;
            }}
            QListWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {item_border};
            }}
            QListWidget::item:selected {{
                background: {t['accent']};
                color: {tab_selected_text};
            }}
            QPushButton {{
                background: {input_bg};
                color: {t['secondary']};
                border: 1px solid {t['border']};
                border-radius: 6px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background: {t['accent']};
                color: {tab_selected_text};
            }}
            #saveBtn {{
                background: {t['accent']};
                color: {tab_selected_text};
                font-weight: bold;
            }}
            #btnFrame {{
                background: {overlay_bg};
                border-top: 1px solid {t['border']};
                padding: 12px;
            }}
        """)


# ============================================
# التطبيق الرئيسي
# ============================================

class ThikrApp(QObject):
    def __init__(self):
        super().__init__()
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        
        self.settings = SettingsManager()
        self.popup = None
        self.settings_window = None
        self.reminder_thread = None
        
        self.setup_tray()
        self.start_reminder()
    
    def setup_tray(self):
        self.tray = QSystemTrayIcon(self.app)
        
        # Create icon - أيقونة واضحة ومميزة
        pm = QPixmap(64, 64)
        pm.fill(Qt.GlobalColor.transparent)
        
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        
        # خلفية دائرية خضراء إسلامية
        grad = QRadialGradient(32, 32, 30)
        grad.setColorAt(0, QColor(0, 180, 100))      # أخضر فاتح في المنتصف
        grad.setColorAt(0.7, QColor(0, 140, 80))     # أخضر متوسط
        grad.setColorAt(1, QColor(0, 100, 60))       # أخضر داكن في الأطراف
        
        p.setBrush(QBrush(grad))
        p.setPen(QPen(QColor(255, 255, 255), 2))     # حدود بيضاء
        p.drawEllipse(2, 2, 60, 60)
        
        # حرف "ذ" كبير وواضح
        p.setPen(QPen(QColor(255, 255, 255)))
        font = QFont("Arial", 32, QFont.Weight.Bold)
        p.setFont(font)
        p.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, "ذ")
        p.end()
        
        self.tray.setIcon(QIcon(pm))
        self.tray.setToolTip("ذِكْر - تذكير بذكر الله")
        
        # Menu
        menu = QMenu()
        
        show_action = QAction("📿 عرض ذكر", menu)
        show_action.triggered.connect(self.show_now)
        menu.addAction(show_action)
        
        # أذكار الصباح والمساء
        morning_action = QAction("🌅 أذكار الصباح", menu)
        morning_action.triggered.connect(self.show_morning_athkar)
        menu.addAction(morning_action)
        
        evening_action = QAction("🌙 أذكار المساء", menu)
        evening_action.triggered.connect(self.show_evening_athkar)
        menu.addAction(evening_action)
        
        menu.addSeparator()
        
        self.pause_action = QAction("⏸️ إيقاف مؤقت", menu)
        self.pause_action.triggered.connect(self.toggle_pause)
        menu.addAction(self.pause_action)
        
        menu.addSeparator()
        
        settings_action = QAction("⚙️ الإعدادات", menu)
        settings_action.triggered.connect(self.show_settings)
        menu.addAction(settings_action)
        
        stats_action = QAction("📊 الإحصائيات", menu)
        stats_action.triggered.connect(self.show_stats)
        menu.addAction(stats_action)
        
        menu.addSeparator()
        
        exit_action = QAction("❌ خروج", menu)
        exit_action.triggered.connect(self.quit)
        menu.addAction(exit_action)
        
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self.on_tray_click)
        self.tray.show()
    
    def start_reminder(self):
        self.reminder_thread = ReminderThread(self.settings)
        self.reminder_thread.show_reminder.connect(self.show_popup)
        self.reminder_thread.start()
    
    def show_popup(self, data, is_surah=False):
        if self.popup:
            self.popup.close()
            self.popup.deleteLater()
        
        self.popup = ReminderPopup(self.settings)
        self.popup.closed.connect(self.on_popup_closed)
        self.popup.show_thikr(data, is_surah)
        self.settings.increment_counter()
    
    def on_popup_closed(self):
        if self.popup:
            self.popup.deleteLater()
            self.popup = None
    
    def show_now(self):
        thikr = self.settings.get_random_thikr()
        self.show_popup(thikr, False)
    
    def show_morning_athkar(self):
        """عرض أذكار الصباح"""
        self.current_athkar_list = MORNING_ATHKAR.copy()
        self.current_athkar_index = 0
        self.athkar_type = "morning"
        self.show_next_thikr_in_list()
    
    def show_evening_athkar(self):
        """عرض أذكار المساء"""
        self.current_athkar_list = EVENING_ATHKAR.copy()
        self.current_athkar_index = 0
        self.athkar_type = "evening"
        self.show_next_thikr_in_list()
    
    def show_next_thikr_in_list(self):
        """عرض الذكر التالي في القائمة"""
        if hasattr(self, 'current_athkar_list') and self.current_athkar_index < len(self.current_athkar_list):
            thikr = self.current_athkar_list[self.current_athkar_index]
            repeat = thikr.get('repeat', 1)
            title = "🌅 أذكار الصباح" if self.athkar_type == "morning" else "🌙 أذكار المساء"
            
            # إضافة عدد التكرار للعنوان
            count_text = f" (تكرر {repeat} مرة)" if repeat > 1 else ""
            progress = f"[{self.current_athkar_index + 1}/{len(self.current_athkar_list)}]"
            
            display_thikr = {
                'text': thikr['text'],
                'virtue': f"{thikr.get('virtue', '')} {count_text}".strip(),
                'title': f"{title} {progress}"
            }
            
            if self.popup:
                self.popup.close()
                self.popup.deleteLater()
            
            self.popup = ReminderPopup(self.settings)
            self.popup.title.setText(display_thikr['title'])
            self.popup.closed.connect(self.on_athkar_popup_closed)
            self.popup.show_thikr(display_thikr, False)
            self.settings.increment_counter()
        else:
            # انتهت الأذكار
            type_name = "الصباح" if self.athkar_type == "morning" else "المساء"
            self.tray.showMessage("ذِكْر", f"تمت أذكار {type_name} ✅\nجزاك الله خيراً", 
                                 QSystemTrayIcon.MessageIcon.Information, 3000)
    
    def on_athkar_popup_closed(self):
        """عند إغلاق نافذة الذكر، عرض التالي"""
        if self.popup:
            self.popup.deleteLater()
            self.popup = None
        
        if hasattr(self, 'current_athkar_list'):
            self.current_athkar_index += 1
            # تأخير بسيط قبل عرض الذكر التالي
            QTimer.singleShot(500, self.show_next_thikr_in_list)
    
    def toggle_pause(self):
        if self.reminder_thread:
            if self.reminder_thread.paused:
                self.reminder_thread.resume()
                self.pause_action.setText("⏸️ إيقاف مؤقت")
                self.tray.showMessage("ذِكْر", "تم استئناف التذكيرات", QSystemTrayIcon.MessageIcon.Information, 2000)
            else:
                self.reminder_thread.pause()
                self.pause_action.setText("▶️ استئناف")
                self.tray.showMessage("ذِكْر", "تم إيقاف التذكيرات", QSystemTrayIcon.MessageIcon.Information, 2000)
    
    def show_settings(self):
        if not self.settings_window or not self.settings_window.isVisible():
            self.settings_window = SettingsWindow(self.settings)
            self.settings_window.settings_changed.connect(self.on_settings_changed)
        self.settings_window.show()
        self.settings_window.activateWindow()
    
    def on_settings_changed(self):
        if self.reminder_thread:
            self.reminder_thread.settings = self.settings
    
    def show_stats(self):
        daily = self.settings.get('stats.daily_count', 0)
        total = self.settings.get('stats.total_count', 0)
        self.tray.showMessage("📊 الإحصائيات", f"أذكار اليوم: {daily}\nالإجمالي: {total}", 
                             QSystemTrayIcon.MessageIcon.Information, 4000)
    
    def on_tray_click(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_settings()
        elif reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_now()
    
    def quit(self):
        if self.reminder_thread:
            self.reminder_thread.stop()
            self.reminder_thread.wait(2000)
        
        if self.popup:
            self.popup.close()
        if self.settings_window:
            self.settings_window.close()
        
        self.tray.hide()
        self.app.quit()
    
    def run(self):
        self.tray.showMessage("ذِكْر", "البرنامج يعمل الآن\nانقر مرتين للإعدادات", 
                             QSystemTrayIcon.MessageIcon.Information, 3000)
        return self.app.exec()


def main():
    app = ThikrApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
