import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime, timezone
import urllib.request
import json
import sys
import os
import re
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.path import Path
from matplotlib.patches import Polygon
from skyfield.api import Star, load, wgs84
from skyfield.data import hipparcos
from skyfield.almanac import fraction_illuminated

PLANET_KEYS = {
    'Sun': 'sun', 'Moon': 'moon', 'Mercury': 'mercury', 'Venus': 'venus',
    'Mars': 'mars', 'Jupiter': 'jupiter barycenter', 'Saturn': 'saturn barycenter',
    'Uranus': 'uranus barycenter', 'Neptune': 'neptune barycenter'
}
PLANET_MAGS = {
    'Sun': -26.7, 'Moon': -12.7, 'Venus': -4.1, 'Jupiter': -2.2,
    'Mars': -0.5, 'Mercury': 0.0, 'Saturn': 0.4, 'Uranus': 5.8, 'Neptune': 7.8
}
PLANET_COLORS = {
    'Sun': '#FFCC00', 'Moon': '#FFFFFF', 'Mercury': '#B0C4DE', 'Venus': '#F5DEB3',
    'Mars': '#FF4500', 'Jupiter': '#DAA520', 'Saturn': '#F4A460', 'Uranus': '#87CEEB', 'Neptune': '#4169E1'
}
PLANET_SYMBOLS = {
    'Sun': '☉', 'Moon': '☽', 'Mercury': '☿', 'Venus': '♀',
    'Mars': '♂', 'Jupiter': '♃', 'Saturn': '♄', 'Uranus': '♅', 'Neptune': '♆'
}

class ConstellationDrawerApp:
    def __init__(self, root, initial_file=None):
        self.root = root
        self.root.title("Constellation Drawer")
        
        self.is_dirty = False
        self.root.protocol("WM_DELETE_WINDOW", self.on_close_request)
        
        self.lines = []           
        self.current_obj = None  
        self.visible_stars = None 
        
        self.custom_points = []
        self.custom_projected = [] 
        self.planet_projected = {}
        
        self.setup_ui()
        self.load_astronomy_data()
        
        if initial_file: self.load_project(initial_file)
        else: self.update_map()

    def set_dirty(self, event=None):
        self.is_dirty = True

    def on_close_request(self):
        if self.is_dirty:
            response = messagebox.askyesnocancel("Unsaved Changes", "You have unsaved changes to your star map.\nDo you want to save your project before closing?")
            if response is True:
                if self.save_project(): self.root.destroy()
            elif response is False: self.root.destroy()
        else:
            self.root.destroy()

    def setup_ui(self):
        sidebar_container = ttk.Frame(self.root)
        sidebar_container.pack(side=tk.LEFT, fill=tk.Y)

        self.sidebar_canvas = tk.Canvas(sidebar_container, width=280, highlightthickness=0)
        scrollbar = ttk.Scrollbar(sidebar_container, orient="vertical", command=self.sidebar_canvas.yview)
        self.sidebar_canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.sidebar_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        control_frame = ttk.Frame(self.sidebar_canvas, padding="10")
        self.sidebar_window = self.sidebar_canvas.create_window((0, 0), window=control_frame, anchor="nw")

        def configure_scrollregion(event): self.sidebar_canvas.configure(scrollregion=self.sidebar_canvas.bbox("all"))
        control_frame.bind("<Configure>", configure_scrollregion)
        
        def configure_canvas_window(event): self.sidebar_canvas.itemconfig(self.sidebar_window, width=event.width)
        self.sidebar_canvas.bind("<Configure>", configure_canvas_window)

        # --- Sidebar Content ---
        ttk.Label(control_frame, text="Observer Location", font=('Arial', 10, 'bold')).pack(pady=(0, 5))
        ttk.Label(control_frame, text="Latitude (-90 to 90):").pack()
        self.lat_entry = ttk.Entry(control_frame); self.lat_entry.insert(0, "40.7128"); self.lat_entry.pack(pady=2)
        ttk.Label(control_frame, text="Longitude (-180 to 180):").pack()
        self.lon_entry = ttk.Entry(control_frame); self.lon_entry.insert(0, "-74.0060"); self.lon_entry.pack(pady=2)
        ttk.Button(control_frame, text="Use My Location", command=self.use_my_location).pack(pady=(5, 2))

        ttk.Label(control_frame, text="Date and Time (UTC)", font=('Arial', 10, 'bold')).pack(pady=(15, 5))
        date_frame = ttk.Frame(control_frame); date_frame.pack(fill='x')
        self.year_entry = ttk.Entry(date_frame, width=6); self.year_entry.insert(0, "2026"); self.year_entry.pack(side=tk.LEFT, padx=1)
        self.month_entry = ttk.Entry(date_frame, width=4); self.month_entry.insert(0, "6"); self.month_entry.pack(side=tk.LEFT, padx=1)
        self.day_entry = ttk.Entry(date_frame, width=4); self.day_entry.insert(0, "10"); self.day_entry.pack(side=tk.LEFT, padx=1)
        self.hour_entry = ttk.Entry(date_frame, width=4); self.hour_entry.insert(0, "22"); self.hour_entry.pack(side=tk.LEFT, padx=1)
        ttk.Button(control_frame, text="Reset to Now (UTC)", command=self.reset_to_now).pack(pady=(5, 2))
        ttk.Button(control_frame, text="Update Sky Map", command=self.update_map).pack(pady=10)

        ttk.Separator(control_frame, orient='horizontal').pack(fill='x', pady=5)
        
        # --- Advanced Features Toggle ---
        self.adv_shown = False
        self.adv_btn = ttk.Button(control_frame, text="Show Advanced Features ▼", command=self.toggle_advanced)
        self.adv_btn.pack(pady=5, fill='x')
        
        self.adv_frame = ttk.Frame(control_frame)
        
        ttk.Label(self.adv_frame, text="Star Calibration", font=('Arial', 9, 'bold')).pack(pady=(5, 2))
        ttk.Label(self.adv_frame, text="Limiting Mag:").pack()
        self.mag_entry = ttk.Entry(self.adv_frame); self.mag_entry.insert(0, "6.0"); self.mag_entry.pack(pady=1)
        ttk.Label(self.adv_frame, text="Ref Mag & Size:").pack()
        self.ref_mag_entry = ttk.Entry(self.adv_frame); self.ref_mag_entry.insert(0, "0.0"); self.ref_mag_entry.pack(pady=1)
        self.ref_size_entry = ttk.Entry(self.adv_frame); self.ref_size_entry.insert(0, "60.0"); self.ref_size_entry.pack(pady=1)

        # --- v1.2.0 Solar System UI ---
        ttk.Label(self.adv_frame, text="Solar System & Moon", font=('Arial', 9, 'bold')).pack(pady=(15, 2))
        self.ss_enabled_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.adv_frame, text="Show Solar System Objects", variable=self.ss_enabled_var, command=self.update_map).pack(anchor='w', pady=1)
        
        self.ss_bodies_frame = ttk.Frame(self.adv_frame)
        self.ss_bodies_frame.pack(fill='x', padx=5, pady=2)
        self.ss_bodies_vars = {}
        bodies_list = ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune']
        for i, body in enumerate(bodies_list):
            var = tk.BooleanVar(value=True)
            self.ss_bodies_vars[body] = var
            chk = ttk.Checkbutton(self.ss_bodies_frame, text=body, variable=var, command=self.update_map)
            chk.grid(row=i//3, column=i%3, sticky='w')
            
        self.ss_style_var = tk.StringVar(value="Dots (●)")
        ttk.Combobox(self.adv_frame, textvariable=self.ss_style_var, values=["Dots (●)", "Icons (♃)"], state="readonly").pack(pady=2, fill='x')
        
        ss_size_frame = ttk.Frame(self.adv_frame)
        ss_size_frame.pack(fill='x', pady=1)
        self.ss_size_mode_var = tk.StringVar(value="Relative Scale")
        ttk.Combobox(ss_size_frame, textvariable=self.ss_size_mode_var, values=["Relative Scale", "Custom Size"], state="readonly", width=12).pack(side=tk.LEFT, padx=(0,2))
        self.ss_size_entry = ttk.Entry(ss_size_frame, width=5)
        self.ss_size_entry.insert(0, "150")
        self.ss_size_entry.pack(side=tk.LEFT)

        # --- Aesthetics & Line Styles ---
        ttk.Label(self.adv_frame, text="Aesthetics (Hex Colors)", font=('Arial', 9, 'bold')).pack(pady=(15, 2))
        self.bg_color_entry = ttk.Entry(self.adv_frame); self.bg_color_entry.insert(0, "#000000"); self.bg_color_entry.pack(pady=1)
        self.star_color_entry = ttk.Entry(self.adv_frame); self.star_color_entry.insert(0, "#FFFFFF"); self.star_color_entry.pack(pady=1)
        self.line_color_entry = ttk.Entry(self.adv_frame); self.line_color_entry.insert(0, "#00FFFF"); self.line_color_entry.pack(pady=1)
        
        ttk.Label(self.adv_frame, text="Line Style:").pack()
        self.line_thick_entry = ttk.Entry(self.adv_frame); self.line_thick_entry.insert(0, "1.5"); self.line_thick_entry.pack(pady=1)
        self.line_style_var = tk.StringVar(value="Solid (—)")
        ttk.Combobox(self.adv_frame, textvariable=self.line_style_var, values=["Solid (—)", "Dashed (--)", "Dotted (ᐧᐧᐧ)"], state="readonly").pack(pady=1)

        # --- Custom Point Adder ---
        ttk.Label(self.adv_frame, text="Custom Point Adder (RA/Dec)", font=('Arial', 9, 'bold')).pack(pady=(15, 2))
        self.cp_name = ttk.Entry(self.adv_frame); self.cp_name.insert(0, "Object Name"); self.cp_name.pack(pady=1)
        self.cp_ra = ttk.Entry(self.adv_frame); self.cp_ra.insert(0, "RA (e.g. 12h 30m)"); self.cp_ra.pack(pady=1)
        self.cp_dec = ttk.Entry(self.adv_frame); self.cp_dec.insert(0, "Dec (e.g. +45d 30m)"); self.cp_dec.pack(pady=1)
        
        self.cp_marker = tk.StringVar(value="Dot (●)")
        ttk.Combobox(self.adv_frame, textvariable=self.cp_marker, values=["Dot (●)", "Triangle (▲)", "Square (■)", "Custom SVG (local)"], state="readonly").pack(pady=1)
        
        size_color_frame = ttk.Frame(self.adv_frame)
        size_color_frame.pack(fill='x', pady=1)
        ttk.Label(size_color_frame, text="Size:").pack(side=tk.LEFT, padx=(0,2))
        self.cp_size = ttk.Entry(size_color_frame, width=5); self.cp_size.insert(0, "150"); self.cp_size.pack(side=tk.LEFT, padx=(0,5))
        ttk.Label(size_color_frame, text="Color:").pack(side=tk.LEFT, padx=(0,2))
        self.cp_color = ttk.Entry(size_color_frame, width=10); self.cp_color.insert(0, "#FFFF00"); self.cp_color.pack(side=tk.LEFT)
        
        ttk.Button(self.adv_frame, text="+ Add Object", command=self.add_custom_point).pack(pady=3)
        self.cp_listbox = tk.Listbox(self.adv_frame, height=4); self.cp_listbox.pack(fill='x', pady=2)
        ttk.Button(self.adv_frame, text="Delete Selected", command=self.delete_custom_point).pack(pady=(0, 5))

        # --- Base Controls Continued ---
        ttk.Separator(control_frame, orient='horizontal').pack(fill='x', pady=10)
        ttk.Label(control_frame, text="Drawing Controls", font=('Arial', 10, 'bold')).pack(pady=(0, 5))
        ttk.Button(control_frame, text="Undo Last Line", command=self.undo_line).pack(pady=2)
        ttk.Button(control_frame, text="Clear All Lines", command=self.clear_lines).pack(pady=2)
        
        ttk.Separator(control_frame, orient='horizontal').pack(fill='x', pady=10)
        ttk.Label(control_frame, text="Project & Export", font=('Arial', 10, 'bold')).pack(pady=(0, 5))
        ttk.Button(control_frame, text="Save Project (.strmp)", command=self.save_project).pack(pady=2)
        ttk.Button(control_frame, text="Load Project (.strmp)", command=self.load_project_dialog).pack(pady=2)
        ttk.Button(control_frame, text="Export as .SVG", command=self.save_svg).pack(pady=10)

        map_frame = ttk.Frame(self.root)
        map_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.fig = plt.Figure(figsize=(8, 8), dpi=100); self.fig.patch.set_facecolor('#000000')
        self.ax = self.fig.add_subplot(111); self.ax.set_facecolor('#000000') 
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=map_frame)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.canvas.mpl_connect('button_press_event', self.on_click)

        self.toolbar = NavigationToolbar2Tk(self.canvas, map_frame)
        self.toolbar.update()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def toggle_advanced(self):
        if self.adv_shown:
            self.adv_frame.pack_forget()
            self.adv_btn.config(text="Show Advanced Features ▼")
            self.adv_shown = False
        else:
            children = self.adv_btn.master.pack_slaves()
            btn_index = children.index(self.adv_btn)
            self.adv_frame.pack(after=children[btn_index], fill='x', pady=5)
            self.adv_btn.config(text="Hide Advanced Features ▲")
            self.adv_shown = True

    def parse_ra(self, val):
        val = str(val).strip().lower()
        if 'h' in val or ':' in val:
            val = val.replace('h', ':').replace('m', ':').replace('s', '').replace(' ', '')
            parts = [p for p in val.split(':') if p]
            h = float(parts[0]) if len(parts) > 0 else 0
            m = float(parts[1]) if len(parts) > 1 else 0
            s = float(parts[2]) if len(parts) > 2 else 0
            return h + (m / 60.0) + (s / 3600.0)
        return float(val) / 15.0 

    def parse_dec(self, val):
        val = str(val).strip().lower()
        sign = -1 if '-' in val else 1
        val = val.replace('-', '').replace('+', '')
        if any(char in val for char in ['d', '°', "'", '"', 'm', ':', 's']):
            val = val.replace('d', ':').replace('°', ':').replace("'", ':').replace('m', ':').replace('"', '').replace('s', '').replace(' ', '')
            parts = [p for p in val.split(':') if p]
            d = float(parts[0]) if len(parts) > 0 else 0
            m = float(parts[1]) if len(parts) > 1 else 0
            s = float(parts[2]) if len(parts) > 2 else 0
            return sign * (d + (m / 60.0) + (s / 3600.0))
        return sign * float(val) 

    def parse_svg_to_mpl_path(self, path_string):
        try:
            path_data, codes = [], []
            commands = re.findall(r'([a-zA-Z])([^a-zA-Z]*)', path_string)
            current_pos = [0.0, 0.0]
            
            for cmd, args_str in commands:
                cmd_char, is_rel, cmd_upper = cmd.strip(), cmd.strip().islower(), cmd.strip().upper()
                args = [float(a) for a in re.findall(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', args_str)]
                
                if cmd_upper == 'M':
                    for i in range(0, len(args), 2):
                        if is_rel and path_data: current_pos[0] += args[i]; current_pos[1] += args[i+1]
                        else: current_pos = [args[i], args[i+1]]
                        path_data.append(tuple(current_pos)); codes.append(Path.MOVETO if i == 0 else Path.LINETO)
                elif cmd_upper == 'L':
                    for i in range(0, len(args), 2):
                        if is_rel: current_pos[0] += args[i]; current_pos[1] += args[i+1]
                        else: current_pos = [args[i], args[i+1]]
                        path_data.append(tuple(current_pos)); codes.append(Path.LINETO)
                elif cmd_upper == 'H':
                    for i in range(len(args)):
                        if is_rel: current_pos[0] += args[i]
                        else: current_pos[0] = args[i]
                        path_data.append(tuple(current_pos)); codes.append(Path.LINETO)
                elif cmd_upper == 'V':
                    for i in range(len(args)):
                        if is_rel: current_pos[1] += args[i]
                        else: current_pos[1] = args[i]
                        path_data.append(tuple(current_pos)); codes.append(Path.LINETO)
                elif cmd_upper in ('C', 'S'):
                    step = 4 if cmd_upper == 'S' else 6
                    for i in range(0, len(args), step):
                        if cmd_upper == 'S':
                            if is_rel:
                                path_data.extend([(current_pos[0], current_pos[1]), (current_pos[0]+args[i], current_pos[1]+args[i+1])])
                                current_pos = [current_pos[0]+args[i+2], current_pos[1]+args[i+3]]
                            else:
                                path_data.extend([(current_pos[0], current_pos[1]), (args[i], args[i+1])])
                                current_pos = [args[i+2], args[i+3]]
                        else:
                            if is_rel:
                                path_data.extend([(current_pos[0]+args[i], current_pos[1]+args[i+1]), (current_pos[0]+args[i+2], current_pos[1]+args[i+3])])
                                current_pos = [current_pos[0]+args[i+4], current_pos[1]+args[i+5]]
                            else:
                                path_data.extend([(args[i], args[i+1]), (args[i+2], args[i+3])])
                                current_pos = [args[i+4], args[i+5]]
                        path_data.append(tuple(current_pos)); codes.extend([Path.CURVE4, Path.CURVE4, Path.CURVE4])
                elif cmd_upper == 'Z':
                    path_data.append(path_data[0] if path_data else tuple(current_pos)); codes.append(Path.CLOSEPOLY)
            
            if len(path_data) < 2: return 'o'
            path_array = np.array(path_data)
            min_vals, max_vals = path_array.min(axis=0), path_array.max(axis=0)
            center = (max_vals + min_vals) / 2
            scale = max(max_vals - min_vals) / 2 or 1
            path_array = (path_array - center) / scale
            path_array[:, 1] = -path_array[:, 1]
            return Path(path_array, codes)
        except Exception: return 'o' 

    def add_custom_point(self):
        try:
            name, ra, dec = self.cp_name.get(), self.parse_ra(self.cp_ra.get()), self.parse_dec(self.cp_dec.get())
            color = self.cp_color.get()
            try: cp_size_val = float(self.cp_size.get())
            except ValueError: cp_size_val = 150.0
            
            marker_selection = self.cp_marker.get()
            svg_path_str = None
            
            if marker_selection == 'Custom SVG (local)':
                filepath = filedialog.askopenfilename(filetypes=[("SVG Vector", "*.svg")])
                if not filepath: return
                with open(filepath, 'r', encoding='utf-8') as f: content = f.read()
                
                match = re.search(r'<path[^>]*d=["\']([^"\']+)["\']', content, re.IGNORECASE | re.DOTALL)
                if match:
                    svg_path_str = match.group(1)
                    marker_type, marker_str = 'custom_svg', None
                else:
                    messagebox.showwarning("SVG Error", "Could not find a valid <path> in the SVG file. Using Dot instead.")
                    marker_type, marker_str = 'preset', 'o'
            else:
                marker_map = {'Dot (●)': 'o', 'Triangle (▲)': '^', 'Square (■)': 's'}
                marker_type, marker_str = 'preset', marker_map.get(marker_selection, 'o')
            
            self.custom_points.append({
                'name': name, 'ra_hours': ra, 'dec_degrees': dec, 
                'marker': marker_str, 'marker_type': marker_type,
                'svg_path': svg_path_str, 'color': color, 'size': cp_size_val
            })
            self.refresh_cp_listbox(); self.set_dirty(); self.update_map()
        except Exception as e: messagebox.showerror("Parsing Error", f"Could not parse Coordinates.\nEnsure they are numbers or h/m/s d/m/s format.\n{e}")

    def delete_custom_point(self):
        selected = self.cp_listbox.curselection()
        if selected:
            del self.custom_points[selected[0]]; self.refresh_cp_listbox(); self.set_dirty(); self.update_map()

    def refresh_cp_listbox(self):
        self.cp_listbox.delete(0, tk.END)
        for cp in self.custom_points:
            mt = "SVG" if cp.get('marker_type') == 'custom_svg' else cp.get('marker', 'o')
            self.cp_listbox.insert(tk.END, f"{cp['name']} ({mt})")

    def use_my_location(self):
        try:
            with urllib.request.urlopen("http://ip-api.com/json/") as response:
                data = json.loads(response.read().decode())
                if data.get("status") == "success":
                    self.lat_entry.delete(0, tk.END); self.lat_entry.insert(0, str(data.get("lat")))
                    self.lon_entry.delete(0, tk.END); self.lon_entry.insert(0, str(data.get("lon")))
                    self.set_dirty(); self.update_map()
        except Exception as e: messagebox.showerror("Error", f"Failed to fetch location.\nDetails: {e}")

    def reset_to_now(self):
        now = datetime.now(timezone.utc)
        self.year_entry.delete(0, tk.END); self.year_entry.insert(0, str(now.year))
        self.month_entry.delete(0, tk.END); self.month_entry.insert(0, str(now.month))
        self.day_entry.delete(0, tk.END); self.day_entry.insert(0, str(now.day))
        self.hour_entry.delete(0, tk.END); self.hour_entry.insert(0, str(now.hour))
        self.set_dirty(); self.update_map()

    def load_astronomy_data(self):
        print("Loading planetary and star data...")
        self.ts = load.timescale()
        self.eph = load('de421.bsp')
        self.earth = self.eph['earth']
        with load.open(hipparcos.URL) as f: self.full_stars_df = hipparcos.load_dataframe(f)

    def update_map(self):
        self.set_dirty()
        try:
            lat, lon = float(self.lat_entry.get()), float(self.lon_entry.get())
            year, month, day, hour = int(self.year_entry.get()), int(self.month_entry.get()), int(self.day_entry.get()), int(self.hour_entry.get())
            mag_limit, ref_mag, ref_size = float(self.mag_entry.get()), float(self.ref_mag_entry.get()), float(self.ref_size_entry.get())
            
            self.stars_df = self.full_stars_df[self.full_stars_df['magnitude'] <= mag_limit]
            self.star_objects = Star.from_dataframe(self.stars_df)
            t, observer = self.ts.utc(year, month, day, hour), self.earth + wgs84.latlon(lat, lon)
            
            # --- 1. Process Stars ---
            apparent = observer.at(t).observe(self.star_objects).apparent()
            alt, az, distance = apparent.altaz()
            visible_mask = alt.degrees > 0
            r = 90 - alt.degrees[visible_mask] 
            az_rad = az.radians[visible_mask]
            
            self.x_coords, self.y_coords = -r * np.sin(az_rad), r * np.cos(az_rad)
            self.visible_stars = np.column_stack((self.x_coords, self.y_coords))
            self.visible_star_ids = self.stars_df.index[visible_mask]
            
            mags = self.stars_df['magnitude'].values[visible_mask]
            denom = max((mag_limit + 0.5 - ref_mag) ** 2, 0.001)
            sizes = np.clip((ref_size / denom) * (mag_limit + 0.5 - mags) ** 2, 0.01, None) 
            
            # --- 2. Process Custom Points ---
            self.custom_projected = []
            for cp in self.custom_points:
                cp_star = Star(ra_hours=cp['ra_hours'], dec_degrees=cp['dec_degrees'])
                cp_alt, cp_az, _ = observer.at(t).observe(cp_star).apparent().altaz()
                if cp_alt.degrees > 0:
                    cp_r = 90 - cp_alt.degrees
                    self.custom_projected.append({'x': -cp_r * np.sin(cp_az.radians), 'y': cp_r * np.cos(cp_az.radians), 'data': cp})
            
            # --- 3. Process Solar System (v1.2.0) ---
            self.planet_projected = {}
            if self.ss_enabled_var.get():
                for body_name, ephem_key in PLANET_KEYS.items():
                    if self.ss_bodies_vars[body_name].get():
                        body_obj = self.eph[ephem_key]
                        app = observer.at(t).observe(body_obj).apparent()
                        p_alt, p_az, _ = app.altaz()
                        
                        # Calculate X/Y regardless of horizon so we can find Moon-to-Sun vector tilt
                        pr = 90 - p_alt.degrees
                        px, py = -pr * np.sin(p_az.radians), pr * np.cos(p_az.radians)
                        
                        self.planet_projected[body_name] = {
                            'x': px, 'y': py, 'visible': p_alt.degrees > 0, 'mag': PLANET_MAGS[body_name]
                        }
                        
                        if body_name == 'Moon':
                            self.moon_fraction = fraction_illuminated(self.eph, 'moon', t)

            self.redraw(sizes)
        except Exception as e: messagebox.showerror("Calculation Error", f"Failed to calculate sky: {e}")

    def draw_exact_moon_phase(self, x, y, size_pts, fraction, sun_x, sun_y):
        """ Projects an exact geometric lunar terminator and parallactic angle! """
        radius = np.sqrt(size_pts) * 0.08
        theta = np.arctan2(sun_y - y, sun_x - x) # Points precisely at the sun
        
        t_vals = np.linspace(-np.pi/2, np.pi/2, 30)
        x_limb, y_limb = radius * np.cos(t_vals), radius * np.sin(t_vals)
        x_term, y_term = radius * np.cos(t_vals) * (1 - 2*fraction), radius * np.sin(t_vals)
        
        x_poly = np.concatenate([x_limb, x_term[::-1]])
        y_poly = np.concatenate([y_limb, y_term[::-1]])
        
        x_rot = x_poly * np.cos(theta) - y_poly * np.sin(theta)
        y_rot = x_poly * np.sin(theta) + y_poly * np.cos(theta)
        
        # Draw Dark Background Base
        x_base = x + radius * np.cos(np.linspace(0, 2*np.pi, 50))
        y_base = y + radius * np.sin(np.linspace(0, 2*np.pi, 50))
        self.ax.add_patch(Polygon(np.column_stack([x_base, y_base]), color='#222222', zorder=3.1))
        
        # Draw Illuminated Phase
        self.ax.add_patch(Polygon(np.column_stack([x + x_rot, y + y_rot]), color='#FFFFFF', zorder=3.2))

    def redraw(self, sizes=None):
        xlim, ylim = self.ax.get_xlim(), self.ax.get_ylim()
        
        try:
            bg_color, star_color, line_color = self.bg_color_entry.get(), self.star_color_entry.get(), self.line_color_entry.get()
            self.fig.patch.set_facecolor(bg_color); self.ax.set_facecolor(bg_color)
        except Exception: bg_color, star_color, line_color = '#000000', '#FFFFFF', '#00FFFF'
            
        try: line_thickness = float(self.line_thick_entry.get())
        except ValueError: line_thickness = 1.5 
        
        style_map = {'Solid (—)': '-', 'Dashed (--)': '--', 'Dotted (ᐧᐧᐧ)': ':', 'Solid (-)': '-', 'Dotted (:)': ':'}
        linestyle = style_map.get(self.line_style_var.get(), '-')

        self.ax.clear(); self.ax.axis('off'); self.ax.set_aspect('equal')
        theta_full = np.linspace(0, 2*np.pi, 100)
        self.ax.plot(90 * np.sin(theta_full), 90 * np.cos(theta_full), color=star_color, linewidth=1)
        self.ax.text(0, 95, 'N', color=star_color, ha='center', va='center', fontsize=12)
        self.ax.text(-95, 0, 'E', color=star_color, ha='center', va='center', fontsize=12)
        self.ax.text(0, -95, 'S', color=star_color, ha='center', va='center', fontsize=12)
        self.ax.text(95, 0, 'W', color=star_color, ha='center', va='center', fontsize=12)

        if hasattr(self, 'x_coords') and sizes is not None:
            self.ax.scatter(self.x_coords, self.y_coords, s=sizes, facecolors=star_color, edgecolors='none', alpha=1.0, zorder=2)
            self.saved_sizes = sizes 

        # --- Draw Solar System ---
        for name, p_data in self.planet_projected.items():
            if not p_data['visible']: continue
            
            if self.ss_size_mode_var.get() == "Custom Size":
                try: p_size = float(self.ss_size_entry.get())
                except ValueError: p_size = 150.0
            else: # Relative apparent scale 
                base = 200.0
                p_size = max(20, base - (p_data['mag'] * 15))
                if name in ('Sun', 'Moon'): p_size = 400.0 
                
            if self.ss_style_var.get() == "Icons (♃)":
                sym = '☽' if name == 'Moon' else PLANET_SYMBOLS[name]
                self.ax.text(p_data['x'], p_data['y'], sym, color=PLANET_COLORS[name], fontsize=np.sqrt(p_size), ha='center', va='center', zorder=4)
            else: # Dots & Phases
                if name == 'Moon':
                    # Fallback to calculate sun angle if sun is currently toggled off in the UI
                    sun_x = self.planet_projected.get('Sun', {}).get('x')
                    sun_y = self.planet_projected.get('Sun', {}).get('y')
                    if sun_x is None:
                        # Silently calculate sun Zenith projection
                        t = self.ts.utc(int(self.year_entry.get()), int(self.month_entry.get()), int(self.day_entry.get()), int(self.hour_entry.get()))
                        obs = self.earth + wgs84.latlon(float(self.lat_entry.get()), float(self.lon_entry.get()))
                        s_app = obs.at(t).observe(self.eph['sun']).apparent()
                        s_alt, s_az, _ = s_app.altaz()
                        s_r = 90 - s_alt.degrees
                        sun_x, sun_y = -s_r * np.sin(s_az.radians), s_r * np.cos(s_az.radians)
                        
                    self.draw_exact_moon_phase(p_data['x'], p_data['y'], p_size, self.moon_fraction, sun_x, sun_y)
                else:
                    self.ax.scatter(p_data['x'], p_data['y'], color=PLANET_COLORS[name], s=p_size, zorder=3.5)

        # --- Draw Custom Points ---
        for p in self.custom_projected:
            marker_shape = p['data'].get('marker', 'o')
            if p['data'].get('marker_type') == 'custom_svg' and p['data'].get('svg_path'):
                marker_shape = self.parse_svg_to_mpl_path(p['data']['svg_path'])
            p_size = p['data'].get('size', 150.0)
            self.ax.scatter(p['x'], p['y'], marker=marker_shape, color=p['data']['color'], s=p_size, zorder=3)
            self.ax.text(p['x'], p['y'] + (np.sqrt(p_size) / 4.0), p['data']['name'], color=p['data']['color'], fontsize=9, ha='center', zorder=4)

        # --- Draw Sticky Lines ---
        for line in self.lines:
            c1, c2 = self.get_obj_coords(line[0]), self.get_obj_coords(line[1])
            if c1 and c2:
                self.ax.plot([c1[0], c2[0]], [c1[1], c2[1]], color=line_color, linewidth=line_thickness, linestyle=linestyle, zorder=1)

        # Active selection ring
        if self.current_obj:
            cx, cy = self.get_obj_coords(self.current_obj)
            if cx is not None:
                self.ax.scatter(cx, cy, facecolors='none', edgecolors='red', s=100, zorder=5)

        if xlim != (0.0, 1.0): self.ax.set_xlim(xlim); self.ax.set_ylim(ylim)
        else: self.ax.set_xlim(-100, 100); self.ax.set_ylim(-100, 100)
        self.canvas.draw()

    # --- v1.2.0 Interaction Engine ---
    def get_obj_coords(self, obj):
        if obj['type'] == 'star': 
            if 'id' in obj:
                ids_list = list(self.visible_star_ids)
                if obj['id'] in ids_list:
                    idx = ids_list.index(obj['id'])
                    return self.visible_stars[idx, 0], self.visible_stars[idx, 1]
                return None # Star went below the horizon
            return obj['x'], obj['y'] # Legacy fallback for older files
        elif obj['type'] == 'custom':
            for cp in self.custom_projected:
                if cp['data']['name'] == obj['id']: return cp['x'], cp['y']
        elif obj['type'] == 'planet':
            if obj['id'] in self.planet_projected and self.planet_projected[obj['id']]['visible']:
                return self.planet_projected[obj['id']]['x'], self.planet_projected[obj['id']]['y']
        return None

    def obj_eq(self, o1, o2):
        if o1['type'] != o2['type']: return False
        if 'id' in o1 and 'id' in o2: return o1['id'] == o2['id']
        return np.isclose(o1['x'], o2['x']) and np.isclose(o1['y'], o2['y'])

    def on_click(self, event):
        if self.toolbar.mode != '': return
        if event.inaxes != self.ax or self.visible_stars is None: return
        
        # Build unified click array
        all_clickables = []
        for i, (sx, sy) in enumerate(self.visible_stars): 
            all_clickables.append({'type': 'star', 'id': int(self.visible_star_ids[i]), 'x': sx, 'y': sy})
        for cp in self.custom_projected: all_clickables.append({'type': 'custom', 'id': cp['data']['name'], 'x': cp['x'], 'y': cp['y']})
        for name, p_data in self.planet_projected.items():
            if p_data['visible']: all_clickables.append({'type': 'planet', 'id': name, 'x': p_data['x'], 'y': p_data['y']})
            
        if not all_clickables: return
        
        click_x, click_y = event.xdata, event.ydata
        target_x, target_y = np.array([c['x'] for c in all_clickables]), np.array([c['y'] for c in all_clickables])
        distances = np.sqrt((target_x - click_x)**2 + (target_y - click_y)**2)
        nearest_idx = np.argmin(distances)
        
        if distances[nearest_idx] < 5:
            selected_obj = all_clickables[nearest_idx]
            if self.current_obj is None: self.current_obj = selected_obj
            else:
                if not self.obj_eq(self.current_obj, selected_obj):
                    line_to_remove = None
                    for line in self.lines:
                        if (self.obj_eq(line[0], self.current_obj) and self.obj_eq(line[1], selected_obj)) or \
                           (self.obj_eq(line[1], self.current_obj) and self.obj_eq(line[0], selected_obj)):
                            line_to_remove = line; break
                            
                    if line_to_remove: self.lines.remove(line_to_remove)
                    else: self.lines.append([self.current_obj, selected_obj])
                    self.set_dirty()
                self.current_obj = None 
            self.redraw(self.saved_sizes)

    def undo_line(self):
        if self.lines: self.lines.pop(); self.set_dirty(); self.redraw(self.saved_sizes)
            
    def clear_lines(self):
        self.lines, self.current_obj = [], None
        self.set_dirty(); self.redraw(self.saved_sizes)

    def save_project(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".strmp", filetypes=[("Star Map Project", "*.strmp")])
        if file_path:
            project_data = {
                "lat": self.lat_entry.get(), "lon": self.lon_entry.get(), "year": self.year_entry.get(), "month": self.month_entry.get(), "day": self.day_entry.get(), "hour": self.hour_entry.get(),
                "mag_limit": self.mag_entry.get(), "ref_mag": self.ref_mag_entry.get(), "ref_size": self.ref_size_entry.get(),
                "bg_color": self.bg_color_entry.get(), "star_color": self.star_color_entry.get(), "line_color": self.line_color_entry.get(), "line_thick": self.line_thick_entry.get(), "line_style": self.line_style_var.get(),
                "solar_system": {
                    "enabled": self.ss_enabled_var.get(), "style": self.ss_style_var.get(), "size_mode": self.ss_size_mode_var.get(), "custom_size": self.ss_size_entry.get(),
                    "active_bodies": [b for b, var in self.ss_bodies_vars.items() if var.get()]
                },
                "lines": self.lines, "custom_points": self.custom_points, "viewport": {"zoom_x": self.ax.get_xlim(), "zoom_y": self.ax.get_ylim()}
            }
            try:
                with open(file_path, 'w') as f: json.dump(project_data, f)
                messagebox.showinfo("Success", f"Project saved to\n{file_path}"); self.is_dirty = False; return True
            except Exception as e: messagebox.showerror("Error", f"Failed to save project: {e}"); return False
        return False

    def load_project_dialog(self):
        if self.is_dirty:
            response = messagebox.askyesnocancel("Unsaved Changes", "Save current project before loading a new one?")
            if response is True:
                if not self.save_project(): return
            elif response is None: return
        self.load_project()

    def load_project(self, file_path=None):
        if not file_path: file_path = filedialog.askopenfilename(filetypes=[("Star Map Project", "*.strmp")])
        if file_path:
            try:
                with open(file_path, 'r') as f: data = json.load(f)
                def set_entry(entry_widget, value): entry_widget.delete(0, tk.END); entry_widget.insert(0, str(value))
                set_entry(self.lat_entry, data.get("lat", "40.7128")); set_entry(self.lon_entry, data.get("lon", "-74.0060")); set_entry(self.year_entry, data.get("year", "2026")); set_entry(self.month_entry, data.get("month", "6")); set_entry(self.day_entry, data.get("day", "10")); set_entry(self.hour_entry, data.get("hour", "22"))
                set_entry(self.mag_entry, data.get("mag_limit", "6.0")); set_entry(self.ref_mag_entry, data.get("ref_mag", "0.0")); set_entry(self.ref_size_entry, data.get("ref_size", "60.0"))
                set_entry(self.bg_color_entry, data.get("bg_color", "#000000")); set_entry(self.star_color_entry, data.get("star_color", "#FFFFFF")); set_entry(self.line_color_entry, data.get("line_color", "#00FFFF")); set_entry(self.line_thick_entry, data.get("line_thick", "1.5"))
                self.line_style_var.set(data.get("line_style", "Solid (—)")); self.custom_points = data.get("custom_points", []); self.refresh_cp_listbox()
                
                # Load Solar System Settings (Backward compatible fallback)
                ss_data = data.get("solar_system", {})
                self.ss_enabled_var.set(ss_data.get("enabled", True))
                self.ss_style_var.set(ss_data.get("style", "Dots (●)"))
                self.ss_size_mode_var.set(ss_data.get("size_mode", "Relative Scale"))
                set_entry(self.ss_size_entry, ss_data.get("custom_size", "150"))
                active_bodies = ss_data.get("active_bodies", list(self.ss_bodies_vars.keys()))
                for b in self.ss_bodies_vars: self.ss_bodies_vars[b].set(b in active_bodies)

                # Upgrade legacy lines (list of lists) into new dictionary objects
                self.lines = []
                for l in data.get("lines", []):
                    if isinstance(l[0], list): # Legacy v1.0/v1.1 format
                        self.lines.append([{'type': 'star', 'x': l[0][0], 'y': l[0][1]}, {'type': 'star', 'x': l[1][0], 'y': l[1][1]}])
                    else: # New v1.2 format
                        self.lines.append(l)
                
                self.update_map()
                if "viewport" in data: self.ax.set_xlim(data["viewport"]["zoom_x"]); self.ax.set_ylim(data["viewport"]["zoom_y"]); self.canvas.draw()
                self.is_dirty = False
            except Exception as e: messagebox.showerror("Error", f"Failed to load project: {e}")

    def save_svg(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".svg", filetypes=[("SVG Vector File", "*.svg")])
        if file_path:
            bg_color = self.bg_color_entry.get()
            original_fig_bg, original_ax_bg = self.fig.patch.get_facecolor(), self.ax.get_facecolor()
            self.fig.patch.set_facecolor(bg_color); self.ax.set_facecolor(bg_color)
            self.fig.savefig(file_path, format='svg', facecolor=bg_color, transparent=False)
            self.fig.patch.set_facecolor(original_fig_bg); self.ax.set_facecolor(original_ax_bg)
            messagebox.showinfo("Success", f"Map saved successfully as\n{file_path}")

def mac_open_document(*args):
    if app: app.load_project(args[0])

if __name__ == "__main__":
    if '.app/Contents/Resources' in os.path.abspath(__file__): os.chdir(os.path.dirname(os.path.abspath(__file__)))
    root = tk.Tk(); app = ConstellationDrawerApp(root, None); root.createcommand("::tk::mac::OpenDocument", mac_open_document); root.mainloop()