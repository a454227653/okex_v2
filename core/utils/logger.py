"""
logger.py
created by Yan on 2023/4/18 20:10;
"""

import os
import sys
import shutil
import logging
import traceback
from logging.handlers import TimedRotatingFileHandler
from numpy.core.defchararray import lower
from core.utils.tools import get_now_date
import datetime

initialized = False


def set_log_lv(log_lv):
    log_lv = lower(log_lv)
    if log_lv=='error':
        logging.getLogger().setLevel(logging.ERROR)
    elif log_lv=='info':
        logging.getLogger().setLevel(logging.INFO)
    elif log_lv=='debug':
        logging.getLogger().setLevel(logging.DEBUG)

def beijing(sec, what):
    beijing_time = datetime.datetime.now() + datetime.timedelta(hours=8)
    return beijing_time.timetuple()


def initLogger(level="DEBUG", path=None, name=None, clear=False, backup_count=0, console=True):
    """Initialize logger.

    Args:
        level: Log level, `DEBUG` or `INFO`, default is `DEBUG`.
        path: Log path, default is `/var/log/aioquant`.
        name: Log file name, default is `quant.log`.
        clear: If clear all history log file when initialize, default is `False`.
        backup_count: How many log file to be saved. We will save log file per day at middle nigh,
            default is `0` to save file permanently.
        console: If print log to console, otherwise print to log file.
    """
    global initialized
    if initialized:
        return
    path = path or "/var/log/aioquant"
    name = name or "quant.log"
    # 修改logger的时间源
    logging.Formatter.converter = beijing
    logger = logging.getLogger()
    logger.setLevel(level)
    if console:
        print("logger init ...")
        handler = logging.StreamHandler()
    else:
        if clear and os.path.isdir(path):
            shutil.rmtree(path)
        if not os.path.isdir(path):
            os.makedirs(path)
        logfile = os.path.join(path, name)
        handler = TimedRotatingFileHandler(logfile, "midnight", backupCount=backup_count)
        print("init logger ...", logfile)
    fmt_str = "%(levelname)1.1s [%(asctime)s] %(message)s"
    fmt = logging.Formatter(fmt=fmt_str, datefmt=None)
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    initialized = True


def info(*args, **kwargs):
    func_name, kwargs = _log_msg_header(*args, **kwargs)
    logging.info(_log(func_name, *args, **kwargs))


def warn(*args, **kwargs):
    msg_header, kwargs = _log_msg_header(*args, **kwargs)
    logging.warning(_log(msg_header, *args, **kwargs))


def debug(*args, **kwargs):
    msg_header, kwargs = _log_msg_header(*args, **kwargs)
    logging.debug(_log(msg_header, *args, **kwargs))


def error(*args, **kwargs):
    logging.error("*" * 60)
    msg_header, kwargs = _log_msg_header(*args, **kwargs)
    logging.error(_log(msg_header, *args, **kwargs))
    logging.error("*" * 60)


def exception(*args, **kwargs):
    logging.error("*" * 60)
    msg_header, kwargs = _log_msg_header(*args, **kwargs)
    logging.error(_log(msg_header, *args, **kwargs))
    logging.error(traceback.format_exc())
    logging.error("*" * 60)


def _log(msg_header, *args, **kwargs):
    _log_msg = msg_header
    for l in args:
        _log_msg += str(l)
    if len(kwargs) > 0:
        _log_msg += str(kwargs)
    return _log_msg



def _log_msg_header(*args, **kwargs):
    """Fetch log message header.

    NOTE:
        logger.xxx(... , caller=self) for instance method.
        logger.xxx(... , caller=cls) for class method.
    """
    cls_name = ""
    func_name = sys._getframe().f_back.f_back.f_code.co_name
    time = get_now_date()
    try:
        _caller = kwargs.get("caller", None)
        if _caller:
            if not hasattr(_caller, "__name__"):
                _caller = _caller.__class__
            cls_name = _caller.__name__
            del kwargs["caller"]
    except:
        pass
    finally:
        msg_header = "[{time}] [{cls_name}.{func_name}] ".format(cls_name=cls_name, func_name=func_name,
                                                                       time=time)
        return msg_header, kwargs


class Error:

    def __init__(self, msg):
        self._msg = msg

    @property
    def msg(self):
        return self._msg

    def __str__(self):
        return str(self._msg)

    def __repr__(self):
        return str(self)