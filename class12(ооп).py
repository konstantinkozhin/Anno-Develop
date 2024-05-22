import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from tkinter import ttk
from PIL import Image, ImageDraw, ImageFont, ImageTk
from ttkthemes import ThemedTk
import random


class ImageAnnotationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Программа для аннотирования изображений")
        self.root.bind("<Left>", self.previous_image)
        self.root.bind("<Right>", self.next_image)
        self.root.bind("<Return>", self.annotate_image)

        self.dataset = []
        self.index = 0
        self.total_images = 0
        self.image_dir = ''
        self.label_dir = ''
        self.current_annotations = []
        self.selected_boxes = set()
        self.classes = [""]
        self.class_colors = {0: "red"}
        self.current_class_id = 0

        self.setup_ui()

    def setup_ui(self):
        style = {"padx": 10, "pady": 10}
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        directory_frame = ttk.Frame(frame)
        directory_frame.pack(fill=tk.X, **style)

        directory_label = ttk.Label(directory_frame, text="Дирректория с изображениями:")
        directory_label.pack(side=tk.LEFT)
        directory_button = ttk.Button(directory_frame, text="Загрузить", command=self.load_dataset)
        directory_button.pack(side=tk.RIGHT)

        class_frame = ttk.Frame(frame)
        class_frame.pack(fill=tk.X, **style)

        class_label = ttk.Label(class_frame, text="Список классов:")
        class_label.pack(side=tk.LEFT)
        class_button = ttk.Button(class_frame, text="Загрузить файл классов", command=self.load_class_file)
        class_button.pack(side=tk.RIGHT)

        show_class_info_button = ttk.Button(class_frame, text="Показать классы", command=self.show_class_info)
        show_class_info_button.pack(side=tk.RIGHT, padx=5)

        refresh_button = ttk.Button(class_frame, text="Обновить", command=self.refresh_display)
        refresh_button.pack(side=tk.RIGHT, padx=5)

        canvas_frame = ttk.Frame(frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, **style)

        self.canvas = tk.Canvas(canvas_frame, bg='gray')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", self.resize_image)

        info_frame = ttk.Frame(frame)
        info_frame.pack(fill=tk.X, **style)

        self.info_label = ttk.Label(info_frame, text="Всего изображений: 0")
        self.info_label.pack()
        self.image_info_label = ttk.Label(info_frame, text="Текущее изображение: N/A, Позиция: 0/0")
        self.image_info_label.pack()

        nav_frame = ttk.Frame(frame)
        nav_frame.pack(fill=tk.X, **style)

        previous_button = ttk.Button(nav_frame, text="Назад", command=self.previous_image)
        previous_button.pack(side=tk.LEFT, padx=5)
        next_button = ttk.Button(nav_frame, text="Вперед", command=self.next_image)
        next_button.pack(side=tk.RIGHT, padx=5)
        annotate_button = ttk.Button(nav_frame, text="Аннотировать", command=self.annotate_image)
        annotate_button.pack(side=tk.RIGHT, padx=5)

        clear_button = ttk.Button(nav_frame, text="Очистить", command=self.clear_annotations)
        clear_button.pack(side=tk.RIGHT, padx=5)

        annotation_frame = ttk.Frame(frame)
        annotation_frame.pack(fill=tk.BOTH, **style)

        annotation_label = ttk.Label(annotation_frame, text="Координаты:")
        annotation_label.pack(anchor=tk.W)
        self.annotation_textbox = scrolledtext.ScrolledText(annotation_frame, wrap=tk.WORD, height=10)
        self.annotation_textbox.pack(fill=tk.BOTH, expand=True)
        self.annotation_textbox.config(state=tk.DISABLED)
        self.annotation_textbox.bind("<KeyRelease>", self.update_annotation_text)

        self.add_copy_paste_select_support()

    def add_copy_paste_select_support(self):
        self.root.bind_all("<Control-c>", self.copy)
        self.root.bind_all("<Control-x>", self.cut)
        self.root.bind_all("<Control-v>", self.paste)
        self.root.bind_all("<Control-a>", self.select_all)

    def load_dataset(self):
        directory = filedialog.askdirectory()
        if not directory:
            return

        self.image_dir = directory
        self.label_dir = os.path.join(os.path.dirname(directory), "labels")
        os.makedirs(self.label_dir, exist_ok=True)

        self.dataset = [os.path.join(self.image_dir, f)
                        for f in os.listdir(self.image_dir) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
        self.total_images = len(self.dataset)
        self.index = 0
        self.current_annotations = []

        if self.dataset:
            self.show_image()
            self.update_counter()
            self.load_annotation_text()
            self.annotation_textbox.config(state=tk.NORMAL)
        else:
            messagebox.showerror("Ошибка", "No images found in the specified directory.")
            self.info_label.config(text="Всего изображений: 0")
            self.annotation_textbox.config(state=tk.DISABLED)

    def draw_boxes(self, image, annotation_list, selected_boxes):
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
            outline_color = self.class_colors.get(int(class_id), "red")
            if i in selected_boxes:
                outline_color = "blue"
            draw.rectangle([x1, y1, x2, y2], outline=outline_color, width=2)
            if int(class_id) < len(self.classes):
                draw.text((x1, y1), f"{int(class_id)}: {self.classes[int(class_id)]}", fill=outline_color, font=font)

        return image

    def show_image(self):
        if not self.dataset:
            return

        img_path = self.dataset[self.index]
        image = Image.open(img_path)

        annotation_path = os.path.join(self.label_dir, os.path.basename(img_path).replace(".jpg", ".txt"))
        if os.path.exists(annotation_path):
            with open(annotation_path, 'r') as file:
                annotation_text = file.read().strip().split('\n')
            annotation_list = [line.split() for line in annotation_text]
        else:
            annotation_list = []

        self.selected_boxes.clear()
        image = self.draw_boxes(image, annotation_list, self.selected_boxes)
        self.update_image_on_canvas(image)
        self.update_image_info()

    def update_image_on_canvas(self, image):
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        image.thumbnail((canvas_width, canvas_height), Image.Resampling.LANCZOS)

        tk_image = ImageTk.PhotoImage(image)
        self.canvas.image = tk_image
        self.canvas.create_image(0, 0, anchor=tk.NW, image=tk_image)
        self.canvas.update_idletasks()
        self.canvas.update()

    def resize_image(self, event):
        if not self.dataset:
            return
        self.show_image()

    def next_image(self, event=None):
        if self.index < self.total_images - 1:
            self.index += 1
            self.show_image()
            self.update_counter()
            self.load_annotation_text()

    def previous_image(self, event=None):
        if self.index > 0:
            self.index -= 1
            self.show_image()
            self.update_counter()
            self.load_annotation_text()

    def update_counter(self):
        num_annotated = sum(1 for img_path in self.dataset if os.path.exists(
            os.path.join(self.label_dir, os.path.basename(img_path).replace(".jpg", ".txt"))) and os.path.getsize(
            os.path.join(self.label_dir, os.path.basename(img_path).replace(".jpg", ".txt"))) > 0)
        self.info_label.config(text=f"Всего изображений: {self.total_images}, Аннотировано: {num_annotated}")

    def update_image_info(self):
        if self.index < len(self.dataset):
            self.image_info_label.config(text=f"Текущее изображение: {os.path.basename(self.dataset[self.index])}, Позиция: {self.index + 1}/{self.total_images}")

    def load_annotation_text(self):
        if self.index < len(self.dataset):
            annotation_path = os.path.join(self.label_dir, os.path.basename(self.dataset[self.index]).replace(".jpg", ".txt"))
            if os.path.exists(annotation_path):
                with open(annotation_path, 'r') as file:
                    annotation_text = file.read()
                self.annotation_textbox.config(state=tk.NORMAL)
                self.annotation_textbox.delete(1.0, tk.END)
                self.annotation_textbox.insert(tk.END, annotation_text)
            else:
                self.annotation_textbox.config(state=tk.NORMAL)
                self.annotation_textbox.delete(1.0, tk.END)

    def update_annotation_text(self, event=None):
        if not self.dataset:
            return
        annotation_text = self.annotation_textbox.get(1.0, tk.END).strip()
        self.current_annotations = [line.split() for line in annotation_text.split('\n') if line]
        if self.index < len(self.dataset):
            annotation_path = os.path.join(self.label_dir, os.path.basename(self.dataset[self.index]).replace(".jpg", ".txt"))
            with open(annotation_path, 'w') as file:
                for ann in self.current_annotations:
                    file.write(" ".join(map(str, ann)) + "\n")
        self.show_image()
        self.update_counter()

    def draw_boxes_cv(self, image_path, annotation_path):
        root = tk.Toplevel(self.root)
        root.title("Draw Boxes")
        root.attributes('-topmost', True)
        root.state('zoomed')
        root.overrideredirect(True)

        img = Image.open(image_path)
        img_width, img_height = img.size

        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()

        scale_factor = min(screen_width / img_width, screen_height / img_height)
        new_width = int(img_width * scale_factor)
        new_height = int(img_height * scale_factor)
        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        tk_img = ImageTk.PhotoImage(img_resized)
        canvas = tk.Canvas(root, width=new_width, height=new_height)
        canvas.pack(fill=tk.BOTH, expand=True)

        canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)

        shapes = []
        self.current_shape = []
        self.selected_boxes = set()

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
                shapes.append((x1, y1, x2, y2, class_id))
                canvas.create_rectangle(x1, y1, x2, y2, outline=self.class_colors.get(int(class_id), 'red'))
                if int(class_id) < len(self.classes):
                    canvas.create_text(x1, y1, anchor=tk.NW, text=f"{int(class_id)}: {self.classes[int(class_id)]}", fill=self.class_colors.get(int(class_id), 'red'))

        canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        canvas.bind("<Motion>", self.on_mouse_move)
        root.bind("<BackSpace>", self.on_backspace)
        root.bind("<Return>", self.on_enter)
        root.bind("<Shift_L>", self.switch_class)

        self.draw_boxes_cv_canvas = canvas
        self.draw_boxes_cv_tk_img = tk_img
        self.draw_boxes_cv_shapes = shapes
        self.draw_boxes_cv_root = root
        self.draw_boxes_cv_annotation_path = annotation_path

        root.mainloop()

    def on_mouse_down(self, event):
        if event.state & 0x0004:
            self.select_box(event.x, event.y)
        else:
            self.start_x = event.x
            self.start_y = event.y
            self.current_shape = self.draw_boxes_cv_canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline=self.class_colors.get(self.current_class_id, 'red'))

    def on_mouse_up(self, event):
        if not (event.state & 0x0004):
            end_x = event.x
            end_y = event.y
            if abs(end_x - self.start_x) > 0 and abs(end_y - self.start_y) > 0:
                self.draw_boxes_cv_shapes.append((self.start_x, self.start_y, end_x, end_y, self.current_class_id))
                self.draw_boxes_cv_canvas.create_text(self.start_x, self.start_y, anchor=tk.NW, text=f"{self.current_class_id}: {self.classes[self.current_class_id]}", fill=self.class_colors.get(self.current_class_id, 'red'))
            else:
                self.draw_boxes_cv_canvas.delete(self.current_shape)
            self.current_shape = None

    def on_mouse_move(self, event):
        if self.current_shape is not None:
            self.draw_boxes_cv_canvas.coords(self.current_shape, self.start_x, self.start_y, event.x, event.y)

    def on_backspace(self, event):
        for box_index in sorted(self.selected_boxes, reverse=True):
            self.draw_boxes_cv_shapes.pop(box_index)
        self.selected_boxes.clear()
        self.refresh_draw_boxes_cv_canvas()

    def on_enter(self, event):
        self.save_annotations()
        self.draw_boxes_cv_root.destroy()

    def save_annotations(self):
        current_annotations = []
        new_width = self.draw_boxes_cv_tk_img.width()
        new_height = self.draw_boxes_cv_tk_img.height()
        for shape in self.draw_boxes_cv_shapes:
            x1, y1, x2, y2, class_id = shape
            width = abs(x2 - x1)
            height = abs(y2 - y1)
            if width == 0 or height == 0:
                continue
            x_center = ((x1 + x2) / 2) / new_width
            y_center = ((y1 + y2) / 2) / new_height
            width /= new_width
            height /= new_height
            x_center = min(max(x_center, 0), 1)
            y_center = min(max(y_center, 0), 1)
            width = min(max(width, 0), 1)
            height = min(max(height, 0), 1)
            current_annotations.append([int(class_id), x_center, y_center, width, height])

        with open(self.draw_boxes_cv_annotation_path, 'w') as file:
            for ann in current_annotations:
                file.write(" ".join(map(str, ann)) + "\n")

        self.load_annotation_text()
        self.update_counter()
        self.show_image()

    def select_box(self, x, y):
        for i, (x1, y1, x2, y2, class_id) in enumerate(self.draw_boxes_cv_shapes):
            if x1 <= x <= x2 and y1 <= y <= y2:
                if i in self.selected_boxes:
                    self.selected_boxes.remove(i)
                else:
                    self.selected_boxes.add(i)
                break
        self.refresh_draw_boxes_cv_canvas()

    def switch_class(self, event):
        new_class_id = (self.current_class_id + 1) % len(self.classes)
        if self.selected_boxes:
            for box_index in self.selected_boxes:
                x1, y1, x2, y2, _ = self.draw_boxes_cv_shapes[box_index]
                self.draw_boxes_cv_shapes[box_index] = (x1, y1, x2, y2, new_class_id)
            self.current_class_id = new_class_id
            self.selected_boxes.clear()
        else:
            self.current_class_id = new_class_id
        self.show_class_label()
        self.refresh_draw_boxes_cv_canvas()

    def refresh_draw_boxes_cv_canvas(self):
        self.draw_boxes_cv_canvas.delete("all")
        self.draw_boxes_cv_canvas.create_image(0, 0, anchor=tk.NW, image=self.draw_boxes_cv_tk_img)
        for i, shape in enumerate(self.draw_boxes_cv_shapes):
            outline_color = "blue" if i in self.selected_boxes else self.class_colors.get(int(shape[4]), 'red')
            self.draw_boxes_cv_canvas.create_rectangle(shape[0], shape[1], shape[2], shape[3], outline=outline_color)
            if int(shape[4]) < len(self.classes):
                self.draw_boxes_cv_canvas.create_text(shape[0], shape[1], anchor=tk.NW, text=f"{int(shape[4])}: {self.classes[int(shape[4])]}", fill=self.class_colors.get(int(shape[4]), 'red'))

    def show_class_label(self):
        class_label = tk.Label(self.draw_boxes_cv_root, text=f"Текущий класс: {self.current_class_id}: {self.classes[self.current_class_id]}", bg="yellow")
        class_label.place(relx=0.5, rely=0, anchor='n')

        def hide_class_label():
            class_label.destroy()

        self.draw_boxes_cv_root.after(2000, hide_class_label)

    def annotate_image(self, event=None):
        if self.index < len(self.dataset):
            img_path = self.dataset[self.index]
            annotation_path = os.path.join(self.label_dir, os.path.basename(self.dataset[self.index]).replace(".jpg", ".txt"))
            self.draw_boxes_cv(img_path, annotation_path)
            self.show_image()
            self.update_counter()
            self.load_annotation_text()
        else:
            messagebox.showinfo("Информация", "No images to annotate")

    def load_class_file(self):
        file_path = filedialog.askopenfilename(title="Выбрать файл классов", filetypes=(("Text files", "*.txt"), ("All files", "*.*")))
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    self.classes = [line.strip() for line in file.readlines()]
                self.class_colors = {i: "#%06x" % random.randint(0, 0xFFFFFF) for i in range(len(self.classes))}
                messagebox.showinfo("Классы загружены", f"Классы: {self.classes}")
                self.refresh_display()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось загрузить классы: {e}")
        else:
            self.classes = [""]
            self.class_colors = {0: "red"}
            messagebox.showwarning("Предупреждение", "Файл классов не выбран, используется класс по умолчанию")

    def refresh_display(self):
        if self.dataset:
            self.show_image()
            self.update_counter()
            self.load_annotation_text()

    def show_class_info(self):
        class_info_window = tk.Toplevel(self.root)
        class_info_window.title("Информация о классах")

        frame = ttk.Frame(class_info_window)
        frame.pack(fill=tk.BOTH, expand=True)

        tree = ttk.Treeview(frame, columns=("ID", "Класс"), show='headings', height=10)
        tree.column("ID", width=50, anchor='center')
        tree.column("Класс", anchor='center')
        tree.heading("ID", text="ID")
        tree.heading("Класс", text="Класс")

        for i, cls in enumerate(self.classes):
            tree.insert("", "end", values=(i, cls), tags=(i,))

        for i in range(len(self.classes)):
            tree.tag_configure(str(i), background=self.class_colors[i])

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        tree.configure(yscrollcommand=scrollbar.set)
        class_info_window.mainloop()

    def clear_annotations(self):
        self.current_annotations = []
        self.annotation_textbox.delete(1.0, tk.END)
        if self.index < len(self.dataset):
            annotation_path = os.path.join(self.label_dir, os.path.basename(self.dataset[self.index]).replace(".jpg", ".txt"))
            with open(annotation_path, 'w') as file:
                file.write("")
        self.show_image()
        self.update_counter()

    def copy(self, event=None):
        widget = self.root.focus_get()
        if isinstance(widget, tk.Text):
            try:
                self.root.clipboard_clear()
                text = widget.selection_get()
                self.root.clipboard_append(text)
            except tk.TclError:
                pass

    def cut(self, event=None):
        widget = self.root.focus_get()
        if isinstance(widget, tk.Text):
            try:
                self.root.clipboard_clear()
                text = widget.selection_get()
                self.root.clipboard_append(text)
                widget.delete("sel.first", "sel.last")
            except tk.TclError:
                pass

    def paste(self, event=None):
        widget = self.root.focus_get()
        if isinstance(widget, tk.Text):
            try:
                text = self.root.clipboard_get()
                widget.insert('insert', text)
            except tk.TclError:
                pass

    def select_all(self, event=None):
        widget = self.root.focus_get()
        if isinstance(widget, tk.Text):
            widget.tag_add('sel', '1.0', 'end')
            return 'break'


if __name__ == "__main__":
    root = ThemedTk(theme="breeze")
    app = ImageAnnotationApp(root)
    root.mainloop()
