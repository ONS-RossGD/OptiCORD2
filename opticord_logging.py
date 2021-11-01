"""
"""
import logging, os

created_logs = [] # list to contain all of the logs in session

# ensure a logs folder is set up
if not os.path.isdir('logs'):
    os.mkdir('logs')

fname = 'logs/'+os.getlogin()+'.log' # log filename base on username
    
def get_log(log_name) -> logging.Logger:
    """Get a logger, or if it doesn't exist yet, set one up.
    Requires;
        log_name: name of the log
    Returns;
        logger: logging.Logger object;
    """
    logger = logging.getLogger(log_name)
    # check if log has handlers, if so it's already been set up
    if logger.hasHandlers():
        return logger
    # if it has no handlers then a log must be set up
    logger.setLevel(logging.DEBUG)
    
    # create console handler and set level to debug
    sh = logging.StreamHandler()
    # create file handler which logs even debug messages
    fh = logging.FileHandler(fname)
    # set log levels
    sh.setLevel(logging.INFO)
    fh.setLevel(logging.DEBUG)
    
    # create formatters
    sf =  logging.Formatter('%(levelname)s: %(message)s')
    ff =  logging.Formatter('%(asctime)s : %(name)s : %(levelname)s: %(message)s')
    
    # add formatters
    sh.setFormatter(sf)
    fh.setFormatter(ff)
    
    # add ch to logger
    logger.addHandler(sh)
    logger.addHandler(fh)
    created_logs.append(log_name)
    return logger

def close_logs():
    """Close all open logs cleanly"""
    for log in created_logs:
        logger = logging.getLogger(log)
        handlers = logger.handlers[:]
        for handler in handlers:
            handler.close()
            logger.removeHandler(handler)

# reset users log file on load
try:
    if os.path.isfile(fname):
        os.remove(fname)
except Exception as e:
    logging.exception(e)