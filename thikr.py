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
import subprocess
import winsound
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
import winreg
import tempfile
import atexit
import msvcrt

# Timezone support
try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Fallback for Python < 3.9
    try:
        from backports.zoneinfo import ZoneInfo
    except ImportError:
        # If no timezone library available, create a simple UTC offset class
        class ZoneInfo:
            def __init__(self, tz_string):
                # Simple UTC+3 implementation as fallback
                self.offset = timedelta(hours=3)
                self.name = tz_string

            def utcoffset(self, dt):
                return self.offset

            def tzname(self, dt):
                return self.name

            def dst(self, dt):
                return timedelta(0)

# ============================================
# Single Instance Lock (Robust - handles stale locks)
# ============================================

_lock_file = None
_lock_path = None

def is_process_running(pid):
    """Check if a process with given PID is still running"""
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        SYNCHRONIZE = 0x00100000
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = kernel32.OpenProcess(SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return False
    except:
        return False

def acquire_single_instance_lock():
    """Prevent multiple instances from running - handles stale locks from crashes/reboots"""
    global _lock_file, _lock_path
    _lock_path = Path(tempfile.gettempdir()) / "thikr_instance.lock"

    # First attempt
    try:
        _lock_file = open(_lock_path, 'w+')
        msvcrt.locking(_lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        # Write our PID so we can be identified
        _lock_file.seek(0)
        _lock_file.write(str(os.getpid()))
        _lock_file.flush()
        atexit.register(release_lock)
        return True
    except (OSError, IOError):
        # Lock failed - check if the other process is still alive
        if _lock_file:
            _lock_file.close()
            _lock_file = None

        try:
            # Read the PID from lock file
            with open(_lock_path, 'r') as f:
                content = f.read().strip()
                if content:
                    old_pid = int(content)
                    if is_process_running(old_pid):
                        # Another instance is truly running
                        return False

            # Stale lock - remove it and try again
            try:
                os.remove(_lock_path)
            except:
                pass

            # Second attempt after removing stale lock
            _lock_file = open(_lock_path, 'w+')
            msvcrt.locking(_lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            _lock_file.seek(0)
            _lock_file.write(str(os.getpid()))
            _lock_file.flush()
            atexit.register(release_lock)
            return True
        except:
            return False

def release_lock():
    """Release the single instance lock and clean up"""
    global _lock_file, _lock_path
    if _lock_file:
        try:
            msvcrt.locking(_lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            _lock_file.close()
        except:
            pass
        _lock_file = None

    # Clean up lock file
    if _lock_path and _lock_path.exists():
        try:
            os.remove(_lock_path)
        except:
            pass

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
except ImportError as e:
    # In compiled executable, dependencies are bundled
    # Show a simple error and exit gracefully
    import ctypes
    ctypes.windll.user32.MessageBoxW(
        0, 
        "خطأ: المكتبات المطلوبة غير موجودة\n\nError: Required libraries not found\n\n" + str(e), 
        "ذِكْر - خطأ", 
        0x10  # MB_ICONERROR
    )
    sys.exit(1)


# ============================================
# الثوابت والمسارات
# ============================================

def get_base_path():
    """الحصول على المسار الأساسي للتطبيق - يدعم التجميع والتطوير"""
    if getattr(sys, 'frozen', False):
        # تشغيل من ملف مجمّع (PyInstaller)
        return Path(sys.executable).parent
    return Path(__file__).parent.resolve()

def get_appdata_path():
    """الحصول على مسار AppData لحفظ بيانات المستخدم"""
    # استخدام متغير البيئة APPDATA (أكثر موثوقية)
    appdata = os.environ.get('APPDATA')
    if appdata:
        return Path(appdata) / "Thikr"
    
    # Fallback: استخدام مجلد المستخدم
    try:
        return Path.home() / "AppData" / "Roaming" / "Thikr"
    except Exception:
        # Fallback نهائي: المجلد الحالي
        return get_base_path() / "data"

APP_NAME = "ذِكْر"
APP_VERSION = "1.0.0"
APP_DIR = get_base_path()

# بيانات المستخدم في AppData (تبقى عند تحديث التطبيق)
DATA_DIR = get_appdata_path()

# لا نحتاج مجلد sounds منفصل في النسخة المجمّعة
SOUNDS_DIR = APP_DIR / "sounds"

# إنشاء مجلد البيانات مع معالجة الأخطاء
def ensure_data_directory():
    """التأكد من وجود مجلد البيانات"""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        return True
    except PermissionError:
        print(f"تحذير: لا يمكن إنشاء مجلد البيانات في {DATA_DIR}")
        return False
    except Exception as e:
        print(f"خطأ غير متوقع: {e}")
        return False

# إنشاء المجلدات عند بدء التشغيل
ensure_data_directory()


# ============================================
# Simple Debug Logging (for troubleshooting)
# ============================================

LOG_FILE = DATA_DIR / "thikr_debug.log"
DEBUG_ENABLED = True  # Set to False to disable logging

def log_debug(message):
    """Write debug message to log file"""
    if not DEBUG_ENABLED:
        return
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {message}\n")
    except:
        pass

def clear_old_logs():
    """Clear log file if it gets too large (>1MB)"""
    try:
        if LOG_FILE.exists() and LOG_FILE.stat().st_size > 1024 * 1024:
            LOG_FILE.unlink()
    except:
        pass

# Clear old logs on startup
clear_old_logs()
log_debug("=" * 50)
log_debug("App starting...")


# ============================================
# Timezone Helper Functions
# ============================================

def get_app_timezone(tz_string="UTC+3"):
    """Get the application timezone (default UTC+3)"""
    try:
        # Try to parse custom UTC offset format
        if tz_string.startswith("UTC"):
            offset_str = tz_string[3:]  # Remove 'UTC' prefix
            if offset_str:
                sign = 1 if offset_str[0] == '+' else -1
                hours = int(offset_str[1:]) if len(offset_str) > 1 else 0
                offset = timedelta(hours=sign * hours)
                return timezone(offset, name=tz_string)
        # For standard timezone names, use ZoneInfo
        return ZoneInfo(tz_string)
    except:
        # Fallback to UTC+3
        return timezone(timedelta(hours=3), name="UTC+3")


def get_now(tz_string="UTC+3"):
    """Get current datetime with timezone awareness"""
    tz = get_app_timezone(tz_string)
    return datetime.now(tz)


# ============================================
# وظائف التشغيل التلقائي (Windows Registry)
# ============================================

def get_app_launch_command():
    """Get the command to launch this app at startup, works for both .exe and source."""
    if getattr(sys, 'frozen', False):
        # Running as compiled .exe - always reliable
        return f'"{sys.executable}" --silent'
    else:
        # Running from Python source
        python_path = sys.executable
        # Convert python.exe to pythonw.exe for no console window
        if python_path.lower().endswith('python.exe'):
            pythonw_path = python_path[:-10] + 'pythonw.exe'
            if Path(pythonw_path).exists():
                python_path = pythonw_path
        script_path = Path(__file__).resolve()
        return f'"{python_path}" "{script_path}" --silent'


def get_autostart_enabled():
    """التحقق من تفعيل التشغيل التلقائي عبر Registry"""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_READ
        )
        try:
            winreg.QueryValueEx(key, "Thikr")
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
    except Exception:
        return False


def set_autostart_enabled(enable: bool):
    """تفعيل/إلغاء التشغيل التلقائي باستخدام Registry فقط (لا يحتاج صلاحيات مسؤول)"""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        if enable:
            exe_path = get_app_launch_command()
            winreg.SetValueEx(key, "Thikr", 0, winreg.REG_SZ, exe_path)
            log_debug(f"Auto-start enabled with path: {exe_path}")
        else:
            try:
                winreg.DeleteValue(key, "Thikr")
            except FileNotFoundError:
                pass
            # Clean up any legacy auto-start methods
            cleanup_legacy_autostart()
            log_debug("Auto-start disabled and legacy methods cleaned up")
        winreg.CloseKey(key)
        return True
    except Exception as e:
        log_debug(f"Autostart error: {e}")
        return False


def cleanup_legacy_autostart():
    """Remove old Task Scheduler tasks and Startup folder .bat files from previous versions"""
    # Remove Task Scheduler task if it exists
    try:
        subprocess.run(
            ['schtasks', '/Delete', '/TN', 'ThikrReminder', '/F'],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
    except Exception:
        pass

    # Remove Startup folder .bat files
    try:
        startup_path = Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        for bat_name in ["ذكر.bat", "Thikr.bat"]:
            bat_file = startup_path / bat_name
            if bat_file.exists():
                bat_file.unlink(missing_ok=True)
                log_debug(f"Removed legacy startup file: {bat_file}")
    except Exception:
        pass


def verify_and_fix_autostart_path():
    """If auto-start is enabled, ensure the registry points to the current .exe location.
    Handles cases where the user moved the app folder after installation."""
    if not get_autostart_enabled():
        return
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_READ
        )
        stored_path, _ = winreg.QueryValueEx(key, "Thikr")
        winreg.CloseKey(key)

        expected_path = get_app_launch_command()
        if stored_path != expected_path:
            set_autostart_enabled(True)  # Re-register with current path
            log_debug(f"Updated autostart path from '{stored_path}' to '{expected_path}'")
    except Exception as e:
        log_debug(f"verify_and_fix_autostart_path error: {e}")


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
                "interval_minutes": 1,  # Default to 1 minute
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
            "timezone": "UTC+3",  # Default timezone
            "custom_athkar": [],
            "first_run_complete": False  # Track if first run setup is done
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
        tz = self.get('timezone', 'UTC+3')
        today = get_now(tz).strftime("%Y-%m-%d")
        if self.get('stats.last_reset') != today:
            self.set('stats.daily_count', 0)
            self.set('stats.last_reset', today)

        daily = self.get('stats.daily_count', 0) + 1
        total = self.get('stats.total_count', 0) + 1
        self.set('stats.daily_count', daily)
        self.set('stats.total_count', total)
        return daily, total


# ============================================
# نافذة الإعداد الأول (First Run)
# ============================================

class FirstRunDialog(QWidget):
    """نافذة ترحيبية تظهر عند التشغيل الأول"""
    setup_complete = pyqtSignal(bool)  # True = enable autostart
    
    def __init__(self):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(450, 350)
        self.setup_ui()
        self.center_on_screen()
        
        # Animation timer
        self.progress_value = 0
        self.progress_timer = QTimer(self)
        self.progress_timer.timeout.connect(self.update_progress)
    
    def setup_ui(self):
        # Main container with beautiful styling
        self.container = QFrame(self)
        self.container.setGeometry(0, 0, 450, 350)
        self.container.setObjectName("container")
        
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        
        # Title with moon emoji
        title = QLabel("🌙 ذِكْر")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Welcome message
        welcome = QLabel("مرحباً بك في برنامج التذكير بذكر الله")
        welcome.setObjectName("welcome")
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome.setWordWrap(True)
        
        # Progress container
        progress_container = QFrame()
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setContentsMargins(0, 20, 0, 10)
        
        self.progress = QProgressBar()
        self.progress.setObjectName("progress")
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        
        self.status_label = QLabel("جاري تهيئة البرنامج...")
        self.status_label.setObjectName("status")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        progress_layout.addWidget(self.progress)
        progress_layout.addWidget(self.status_label)
        
        # Autostart checkbox (default checked)
        self.autostart_cb = QCheckBox("تشغيل البرنامج مع بدء Windows")
        self.autostart_cb.setObjectName("checkbox")
        self.autostart_cb.setChecked(True)
        self.autostart_cb.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        
        # Start button (hidden initially)
        self.start_btn = QPushButton("ابدأ الآن")
        self.start_btn.setObjectName("startBtn")
        self.start_btn.setFixedHeight(45)
        self.start_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.start_btn.clicked.connect(self.on_start_clicked)
        self.start_btn.setVisible(False)
        
        layout.addWidget(title)
        layout.addWidget(welcome)
        layout.addWidget(progress_container)
        layout.addWidget(self.autostart_cb)
        layout.addStretch()
        layout.addWidget(self.start_btn)
        
        self.apply_style()
        
        # Add glow effect
        glow = QGraphicsDropShadowEffect(self)
        glow.setBlurRadius(30)
        glow.setColor(QColor("#00ffff"))
        glow.setOffset(0, 0)
        self.container.setGraphicsEffect(glow)
    
    def apply_style(self):
        self.setStyleSheet("""
            #container {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #0a0a0f, stop:0.5 #1a1a2e, stop:1 #0f0f1a);
                border: 2px solid #00ffff;
                border-radius: 20px;
            }
            #title {
                color: #00ffff;
                font-size: 36px;
                font-weight: bold;
                padding: 10px;
            }
            #welcome {
                color: #ffffff;
                font-size: 18px;
                padding: 5px;
            }
            #progress {
                background: rgba(255,255,255,0.1);
                border: none;
                border-radius: 4px;
            }
            #progress::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00ffff, stop:1 #ff00ff);
                border-radius: 4px;
            }
            #status {
                color: #00ff88;
                font-size: 14px;
            }
            #checkbox {
                color: #ffffff;
                font-size: 15px;
                spacing: 10px;
            }
            #checkbox::indicator {
                width: 20px;
                height: 20px;
            }
            #checkbox::indicator:unchecked {
                border: 2px solid #00ffff;
                border-radius: 4px;
                background: transparent;
            }
            #checkbox::indicator:checked {
                border: 2px solid #00ffff;
                border-radius: 4px;
                background: #00ffff;
            }
            #startBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00ffff, stop:1 #00ff88);
                color: #000000;
                font-size: 18px;
                font-weight: bold;
                border: none;
                border-radius: 10px;
            }
            #startBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00ff88, stop:1 #00ffff);
            }
        """)
    
    def center_on_screen(self):
        screen = QGuiApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
    
    def start_setup(self):
        self.show()
        self.progress_timer.start(30)  # Fast animation
    
    def update_progress(self):
        self.progress_value += 2
        self.progress.setValue(min(100, self.progress_value))
        
        # Update status text at different stages
        if self.progress_value == 30:
            self.status_label.setText("جاري تحميل الأذكار...")
        elif self.progress_value == 60:
            self.status_label.setText("جاري إعداد الواجهة...")
        elif self.progress_value == 90:
            self.status_label.setText("جاهز! ✓")
        
        if self.progress_value >= 100:
            self.progress_timer.stop()
            self.start_btn.setVisible(True)
    
    def on_start_clicked(self):
        enable_autostart = self.autostart_cb.isChecked()
        self.setup_complete.emit(enable_autostart)
        self.close()
    
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
    
    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.MouseButton.LeftButton and hasattr(self, 'drag_pos'):
            self.move(e.globalPosition().toPoint() - self.drag_pos)


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

        # Show with animation, but ensure visibility even if animation fails
        try:
            self.setWindowOpacity(0)
            self.show()
            self.raise_()  # Bring to front
            self.activateWindow()  # Activate window
            self.show_anim.start()

            # Fallback: Force visibility after 500ms if animation didn't work
            QTimer.singleShot(500, self.ensure_visible)
        except Exception as e:
            log_debug(f"Animation error, forcing visibility: {e}")
            self.setWindowOpacity(self.settings.get('popup.opacity', 0.95))
            self.show()
            self.raise_()

        duration = self.settings.get('popup.duration_seconds', 8) * 1000
        self.close_timer.start(duration)
        self.progress_value = 100
        self.progress.setValue(100)
        self.progress_timer.start(duration // 100)

    def ensure_visible(self):
        """Fallback to ensure popup is visible if animation failed"""
        if self.isVisible() and self.windowOpacity() < 0.1:
            log_debug("Forcing popup visibility (animation may have failed)")
            self.setWindowOpacity(self.settings.get('popup.opacity', 0.95))

    def position_popup(self):
        try:
            screen = QGuiApplication.primaryScreen()
            if screen is None:
                log_debug("No primary screen found, using fallback position")
                self.move(100, 100)
                return

            geom = screen.availableGeometry()
            if geom.width() <= 0 or geom.height() <= 0:
                log_debug(f"Invalid screen geometry: {geom}, using fallback")
                self.move(100, 100)
                return

            pos = self.settings.get('popup.position', 'bottom_right')
            margin = 20

            positions = {
                'top_left': (margin, margin),
                'top_right': (geom.width() - self.width() - margin, margin),
                'top_center': ((geom.width() - self.width()) // 2, margin),
                'bottom_left': (margin, geom.height() - self.height() - margin),
                'bottom_right': (geom.width() - self.width() - margin, geom.height() - self.height() - margin),
                'bottom_center': ((geom.width() - self.width()) // 2, geom.height() - self.height() - margin),
                'center': ((geom.width() - self.width()) // 2, (geom.height() - self.height()) // 2)
            }

            x, y = positions.get(pos, positions['bottom_right'])
            # Ensure coordinates are valid (on screen)
            x = max(0, min(int(x), geom.width() - self.width()))
            y = max(0, min(int(y), geom.height() - self.height()))
            self.move(x, y)
            log_debug(f"Popup positioned at ({x}, {y})")
        except Exception as e:
            log_debug(f"Error positioning popup: {e}, using fallback")
            self.move(100, 100)
    
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
# خيط التذكير (Robust - with exception handling and auto-recovery)
# ============================================

class ReminderThread(QThread):
    show_reminder = pyqtSignal(dict, bool)
    thread_error = pyqtSignal(str)  # Signal for error reporting
    thread_started = pyqtSignal()   # Signal when thread starts successfully

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.running = True
        self.paused = False
        self.error_count = 0
        self.max_errors = 5  # Max consecutive errors before giving up
        self.first_run = True  # Flag for showing reminder sooner on first run

    def run(self):
        log_debug("ReminderThread started")
        self.thread_started.emit()

        while self.running:
            try:
                enabled = self.settings.get('reminder.enabled', True)
                paused = self.paused
                quiet = self.is_quiet_time()

                log_debug(f"ReminderThread loop: enabled={enabled}, paused={paused}, quiet={quiet}, first_run={self.first_run}")

                # On first run, show reminder after a short delay (10 seconds)
                if self.first_run:
                    self.first_run = False
                    log_debug("First run - waiting 10 seconds...")
                    # Wait 10 seconds before first reminder (instead of full interval)
                    for _ in range(10):
                        if not self.running:
                            break
                        time.sleep(1)

                    if self.running and not paused and enabled:
                        if not quiet:
                            thikr = self.settings.get_random_thikr()
                            log_debug(f"Emitting first reminder: {thikr.get('text', '')[:30]}...")
                            self.show_reminder.emit(thikr, False)
                            self.error_count = 0
                        else:
                            log_debug("Skipped first reminder - quiet time")
                    else:
                        log_debug(f"Skipped first reminder - running={self.running}, paused={paused}, enabled={enabled}")
                else:
                    # Normal reminder cycle (not first run)
                    if not paused and enabled:
                        if not quiet:
                            if self.should_show_surah():
                                surah = self.settings.get_random_surah()
                                if surah:
                                    log_debug(f"Emitting surah reminder: {surah.get('name', '')}")
                                    self.show_reminder.emit(surah, True)
                                    tz = self.settings.get('timezone', 'UTC+3')
                                    self.settings.set('surah_reminder.last_shown', get_now(tz).isoformat())
                            else:
                                thikr = self.settings.get_random_thikr()
                                log_debug(f"Emitting thikr reminder: {thikr.get('text', '')[:30]}...")
                                self.show_reminder.emit(thikr, False)
                            self.error_count = 0
                        else:
                            log_debug("Skipped reminder - quiet time")
                    else:
                        log_debug(f"Skipped reminder - paused={paused}, enabled={enabled}")

                # Wait for interval before next reminder
                interval = self.settings.get('reminder.interval_minutes', 1) * 60
                log_debug(f"Waiting {interval} seconds until next reminder...")
                for _ in range(interval):
                    if not self.running:
                        break
                    time.sleep(1)

            except Exception as e:
                self.error_count += 1
                error_msg = f"ReminderThread error ({self.error_count}/{self.max_errors}): {str(e)}"
                self.thread_error.emit(error_msg)

                if self.error_count >= self.max_errors:
                    # Too many errors - signal for restart
                    self.thread_error.emit("CRITICAL: Max errors reached, thread needs restart")
                    break

                # Wait before retrying to avoid rapid error loops
                time.sleep(5)

    def is_quiet_time(self):
        try:
            q = self.settings.get('reminder.quiet_hours', {})
            if not q.get('enabled'):
                return False

            tz = self.settings.get('timezone', 'UTC+3')
            now = get_now(tz).time()
            start = datetime.strptime(q.get('start', '23:00'), '%H:%M').time()
            end = datetime.strptime(q.get('end', '06:00'), '%H:%M').time()

            if start <= end:
                return start <= now <= end
            return now >= start or now <= end
        except:
            return False  # Default to not quiet time if there's an error

    def should_show_surah(self):
        try:
            if not self.settings.get('surah_reminder.enabled', True):
                return False

            last = self.settings.get('surah_reminder.last_shown')
            if not last:
                return True

            last_date = datetime.fromisoformat(last)
            tz = self.settings.get('timezone', 'UTC+3')
            now = get_now(tz)

            # Make last_date timezone-aware if it isn't already
            if last_date.tzinfo is None:
                tz_obj = get_app_timezone(tz)
                last_date = last_date.replace(tzinfo=tz_obj)

            days = self.settings.get('surah_reminder.interval_days', 3)
            return now - last_date >= timedelta(days=days)
        except:
            return False  # Default to regular thikr if there's an error

    def stop(self):
        self.running = False

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def reset_for_restart(self):
        """Reset state for thread restart"""
        self.running = True
        self.paused = False
        self.error_count = 0
        self.first_run = False  # Don't show immediate reminder on restart


# ============================================
# Helper: Create App Icon
# ============================================

def create_app_icon():
    """Create the ذ app icon - used for tray and windows"""
    pm = QPixmap(64, 64)
    pm.fill(Qt.GlobalColor.transparent)
    
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    
    # خلفية دائرية خضراء إسلامية
    grad = QRadialGradient(32, 32, 30)
    grad.setColorAt(0, QColor(0, 180, 100))
    grad.setColorAt(0.7, QColor(0, 140, 80))
    grad.setColorAt(1, QColor(0, 100, 60))
    
    p.setBrush(QBrush(grad))
    p.setPen(QPen(QColor(255, 255, 255), 2))
    p.drawEllipse(2, 2, 60, 60)
    
    # حرف "ذ" كبير وواضح
    p.setPen(QPen(QColor(255, 255, 255)))
    font = QFont("Arial", 32, QFont.Weight.Bold)
    p.setFont(font)
    p.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, "ذ")
    p.end()
    
    return QIcon(pm)


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
        self.setMinimumSize(700, 840)  # Increased height +20%
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        
        # Set window icon (same as tray icon)
        self.setWindowIcon(create_app_icon())
        
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
        tabs.addTab(self.create_about_tab(), "ℹ️ حول")
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

    def create_about_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # App Title
        title = QLabel("🌙 ذِكْر - Thikr")
        title.setObjectName("aboutTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Brief Description
        desc = QLabel("برنامج للتذكير بذكر الله يعمل في الخلفية")
        desc.setObjectName("aboutDesc")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)

        layout.addSpacing(20)

        # Info Group
        info_group = QGroupBox("معلومات هامة")
        info_layout = QVBoxLayout(info_group)
        info_layout.setSpacing(12)

        info_items = [
            "📍 البرنامج يعمل من شريط المهام (بجانب الساعة)",
            "⚙️ للإعدادات: انقر مرتين على أيقونة ذ",
            "📿 لعرض ذكر: انقر مرة واحدة على الأيقونة",
            "⏸️ للإيقاف المؤقت: انقر يمين ← إيقاف مؤقت",
        ]

        for item in info_items:
            lbl = QLabel(item)
            lbl.setWordWrap(True)
            info_layout.addWidget(lbl)

        layout.addWidget(info_group)

        # Important Notice
        notice_group = QGroupBox("⚠️ تنبيه مهم")
        notice_layout = QVBoxLayout(notice_group)

        notice = QLabel(
            "أغلق هذه النافذة الآن!\n\n"
            "البرنامج يعمل دائماً في الخلفية.\n"
            "لا حاجة لإبقاء هذه النافذة مفتوحة."
        )
        notice.setObjectName("noticeLabel")
        notice.setAlignment(Qt.AlignmentFlag.AlignCenter)
        notice.setWordWrap(True)
        notice_layout.addWidget(notice)

        layout.addWidget(notice_group)

        layout.addStretch()

        # Version
        version = QLabel(f"الإصدار {APP_VERSION}")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)

        return w

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
        self.interval_spin.setFixedWidth(80)
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
        self.quiet_start.setFixedWidth(80)
        h2.addWidget(self.quiet_start)
        h2.addWidget(QLabel("إلى:"))
        self.quiet_end = QTimeEdit()
        self.quiet_end.setDisplayFormat("HH:mm")
        self.quiet_end.setFixedWidth(80)
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
        self.surah_spin.setFixedWidth(80)
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
        self.font_spin.setFixedWidth(80)
        h2.addWidget(self.font_spin)
        h2.addStretch()
        l2.addLayout(h2)
        
        h3 = QHBoxLayout()
        h3.addWidget(QLabel("المدة (ثانية):"))
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(3, 60)
        self.duration_spin.setFixedWidth(80)
        h3.addWidget(self.duration_spin)
        h3.addStretch()
        l2.addLayout(h3)
        
        h4 = QHBoxLayout()
        h4.addWidget(QLabel("العرض:"))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(300, 800)
        self.width_spin.setFixedWidth(80)
        h4.addWidget(self.width_spin)
        h4.addWidget(QLabel("الارتفاع:"))
        self.height_spin = QSpinBox()
        self.height_spin.setRange(150, 400)
        self.height_spin.setFixedWidth(80)
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
        
        # Get all unique categories from default athkar
        self.all_categories = list(set(a.get('category', 'مخصص') for a in DEFAULT_ATHKAR))
        self.all_categories.append('مخصص')
        self.all_categories = sorted(set(self.all_categories))
        
        # Category filter
        filter_group = QGroupBox("تصفية حسب التصنيف")
        filter_layout = QHBoxLayout(filter_group)
        filter_layout.addWidget(QLabel("التصنيف:"))
        self.category_filter = QComboBox()
        self.category_filter.addItem("📿 الكل", "all")
        for cat in self.all_categories:
            self.category_filter.addItem(cat, cat)
        self.category_filter.currentIndexChanged.connect(self.filter_athkar_list)
        filter_layout.addWidget(self.category_filter)
        filter_layout.addStretch()
        layout.addWidget(filter_group)
        
        # Athkar list
        g = QGroupBox("الأذكار")
        l = QVBoxLayout(g)
        
        self.athkar_list = QListWidget()
        self.athkar_list.setMinimumHeight(200)
        self.athkar_list.itemClicked.connect(self.on_thikr_selected)
        l.addWidget(self.athkar_list)
        
        # Buttons
        h1 = QHBoxLayout()
        self.add_btn = QPushButton("➕ إضافة")
        self.add_btn.clicked.connect(self.add_thikr)
        self.edit_btn = QPushButton("✏️ تعديل")
        self.edit_btn.clicked.connect(self.edit_thikr)
        self.del_btn = QPushButton("🗑️ حذف")
        self.del_btn.clicked.connect(self.del_thikr)
        self.clear_btn = QPushButton("🔄 جديد")
        self.clear_btn.clicked.connect(self.clear_thikr_form)
        h1.addWidget(self.add_btn)
        h1.addWidget(self.edit_btn)
        h1.addWidget(self.del_btn)
        h1.addWidget(self.clear_btn)
        h1.addStretch()
        l.addLayout(h1)
        
        # Input form
        form_frame = QFrame()
        form_layout = QVBoxLayout(form_frame)
        
        form_layout.addWidget(QLabel("نص الذكر:"))
        self.thikr_input = QLineEdit()
        self.thikr_input.setPlaceholderText("أدخل الذكر...")
        form_layout.addWidget(self.thikr_input)
        
        form_layout.addWidget(QLabel("الفضيلة (اختياري):"))
        self.virtue_input = QLineEdit()
        self.virtue_input.setPlaceholderText("أدخل الفضيلة...")
        form_layout.addWidget(self.virtue_input)
        
        cat_layout = QHBoxLayout()
        cat_layout.addWidget(QLabel("التصنيف:"))
        self.category_input = QComboBox()
        for cat in self.all_categories:
            self.category_input.addItem(cat, cat)
        cat_layout.addWidget(self.category_input)
        cat_layout.addStretch()
        form_layout.addLayout(cat_layout)
        
        l.addWidget(form_frame)
        
        layout.addWidget(g)
        
        # Track editing state
        self.editing_thikr_id = None
        self.editing_is_custom = False
        
        return w
    
    def get_all_athkar(self):
        """Get combined list of default + custom athkar"""
        deleted_ids = self.settings.get('deleted_default_athkar', [])
        modified = self.settings.get('modified_athkar', {})
        
        all_athkar = []
        
        # Add default athkar (with modifications applied)
        for thikr in DEFAULT_ATHKAR:
            if thikr['id'] in deleted_ids:
                continue
            thikr_copy = thikr.copy()
            thikr_copy['is_custom'] = False
            # Apply modifications if any
            if str(thikr['id']) in modified:
                thikr_copy.update(modified[str(thikr['id'])])
            all_athkar.append(thikr_copy)
        
        # Add custom athkar
        custom = self.settings.get('custom_athkar', [])
        for i, thikr in enumerate(custom):
            thikr_copy = thikr.copy()
            thikr_copy['id'] = f'custom_{i}'
            thikr_copy['is_custom'] = True
            thikr_copy['category'] = thikr.get('category', 'مخصص')
            all_athkar.append(thikr_copy)
        
        return all_athkar
    
    def filter_athkar_list(self):
        """Filter and display athkar based on selected category"""
        self.athkar_list.clear()
        selected_cat = self.category_filter.currentData()
        
        for thikr in self.get_all_athkar():
            if selected_cat != "all" and thikr.get('category', 'مخصص') != selected_cat:
                continue
            
            # Display with icon
            icon = "⭐" if thikr.get('is_custom') else "📌"
            cat = thikr.get('category', 'مخصص')
            display_text = f"{icon} {thikr['text'][:50]}{'...' if len(thikr['text']) > 50 else ''} [{cat}]"
            
            item = self.athkar_list.addItem(display_text)
            # Store thikr data with item
            self.athkar_list.item(self.athkar_list.count() - 1).setData(Qt.ItemDataRole.UserRole, thikr)
    
    def on_thikr_selected(self, item):
        """Populate form when thikr is selected"""
        thikr = item.data(Qt.ItemDataRole.UserRole)
        if thikr:
            self.thikr_input.setText(thikr.get('text', ''))
            self.virtue_input.setText(thikr.get('virtue', ''))
            
            # Set category
            cat = thikr.get('category', 'مخصص')
            idx = self.category_input.findData(cat)
            if idx >= 0:
                self.category_input.setCurrentIndex(idx)
            
            self.editing_thikr_id = thikr.get('id')
            self.editing_is_custom = thikr.get('is_custom', False)
    
    def clear_thikr_form(self):
        """Clear the form for new entry"""
        self.thikr_input.clear()
        self.virtue_input.clear()
        self.category_input.setCurrentIndex(0)
        self.editing_thikr_id = None
        self.editing_is_custom = False
        self.athkar_list.clearSelection()
    
    def edit_thikr(self):
        """Save edits to selected thikr"""
        if self.editing_thikr_id is None:
            QMessageBox.warning(self, "تنبيه", "الرجاء اختيار ذكر للتعديل")
            return
        
        text = self.thikr_input.text().strip()
        if not text:
            QMessageBox.warning(self, "تنبيه", "الرجاء إدخال نص الذكر")
            return
        
        virtue = self.virtue_input.text().strip()
        category = self.category_input.currentData()
        
        if self.editing_is_custom:
            # Edit custom thikr
            custom = self.settings.get('custom_athkar', [])
            idx = int(str(self.editing_thikr_id).replace('custom_', ''))
            if 0 <= idx < len(custom):
                custom[idx] = {'text': text, 'virtue': virtue, 'category': category}
                self.settings.set('custom_athkar', custom)
        else:
            # Edit default thikr (store modification)
            modified = self.settings.get('modified_athkar', {})
            modified[str(self.editing_thikr_id)] = {'text': text, 'virtue': virtue, 'category': category}
            self.settings.set('modified_athkar', modified)
        
        self.filter_athkar_list()
        self.clear_thikr_form()
        QMessageBox.information(self, "تم", "تم تعديل الذكر!")
    
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
        self.interval_spin.setValue(self.settings.get('reminder.interval_minutes', 1))
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
        
        # Athkar - populate the enhanced list
        self.filter_athkar_list()
        
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
        """Add new custom thikr"""
        text = self.thikr_input.text().strip()
        if not text:
            QMessageBox.warning(self, "تنبيه", "الرجاء إدخال نص الذكر")
            return
        
        virtue = self.virtue_input.text().strip()
        category = self.category_input.currentData() if hasattr(self, 'category_input') else 'مخصص'
        
        custom = self.settings.get('custom_athkar', [])
        custom.append({'text': text, 'virtue': virtue, 'category': category})
        self.settings.set('custom_athkar', custom)
        
        self.filter_athkar_list()
        self.clear_thikr_form()
        QMessageBox.information(self, "تم", "تمت إضافة الذكر!")
    
    def del_thikr(self):
        """Delete selected thikr"""
        if self.editing_thikr_id is None:
            QMessageBox.warning(self, "تنبيه", "الرجاء اختيار ذكر للحذف")
            return
        
        if QMessageBox.question(self, "تأكيد", "هل تريد حذف هذا الذكر؟") != QMessageBox.StandardButton.Yes:
            return
        
        if self.editing_is_custom:
            # Delete custom thikr
            custom = self.settings.get('custom_athkar', [])
            idx = int(str(self.editing_thikr_id).replace('custom_', ''))
            if 0 <= idx < len(custom):
                custom.pop(idx)
                self.settings.set('custom_athkar', custom)
        else:
            # Mark default thikr as deleted
            deleted = self.settings.get('deleted_default_athkar', [])
            if self.editing_thikr_id not in deleted:
                deleted.append(self.editing_thikr_id)
                self.settings.set('deleted_default_athkar', deleted)
        
        self.filter_athkar_list()
        self.clear_thikr_form()
        QMessageBox.information(self, "تم", "تم حذف الذكر!")
    
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
    
    def is_autostart_enabled(self):
        """التحقق من تفعيل التشغيل التلقائي عبر Registry"""
        return get_autostart_enabled()

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
        """تفعيل أو إلغاء التشغيل التلقائي عبر Registry"""
        success = set_autostart_enabled(enable)
        if success:
            if enable:
                self.autostart_status.setText("✅ تم التفعيل!")
                self.autostart_status.setStyleSheet("color: #00ff88;")
            else:
                self.autostart_status.setText("❌ تم الإلغاء")
                self.autostart_status.setStyleSheet("color: #ff6b6b;")
        else:
            QMessageBox.warning(self, "خطأ", "فشل تغيير إعداد التشغيل التلقائي")
    
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
                font-weight: bold;
                margin-right: 10px;
            }}
            #statLabel {{
                color: {t['text']};
                font-size: 16px;
                font-weight: bold;
            }}
            #aboutTitle {{
                color: #ffffff;
                font-size: 28px;
                font-weight: bold;
            }}
            #aboutDesc {{
                color: #ffffff;
                font-size: 16px;
            }}
            #noticeLabel {{
                color: #ffffff;
                font-size: 15px;
                font-weight: bold;
                padding: 15px;
            }}
            QCheckBox {{
                color: {t['secondary']};
                font-size: 13px;
                font-weight: bold;
                spacing: 12px;
                margin-right: 10px;
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
                margin-left: 8px;
                font-weight: bold;
            }}
            QComboBox QAbstractItemView {{
                background: {dropdown_bg};
                color: {t['text']};
                selection-background-color: {t['accent']};
            }}
            QSpinBox::up-button, QTimeEdit::up-button {{
                background: {t['accent']};
                border: none;
                border-radius: 3px;
                width: 20px;
                margin: 2px;
            }}
            QSpinBox::down-button, QTimeEdit::down-button {{
                background: {t['accent']};
                border: none;
                border-radius: 3px;
                width: 20px;
                margin: 2px;
            }}
            QSpinBox::up-button:hover, QTimeEdit::up-button:hover,
            QSpinBox::down-button:hover, QTimeEdit::down-button:hover {{
                background: {t['glow']};
            }}
            QSpinBox::up-arrow, QTimeEdit::up-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-bottom: 6px solid white;
                width: 0;
                height: 0;
            }}
            QSpinBox::down-arrow, QTimeEdit::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid white;
                width: 0;
                height: 0;
            }}
            QComboBox::drop-down {{
                background: {t['accent']};
                border: none;
                border-radius: 3px;
                width: 25px;
                margin: 2px;
            }}
            QComboBox::drop-down:hover {{
                background: {t['glow']};
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid white;
                width: 0;
                height: 0;
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
    def __init__(self, existing_app=None, existing_settings=None):
        super().__init__()
        # استخدام تطبيق موجود أو إنشاء جديد
        if existing_app:
            self.app = existing_app
        else:
            self.app = QApplication(sys.argv)
            self.app.setQuitOnLastWindowClosed(False)
        self.app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        # استخدام إعدادات موجودة أو إنشاء جديدة
        self.settings = existing_settings if existing_settings else SettingsManager()
        self.popup = None
        self.settings_window = None
        self.reminder_thread = None
        self.thread_restart_count = 0
        self.max_thread_restarts = 10  # Max restarts before giving up

        # Watchdog timer to ensure reminder thread stays alive
        self.watchdog_timer = QTimer(self)
        self.watchdog_timer.timeout.connect(self.check_reminder_thread)
        self.watchdog_timer.start(30000)  # Check every 30 seconds

        # Backup reminder timer (main thread) - fires if thread signals fail
        self.last_reminder_time = None
        self.backup_timer = QTimer(self)
        self.backup_timer.timeout.connect(self.backup_reminder_check)
        self.backup_timer.start(60000)  # Check every 60 seconds

        self.setup_tray()

        # Delay thread start slightly to ensure Qt event loop is ready
        QTimer.singleShot(2000, self.start_reminder)

        # Show a startup reminder after 15 seconds to confirm app is working
        QTimer.singleShot(15000, self.show_startup_reminder)

    def show_startup_reminder(self):
        """Show a reminder shortly after startup to confirm app is working"""
        if self.settings.get('reminder.enabled', True):
            # Only show if no reminder has been shown yet
            if self.last_reminder_time is None:
                log_debug("Showing startup reminder to confirm app is working")
                thikr = self.settings.get_random_thikr()
                self.show_popup(thikr, False)
    
    def setup_tray(self):
        self.tray = QSystemTrayIcon(self.app)
        
        # Use the shared app icon
        self.tray.setIcon(create_app_icon())
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
        """Start the reminder thread with error handling"""
        log_debug("start_reminder called")
        if self.reminder_thread and self.reminder_thread.isRunning():
            log_debug("Thread already running, skipping start")
            return  # Already running

        log_debug("Creating new ReminderThread...")
        self.reminder_thread = ReminderThread(self.settings)

        # Use QueuedConnection to ensure signals from thread are properly
        # delivered to main thread's event loop (critical for post-restart reliability)
        self.reminder_thread.show_reminder.connect(
            self.show_popup,
            Qt.ConnectionType.QueuedConnection
        )
        self.reminder_thread.thread_error.connect(
            self.on_thread_error,
            Qt.ConnectionType.QueuedConnection
        )
        self.reminder_thread.finished.connect(self.on_thread_finished)
        self.reminder_thread.start()
        log_debug("ReminderThread started successfully")

    def on_thread_error(self, error_msg):
        """Handle errors from reminder thread"""
        log_debug(f"Thread error: {error_msg}")

    def on_thread_finished(self):
        """Handle when reminder thread finishes (possibly due to error)"""
        log_debug(f"ReminderThread finished! restart_count={self.thread_restart_count}")
        if self.thread_restart_count < self.max_thread_restarts:
            # Auto-restart the thread after a short delay
            QTimer.singleShot(2000, self.restart_reminder_thread)

    def restart_reminder_thread(self):
        """Restart the reminder thread after it dies"""
        log_debug("Attempting to restart reminder thread...")
        if self.reminder_thread:
            if self.reminder_thread.isRunning():
                log_debug("Thread still running, no restart needed")
                return  # Still running, no need to restart

            self.thread_restart_count += 1
            log_debug(f"Restarting thread (attempt {self.thread_restart_count})")

            # Create new thread
            self.reminder_thread = ReminderThread(self.settings)
            self.reminder_thread.show_reminder.connect(self.show_popup)
            self.reminder_thread.thread_error.connect(self.on_thread_error)
            self.reminder_thread.finished.connect(self.on_thread_finished)
            self.reminder_thread.first_run = False  # Don't show immediate reminder on restart
            self.reminder_thread.start()

    def check_reminder_thread(self):
        """Watchdog: Check if reminder thread is still alive and restart if needed"""
        is_running = self.reminder_thread is not None and self.reminder_thread.isRunning()
        if not is_running:
            log_debug(f"Watchdog: Thread not running! restart_count={self.thread_restart_count}")
            if self.thread_restart_count < self.max_thread_restarts:
                self.restart_reminder_thread()

    def backup_reminder_check(self):
        """Backup mechanism: Show reminder from main thread if thread signals failed"""
        if not self.settings.get('reminder.enabled', True):
            return

        if self.reminder_thread and self.reminder_thread.paused:
            return

        interval_minutes = self.settings.get('reminder.interval_minutes', 1)
        now = datetime.now()

        # If no reminder has been shown for twice the interval, force one
        if self.last_reminder_time is None:
            # First check - just set the time
            self.last_reminder_time = now
            return

        elapsed_minutes = (now - self.last_reminder_time).total_seconds() / 60

        # If more than 2x interval has passed without a reminder, force one
        if elapsed_minutes > (interval_minutes * 2):
            log_debug(f"Backup timer: No reminder for {elapsed_minutes:.1f} min, forcing one")
            thikr = self.settings.get_random_thikr()
            self.show_popup(thikr, False)

    def show_popup(self, data, is_surah=False):
        log_debug(f"show_popup called! is_surah={is_surah}")
        try:
            if self.popup:
                self.popup.close()
                self.popup.deleteLater()

            self.popup = ReminderPopup(self.settings)
            self.popup.closed.connect(self.on_popup_closed)
            self.popup.show_thikr(data, is_surah)
            self.settings.increment_counter()

            # Track last reminder time for backup mechanism
            self.last_reminder_time = datetime.now()

            # Play notification sound if enabled
            self.play_notification_sound()
            log_debug("Popup shown successfully")
        except Exception as e:
            log_debug(f"Error showing popup: {e}")

    def play_notification_sound(self):
        """Play a notification sound when reminder shows"""
        if self.settings.get('sound.enabled', True):
            try:
                # Play Windows default notification sound in background thread
                def play_sound():
                    try:
                        # Use Windows system sound (asterisk/notification)
                        winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
                    except:
                        pass
                threading.Thread(target=play_sound, daemon=True).start()
            except:
                pass
    
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
        log_debug("App quitting...")
        # Stop all timers first
        if self.watchdog_timer:
            self.watchdog_timer.stop()
        if self.backup_timer:
            self.backup_timer.stop()

        # Prevent auto-restart during shutdown
        self.max_thread_restarts = 0

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
        # Open settings window on launch (About tab is first)
        self.show_settings()
        return self.app.exec()


def main():
    """نقطة الدخول الرئيسية مع دعم الإعداد الأول"""
    try:
        # دعم التجميد للتطبيقات المجمعة (PyInstaller)
        import multiprocessing
        multiprocessing.freeze_support()

        # Check for --silent flag (used by autostart)
        silent_mode = '--silent' in sys.argv or '-s' in sys.argv

        # Check single instance FIRST
        if not acquire_single_instance_lock():
            # If in silent mode, just exit quietly
            if not silent_mode:
                import ctypes
                ctypes.windll.user32.MessageBoxW(0, "البرنامج يعمل بالفعل!\n\nThe application is already running!", "ذِكْر", 0x40)
            sys.exit(0)

        # إنشاء تطبيق Qt أولاً
        qt_app = QApplication(sys.argv)
        qt_app.setQuitOnLastWindowClosed(False)

        # تحميل الإعدادات للتحقق من first_run
        settings = SettingsManager()

        # Debug: Log settings file location and first_run status
        log_debug(f"Settings file: {settings.settings_file}")
        log_debug(f"Settings file exists: {settings.settings_file.exists()}")
        log_debug(f"first_run_complete value: {settings.get('first_run_complete', False)}")

        # Clean up legacy auto-start methods (Task Scheduler, Startup .bat) from older versions
        cleanup_legacy_autostart()

        # If auto-start is enabled, verify the registry path matches current .exe location
        # This handles the case where the user moved the app folder
        verify_and_fix_autostart_path()

        # التحقق إذا كان التشغيل الأول
        if not settings.get('first_run_complete', False):
            # إظهار نافذة الإعداد الأول
            first_run_dialog = FirstRunDialog()

            def on_setup_complete(enable_autostart):
                # حفظ إعداد التشغيل التلقائي
                if enable_autostart:
                    set_autostart_enabled(True)

                # حفظ أن الإعداد الأول اكتمل
                settings.set('first_run_complete', True)
                settings.save()  # Ensure it's saved to disk
                log_debug(f"First run complete saved. File: {settings.settings_file}")

                # بدء التطبيق الرئيسي (not silent on first run)
                start_main_app(qt_app, settings, silent=False)

            first_run_dialog.setup_complete.connect(on_setup_complete)
            first_run_dialog.start_setup()
            sys.exit(qt_app.exec())
        else:
            # التشغيل العادي - use silent mode if specified
            start_main_app(qt_app, settings, silent=silent_mode)
            sys.exit(qt_app.exec())
    
    except Exception as e:
        # Global exception handler - show error dialog
        import ctypes
        import traceback
        error_msg = f"خطأ غير متوقع:\n{str(e)}\n\nUnexpected error:\n{traceback.format_exc()[:500]}"
        ctypes.windll.user32.MessageBoxW(0, error_msg, "ذِكْر - خطأ", 0x10)
        sys.exit(1)

# Global reference to prevent garbage collection
_app_instance = None

def start_main_app(qt_app, settings, silent=False):
    """بدء التطبيق الرئيسي بعد الإعداد الأول"""
    global _app_instance
    log_debug(f"start_main_app called, silent={silent}")
    _app_instance = ThikrApp(existing_app=qt_app, existing_settings=settings)
    log_debug("ThikrApp instance created")

    # Only show settings window if not starting silently
    # For autostart, we want to run silently in background
    if not silent:
        _app_instance.show_settings()
        log_debug("Settings window shown")
    else:
        # Show tray notification that app is running
        _app_instance.tray.showMessage(
            "ذِكْر",
            "يعمل في الخلفية - اضغط على الأيقونة للإعدادات",
            QSystemTrayIcon.MessageIcon.Information,
            3000
        )


if __name__ == "__main__":
    main()
