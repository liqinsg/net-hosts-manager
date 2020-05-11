#!/usr/bin/python3


import csv
#import logging
import threading


CSV_WRITER_LOCK = threading.Lock()

#module_logger = logging.getLogger('ReporterCsv')

class ReporterCsv():

    _delimeter = ','
    _csv = None

    def __init__(self, filename, mode='a+', newline='\n'):
        self._csv = open(filename + '.csv', mode=mode, newline=newline)
        if mode == 'r':
            self._reader = csv.reader(self._csv, dialect='excel', quotechar='"', delimiter=self.delimiter)
        else:
            self._writer = csv.writer(self._csv, dialect='excel', quotechar='"', delimiter=self.delimiter)

    def __del__(self):
        try:
            self._csv.close()
        except AttributeError:
            pass

    @property
    def delimiter(self):
        return self._delimeter

    @delimiter.setter
    def delimiter(self, delimiter):
        self._delimeter = delimiter

    @property
    def reader(self):
        return self._reader

    def read_row(self):
        return self._reader.__next__()

    def write_header(self, column_names):
        with CSV_WRITER_LOCK:
            self._writer.writerow(column_names)

    def write_row(self, row):
        with CSV_WRITER_LOCK:
            self._writer.writerow(row)


def addCheckFunctionResultToCsv(check_result, device_info, report_name):
    if check_result:
        append_row_to_csv(device_info + [check_result], report_name)
        return 1
    else:
        return 0


def convertCsvNewlineStyleWindowsToLinux(filename):
    fileContents = open(filename, "r").read()
    f = open(filename, "w", newline="\n")
    f.write(fileContents)
    f.close()
    return 1
