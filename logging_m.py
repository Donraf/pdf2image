from constants import LOG_INDICATING, LOG_TEXT_UNDONE, LOG_IMAGE_UNDONE,\
    TEMP_LOG_IND, LOG_NONE
import re
import os


def clear_log(filename):
    with open(LOG_INDICATING, "r") as log_orig:
        with open(TEMP_LOG_IND, "a+") as log_temp:
            for line in log_orig:
                new_line = line
                filename_list = re.findall(r'(\d+):\d+', line)
                if filename in filename_list:
                    new_line = re.sub(rf' {filename}:\d+,', '', line)
                log_temp.write(new_line)
    os.replace(TEMP_LOG_IND, LOG_INDICATING)


def log_indicating(filename, page, text_ind_log=False, image_ind_log=False):
    with open(LOG_INDICATING, "r") as log_orig:
        with open(TEMP_LOG_IND, "a+") as log_temp:
            for line in log_orig:
                new_line = line
                filename_list = re.findall(r'(\d+):\d+', line)
                if text_ind_log and re.match(LOG_TEXT_UNDONE, line):
                    if filename in filename_list:
                        new_line = re.sub(rf' {filename}:\d+,', f' {filename}:{page},', line)
                    else:
                        new_line = line[:-1] + f' {filename}:{page},' + '\n'
                if image_ind_log and re.match(LOG_IMAGE_UNDONE, line):
                    if filename in filename_list:
                        new_line = re.sub(rf' {filename}:\d+,', f' {filename}:{page},', line)
                    else:
                        new_line = line[:-1] + f' {filename}:{page},' + '\n'
                log_temp.write(new_line)
    os.replace(TEMP_LOG_IND, LOG_INDICATING)


def get_file_condition(filename):
    page_text_num = 0
    page_image_num = 0
    text_undone = False
    image_undone = False
    with open(LOG_INDICATING, "r") as log:
        for line in log:
            text_ind = re.match(LOG_TEXT_UNDONE, line)
            filename_list = re.findall(r'(\d+):\d+', line)
            if text_ind:
                if filename in filename_list:
                    page = re.search(rf'{filename}:(?P<page>\d+)', line)
                    page_text_num = int(page.group('page'))
                    text_undone = True
            image_ind = re.match(LOG_IMAGE_UNDONE, line)
            if image_ind:
                if filename in filename_list:
                    page = re.search(rf'{filename}:(?P<page>\d+)', line)
                    page_image_num = int(page.group('page'))
                    image_undone = True
    return {
            "text_undone": text_undone,
            "text_page": page_text_num,
            "image_undone": image_undone,
            "image_page": page_image_num,
           }
