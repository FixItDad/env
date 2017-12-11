# Log to syslog
import logging
import logging.handlers

log = logging.getLogger('MyLogger')
log.setLevel(logging.DEBUG)

handler = logging.handlers.SysLogHandler(address= '/dev/log')

log.addHandler(handler)
log.info('Some message')
log.debug('Some debug')

