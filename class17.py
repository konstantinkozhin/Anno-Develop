import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from tkinter import ttk
from PIL import Image, ImageDraw, ImageFont, ImageTk
from ttkthemes import ThemedTk
import random

# Глобальные переменные для хранения состояния
dataset = []
index = 0
total_images = 0
image_dir = ''
label_dir = ''
current_annotations = []
start_x = 0
start_y = 0
selected_boxes = set()  # Множество для хранения индексов выделенных боксов
classes = [""]  # Список классов по умолчанию с пустым классом
class_colors = {0: "red"}  # Цвет по умолчанию для класса 0
current_class_id = 0

def reset_state():
    global dataset, index, total_images, image_dir, label_dir, current_annotations, start_x, start_y, selected_boxes, classes, class_colors, current_class_id
    dataset = []
    index = 0
    total_images = 0
    image_dir = ''
    label_dir = ''
    current_annotations = []
    start_x = 0
    start_y = 0
    selected_boxes = set()
    classes = [""]
    class_colors = {0: "red"}
    current_class_id = 0
    if 'info_label' in globals() and info_label.winfo_exists():
        info_label.config(text="Всего изображений: 0")
    if 'image_info_label' in globals() and image_info_label.winfo_exists():
        image_info_label.config(text="Текущее изображение: N/A, Позиция: 0/0")
    if 'annotation_textbox' in globals() and annotation_textbox.winfo_exists():
        annotation_textbox.config(state=tk.NORMAL)
        annotation_textbox.delete(1.0, tk.END)
        annotation_textbox.config(state=tk.DISABLED)

def load_dataset():
    global dataset, index, total_images, image_dir, label_dir, current_annotations
    
    directory = filedialog.askdirectory()
    if not directory:
        return
    
    reset_state()
    
    image_dir = directory
    label_dir = os.path.join(os.path.dirname(directory), "labels")
    os.makedirs(label_dir, exist_ok=True)
    
    dataset = [os.path.join(image_dir, f)
               for f in os.listdir(image_dir) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    total_images = len(dataset)
    index = 0
    current_annotations = []
    
    if dataset:
        populate_gallery()
        show_image()
        update_counter()
        load_annotation_text()
        annotation_textbox.config(state=tk.NORMAL)  # Разблокировать поле после загрузки датасета
    else:
        messagebox.showerror("Ошибка", "No images found in the specified directory.")
        info_label.config(text="Всего изображений: 0")
        annotation_textbox.config(state=tk.DISABLED)  # Оставить поле заблокированным

def draw_boxes(image, annotation_list, selected_boxes):
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial", 15)
    except IOError:
        font = ImageFont.load_default()
    
    for i, annotation in enumerate(annotation_list):
        if len(annotation) != 5:
            continue
        class_id, x_center, y_center, width, height = map(float, annotation)
        img_width, img_height = image.size
        x_center *= img_width
        y_center *= img_height
        width *= img_width
        height *= img_height
        x1 = x_center - width / 2
        y1 = y_center - height / 2
        x2 = x_center + width / 2
        y2 = y_center + height / 2
        outline_color = class_colors.get(int(class_id), "red")
        if i in selected_boxes:
            outline_color = "blue"
        draw.rectangle([x1, y1, x2, y2], outline=outline_color, width=2)
        if int(class_id) < len(classes):
            draw.text((x1, y1), f"{int(class_id)}: {classes[int(class_id)]}", fill=outline_color, font=font)
    
    return image

def show_image():
    global index, dataset, label_dir, img_path, selected_boxes
    
    img_path = dataset[index]
    image = Image.open(img_path)
    
    annotation_path = os.path.join(label_dir, os.path.basename(img_path).replace(".jpg", ".txt"))
    if os.path.exists(annotation_path):
        with open(annotation_path, 'r') as file:
            annotation_text = file.read().strip().split('\n')
        annotation_list = [line.split() for line in annotation_text]
    else:
        annotation_list = []
    
    selected_boxes.clear()
    image = draw_boxes(image, annotation_list, selected_boxes)
    update_image_info()

def next_image(event=None):
    global index, total_images
    if index < total_images - 1:
        index += 1
        show_image()
        update_counter()
        load_annotation_text()
        update_gallery_selection()

def previous_image(event=None):
    global index
    if index > 0:
        index -= 1
        show_image()
        update_counter()
        load_annotation_text()
        update_gallery_selection()

def update_counter():
    global label_dir
    num_annotated = 0
    for img_path in dataset:
        annotation_path = os.path.join(label_dir, os.path.basename(img_path).replace(".jpg", ".txt"))
        if os.path.exists(annotation_path) and os.path.getsize(annotation_path) > 0:
            num_annotated += 1
    if 'info_label' in globals() and info_label.winfo_exists():
        info_label.config(text=f"Всего изображений: {total_images}, Аннотировано: {num_annotated}")

def update_image_info():
    global index, dataset
    if index < len(dataset):
        if 'image_info_label' in globals() and image_info_label.winfo_exists():
            image_info_label.config(text=f"Текущее изображение: {os.path.basename(dataset[index])}, Позиция: {index + 1}/{total_images}")

def load_annotation_text():
    global index, dataset, label_dir
    
    if index < len(dataset):
        annotation_path = os.path.join(label_dir, os.path.basename(dataset[index]).replace(".jpg", ".txt"))
        if os.path.exists(annotation_path):
            with open(annotation_path, 'r') as file:
                annotation_text = file.read()
            if 'annotation_textbox' in globals() and annotation_textbox.winfo_exists():
                annotation_textbox.config(state=tk.NORMAL)  # Разблокировать поле перед загрузкой текста
                annotation_textbox.delete(1.0, tk.END)
                annotation_textbox.insert(tk.END, annotation_text)
        else:
            if 'annotation_textbox' in globals() and annotation_textbox.winfo_exists():
                annotation_textbox.config(state=tk.NORMAL)  # Разблокировать поле перед очисткой текста
                annotation_textbox.delete(1.0, tk.END)

def update_annotation_text(event=None):
    global current_annotations, label_dir, index, dataset
    if not dataset:
        return
    annotation_text = annotation_textbox.get(1.0, tk.END).strip()
    current_annotations = [line.split() for line in annotation_text.split('\n') if line]
    if index < len(dataset):
        annotation_path = os.path.join(label_dir, os.path.basename(dataset[index]).replace(".jpg", ".txt"))
        with
