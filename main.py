import copy
import os
import re
import shutil

import pytesseract
import fitz
from pdf2image import convert_from_path, pdfinfo_from_path
from PIL import Image

import logging_m
from constants import *


pytesseract.pytesseract.tesseract_cmd = PYTESSERACT_PATH

file_counter = 0
# print(os.listdir(PDF_FOLDER))
while len(os.listdir(PDF_FOLDER)) > 0:

    for batch_ind in range(0, BATCH_SIZE):
        if batch_ind >= len(os.listdir(PDF_FOLDER)):
            break
        file_counter += 1
        file_name = os.listdir(PDF_FOLDER)[batch_ind]
        print(file_name)
        path_to_file = os.path.join(PDF_FOLDER, file_name)
        file_condition = logging_m.get_file_condition(file_name[:-4])
        # print(file_condition)

        page_number = pdfinfo_from_path(path_to_file, poppler_path=POPPLER_PATH)['Pages']
        print(f'File {file_counter} has {page_number} pages.')

        pdf = fitz.open(path_to_file)
        is_readable = False
        for page in pdf:
            text = page.get_text("text")
            if len(text) > 0:
                is_readable = True
                print("PDF файл является читаемым. Пропускаем стадию изображений и OCR.")
                break
        pdf.close()

        # Проверка на существования текстового файла для pdf:
        # Если в логе есть информация о том, что для файла текст НЕ готов и при этом файл существует,
        # то удаляем текстовый файл
        # Если в логе есть информация о том, что для файла текст готов и при этом файл существует,
        # то удаляем pdf и переходим к следующему pdf
        if os.path.exists(os.path.join(TEXT_FOLDER, file_name[:-4] + TXT)):
            if file_condition["text_undone"] is False:
                print("Обнаружен готовый текст для документа. Удаление документа.")
                os.remove(path_to_file)
                if os.path.exists(os.path.join(IMAGE_FOLDER, file_name[:-4])):
                    print("Удаляем изображения.")
                    shutil.rmtree(os.path.join(IMAGE_FOLDER, file_name[:-4]), ignore_errors=True)
                continue
            else:
                page_text_done = file_condition["text_page"]
                print(f"Для документа получен текст из {page_text_done - 1} страниц. Обработка продолжится со " +
                      "следующей страницы.")
                if not is_readable:
                    continue

        if is_readable:
            pdf = fitz.open(path_to_file)
            text_file_name = os.path.join(TEXT_FOLDER, file_name[:-4] + TXT)
            # Создание файла для записи текста. Постраничная запись текста в файл.
            with open(text_file_name, "a+", encoding='utf-8') as txt_file:
                page_counter = 0
                for page in pdf:
                    page_counter += 1
                    if page_counter < file_condition['text_page']:
                        continue
                    logging_m.log_indicating(file_name[:-4], page_counter, text_ind_log=True, image_ind_log=False)
                    text = page.get_text("text")
                    print(f"Чтение текста со страницы {page_counter}")
                    txt_file.write(text)
            pdf.close()
            os.replace(PDF_FOLDER + fr"\{file_name[:-4]}" + PDF,
                       USED_PDF_FOLDER + fr"\{file_name[:-4]}" + PDF)
            logging_m.clear_log(file_name[:-4])
            continue

        if page_number >= 100:
            print(f"File {file_counter}: {file_name} is too huge. Moving it to a huge_dir.")
            os.replace(path_to_file,
                       HUGE_PDF_FOLDER + fr"\{file_name}")
            continue

        # Проверка на существования изображений для pdf:
        # Если в логе есть информация о том, что для файла изображения НЕ готовы и при этом изображения существуют,
        # то удаляем изображения
        # Если в логе есть информация о том, что для файла изображения готовы и при этом изображения существуют,
        # то пропускаем стадию подготовки изображений
        if os.path.exists(os.path.join(IMAGE_FOLDER, file_name[:-4])):
            if file_condition["image_undone"] is False:
                print("Пропуск стадии подготовки изображений.")
                continue
            else:
                print(f"Для документа готово {file_condition['image_page'] - 1} изображений. " +
                      "Продолжение подготовки изображений.")
                image_list = os.listdir(os.path.join(IMAGE_FOLDER, file_name[:-4]))
                for image in image_list:
                    if re.search(r'\.ppm', image):
                        os.remove(os.path.join(os.path.join(IMAGE_FOLDER, file_name[:-4]), image))

    # --- PDF to Image - START
        print(f"File {file_counter}: {file_name}. Converting from PDF to PPM")
        # [:-4] отсечение от имени файла ".pdf" (костыль :) )
        # TODO: Use regexp
        image_dir_name = os.path.join(IMAGE_FOLDER, file_name[:-4])
        if not os.path.exists(image_dir_name):
            os.makedirs(image_dir_name)
        convert_from_path(path_to_file, output_folder=image_dir_name, first_page=file_condition['image_page'],
                          fmt="ppm", thread_count=4, poppler_path=POPPLER_PATH)
        print(f"File {file_counter}: {file_name}. Converting from PPM to JPEG")
        jpeg_counter = 0
        images = os.listdir(image_dir_name)
        image_counter = 0
        for image_name in images:
            image_counter += 1
            if re.search(r'\.jpeg', image_name):
                jpeg_counter += 1
                if jpeg_counter == file_condition['image_page']:
                    os.remove(os.path.join(image_dir_name, image_name))
                    image_counter -= 1
                continue
            logging_m.log_indicating(file_name[:-4], image_counter, text_ind_log=False, image_ind_log=True)
            path_to_image = os.path.join(image_dir_name, image_name)
            with Image.open(path_to_image) as image:
                # TODO: Use regexp
                image.save(path_to_image[:-4] + JPEG)
            os.remove(path_to_image)
        print(f"File {file_counter}. Created {image_counter} JPEG images.")

        logging_m.clear_log(file_name[:-4])
    # --- PDF to Image - END

    # --- Image to Text - START

    file_gen = os.walk(IMAGE_FOLDER)
    file_ocr_counter = 0
    for file_dir in file_gen:
        doc_name = re.search(r'\d+', file_dir[0])
        if doc_name:
            doc_name = doc_name.group()
        else:
            continue

        file_condition = logging_m.get_file_condition(doc_name)
        if file_condition['image_undone']:
            print(f'Для документа {doc_name} не подготовлены изображения. Пропуск текстовой обработки документа.')
            continue

        file_ocr_counter += 1
        page_quantity = len(os.listdir(file_dir[0]))
        text_file_name = os.path.join(TEXT_FOLDER, doc_name + TXT)
        # Создание файла для записи текста. Постраничная запись текста в файл.
        with open(text_file_name, "a+", encoding='utf-8') as txt_file:
            page_counter = 0
            doc_name = re.search(r'\d+', file_dir[0]).group()
            print(f"File {file_counter} ({file_ocr_counter}/{BATCH_SIZE})")
            print(f"Start processing OCR in {doc_name} file")
            jpeg_list = copy.copy(file_dir[2])
            jpeg_list = sorted(jpeg_list, key=lambda x: re.search(r'-(?P<page_num>\d+)\.', x).group('page_num'))
            for file_name in jpeg_list:
                page_counter += 1
                if page_counter < file_condition['text_page']:
                    continue
                logging_m.log_indicating(doc_name, page_counter, text_ind_log=True, image_ind_log=False)
                print(f"Processing OCR for page {page_counter}/{page_quantity}")
                path_to_image_file = os.path.join(file_dir[0], file_name)
                text = pytesseract.image_to_string(path_to_image_file, lang='rus')
                txt_file.write(text)
            print(f"End processing OCR in {doc_name} file")
            shutil.rmtree(file_dir[0], ignore_errors=True)
            os.replace(PDF_FOLDER + fr"\{doc_name}" + PDF,
                       USED_PDF_FOLDER + fr"\{doc_name}" + PDF)
        logging_m.clear_log(doc_name)
    # --- Image to Text - END
