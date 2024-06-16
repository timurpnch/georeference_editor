import os
from tkinter import *
from tkinter import filedialog as fd
from tkinter import messagebox as mb
from tkinter.ttk import Notebook

import rasterio
from PIL import Image, ImageTk, ImageOps, ImageFilter


class Point:
    def __init__(self, x=0, y=0, x_coord=0, y_coord=0):
        self.x = x
        self.y = y
        self.x_coord = x_coord
        self.y_coord = y_coord

    def __str__(self):
        return f"{self.x=} {self.y=} {self.x_coord=} {self.y_coord=}"


class Editor:
    def __init__(self):
        self.root = Tk()
        self.image_tabs = Notebook(self.root)
        self.opened_images = []

        self.selection_top_x = 0
        self.selection_top_y = 0
        self.selection_bottom_x = 0
        self.selection_bottom_y = 0

        self.canvas_for_selection = None
        self.selection_rect = None

        self.canvas_for_markup = None
        self.markup_rect = None

        self.markup_top_x = 0
        self.markup_top_y = 0
        self.markup_bottom_x = 0
        self.markup_bottom_y = 0

        self.points = list()
        self.canvas_for_points = None
        self.point_draw = None
        self.point_x = 0
        self.point_y = 0

        self.init()

    def init(self):
        self.root.title("Editor")
        self.root.iconphoto(True, PhotoImage(file="resources/geoscan.png"))
        self.image_tabs.enable_traversal()
        self.root.geometry("1280x720")

        self.root.bind("<Escape>", self._close)
        self.root.protocol("WM_DELETE_WINDOW", self._close)

    def run(self):
        self.draw_menu()
        self.draw_widgets()

        self.root.mainloop()

    def draw_menu(self):
        menu_bar = Menu(self.root)

        file_menu = Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Открыть", command=self.open_new_images)
        file_menu.add_command(label="Сохранить", command=self.save_current_image)
        file_menu.add_command(label="Сохранить как", command=self.save_image_as)
        file_menu.add_command(label="Сохранить все", command=self.save_all_changes)
        file_menu.add_separator()
        file_menu.add_command(label="Закрыть изображение", command=self.close_current_image)
        menu_bar.add_cascade(label="Файл", menu=file_menu)

        edit_menu = Menu(menu_bar, tearoff=0)
        transform_menu = Menu(edit_menu, tearoff=0)
        georeference_menu = Menu(menu_bar, tearoff=0)
        # markup_menu = Menu(menu_bar, tearoff=0)

        # markup_menu.add_command(label="Разметить изображение", command=self.start_markup)
        # markup_menu.add_command(label="Добавить объект", command=self.stop_markup)

        georeference_menu.add_command(label="Добавить точки", command=self.add_point)
        georeference_menu.add_command(label="Привязать", command=self.georeference)

        rotate_menu = Menu(edit_menu, tearoff=0)
        rotate_menu.add_command(label="Повернуть влево на 90", command=lambda: self.rotate_current_image(90))
        rotate_menu.add_command(label="Повернуть вправо на 90", command=lambda: self.rotate_current_image(-90))
        rotate_menu.add_command(label="Повернуть влево на 180", command=lambda: self.rotate_current_image(180))
        rotate_menu.add_command(label="Повернуть вправо на 180", command=lambda: self.rotate_current_image(-180))
        transform_menu.add_cascade(label="Повернуть", menu=rotate_menu)

        flip_menu = Menu(edit_menu, tearoff=0)
        flip_menu.add_command(label="Отразить горизонтально", command=lambda: self.flip_current_image("horizontally"))
        flip_menu.add_command(label="Отразить вертикально", command=lambda: self.flip_current_image("vertically"))

        resize_menu = Menu(edit_menu, tearoff=0)
        resize_menu.add_command(label="25% от оригинала", command=lambda: self.resize_current_image(25))
        resize_menu.add_command(label="50% от оригинала", command=lambda: self.resize_current_image(50))
        resize_menu.add_command(label="75% от оригинала", command=lambda: self.resize_current_image(75))
        resize_menu.add_command(label="125% от оригинала", command=lambda: self.resize_current_image(125))
        resize_menu.add_command(label="150% от оригинала", command=lambda: self.resize_current_image(150))
        resize_menu.add_command(label="175% от оригинала", command=lambda: self.resize_current_image(175))
        resize_menu.add_command(label="200% от оригинала", command=lambda: self.resize_current_image(200))

        filter_menu = Menu(edit_menu, tearoff=0)
        filter_menu.add_command(label="Размытие", command=lambda: self.apply_filter_to_current_image(ImageFilter.BLUR))
        filter_menu.add_command(label="Повысить контрастность",
                                command=lambda: self.apply_filter_to_current_image(ImageFilter.SHARPEN))
        filter_menu.add_command(label="Увеличить контрастность контура",
                                command=lambda: self.apply_filter_to_current_image(ImageFilter.CONTOUR))
        filter_menu.add_command(label="Повышение детализации",
                                command=lambda: self.apply_filter_to_current_image(ImageFilter.DETAIL))

        crop_menu = Menu(edit_menu, tearoff=0)
        crop_menu.add_command(label="Выделить", command=self.start_area_selection_of_current_image)
        crop_menu.add_command(label="Обрезать", command=self.stop_area_selection_of_current_image)

        edit_menu.add_cascade(label="Преобразовать", menu=transform_menu)
        edit_menu.add_cascade(label="Отразить", menu=flip_menu)
        edit_menu.add_cascade(label="Изменить размер", menu=resize_menu)
        edit_menu.add_cascade(label="Фильтры", menu=filter_menu)
        edit_menu.add_cascade(label="Обрезать", menu=crop_menu)
        menu_bar.add_cascade(label="Редактирование", menu=edit_menu)
        menu_bar.add_cascade(label="Геопривязка", menu=georeference_menu)
        # menu_bar.add_cascade(label="Разметка", menu=markup_menu)

        self.root.configure(menu=menu_bar)

    def draw_widgets(self):
        self.image_tabs.pack(fill="both", expand=1)

    def open_new_images(self):
        image_paths = fd.askopenfilenames(filetypes=[("Images", "*.jpeg;*.jpg;*.png")])
        for image_path in image_paths:
            self.add_new_image(image_path)

    def add_new_image(self, image_path):
        image = Image.open(image_path)
        image_tk = ImageTk.PhotoImage(image)
        self.opened_images.append([image_path, image])

        image_tab = Frame(self.image_tabs)

        image_panel = Canvas(image_tab, width=image_tk.width(), height=image_tk.height(), bd=0, highlightthickness=0)
        image_panel.image = image_tk
        image_panel.create_image(0, 0, image=image_tk, anchor="nw")
        image_panel.pack(expand=True)

        self.image_tabs.add(image_tab, text=image_path.split('/')[-1])
        self.image_tabs.select(image_tab)

    def get_current_working_data(self):
        # returns (tab, image, path)
        current_tab = self.image_tabs.select()
        if not current_tab:
            return None, None, None
        tab_number = self.image_tabs.index(current_tab)
        path, image = self.opened_images[tab_number]

        return current_tab, path, image

    def save_current_image(self):
        current_tab, path, image = self.get_current_working_data()
        if not current_tab:
            return
        tab_number = self.image_tabs.index(current_tab)

        if path[-1] == "*":
            path = path[:-1]
            self.opened_images[tab_number][0] = path
            image.save(path)
            self.image_tabs.add(current_tab, text=path.split('/')[-1])

    def save_image_as(self):
        current_tab, path, image = self.get_current_working_data()
        if not current_tab:
            return
        tab_number = self.image_tabs.index(current_tab)

        old_path, old_ext = os.path.splitext(path)
        new_path = fd.asksaveasfilename(initialdir=old_path, filetypes=[("Images", "*.jpeg;*.jpg;*.png")])
        if old_ext[-1] == "*":
            old_ext = old_ext[:-1]
        if not new_path:
            return

        new_path, new_ext = os.path.splitext(new_path)
        if not new_ext:
            new_ext = old_ext
        elif old_ext != new_ext:
            mb.showerror("Неправильное расширение файла",
                         f"Получили непраильное расширение: {new_ext}. Прошлое было: {old_ext}")

        image.save(new_path + new_ext)
        image.close()

        del self.opened_images[tab_number]
        self.image_tabs.forget(current_tab)

        self.add_new_image(new_path + new_ext)

    def save_all_changes(self):
        for index, (path, image) in enumerate(self.opened_images):
            if path[-1] != "*":
                continue
            path = path[:-1]
            self.opened_images[index][0] = path
            image.save(path)
            self.image_tabs.tab(index, text=path.split('/')[-1])

    def close_current_image(self):
        current_tab, path, image = self.get_current_working_data()
        if not current_tab:
            return
        index = self.image_tabs.index(current_tab)

        image.close()
        del self.opened_images[index]
        self.image_tabs.forget(current_tab)

    def update_image_inside_app(self, current_tab, image):
        tab_number = self.image_tabs.index(current_tab)
        tab_frame = self.image_tabs.children[current_tab[current_tab.rfind("!"):]]
        canvas = tab_frame.children['!canvas']

        self.opened_images[tab_number][1] = image

        image_tk = ImageTk.PhotoImage(image)
        canvas.delete("all")
        canvas.image = image_tk
        canvas.configure(width=image_tk.width(), height=image_tk.height())
        canvas.create_image(0, 0, image=image_tk, anchor="nw")

        image_path = self.opened_images[tab_number][0]
        if image_path[-1] != '*':
            image_path += "*"
            self.opened_images[tab_number][0] = image_path
            image_name = image_path.split('/')[-1]
            self.image_tabs.tab(current_tab, text=image_name)

    def rotate_current_image(self, degrees):
        current_tab, path, image = self.get_current_working_data()
        if not current_tab:
            return

        image = image.rotate(degrees)
        self.update_image_inside_app(current_tab, image)

    def flip_current_image(self, flip_type):
        current_tab, path, image = self.get_current_working_data()
        if not current_tab:
            return

        if flip_type == "horizontally":
            image = ImageOps.mirror(image)
        elif flip_type == "vertically":
            image = ImageOps.flip(image)

        self.update_image_inside_app(current_tab, image)

    def resize_current_image(self, percents):
        current_tab, path, image = self.get_current_working_data()

        if not current_tab:
            return

        w, h = image.size
        w = (w * percents) // 100
        h = (h * percents) // 100

        image = image.resize((w, h), Image.LANCZOS)
        self.update_image_inside_app(current_tab, image)

    def apply_filter_to_current_image(self, filter_type):
        current_tab, path, image = self.get_current_working_data()
        if not current_tab:
            return

        image = image.filter(filter_type)
        self.update_image_inside_app(current_tab, image)

    def add_point(self):
        current_tab = self.image_tabs.select()
        if not current_tab:
            return
        tab_frame = self.image_tabs.children[current_tab[current_tab.rfind("!"):]]
        canvas = tab_frame.children['!canvas']

        self.canvas_for_points = canvas

        canvas.bind("<Button-1>", self.add_new_point)

    def add_point_to_list(self, x_coord, y_coord, window):
        if x_coord.replace(".", "").replace("-", "").isnumeric() and y_coord.replace(".", "").isnumeric():
            self.points.append(Point(self.point_x, self.point_y, float(x_coord), float(y_coord)))
            self.print_point_list()
            window.destroy()
        else:
            mb.showerror("Неверные координаты",
                         f"Координаты неверны")

    def print_point_list(self):
        for x in self.points:
            print(x)

    def add_new_point(self, event):
        current_tab = self.image_tabs.select()
        if not current_tab:
            return
        tab_frame = self.image_tabs.children[current_tab[current_tab.rfind("!"):]]
        canvas = tab_frame.children['!canvas']
        self.point_x = event.x
        self.point_y = event.y
        self.point_draw = canvas.create_oval(self.point_x, self.point_y, self.point_x, self.point_y,
                                             fill="black", width=3)
        points_window = Toplevel(self.root)
        points_window.geometry("400x200")

        points_window.title("Введите координаты точки")
        Label(points_window, text="Введите XY координаты точки, соответствующие точке изображения").pack()

        Label(points_window, text="X / долгота").pack()
        EntryX = Entry(points_window, width=10)
        EntryX.pack()

        Label(points_window, text="Y / широта").pack()
        EntryY = Entry(points_window, width=10)
        EntryY.pack()

        but = Button(points_window, text="Добавить точку",
                     command=lambda: self.add_point_to_list(EntryX.get(), EntryY.get(), points_window))
        but.pack()

        points_window.transient(self.root)
        points_window.grab_set()
        points_window.focus_set()
        points_window.wait_window()

    def georeference(self):
        current_tab, path, image = self.get_current_working_data()
        if not current_tab:
            return
        unRefRaster = rasterio.open(path)
        gcps = []
        for point in self.points:
            gcp = rasterio.control.GroundControlPoint(row=point.y, col=point.x, x=point.x_coord, y=point.y_coord)
            gcps.append(gcp)
        transformation = rasterio.transform.from_gcps(gcps)

        outputPath = path[:path.rfind(".")] + "_out" + path[path.rfind("."):]
        with rasterio.open(
                outputPath,
                'w',
                driver='GTiff',
                height=unRefRaster.read(1).shape[0],
                width=unRefRaster.read(1).shape[1],
                count=3,
                dtype=unRefRaster.read(1).dtype,
                crs=rasterio.crs.CRS.from_epsg(4326),
                transform=transformation,
        ) as dst:
            dst.write(unRefRaster.read(1), 1)
            dst.write(unRefRaster.read(2), 2)
            dst.write(unRefRaster.read(3), 3)

    def start_area_selection_of_current_image(self):
        current_tab = self.image_tabs.select()
        if not current_tab:
            return
        tab_frame = self.image_tabs.children[current_tab[current_tab.rfind("!"):]]
        canvas = tab_frame.children['!canvas']

        self.canvas_for_selection = canvas
        self.selection_rect = canvas.create_rectangle(
            self.selection_top_x, self.selection_top_y,
            self.selection_bottom_x, self.selection_bottom_y,
            dash=(10, 10), fill='', outline="white", width=2
        )

        canvas.bind("<Button-1>", self.get_selection_start_pos)
        canvas.bind("<B1-Motion>", self.update_selection_and_pos)

    def get_selection_start_pos(self, event):
        self.selection_top_x, self.selection_top_y = event.x, event.y

    def update_selection_and_pos(self, event):
        self.selection_bottom_x, self.selection_bottom_y = event.x, event.y
        if self.canvas_for_selection is not None and self.selection_rect is not None:
            self.canvas_for_selection.coords(
                self.selection_rect,
                self.selection_top_x, self.selection_top_y,
                self.selection_bottom_x, self.selection_bottom_y
            )

    def stop_area_selection_of_current_image(self):
        self.canvas_for_selection.unbind("<Button-1>")
        self.canvas_for_selection.unbind("<B1-Motion>")

        self.canvas_for_selection.delete(self.selection_rect)

        self.crop_current_image()

        self.selection_rect = None
        self.canvas_for_selection = None
        self.selection_top_x, self.selection_top_y = 0, 0
        self.selection_bottom_x, self.selection_bottom_y = 0, 0

    def crop_current_image(self):
        current_tab, path, image = self.get_current_working_data()
        if not current_tab:
            return
        image = image.crop((
            self.selection_top_x, self.selection_top_y,
            self.selection_bottom_x, self.selection_bottom_y
        ))

        self.update_image_inside_app(current_tab, image)

    def start_markup(self):
        current_tab = self.image_tabs.select()
        if not current_tab:
            return
        tab_frame = self.image_tabs.children[current_tab[current_tab.rfind("!"):]]
        canvas = tab_frame.children['!canvas']

        self.canvas_for_markup = canvas
        self.markup_rect = canvas.create_rectangle(
            self.markup_top_x, self.markup_top_y,
            self.markup_bottom_x, self.markup_bottom_y, fill='', outline="white", width=2
        )

        canvas.bind("<Button-1>", self.get_markup_start_pos)
        canvas.bind("<B1-Motion>", self.update_markup_and_pos)

        markup_window = Toplevel(self.root)
        markup_window.geometry("400x720")

        markup_window.title("Разметка данных")

        markup_window.transient(self.root)

    def get_markup_start_pos(self, event):
        self.markup_top_x, self.markup_top_y = event.x, event.y

    def update_markup_and_pos(self, event):
        self.markup_bottom_x, self.markup_bottom_y = event.x, event.y
        if self.canvas_for_markup is not None and self.markup_rect is not None:
            self.canvas_for_markup.coords(
                self.markup_rect,
                self.markup_top_x, self.markup_top_y,
                self.markup_bottom_x, self.markup_bottom_y
            )

    def stop_markup(self):
        add_class_window = Toplevel(self.root)
        add_class_window.geometry("400x200")

        points_window.title("Выберите класс объекта")
        Label(points_window, text="Введите XY координаты точки, соответствующие точке изображения").pack()

        Label(points_window, text="X / долгота").pack()
        EntryX = Entry(points_window, width=10)
        EntryX.pack()

        Label(points_window, text="Y / широта").pack()
        EntryY = Entry(points_window, width=10)
        EntryY.pack()

        but = Button(points_window, text="Добавить точку",
                     command=lambda: self.add_point_to_list(EntryX.get(), EntryY.get(), points_window))
        but.pack()

        points_window.transient(self.root)
        points_window.grab_set()
        points_window.focus_set()
        points_window.wait_window()


        self.canvas_for_markup.unbind("<Button-1>")
        self.canvas_for_markup.unbind("<B1-Motion>")

        # self.canvas_for_selection.delete(self.selection_rect)

        self.markup_current_image()

        self.markup_rect = None
        self.canvas_for_markup = None
        self.markup_top_x, self.markup_top_y = 0, 0
        self.markup_bottom_x, self.markup_bottom_y = 0, 0


    def markup_current_image(self):
        print("end")
        current_tab, path, image = self.get_current_working_data()
        if not current_tab:
            return




        # image = image.crop((
        #     self.selection_top_x, self.selection_top_y,
        #     self.selection_bottom_x, self.selection_bottom_y
        # ))

        self.update_image_inside_app(current_tab, image)

    def unsaved_images(self):
        for path, _ in self.opened_images:
            if path[-1] == "*":
                return True
        return False

    def _close(self, event=None):
        if self.unsaved_images():
            if not mb.askyesno("Несохраненные изменения",
                               "Имеются несохраненные изменения. Вы хотите выйти без сохранения?"):
                return
        self.root.quit()


if __name__ == "__main__":
    Editor().run()
