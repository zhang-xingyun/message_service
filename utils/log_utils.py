

import logging
import os


def log(message, file='receive.log'):
    path = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(path, file)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)  # 设置打印级别
    formatter = logging.Formatter(
        '%(asctime)s %(filename)s %(funcName)s '
        '[line:%(lineno)d] %(levelname)s %(message)s')

    # 设置屏幕打印的格式
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    logger.addHandler(sh)
    logger.removeHandler(sh)

    # 设置log保存
    fh = logging.FileHandler(log_path, encoding='utf8')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    logging.error(message)
    logger.removeHandler(fh)
