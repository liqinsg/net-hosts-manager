#!/usr/bin/python3

import logging

LOGGING_MODE_COLLECTOR = 'collector'
LOGGING_MODE_WATCHER = 'watcher'

DEFAULT_SETTINGS = {
    'parent_logger' : None,
    'propagate': True,
    'mode': None,
    'logger_name': '',
    'log_file_level': logging.INFO,
    'log_console_level': logging.WARNING,
    'log_filename_extension' : 'log',
    'log_directory': '',
    'log_write_mode': 'a'
}

class LoggingSettings():


    @staticmethod
    def get_default_settings():
        return DEFAULT_SETTINGS.copy()

    @staticmethod
    def get_logger(**settings):
        settings = {**LoggingSettings.get_default_settings(), **settings}

        if 'parent_logger' in settings.keys() and settings['parent_logger']:
            logger = settings['parent_logger'].getChild(settings['logger_name'])
            logger.propagate = settings['propagate']
            logger.setLevel(settings['parent_logger'].level)
        else:
            logger = logging.getLogger(settings['logger_name'])
            logger.setLevel(logging.DEBUG)      # More logs is better that less logs (c)
            if settings['log_file_level']:
                logger.addHandler(
                    LoggingSettings.get_console_handler(
                        settings['logger_name'],
                        settings['mode'], 
                        settings['log_console_level']))
        if settings['log_console_level']:
            logger.addHandler(
                LoggingSettings.get_file_handler(
                    settings['log_directory'],
                    settings['logger_name'],
                    settings['log_filename_extension'],
                    settings['log_write_mode'],
                    settings['mode'], 
                    settings['log_file_level']))
        return logger

    @staticmethod
    def get_propogate(mode):
        return False if mode == LOGGING_MODE_COLLECTOR else True

    @staticmethod
    def get_console_handler(logger_name, mode, level):
        """Return console handler
        
        Returns:
            [logging.Logger] -- Logger to console
        """        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        if level == logging.DEBUG:
            formatter = logging.Formatter(
                '%(asctime)s:%(name)s:%(levelname)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S')
        elif level == logging.INFO and mode == LOGGING_MODE_WATCHER:
            formatter = logging.Formatter('%(message)s')
        elif level == logging.INFO:
            formatter = logging.Formatter(
                '%(name)s:%(levelname)s: %(message)s')
        else:
            formatter = logging.Formatter('%(message)s')    
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level)
        return console_handler

    @staticmethod
    def get_file_handler(directory, filename, file_extension, log_write_mode, mode, level):
        if directory: 
            fh = logging.FileHandler(
                directory + '/' + filename + '.' + file_extension,
                mode=log_write_mode)
        else:
            fh = logging.FileHandler(
                filename + '.' + file_extension,
                mode=log_write_mode)
        fh.setLevel(level)
        if mode == LOGGING_MODE_COLLECTOR:
            fh.setFormatter(
                logging.Formatter('%(message)s'))
        elif level <= logging.DEBUG:
            fh.setFormatter(
                logging.Formatter(
                    '%(asctime)s:%(name)s:%(levelname)s: %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S'))
        else:
            fh.setFormatter(
                logging.Formatter('%(message)s'))
        return fh

    @staticmethod
    def get_level(mode, debugging, verbose):
        if mode == LOGGING_MODE_COLLECTOR:
            return LoggingSettings.get_level_collector_mode(debugging, verbose)
        else:
            return LoggingSettings.get_level_common_mode(debugging, verbose)

    @staticmethod
    def get_level_common_mode(debugging, verbose):     
        if debugging:
            return logging.DEBUG
        elif not debugging and verbose:
            return logging.INFO
        elif not debugging and not verbose:
            return logging.WARNING

    @staticmethod
    def get_level_collector_mode(debugging, verbose):
        return logging.DEBUG
        
    def get_child_logger(self, 
                        parent_logger, 
                        logging_level=logging.WARNING, 
                        logger_name=__name__):
        logger = parent_logger.getChild(logger_name)
        logger.setLevel