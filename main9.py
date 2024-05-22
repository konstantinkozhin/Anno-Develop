import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from tkinter import ttk
from PIL import Image, ImageDraw, ImageTk
from ttkthemes import ThemedTk

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

def load_dataset():
    global dataset, index, total_images, image_dir, label_dir, current_annotations
    
    directory = filedialog.askdirectory()
    if not directory:
        return
    
    image_dir = directory
    label_dir = os.path.join(os.path.dirname(directory), "labels")
    os.makedirs(label_dir, exist_ok=True)
    
    dataset = [os.path.join(image_dir, f)
               for f in os.listdir(image_dir) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    total_images = len(dataset)
    index = 0
    current_annotations = []
    
    if dataset:
        show_image()
        update_counter()
        load_annotation_text()
    else:
        messagebox.showerror("Ошибка", "No images found in the specified directory.")
        info_label.config(text="Всего изображений: 0")

def draw_boxes(image, annotation_list, selected_boxes):
    draw = ImageDraw.Draw(image)
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
        outline_color = "blue" if i in selected_boxes else "red"
        draw.rectangle([x1, y1, x2, y2], outline=outline_color, width=2)
    
    return image

def show_image():
    global index, dataset, label_dir, canvas, img_path, selected_boxes
    
    if index >= len(dataset):
        messagebox.showinfo("Информация", "Evaluation complete")
        return
    
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
    update_image_on_canvas(image)

def update_image_on_canvas(image):
    canvas_width = canvas.winfo_width()
    canvas_height = canvas.winfo_height()
    image.thumbnail((canvas_width, canvas_height), Image.Resampling.LANCZOS)
    
    tk_image = ImageTk.PhotoImage(image)
    canvas.image = tk_image
    canvas.create_image(0, 0, anchor=tk.NW, image=tk_image)
    canvas.update_idletasks()
    canvas.update()

def resize_image(event):
    if dataset:
        image = Image.open(dataset[index])
        annotation_path = os.path.join(label_dir, os.path.basename(dataset[index]).replace(".jpg", ".txt"))
        if os.path.exists(annotation_path):
            with open(annotation_path, 'r') as file:
                annotation_text = file.read().strip().split('\n')
            annotation_list = [line.split() for line in annotation_text]
        else:
            annotation_list = []
        
        image = draw_boxes(image, annotation_list, selected_boxes)
        update_image_on_canvas(image)

def next_image(event=None):
    global index, total_images
    if index < total_images - 1:
        index += 1
        show_image()
        update_counter()
        load_annotation_text()

def previous_image(event=None):
    global index
    if index > 0:
        index -= 1
        show_image()
        update_counter()
        load_annotation_text()

def update_counter():
    global label_dir
    num_annotated = 0
    for img_path in dataset:
        annotation_path = os.path.join(label_dir, os.path.basename(img_path).replace(".jpg", ".txt"))
        if os.path.exists(annotation_path) and os.path.getsize(annotation_path) > 0:
            num_annotated += 1
    info_label.config(text=f"Всего изображений: {total_images}, Аннотировано: {num_annotated}")

def load_annotation_text():
    global index, dataset, label_dir
    
    if index < len(dataset):
        annotation_path = os.path.join(label_dir, os.path.basename(dataset[index]).replace(".jpg", ".txt"))
        if os.path.exists(annotation_path):
            with open(annotation_path, 'r') as file:
                annotation_text = file.read()
            annotation_textbox.delete(1.0, tk.END)
            annotation_textbox.insert(tk.END, annotation_text)
        else:
            annotation_textbox.delete(1.0, tk.END)

def update_annotation_text(event=None):
    global current_annotations, label_dir, index, dataset
    annotation_text = annotation_textbox.get(1.0, tk.END).strip()
    current_annotations = [line.split() for line in annotation_text.split('\n') if line]
    if index < len(dataset):
        annotation_path = os.path.join(label_dir, os.path.basename(dataset[index]).replace(".jpg", ".txt"))
        with open(annotation_path, 'w') as file:
            for ann in current_annotations:
                file.write(" ".join(map(str, ann)) + "\n")
    show_image()
    update_counter()

def draw_boxes_cv(image_path, annotation_path):
    global current_annotations, current_shape, start_x, start_y, selected_boxes
    
    root = tk.Toplevel()
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
    
    shapes = []
    current_shape = []
    selected_boxes = set()

    # Load existing annotations
    if os.path.exists(annotation_path):
        with open(annotation_path, 'r') as file:
            existing_annotations = file.readlines()
        for i, ann in enumerate(existing_annotations):
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
            shapes.append((x1, y1, x2, y2))
            canvas.create_rectangle(x1, y1, x2, y2, outline='red')
    
    def on_mouse_down(event):
        global start_x, start_y, current_shape
        if event.state & 0x0004:  # Проверяем, что Ctrl нажат
            select_box(event.x, event.y)
        else:
            start_x = event.x
            start_y = event.y
            current_shape = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline='red')
    
    def on_mouse_up(event):
        global start_x, start_y, current_shape
        if not (event.state & 0x0004):  # Проверяем, что Ctrl не нажат
            end_x = event.x
            end_y = event.y
            shapes.append((start_x, start_y, end_x, end_y))
            current_shape = None
    
    def on_mouse_move(event):
        global start_x, start_y, current_shape
        if current_shape is not None:
            canvas.coords(current_shape, start_x, start_y, event.x, event.y)
    
    def on_backspace(event):
        global selected_boxes
        for box_index in sorted(selected_boxes, reverse=True):
            shapes.pop(box_index)
        selected_boxes.clear()
        canvas.delete("all")
        canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)
        for i, shape in enumerate(shapes):
            outline_color = "blue" if i in selected_boxes else "red"
            canvas.create_rectangle(shape[0], shape[1], shape[2], shape[3], outline=outline_color)
    
    def on_enter(event):
        save_annotations()
        root.destroy()

    def save_annotations():
        global current_annotations
        current_annotations = []
        for shape in shapes:
            x1, y1, x2, y2 = shape
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
        
        load_annotation_text()  # Update annotation text box after saving annotations
        update_counter()  # Update the counter after saving annotations
        show_image()  # Refresh the image with the new annotations
    
    def select_box(x, y):
        global selected_boxes
        for i, (x1, y1, x2, y2) in enumerate(shapes):
            if x1 <= x <= x2 and y1 <= y <= y2:
                if i in selected_boxes:
                    selected_boxes.remove(i)
                else:
                    selected_boxes.add(i)
                break
        canvas.delete("all")
        canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)
        for i, shape in enumerate(shapes):
            outline_color = "blue" if i in selected_boxes else "red"
            canvas.create_rectangle(shape[0], shape[1], shape[2], shape[3], outline=outline_color)
    
    root.bind("<BackSpace>", on_backspace)
    root.bind("<Return>", on_enter)
    canvas.bind("<ButtonPress-1>", on_mouse_down)
    canvas.bind("<ButtonRelease-1>", on_mouse_up)
    canvas.bind("<Motion>", on_mouse_move)
    
    root.mainloop()

def annotate_image(event=None):
    global index, dataset
    if index < len(dataset):
        img_path = dataset[index]
        annotation_path = os.path.join(label_dir, os.path.basename(dataset[index]).replace(".jpg", ".txt"))
        draw_boxes_cv(img_path, annotation_path)
        show_image()
        update_counter()
        load_annotation_text()
    else:
        messagebox.showinfo("Информация", "No images to annotate")

root = ThemedTk(theme="breeze")
root.title("Программа для аннотирования изображений")

# Set modern style
style = {"padx": 10, "pady": 10}
frame = ttk.Frame(root, padding=20)
frame.pack(fill=tk.BOTH, expand=True)

directory_frame = ttk.Frame(frame)
directory_frame.pack(fill=tk.X, **style)

directory_label = ttk.Label(directory_frame, text="Дирректория с изображениями:")
directory_label.pack(side=tk.LEFT)
directory_button = ttk.Button(directory_frame, text="Загрузить", command=load_dataset)
directory_button.pack(side=tk.RIGHT)

canvas_frame = ttk.Frame(frame)
canvas_frame.pack(fill=tk.BOTH, expand=True, **style)

canvas = tk.Canvas(canvas_frame, bg='gray')
canvas.pack(fill=tk.BOTH, expand=True)
canvas.bind("<Configure>", resize_image)

info_frame = ttk.Frame(frame)
info_frame.pack(fill=tk.X, **style)

info_label = ttk.Label(info_frame, text="Всего изображений: 0")
info_label.pack()

nav_frame = ttk.Frame(frame)
nav_frame.pack(fill=tk.X, **style)

previous_button = ttk.Button(nav_frame, text="Назад", command=previous_image)
previous_button.pack(side=tk.LEFT)
next_button = ttk.Button(nav_frame, text="Вперед", command=next_image)
next_button.pack(side=tk.RIGHT)
annotate_button = ttk.Button(nav_frame, text="Аннотировать", command=annotate_image)
annotate_button.pack(side=tk.RIGHT, padx=5)

annotation_frame = ttk.Frame(frame)
annotation_frame.pack(fill=tk.BOTH, **style)

annotation_label = ttk.Label(annotation_frame, text="Координаты:")
annotation_label.pack(anchor=tk.W)
annotation_textbox = scrolledtext.ScrolledText(annotation_frame, wrap=tk.WORD, height=10)
annotation_textbox.pack(fill=tk.BOTH, expand=True)

annotation_textbox.bind("<KeyRelease>", update_annotation_text)

# Bind arrow keys for navigation and Enter key for annotation
root.bind("<Left>", previous_image)
root.bind("<Right>", next_image)
root.bind("<Return>", annotate_image)

root.mainloop()
