# Log to syslog
import logging
import logging.handlers

log = logging.getLogger('MyLogger')
log.setLevel(logging.DEBUG)

handler = logging.handlers.SysLogHandler(address= '/dev/log')

log.addHandler(handler)
log.info('Some message')
log.debug('Some debug')


# Singleton
class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

#Python2
class MyClass(BaseClass):
    __metaclass__ = Singleton

#Python3
class MyClass(BaseClass, metaclass=Singleton):
    pass
