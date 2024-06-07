import os
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageTk
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
shapes = []
scale = 1
new_width = 0
new_height = 0
contrast_level = 1  # Уровень контрастности

def reset_state():
    global dataset, index, total_images, image_dir, label_dir, current_annotations, start_x, start_y, selected_boxes, classes, class_colors, current_class_id, contrast_level
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
    contrast_level = 1
    if 'info_label' in globals() and info_label.winfo_exists():
        info_label.config(text="Всего изображений: 0")
    if 'image_info_label' in globals() and image_info_label.winfo_exists():
        image_info_label.config(text="Текущее изображение: N/A, Позиция: 0/0")

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
        annotation_canvas.config(state=tk.NORMAL)  # Разблокировать поле после загрузки датасета
    else:
        messagebox.showerror("Ошибка", "No images found in the specified directory.")
        info_label.config(text="Всего изображений: 0")
        annotation_canvas.config(state=tk.DISABLED)  # Оставить поле заблокированным

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
    global index, dataset, label_dir, img_path, selected_boxes, tk_img, annotation_canvas, shapes, scale, new_width, new_height
    
    img_path = dataset[index]
    image = Image.open(img_path)

    # Применение контрастности
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(contrast_level)
    
    annotation_path = os.path.join(label_dir, os.path.basename(img_path).replace(".jpg", ".txt"))
    if os.path.exists(annotation_path):
        with open(annotation_path, 'r') as file:
            annotation_text = file.read().strip().split('\n')
        annotation_list = [line.split() for line in annotation_text]
    else:
        annotation_list = []
    
    selected_boxes.clear()
    shapes = []
    img_width, img_height = image.size
    canvas_width = annotation_canvas.winfo_width()
    canvas_height = annotation_canvas.winfo_height()
    scale = min(canvas_width/img_width, canvas_height/img_height)
    new_width = int(img_width * scale)
    new_height = int(img_height * scale)
    image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    for annotation in annotation_list:
        if len(annotation) == 5:
            class_id, x_center, y_center, width, height = map(float, annotation)
            x_center *= new_width
            y_center *= new_height
            width *= new_width
            height *= new_height
            x1 = x_center - width / 2
            y1 = y_center - height / 2
            x2 = x_center + width / 2
            y2 = y_center + height / 2
            shapes.append((x1, y1, x2, y2, int(class_id)))
    
    tk_img = ImageTk.PhotoImage(image)
    annotation_canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)
    annotation_canvas.config(scrollregion=annotation_canvas.bbox(tk.ALL))
    refresh_canvas()
    update_image_info()

def next_image(event=None):
    global index, total_images
    if index < total_images - 1:
        save_annotations()
        index += 1
        show_image()
        update_counter()
        update_gallery_selection()

def previous_image(event=None):
    global index
    if index > 0:
        save_annotations()
        index -= 1
        show_image()
        update_counter()
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

def load_class_file():
    global classes, class_colors
    file_path = filedialog.askopenfilename(title="Выбрать файл классов", filetypes=(("Text files", "*.txt"), ("All files", "*.*")))
    if file_path:
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                classes = [line.strip() for line in file.readlines()]
            class_colors = {i: "#%06x" % random.randint(0, 0xFFFFFF) for i in range(len(classes))}
            messagebox.showinfo("Классы загружены", f"Классы: {classes}")
            refresh_display()  # Добавляем обновление отображения после загрузки классов
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить классы: {e}")
    else:
        messagebox.showwarning("Предупреждение", "Файл классов не выбран. Используются текущие классы.")

def refresh_display():
    if dataset:
        show_image()
        update_counter()

def show_class_info():
    global classes, class_colors
    class_info_window = tk.Toplevel(root)
    class_info_window.title("Информация о классах")
    
    frame = ttk.Frame(class_info_window)
    frame.pack(fill=tk.BOTH, expand=True)
    
    tree = ttk.Treeview(frame, columns=("ID", "Класс"), show='headings', height=10)
    tree.column("ID", width=50, anchor='center')
    tree.column("Класс", anchor='center')
    tree.heading("ID", text="ID")
    tree.heading("Класс", text="Класс")

    for i, cls in enumerate(classes):
        tree.insert("", "end", values=(i, cls), tags=(i,))
    
    for i in range(len(classes)):
        tree.tag_configure(str(i), background=class_colors[i])
    
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    tree.configure(yscrollcommand=scrollbar.set)
    class_info_window.mainloop()

def clear_annotations():
    global current_annotations, label_dir, index, dataset
    current_annotations = []
    if index < len(dataset):
        annotation_path = os.path.join(label_dir, os.path.basename(dataset[index]).replace(".jpg", ".txt"))
        with open(annotation_path, 'w') as file:
            file.write("")
    show_image()
    update_counter()

def populate_gallery():
    for widget in scrollable_frame.winfo_children():
        widget.destroy()
    
    for idx, img_path in enumerate(dataset):
        thumb = Image.open(img_path)
        thumb.thumbnail((50, 50), Image.Resampling.LANCZOS)  # Установить размер миниатюр
        tk_thumb = ImageTk.PhotoImage(thumb.resize((100, 100)))  # Растянуть до необходимого размера
        thumb_button = tk.Button(scrollable_frame, image=tk_thumb, command=lambda idx=idx: select_image(idx))
        thumb_button.image = tk_thumb  # Сохранить ссылку на изображение
        thumb_button.grid(row=0, column=idx, padx=5, pady=5)
        if idx == index:
            thumb_button.config(relief=tk.SUNKEN, bg="yellow")

def select_image(idx):
    global index
    save_annotations()
    index = idx
    show_image()
    update_counter()
    update_gallery_selection()

def update_gallery_selection():
    for idx, widget in enumerate(scrollable_frame.winfo_children()):
        if isinstance(widget, tk.Button):
            widget.config(relief=tk.SUNKEN if idx == index else tk.RAISED, bg="yellow" if idx == index else "SystemButtonFace")

def on_mouse_down(event):
    global start_x, start_y, current_shape
    if event.state & 0x0004:  # Проверяем, что Ctrl нажат
        select_box(event.x, event.y)
    else:
        start_x = min(max(event.x, 0), new_width)
        start_y = min(max(event.y, 0), new_height)
        current_shape = annotation_canvas.create_rectangle(start_x, start_y, start_x, start_y, outline=class_colors.get(current_class_id, 'red'))

def on_mouse_up(event):
    global start_x, start_y, current_shape, shapes
    if not (event.state & 0x0004):  # Проверяем, что Ctrl не нажат
        end_x = min(max(event.x, 0), new_width)
        end_y = min(max(event.y, 0), new_height)
        # Проверяем размеры бокса
        if abs(end_x - start_x) > 0 and abs(end_y - start_y) > 0:
            shapes.append((start_x, start_y, end_x, end_y, current_class_id))
        else:
            annotation_canvas.delete(current_shape)
        current_shape = None
        save_annotations()
        refresh_canvas()

def on_mouse_move(event):
    global start_x, start_y, current_shape
    if current_shape is not None:
        end_x = min(max(event.x, 0), new_width)
        end_y = min(max(event.y, 0), new_height)
        annotation_canvas.coords(current_shape, start_x, start_y, end_x, end_y)

def save_annotations():
    global current_annotations, shapes, label_dir, index, dataset, annotation_canvas, scale
    
    current_annotations = []
    for shape in shapes:
        x1, y1, x2, y2, class_id = shape
        width = abs(x2 - x1)
        height = abs(y2 - y1)
        if width == 0 or height == 0:
            continue  # Пропускаем боксы с нулевым размером
        x_center = ((x1 + x2) / 2) / new_width
        y_center = ((y1 + y2) / 2) / new_height
        width /= new_width
        height /= new_height
        x_center = min(max(x_center, 0), 1)
        y_center = min(max(y_center, 0), 1)
        width = min(max(width, 0), 1)
        height = min(max(height, 0), 1)
        current_annotations.append([int(class_id), x_center, y_center, width, height])
    
    if index < len(dataset):
        annotation_path = os.path.join(label_dir, os.path.basename(dataset[index]).replace(".jpg", ".txt"))
        with open(annotation_path, 'w') as file:
            for ann in current_annotations:
                file.write(" ".join(map(str, ann)) + "\n")
    
    update_counter()
    show_image()  # Обновить изображение с новыми аннотациями

def select_box(x, y):
    global selected_boxes
    for i, (x1, y1, x2, y2, class_id) in enumerate(shapes):
        if x1 <= x <= x2 and y1 <= y <= y2:
            if i in selected_boxes:
                selected_boxes.remove(i)
            else:
                selected_boxes.add(i)
            break
    refresh_canvas()

def on_delete(event):
    global selected_boxes, shapes
    shapes = [shape for i, shape in enumerate(shapes) if i not in selected_boxes]
    selected_boxes.clear()
    save_annotations()
    refresh_canvas()

def switch_class(event):
    global current_class_id, selected_boxes
    new_class_id = (current_class_id + 1) % len(classes)
    if selected_boxes:
        for box_index in selected_boxes:
            x1, y1, x2, y2, _ = shapes[box_index]
            shapes[box_index] = (x1, y1, x2, y2, new_class_id)
        current_class_id = new_class_id  # Обновляем текущий класс
        selected_boxes.clear()
    else:
        current_class_id = new_class_id
    show_class_label()
    refresh_canvas()

def refresh_canvas():
    annotation_canvas.delete("all")
    annotation_canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)
    for i, shape in enumerate(shapes):
        outline_color = "blue" if i in selected_boxes else class_colors.get(int(shape[4]), 'red')
        annotation_canvas.create_rectangle(shape[0], shape[1], shape[2], shape[3], outline=outline_color)
        if int(shape[4]) < len(classes):
            annotation_canvas.create_text(shape[0], shape[1], anchor=tk.NW, text=f"{int(shape[4])}: {classes[int(shape[4])]}", fill=class_colors.get(int(shape[4]), 'red'))

def show_class_label():
    class_label = tk.Label(root, text=f"Текущий класс: {current_class_id}: {classes[current_class_id]}", bg="yellow")
    class_label.place(relx=0.5, rely=0, anchor='n')

    def hide_class_label():
        class_label.destroy()

    root.after(2000, hide_class_label)

def increase_contrast(level):
    global contrast_level
    contrast_level = level
    refresh_display()

root = ThemedTk(theme="breeze")
root.title("Программа для аннотирования изображений")
root.state('zoomed')
root.resizable(False, False)

# Установить современный стиль
style = {"padx": 10, "pady": 10}
frame = ttk.Frame(root, padding=20)
frame.pack(fill=tk.BOTH, expand=True)

top_frame = ttk.Frame(frame)
top_frame.pack(fill=tk.X, **style)

directory_label = ttk.Label(top_frame, text="Дирректория с изображениями:")
directory_label.pack(side=tk.LEFT)
directory_button = ttk.Button(top_frame, text="Выбрать дирректорию", command=load_dataset)
directory_button.pack(side=tk.LEFT, padx=5)

class_label = ttk.Label(top_frame, text="Настройки классов:")
class_label.pack(side=tk.LEFT, padx=5)
class_button = ttk.Button(top_frame, text="Загрузить файл классов", command=load_class_file)
class_button.pack(side=tk.LEFT, padx=5)

show_class_info_button = ttk.Button(top_frame, text="Показать классы", command=show_class_info)
show_class_info_button.pack(side=tk.LEFT, padx=5)

refresh_button = ttk.Button(top_frame, text="Обновить", command=refresh_display)  # Добавлена кнопка "Обновить"
refresh_button.pack(side=tk.LEFT, padx=5)

clear_button = ttk.Button(top_frame, text="Очистить", command=clear_annotations)
clear_button.pack(side=tk.LEFT, padx=5)

info_frame = ttk.Frame(frame)
info_frame.pack(fill=tk.X, **style)

info_label = ttk.Label(info_frame, text="Всего изображений: 0")
info_label.pack(side=tk.LEFT, padx=5)
image_info_label = ttk.Label(info_frame, text="Текущее изображение: N/A, Позиция: 0/0")
image_info_label.pack(side=tk.LEFT, padx=5)

main_frame = ttk.Frame(frame)
main_frame.pack(fill=tk.BOTH, expand=True)

# Галерея иконок изображений
gallery_frame = ttk.Frame(main_frame, height=50)
gallery_frame.pack(fill=tk.X, expand=False, **style)

# Добавить возможность прокрутки
canvas = tk.Canvas(gallery_frame)
scrollbar = ttk.Scrollbar(gallery_frame, orient="horizontal", command=canvas.xview)
scrollable_frame = ttk.Frame(canvas)

scrollable_frame.bind(
    "<Configure>",
    lambda e: canvas.configure(
        scrollregion=canvas.bbox("all")
    )
)

canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
canvas.configure(xscrollcommand=scrollbar.set)

canvas.pack(side="top", fill="both", expand=True)
scrollbar.pack(side="bottom", fill="x")

# Добавить возможность прокрутки колесиком мыши
canvas.bind_all("<MouseWheel>", lambda event: canvas.xview_scroll(int(-1*(event.delta/120)), "units"))

# Поле для аннотирования
annotation_frame = ttk.Frame(main_frame, height=100)
annotation_frame.pack(fill=tk.BOTH, expand=True, **style)

annotation_canvas = tk.Canvas(annotation_frame, bg="white")
annotation_canvas.pack(fill=tk.BOTH, expand=True)

annotation_canvas.bind("<ButtonPress-1>", on_mouse_down)
annotation_canvas.bind("<ButtonRelease-1>", on_mouse_up)
annotation_canvas.bind("<Motion>", on_mouse_move)
root.bind("<Shift_L>", switch_class)
root.bind("<BackSpace>", on_delete)

root.bind("<Left>", previous_image)
root.bind("<Right>", next_image)

root.bind("a", lambda e: previous_image())
root.bind("A", lambda e: previous_image())
root.bind("ф", lambda e: previous_image())
root.bind("Ф", lambda e: previous_image())

root.bind("d", lambda e: next_image())
root.bind("D", lambda e: next_image())
root.bind("в", lambda e: next_image())
root.bind("В", lambda e: next_image())

root.bind("2", lambda e: increase_contrast(1.5))
root.bind("3", lambda e: increase_contrast(2.0))
root.bind("4", lambda e: increase_contrast(2.5))
root.bind("5", lambda e: increase_contrast(3.0))
root.bind("6", lambda e: increase_contrast(3.5))
root.bind("7", lambda e: increase_contrast(4.0))
root.bind("8", lambda e: increase_contrast(4.5))
root.bind("9", lambda e: increase_contrast(5.0))
root.bind("0", lambda e: increase_contrast(5.5))
root.bind("1", lambda e: increase_contrast(1))

root.mainloop()
