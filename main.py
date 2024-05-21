import os
import gradio as gr
from PIL import Image, ImageDraw
import tkinter as tk
from tkinter import filedialog
from PIL import ImageTk

# Глобальные переменные для хранения состояния
dataset = []
index = 0
total_images = 0
image_dir = ''
label_dir = ''
current_annotations = []

def load_dataset(directory):
    global dataset, index, total_images, image_dir, label_dir, current_annotations
    image_dir = directory
    label_dir = os.path.join(os.path.dirname(directory), "labels")
    os.makedirs(label_dir, exist_ok=True)
    
    dataset = [os.path.join(image_dir, f)
               for f in os.listdir(image_dir) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    total_images = len(dataset)
    index = 0
    current_annotations = []
    if dataset:
        return show_image(), update_counter(), load_annotation_text()
    else:
        return "No images found in the specified directory.", "Всего изображений: 0", ""

def draw_boxes(image, annotation_list):
    draw = ImageDraw.Draw(image)
    for annotation in annotation_list:
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
        draw.rectangle([x1, y1, x2, y2], outline="red", width=2)
    
    return image

def show_image():
    global index, dataset, label_dir
    if index >= len(dataset):
        return "Evaluation complete", None
    
    img_path = dataset[index]
    annotation_path = os.path.join(label_dir, os.path.basename(img_path).replace(".jpg", ".txt"))
    image = Image.open(img_path)
    
    if os.path.exists(annotation_path):
        with open(annotation_path, 'r') as file:
            annotation_text = file.read().strip().split('\n')
        annotation_list = [line.split() for line in annotation_text]
    else:
        annotation_list = []
    
    image = draw_boxes(image, annotation_list)
    
    return image

def next_image():
    global index, total_images
    if index < total_images - 1:
        index += 1
    return show_image(), update_counter(), load_annotation_text()

def previous_image():
    global index
    if index > 0:
        index -= 1
    return show_image(), update_counter(), load_annotation_text()

def update_counter():
    global label_dir
    num_annotated = len([f for f in os.listdir(label_dir) if f.endswith('.txt')])
    return f"Всего изображений: {total_images}, Аннотировано: {num_annotated}"

def load_annotation_text():
    global index, dataset, label_dir
    if index < len(dataset):
        annotation_path = os.path.join(label_dir, os.path.basename(dataset[index]).replace(".jpg", ".txt"))
        if os.path.exists(annotation_path):
            with open(annotation_path, 'r') as file:
                annotation_text = file.read()
            return annotation_text
    return ""

def update_annotation_text(annotation_text):
    global current_annotations, label_dir, index, dataset
    current_annotations = [line.split() for line in annotation_text.strip().split('\n') if line]
    if index < len(dataset):
        annotation_path = os.path.join(label_dir, os.path.basename(dataset[index]).replace(".jpg", ".txt"))
        with open(annotation_path, 'w') as file:
            for ann in current_annotations:
                file.write(" ".join(map(str, ann)) + "\n")
    return show_image()

def draw_boxes_cv(image_path, annotation_path):
    global current_annotations
    
    root = tk.Tk()
    root.title("Draw Boxes")
    root.attributes('-topmost', True)  # Сделать окно поверх всех
    root.state('zoomed')  # Развернуть окно на весь экран
    root.overrideredirect(True)  # Убрать верхнее меню
    
    img = Image.open(image_path)
    img_width, img_height = img.size
    
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    # Рассчитать масштабирование изображения
    scale_factor = min(screen_width / img_width, screen_height / img_height)
    new_width = int(img_width * scale_factor)
    new_height = int(img_height * scale_factor)
    img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    tk_img = ImageTk.PhotoImage(img_resized)
    canvas = tk.Canvas(root, width=new_width, height=new_height)
    canvas.pack(fill=tk.BOTH, expand=True)
    
    canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)
    
    boxes = []
    current_box = None
    
    # Load existing annotations
    if os.path.exists(annotation_path):
        with open(annotation_path, 'r') as file:
            existing_annotations = file.readlines()
        for ann in existing_annotations:
            parts = ann.strip().split()
            class_id, x_center, y_center, width, height = map(float, parts)
            x_center *= new_width
            y_center *= new_height
            width *= new_width
            height *= new_height
            x1 = x_center - width / 2
            y1 = y_center - height / 2
            x2 = x_center + width / 2
            y2 = y_center + height / 2
            boxes.append((x1, y1, x2, y2))
            canvas.create_rectangle(x1, y1, x2, y2, outline='red')
    
    def on_mouse_down(event):
        global start_x, start_y, current_box
        start_x = event.x
        start_y = event.y
        current_box = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline='red')
    
    def on_mouse_up(event):
        global start_x, start_y, current_box
        end_x = event.x
        end_y = event.y
        boxes.append((start_x, start_y, end_x, end_y))
        current_box = None
    
    def on_mouse_move(event):
        global start_x, start_y, current_box
        if current_box is not None:
            canvas.coords(current_box, start_x, start_y, event.x, event.y)
    
    def on_backspace(event):
        if boxes:
            last_box = boxes.pop()
            canvas.delete("all")
            canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)
            for box in boxes:
                canvas.create_rectangle(box[0], box[1], box[2], box[3], outline='red')
    
    def on_enter(event):
        save_annotations()
        root.destroy()
    
    def save_annotations():
        global current_annotations
        current_annotations = []
        for box in boxes:
            x1, y1, x2, y2 = box
            x_center = ((x1 + x2) / 2) / new_width
            y_center = ((y1 + y2) / 2) / new_height
            width = abs(x2 - x1) / new_width
            height = abs(y2 - y1) / new_height
            x_center = min(max(x_center, 0), 1)
            y_center = min(max(y_center, 0), 1)
            width = min(max(width, 0), 1)
            height = min(max(height, 0), 1)
            current_annotations.append([0, x_center, y_center, width, height])
        
        with open(annotation_path, 'w') as file:
            for ann in current_annotations:
                file.write(" ".join(map(str, ann)) + "\n")
    
    root.bind("<BackSpace>", on_backspace)
    root.bind("<Return>", on_enter)

    canvas.bind("<ButtonPress-1>", on_mouse_down)
    canvas.bind("<ButtonRelease-1>", on_mouse_up)
    canvas.bind("<Motion>", on_mouse_move)
    
    root.mainloop()

def annotate_image():
    global index, dataset
    if index < len(dataset):
        img_path = dataset[index]
        annotation_path = os.path.join(label_dir, os.path.basename(img_path).replace(".jpg", ".txt"))
        draw_boxes_cv(img_path, annotation_path)
        return show_image(), update_counter(), load_annotation_text()
    return "No images to annotate", ""

with gr.Blocks() as demo:
    gr.Markdown("## Программа для аннотирования изображений")
    
    with gr.Row():
        directory_input = gr.Textbox(label="Дирректория с изображениями")
        load_button = gr.Button("Загрузить")
    
    with gr.Row():
        image_output = gr.Image(label="Изображение для аннотации")
    
    with gr.Row():
        counter_text = gr.Textbox(label="Информация", interactive=False)
    
    with gr.Row():
        previous_button = gr.Button("Назад")
        next_button = gr.Button("Вперед")
        annotate_button = gr.Button("Аннотировать")
    
    with gr.Row():
        annotation_text = gr.Textbox(label="Координаты", lines=10)
    
    load_button.click(load_dataset, inputs=directory_input, outputs=[image_output, counter_text, annotation_text])
    next_button.click(next_image, outputs=[image_output, counter_text, annotation_text])
    previous_button.click(previous_image, outputs=[image_output, counter_text, annotation_text])
    annotation_text.change(update_annotation_text, inputs=annotation_text, outputs=image_output)
    annotate_button.click(annotate_image, outputs=[image_output, counter_text, annotation_text])

demo.launch()
