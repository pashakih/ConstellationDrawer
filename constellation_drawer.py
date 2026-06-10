import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime, timezone
import urllib.request
import json
import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from skyfield.api import Star, load, wgs84
from skyfield.data import hipparcos

class ConstellationDrawerApp:
    def __init__(self, root, initial_file=None):
        self.root = root
        self.root.title("Constellation Drawer")
        
        # Application state variables
        self.lines = []           # Stores tuples of connected star coordinates
        self.current_star = None  # Stores the first clicked star for drawing a line
        self.visible_stars = None # Stores calculated positions of visible stars
        
        self.setup_ui()
        self.load_astronomy_data()
        
        # If the app was launched by double-clicking a file, load it immediately
        if initial_file:
            self.load_project(initial_file)
        else:
            self.update_map()

    def setup_ui(self):
        # Left Control Panel (Scrollable Container)
        sidebar_container = ttk.Frame(self.root)
        sidebar_container.pack(side=tk.LEFT, fill=tk.Y)

        self.sidebar_canvas = tk.Canvas(sidebar_container, width=240, highlightthickness=0)
        scrollbar = ttk.Scrollbar(sidebar_container, orient="vertical", command=self.sidebar_canvas.yview)
        self.sidebar_canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.sidebar_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        control_frame = ttk.Frame(self.sidebar_canvas, padding="10")
        self.sidebar_window = self.sidebar_canvas.create_window((0, 0), window=control_frame, anchor="nw")

        # Automatically update the scroll region when the inner frame changes size
        def configure_scrollregion(event):
            self.sidebar_canvas.configure(scrollregion=self.sidebar_canvas.bbox("all"))
        control_frame.bind("<Configure>", configure_scrollregion)
        
        # Automatically resize the inner frame width to match the canvas
        def configure_canvas_window(event):
            self.sidebar_canvas.itemconfig(self.sidebar_window, width=event.width)
        self.sidebar_canvas.bind("<Configure>", configure_canvas_window)

        # --- Sidebar Content ---
        ttk.Label(control_frame, text="Observer Location", font=('Arial', 10, 'bold')).pack(pady=(0, 5))
        
        ttk.Label(control_frame, text="Latitude (-90 to 90):").pack()
        self.lat_entry = ttk.Entry(control_frame)
        self.lat_entry.insert(0, "40.7128") # Default NYC
        self.lat_entry.pack(pady=2)

        ttk.Label(control_frame, text="Longitude (-180 to 180):").pack()
        self.lon_entry = ttk.Entry(control_frame)
        self.lon_entry.insert(0, "-74.0060") # Default NYC
        self.lon_entry.pack(pady=2)

        ttk.Button(control_frame, text="Use My Location", command=self.use_my_location).pack(pady=(5, 2))

        ttk.Label(control_frame, text="Date and Time (UTC)", font=('Arial', 10, 'bold')).pack(pady=(15, 5))
        
        ttk.Label(control_frame, text="Year:").pack()
        self.year_entry = ttk.Entry(control_frame)
        self.year_entry.insert(0, "2026")
        self.year_entry.pack(pady=2)

        ttk.Label(control_frame, text="Month (1-12):").pack()
        self.month_entry = ttk.Entry(control_frame)
        self.month_entry.insert(0, "6")
        self.month_entry.pack(pady=2)

        ttk.Label(control_frame, text="Day (1-31):").pack()
        self.day_entry = ttk.Entry(control_frame)
        self.day_entry.insert(0, "10")
        self.day_entry.pack(pady=2)
        
        ttk.Label(control_frame, text="Hour (0-23):").pack()
        self.hour_entry = ttk.Entry(control_frame)
        self.hour_entry.insert(0, "22")
        self.hour_entry.pack(pady=2)

        ttk.Button(control_frame, text="Reset to Now (UTC)", command=self.reset_to_now).pack(pady=(5, 2))

        ttk.Separator(control_frame, orient='horizontal').pack(fill='x', pady=10)
        
        ttk.Label(control_frame, text="Display Settings", font=('Arial', 10, 'bold')).pack(pady=(0, 5))
        
        ttk.Label(control_frame, text="Limiting Mag. (Max Dimmest):").pack()
        self.mag_entry = ttk.Entry(control_frame)
        self.mag_entry.insert(0, "6.0") # 6.0 is naked eye limit
        self.mag_entry.pack(pady=2)

        ttk.Label(control_frame, text="Reference Magnitude:").pack()
        self.ref_mag_entry = ttk.Entry(control_frame)
        self.ref_mag_entry.insert(0, "0.0") # Set 0.0 (very bright star) as default reference
        self.ref_mag_entry.pack(pady=2)

        ttk.Label(control_frame, text="Size at Ref. Mag:").pack()
        self.ref_size_entry = ttk.Entry(control_frame)
        self.ref_size_entry.insert(0, "60.0") # Size parameter in Matplotlib
        self.ref_size_entry.pack(pady=2)

        ttk.Label(control_frame, text="Colors (Hex Codes)", font=('Arial', 10, 'bold')).pack(pady=(15, 5))
        
        ttk.Label(control_frame, text="Background:").pack()
        self.bg_color_entry = ttk.Entry(control_frame)
        self.bg_color_entry.insert(0, "#000000")
        self.bg_color_entry.pack(pady=2)

        ttk.Label(control_frame, text="Stars & Text:").pack()
        self.star_color_entry = ttk.Entry(control_frame)
        self.star_color_entry.insert(0, "#FFFFFF")
        self.star_color_entry.pack(pady=2)

        ttk.Label(control_frame, text="Lines:").pack()
        self.line_color_entry = ttk.Entry(control_frame)
        self.line_color_entry.insert(0, "#00FFFF")
        self.line_color_entry.pack(pady=2)

        ttk.Label(control_frame, text="Line Thickness:").pack()
        self.line_thick_entry = ttk.Entry(control_frame)
        self.line_thick_entry.insert(0, "1.5")
        self.line_thick_entry.pack(pady=2)

        ttk.Button(control_frame, text="Update Sky", command=self.update_map).pack(pady=15)
        
        ttk.Separator(control_frame, orient='horizontal').pack(fill='x', pady=10)
        
        ttk.Label(control_frame, text="Drawing Controls", font=('Arial', 10, 'bold')).pack(pady=(0, 5))
        ttk.Label(control_frame, text="Click two stars on the map\nto connect them.", justify=tk.CENTER).pack(pady=5)
        
        ttk.Button(control_frame, text="Undo Last Line", command=self.undo_line).pack(pady=2)
        ttk.Button(control_frame, text="Clear All Lines", command=self.clear_lines).pack(pady=2)
        
        ttk.Separator(control_frame, orient='horizontal').pack(fill='x', pady=10)
        
        ttk.Label(control_frame, text="Project Files", font=('Arial', 10, 'bold')).pack(pady=(0, 5))
        ttk.Button(control_frame, text="Save Project (.strmp)", command=self.save_project).pack(pady=2)
        ttk.Button(control_frame, text="Load Project (.strmp)", command=self.load_project).pack(pady=2)
        
        ttk.Separator(control_frame, orient='horizontal').pack(fill='x', pady=10)
        
        ttk.Button(control_frame, text="Export as .SVG", command=self.save_svg).pack(pady=10)

        # Right Map Panel (Matplotlib)
        map_frame = ttk.Frame(self.root)
        map_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.fig = plt.Figure(figsize=(8, 8), dpi=100)
        self.fig.patch.set_facecolor('#000000') # Background color around the map
        
        # Changed from polar to standard 2D Cartesian for zooming capabilities
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#000000') # Map background color
        
        # Set up interactive canvas
        self.canvas = FigureCanvasTkAgg(self.fig, master=map_frame)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.canvas.mpl_connect('button_press_event', self.on_click)

        # Add the interactive toolbar for panning and zooming!
        self.toolbar = NavigationToolbar2Tk(self.canvas, map_frame)
        self.toolbar.update()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def use_my_location(self):
        try:
            with urllib.request.urlopen("http://ip-api.com/json/") as response:
                data = json.loads(response.read().decode())
                if data.get("status") == "success":
                    self.lat_entry.delete(0, tk.END)
                    self.lat_entry.insert(0, str(data.get("lat")))
                    self.lon_entry.delete(0, tk.END)
                    self.lon_entry.insert(0, str(data.get("lon")))
                    self.update_map()
                else:
                    messagebox.showerror("Error", "Could not determine location from IP.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch location.\nDetails: {e}")

    def reset_to_now(self):
        now = datetime.now(timezone.utc)
        self.year_entry.delete(0, tk.END); self.year_entry.insert(0, str(now.year))
        self.month_entry.delete(0, tk.END); self.month_entry.insert(0, str(now.month))
        self.day_entry.delete(0, tk.END); self.day_entry.insert(0, str(now.day))
        self.hour_entry.delete(0, tk.END); self.hour_entry.insert(0, str(now.hour))
        self.update_map()

    def load_astronomy_data(self):
        print("Loading planetary and star data...")
        self.ts = load.timescale()
        self.eph = load('de421.bsp')
        self.earth = self.eph['earth']
        with load.open(hipparcos.URL) as f:
            self.full_stars_df = hipparcos.load_dataframe(f)

    def update_map(self):
        try:
            lat = float(self.lat_entry.get())
            lon = float(self.lon_entry.get())
            year = int(self.year_entry.get())
            month = int(self.month_entry.get())
            day = int(self.day_entry.get())
            hour = int(self.hour_entry.get())
            mag_limit = float(self.mag_entry.get())
            ref_mag = float(self.ref_mag_entry.get())
            ref_size = float(self.ref_size_entry.get())
            
            self.stars_df = self.full_stars_df[self.full_stars_df['magnitude'] <= mag_limit]
            self.star_objects = Star.from_dataframe(self.stars_df)

            t = self.ts.utc(year, month, day, hour)
            observer = self.earth + wgs84.latlon(lat, lon)
            
            astrometric = observer.at(t).observe(self.star_objects)
            apparent = astrometric.apparent()
            alt, az, distance = apparent.altaz()
            
            visible_mask = alt.degrees > 0
            r = 90 - alt.degrees[visible_mask] 
            az_rad = az.radians[visible_mask]
            
            self.x_coords = -r * np.sin(az_rad)
            self.y_coords = r * np.cos(az_rad)
            
            mags = self.stars_df['magnitude'].values[visible_mask]
            
            denom = (mag_limit + 0.5 - ref_mag) ** 2
            if denom == 0: denom = 0.001
            
            scale_c = ref_size / denom
            sizes = scale_c * (mag_limit + 0.5 - mags) ** 2 
            sizes = np.clip(sizes, 0.01, None) 
            
            self.visible_stars = np.column_stack((self.x_coords, self.y_coords))
            self.redraw(sizes)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to calculate sky: {e}")

    def redraw(self, sizes=None):
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        
        try:
            bg_color = self.bg_color_entry.get()
            star_color = self.star_color_entry.get()
            line_color = self.line_color_entry.get()
            self.fig.patch.set_facecolor(bg_color)
            self.ax.set_facecolor(bg_color)
        except Exception:
            bg_color, star_color, line_color = '#000000', '#FFFFFF', '#00FFFF'
            
        try:
            line_thickness = float(self.line_thick_entry.get())
        except ValueError:
            line_thickness = 1.5 

        self.ax.clear()
        self.ax.axis('off') 
        self.ax.set_aspect('equal')
        
        theta_full = np.linspace(0, 2*np.pi, 100)
        r_full = 90
        self.ax.plot(r_full * np.sin(theta_full), r_full * np.cos(theta_full), color=star_color, linewidth=1)
        
        self.ax.text(0, 95, 'N', color=star_color, ha='center', va='center', fontsize=12)
        self.ax.text(-95, 0, 'E', color=star_color, ha='center', va='center', fontsize=12)
        self.ax.text(0, -95, 'S', color=star_color, ha='center', va='center', fontsize=12)
        self.ax.text(95, 0, 'W', color=star_color, ha='center', va='center', fontsize=12)

        if hasattr(self, 'x_coords') and sizes is not None:
            self.ax.scatter(self.x_coords, self.y_coords, s=sizes, facecolors=star_color, edgecolors='none', linewidths=0, alpha=1.0, zorder=2)
            self.saved_sizes = sizes 

        for line in self.lines:
            x_points = [line[0][0], line[1][0]]
            y_points = [line[0][1], line[1][1]]
            self.ax.plot(x_points, y_points, color=line_color, linewidth=line_thickness, alpha=1.0, zorder=1)

        if self.current_star:
            self.ax.scatter(self.current_star[0], self.current_star[1], facecolors='none', edgecolors='red', s=100, zorder=3)

        if xlim != (0.0, 1.0): 
            self.ax.set_xlim(xlim)
            self.ax.set_ylim(ylim)
        else:
            self.ax.set_xlim(-100, 100)
            self.ax.set_ylim(-100, 100)

        self.canvas.draw()

    def on_click(self, event):
        if self.toolbar.mode != '': return
        if event.inaxes != self.ax or self.visible_stars is None: return
            
        click_x, click_y = event.xdata, event.ydata
        star_x, star_y = self.visible_stars[:, 0], self.visible_stars[:, 1]
        
        distances = np.sqrt((star_x - click_x)**2 + (star_y - click_y)**2)
        nearest_idx = np.argmin(distances)
        
        if distances[nearest_idx] < 5:
            selected_star = (self.visible_stars[nearest_idx, 0], self.visible_stars[nearest_idx, 1])
            
            if self.current_star is None:
                self.current_star = selected_star
            else:
                if self.current_star != selected_star:
                    line_to_remove = None
                    for line in self.lines:
                        if (line[0] == self.current_star and line[1] == selected_star) or \
                           (line[1] == self.current_star and line[0] == selected_star):
                            line_to_remove = line
                            break
                            
                    if line_to_remove:
                        self.lines.remove(line_to_remove)
                    else:
                        self.lines.append((self.current_star, selected_star))
                        
                self.current_star = None 
                
            self.redraw(self.saved_sizes)

    def undo_line(self):
        if self.lines:
            self.lines.pop()
            self.redraw(self.saved_sizes)
            
    def clear_lines(self):
        self.lines = []
        self.current_star = None
        self.redraw(self.saved_sizes)

    def save_project(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".strmp", filetypes=[("Star Map Project", "*.strmp")])
        if file_path:
            project_data = {
                "lat": self.lat_entry.get(), "lon": self.lon_entry.get(),
                "year": self.year_entry.get(), "month": self.month_entry.get(),
                "day": self.day_entry.get(), "hour": self.hour_entry.get(),
                "mag_limit": self.mag_entry.get(), "ref_mag": self.ref_mag_entry.get(), "ref_size": self.ref_size_entry.get(),
                "bg_color": self.bg_color_entry.get(), "star_color": self.star_color_entry.get(),
                "line_color": self.line_color_entry.get(), "line_thick": self.line_thick_entry.get(),
                "lines": self.lines
            }
            try:
                with open(file_path, 'w') as f: json.dump(project_data, f)
                messagebox.showinfo("Success", f"Project saved to\n{file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save project: {e}")

    def load_project(self, file_path=None):
        if not file_path:
            file_path = filedialog.askopenfilename(filetypes=[("Star Map Project", "*.strmp")])
            
        if file_path:
            try:
                with open(file_path, 'r') as f: data = json.load(f)
                
                def set_entry(entry_widget, value):
                    entry_widget.delete(0, tk.END); entry_widget.insert(0, str(value))

                set_entry(self.lat_entry, data.get("lat", "40.7128"))
                set_entry(self.lon_entry, data.get("lon", "-74.0060"))
                set_entry(self.year_entry, data.get("year", "2026"))
                set_entry(self.month_entry, data.get("month", "6"))
                set_entry(self.day_entry, data.get("day", "10"))
                set_entry(self.hour_entry, data.get("hour", "22"))
                set_entry(self.mag_entry, data.get("mag_limit", "6.0"))
                set_entry(self.ref_mag_entry, data.get("ref_mag", "0.0"))
                set_entry(self.ref_size_entry, data.get("ref_size", "60.0"))
                set_entry(self.bg_color_entry, data.get("bg_color", "#000000"))
                set_entry(self.star_color_entry, data.get("star_color", "#FFFFFF"))
                set_entry(self.line_color_entry, data.get("line_color", "#FFFFFF"))
                set_entry(self.line_thick_entry, data.get("line_thick", "0.5"))

                loaded_lines = data.get("lines", [])
                self.lines = [((l[0][0], l[0][1]), (l[1][0], l[1][1])) for l in loaded_lines]
                
                self.update_map()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load project: {e}")

    def save_svg(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".svg", filetypes=[("SVG Vector File", "*.svg")])
        if file_path:
            bg_color = self.bg_color_entry.get()
            original_fig_bg = self.fig.patch.get_facecolor()
            original_ax_bg = self.ax.get_facecolor()
            self.fig.patch.set_facecolor(bg_color); self.ax.set_facecolor(bg_color)
            
            self.fig.savefig(file_path, format='svg', facecolor=bg_color, transparent=False)
            
            self.fig.patch.set_facecolor(original_fig_bg); self.ax.set_facecolor(original_ax_bg)
            messagebox.showinfo("Success", f"Map saved successfully as\n{file_path}")

def mac_open_document(*args):
    if app:
        app.load_project(args[0])

if __name__ == "__main__":
    root = tk.Tk()
    
    initial_file = sys.argv[1] if len(sys.argv) > 1 else None
    app = ConstellationDrawerApp(root, initial_file)
    
    root.createcommand("::tk::mac::OpenDocument", mac_open_document)
    root.mainloop()