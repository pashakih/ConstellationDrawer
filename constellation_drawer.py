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
from skyfield.api import Star, load, wgs84
from skyfield.data import hipparcos

class ConstellationDrawerApp:
    def __init__(self, root, initial_file=None):
        self.root = root
        self.root.title("Constellation Drawer")
        
        # State Management (v1.1.0 Dirty State Tracker)
        self.is_dirty = False
        self.root.protocol("WM_DELETE_WINDOW", self.on_close_request)
        
        # Application state variables
        self.lines = []           
        self.current_star = None  
        self.visible_stars = None 
        
        # Custom Points Database
        self.custom_points = []
        self.custom_projected = [] # Stores active 2D coords for click detection
        
        self.setup_ui()
        self.load_astronomy_data()
        
        if initial_file:
            self.load_project(initial_file)
        else:
            self.update_map()

    def set_dirty(self, event=None):
        self.is_dirty = True

    def on_close_request(self):
        if self.is_dirty:
            response = messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved changes to your star map.\nDo you want to save your project before closing?"
            )
            if response is True:  # Yes
                if self.save_project():
                    self.root.destroy()
            elif response is False: # No
                self.root.destroy()
            # If None (Cancel), do nothing, keep app open.
        else:
            self.root.destroy()

    def setup_ui(self):
        # Left Control Panel (Scrollable Container)
        sidebar_container = ttk.Frame(self.root)
        sidebar_container.pack(side=tk.LEFT, fill=tk.Y)

        self.sidebar_canvas = tk.Canvas(sidebar_container, width=260, highlightthickness=0)
        scrollbar = ttk.Scrollbar(sidebar_container, orient="vertical", command=self.sidebar_canvas.yview)
        self.sidebar_canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.sidebar_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        control_frame = ttk.Frame(self.sidebar_canvas, padding="10")
        self.sidebar_window = self.sidebar_canvas.create_window((0, 0), window=control_frame, anchor="nw")

        def configure_scrollregion(event):
            self.sidebar_canvas.configure(scrollregion=self.sidebar_canvas.bbox("all"))
        control_frame.bind("<Configure>", configure_scrollregion)
        
        def configure_canvas_window(event):
            self.sidebar_canvas.itemconfig(self.sidebar_window, width=event.width)
        self.sidebar_canvas.bind("<Configure>", configure_canvas_window)

        # --- Sidebar Content ---
        ttk.Label(control_frame, text="Observer Location", font=('Arial', 10, 'bold')).pack(pady=(0, 5))
        
        ttk.Label(control_frame, text="Latitude (-90 to 90):").pack()
        self.lat_entry = ttk.Entry(control_frame)
        self.lat_entry.insert(0, "40.7128")
        self.lat_entry.pack(pady=2)

        ttk.Label(control_frame, text="Longitude (-180 to 180):").pack()
        self.lon_entry = ttk.Entry(control_frame)
        self.lon_entry.insert(0, "-74.0060")
        self.lon_entry.pack(pady=2)

        ttk.Button(control_frame, text="Use My Location", command=self.use_my_location).pack(pady=(5, 2))

        ttk.Label(control_frame, text="Date and Time (UTC)", font=('Arial', 10, 'bold')).pack(pady=(15, 5))
        
        date_frame = ttk.Frame(control_frame)
        date_frame.pack(fill='x')
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

        ttk.Label(self.adv_frame, text="Aesthetics (Hex Colors)", font=('Arial', 9, 'bold')).pack(pady=(10, 2))
        self.bg_color_entry = ttk.Entry(self.adv_frame); self.bg_color_entry.insert(0, "#000000"); self.bg_color_entry.pack(pady=1)
        self.star_color_entry = ttk.Entry(self.adv_frame); self.star_color_entry.insert(0, "#FFFFFF"); self.star_color_entry.pack(pady=1)
        self.line_color_entry = ttk.Entry(self.adv_frame); self.line_color_entry.insert(0, "#00FFFF"); self.line_color_entry.pack(pady=1)
        
        ttk.Label(self.adv_frame, text="Line Style:").pack()
        self.line_thick_entry = ttk.Entry(self.adv_frame); self.line_thick_entry.insert(0, "1.5"); self.line_thick_entry.pack(pady=1)
        self.line_style_var = tk.StringVar(value="Solid (—)")
        ttk.Combobox(self.adv_frame, textvariable=self.line_style_var, values=["Solid (—)", "Dashed (--)", "Dotted (ᐧᐧᐧ)"], state="readonly").pack(pady=1)

        ttk.Label(self.adv_frame, text="Custom Point Adder (RA/Dec)", font=('Arial', 9, 'bold')).pack(pady=(15, 2))
        self.cp_name = ttk.Entry(self.adv_frame); self.cp_name.insert(0, "Object Name"); self.cp_name.pack(pady=1)
        self.cp_ra = ttk.Entry(self.adv_frame); self.cp_ra.insert(0, "RA (e.g. 12h 30m)"); self.cp_ra.pack(pady=1)
        self.cp_dec = ttk.Entry(self.adv_frame); self.cp_dec.insert(0, "Dec (e.g. +45d 30m)"); self.cp_dec.pack(pady=1)
        
        self.cp_marker = tk.StringVar(value="Dot (●)")
        ttk.Combobox(self.adv_frame, textvariable=self.cp_marker, values=["Dot (●)", "Triangle (▲)", "Square (■)", "Custom SVG (local)"], state="readonly").pack(pady=1)
        
        # New Size and Color Layout
        size_color_frame = ttk.Frame(self.adv_frame)
        size_color_frame.pack(fill='x', pady=1)
        ttk.Label(size_color_frame, text="Size:").pack(side=tk.LEFT, padx=(0,2))
        self.cp_size = ttk.Entry(size_color_frame, width=5); self.cp_size.insert(0, "150"); self.cp_size.pack(side=tk.LEFT, padx=(0,5))
        ttk.Label(size_color_frame, text="Color:").pack(side=tk.LEFT, padx=(0,2))
        self.cp_color = ttk.Entry(size_color_frame, width=10); self.cp_color.insert(0, "#FFFF00"); self.cp_color.pack(side=tk.LEFT)
        
        ttk.Button(self.adv_frame, text="+ Add Object", command=self.add_custom_point).pack(pady=3)
        
        self.cp_listbox = tk.Listbox(self.adv_frame, height=4)
        self.cp_listbox.pack(fill='x', pady=2)
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

        # Right Map Panel (Matplotlib)
        map_frame = ttk.Frame(self.root)
        map_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.fig = plt.Figure(figsize=(8, 8), dpi=100)
        self.fig.patch.set_facecolor('#000000')
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#000000') 
        
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

    # --- Robust RA/Dec Parsing Engine ---
    def parse_ra(self, val):
        val = str(val).strip().lower()
        if 'h' in val or ':' in val:
            # Strip all letters and spaces
            val = val.replace('h', ':').replace('m', ':').replace('s', '').replace(' ', '')
            parts = [p for p in val.split(':') if p] # Filter out empty strings
            h = float(parts[0]) if len(parts) > 0 else 0
            m = float(parts[1]) if len(parts) > 1 else 0
            s = float(parts[2]) if len(parts) > 2 else 0
            return h + (m / 60.0) + (s / 3600.0)
        return float(val) / 15.0 # Assume pure decimal degrees if no markers present

    def parse_dec(self, val):
        val = str(val).strip().lower()
        sign = -1 if '-' in val else 1
        val = val.replace('-', '').replace('+', '')
        
        # Check for any valid astronomical delineator
        if any(char in val for char in ['d', '°', "'", '"', 'm', ':', 's']):
            val = val.replace('d', ':').replace('°', ':').replace("'", ':').replace('m', ':').replace('"', '').replace('s', '').replace(' ', '')
            parts = [p for p in val.split(':') if p] # Filter out empty strings
            d = float(parts[0]) if len(parts) > 0 else 0
            m = float(parts[1]) if len(parts) > 1 else 0
            s = float(parts[2]) if len(parts) > 2 else 0
            return sign * (d + (m / 60.0) + (s / 3600.0))
        return sign * float(val) # Assume pure decimal degrees

    # --- SVG Path Parser (Keeps .strmp Self-Contained) ---
    def parse_svg_to_mpl_path(self, path_string):
        """ Translates raw SVG <path d="..."> into a matplotlib vector object """
        try:
            path_data, codes = [], []
            commands = re.findall(r'([MmLlHhVvCcZz])([^MmLlHhVvCcZz]*)', path_string)
            current_pos = [0.0, 0.0]
            
            for cmd, args_str in commands:
                cmd = cmd.strip()
                args = [float(a) for a in re.findall(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', args_str)]
                
                if cmd in ('M', 'm'):
                    for i in range(0, len(args), 2):
                        if cmd == 'm' and path_data:
                            current_pos[0] += args[i]; current_pos[1] += args[i+1]
                        else:
                            current_pos = [args[i], args[i+1]]
                        path_data.append(tuple(current_pos))
                        codes.append(Path.MOVETO if i == 0 else Path.LINETO)
                elif cmd in ('L', 'l'):
                    for i in range(0, len(args), 2):
                        if cmd == 'l':
                            current_pos[0] += args[i]; current_pos[1] += args[i+1]
                        else:
                            current_pos = [args[i], args[i+1]]
                        path_data.append(tuple(current_pos)); codes.append(Path.LINETO)
                elif cmd in ('C', 'c'):
                    for i in range(0, len(args), 6):
                        if cmd == 'c':
                            path_data.extend([
                                (current_pos[0]+args[i], current_pos[1]+args[i+1]),
                                (current_pos[0]+args[i+2], current_pos[1]+args[i+3])
                            ])
                            current_pos = [current_pos[0]+args[i+4], current_pos[1]+args[i+5]]
                        else:
                            path_data.extend([(args[i], args[i+1]), (args[i+2], args[i+3])])
                            current_pos = [args[i+4], args[i+5]]
                        path_data.append(tuple(current_pos))
                        codes.extend([Path.CURVE4, Path.CURVE4, Path.CURVE4])
                elif cmd in ('Z', 'z'):
                    path_data.append(path_data[0] if path_data else tuple(current_pos))
                    codes.append(Path.CLOSEPOLY)
            
            if not path_data: return 'o'
                
            # Center and Scale the icon to fit properly on the map
            path_array = np.array(path_data)
            min_vals, max_vals = path_array.min(axis=0), path_array.max(axis=0)
            center = (max_vals + min_vals) / 2
            scale = max(max_vals - min_vals) / 2 or 1
            
            path_array = (path_array - center) / scale
            path_array[:, 1] = -path_array[:, 1] # Flip Y for Matplotlib
            
            return Path(path_array, codes)
        except Exception:
            return 'o' # Fallback to dot if the SVG format is weird

    def add_custom_point(self):
        try:
            name = self.cp_name.get()
            ra = self.parse_ra(self.cp_ra.get())
            dec = self.parse_dec(self.cp_dec.get())
            color = self.cp_color.get()
            
            try:
                cp_size_val = float(self.cp_size.get())
            except ValueError:
                cp_size_val = 150.0
            
            marker_selection = self.cp_marker.get()
            svg_path_str = None
            
            if marker_selection == 'Custom SVG (local)':
                filepath = filedialog.askopenfilename(filetypes=[("SVG Vector", "*.svg")])
                if not filepath: return
                
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract the vector path using regex to avoid namespace crashes
                match = re.search(r'<path[^>]*d=["\']([^"\']+)["\']', content, re.IGNORECASE)
                if match:
                    svg_path_str = match.group(1)
                    marker_type = 'custom_svg'
                    marker_str = None
                else:
                    messagebox.showwarning("SVG Error", "Could not find a valid <path> in the SVG file. Using Dot instead.")
                    marker_type = 'preset'
                    marker_str = 'o'
            else:
                marker_map = {'Dot (●)': 'o', 'Triangle (▲)': '^', 'Square (■)': 's'}
                marker_type = 'preset'
                marker_str = marker_map.get(marker_selection, 'o')
            
            self.custom_points.append({
                'name': name, 'ra_hours': ra, 'dec_degrees': dec, 
                'marker': marker_str, 'marker_type': marker_type,
                'svg_path': svg_path_str, 'color': color, 'size': cp_size_val
            })
            self.refresh_cp_listbox()
            self.set_dirty()
            self.update_map()
        except Exception as e:
            messagebox.showerror("Parsing Error", f"Could not parse Coordinates.\nEnsure they are numbers or h/m/s d/m/s format.\n{e}")

    def delete_custom_point(self):
        selected = self.cp_listbox.curselection()
        if selected:
            del self.custom_points[selected[0]]
            self.refresh_cp_listbox()
            self.set_dirty()
            self.update_map()

    def refresh_cp_listbox(self):
        self.cp_listbox.delete(0, tk.END)
        for cp in self.custom_points:
            mt = "SVG" if cp.get('marker_type') == 'custom_svg' else cp.get('marker', 'o')
            self.cp_listbox.insert(tk.END, f"{cp['name']} ({mt})")

    # --- Astronomy Logic ---
    def use_my_location(self):
        try:
            with urllib.request.urlopen("http://ip-api.com/json/") as response:
                data = json.loads(response.read().decode())
                if data.get("status") == "success":
                    self.lat_entry.delete(0, tk.END); self.lat_entry.insert(0, str(data.get("lat")))
                    self.lon_entry.delete(0, tk.END); self.lon_entry.insert(0, str(data.get("lon")))
                    self.set_dirty()
                    self.update_map()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch location.\nDetails: {e}")

    def reset_to_now(self):
        now = datetime.now(timezone.utc)
        self.year_entry.delete(0, tk.END); self.year_entry.insert(0, str(now.year))
        self.month_entry.delete(0, tk.END); self.month_entry.insert(0, str(now.month))
        self.day_entry.delete(0, tk.END); self.day_entry.insert(0, str(now.day))
        self.hour_entry.delete(0, tk.END); self.hour_entry.insert(0, str(now.hour))
        self.set_dirty()
        self.update_map()

    def load_astronomy_data(self):
        print("Loading planetary and star data...")
        self.ts = load.timescale()
        self.eph = load('de421.bsp')
        self.earth = self.eph['earth']
        with load.open(hipparcos.URL) as f:
            self.full_stars_df = hipparcos.load_dataframe(f)

    def update_map(self):
        self.set_dirty()
        try:
            lat, lon = float(self.lat_entry.get()), float(self.lon_entry.get())
            year, month, day, hour = int(self.year_entry.get()), int(self.month_entry.get()), int(self.day_entry.get()), int(self.hour_entry.get())
            mag_limit, ref_mag, ref_size = float(self.mag_entry.get()), float(self.ref_mag_entry.get()), float(self.ref_size_entry.get())
            
            self.stars_df = self.full_stars_df[self.full_stars_df['magnitude'] <= mag_limit]
            self.star_objects = Star.from_dataframe(self.stars_df)

            t = self.ts.utc(year, month, day, hour)
            observer = self.earth + wgs84.latlon(lat, lon)
            
            # Process Stars
            apparent = observer.at(t).observe(self.star_objects).apparent()
            alt, az, distance = apparent.altaz()
            visible_mask = alt.degrees > 0
            r = 90 - alt.degrees[visible_mask] 
            az_rad = az.radians[visible_mask]
            
            self.x_coords = -r * np.sin(az_rad)
            self.y_coords = r * np.cos(az_rad)
            self.visible_stars = np.column_stack((self.x_coords, self.y_coords))
            
            mags = self.stars_df['magnitude'].values[visible_mask]
            denom = max((mag_limit + 0.5 - ref_mag) ** 2, 0.001)
            sizes = np.clip((ref_size / denom) * (mag_limit + 0.5 - mags) ** 2, 0.01, None) 
            
            # Process Custom Points
            self.custom_projected = []
            for cp in self.custom_points:
                cp_star = Star(ra_hours=cp['ra_hours'], dec_degrees=cp['dec_degrees'])
                cp_alt, cp_az, _ = observer.at(t).observe(cp_star).apparent().altaz()
                if cp_alt.degrees > 0:
                    cp_r = 90 - cp_alt.degrees
                    cp_x = -cp_r * np.sin(cp_az.radians)
                    cp_y = cp_r * np.cos(cp_az.radians)
                    self.custom_projected.append({'x': cp_x, 'y': cp_y, 'data': cp})
            
            self.redraw(sizes)
            
        except Exception as e:
            messagebox.showerror("Calculation Error", f"Failed to calculate sky: {e}")

    def redraw(self, sizes=None):
        xlim, ylim = self.ax.get_xlim(), self.ax.get_ylim()
        
        try:
            bg_color, star_color, line_color = self.bg_color_entry.get(), self.star_color_entry.get(), self.line_color_entry.get()
            self.fig.patch.set_facecolor(bg_color); self.ax.set_facecolor(bg_color)
        except Exception:
            bg_color, star_color, line_color = '#000000', '#FFFFFF', '#00FFFF'
            
        try: line_thickness = float(self.line_thick_entry.get())
        except ValueError: line_thickness = 1.5 
        
        style_map = {'Solid (—)': '-', 'Dashed (--)': '--', 'Dotted (ᐧᐧᐧ)': ':', 'Solid (-)': '-', 'Dotted (:)': ':'}
        linestyle = style_map.get(self.line_style_var.get(), '-')

        self.ax.clear(); self.ax.axis('off'); self.ax.set_aspect('equal')
        
        # Horizon & Compass
        theta_full = np.linspace(0, 2*np.pi, 100)
        self.ax.plot(90 * np.sin(theta_full), 90 * np.cos(theta_full), color=star_color, linewidth=1)
        self.ax.text(0, 95, 'N', color=star_color, ha='center', va='center', fontsize=12)
        self.ax.text(-95, 0, 'E', color=star_color, ha='center', va='center', fontsize=12)
        self.ax.text(0, -95, 'S', color=star_color, ha='center', va='center', fontsize=12)
        self.ax.text(95, 0, 'W', color=star_color, ha='center', va='center', fontsize=12)

        # Plot Stars
        if hasattr(self, 'x_coords') and sizes is not None:
            self.ax.scatter(self.x_coords, self.y_coords, s=sizes, facecolors=star_color, edgecolors='none', alpha=1.0, zorder=2)
            self.saved_sizes = sizes 

        # Plot Custom Points (with dynamic SVG path evaluation!)
        for p in self.custom_projected:
            marker_shape = p['data'].get('marker', 'o')
            if p['data'].get('marker_type') == 'custom_svg' and p['data'].get('svg_path'):
                marker_shape = self.parse_svg_to_mpl_path(p['data']['svg_path'])
                
            p_size = p['data'].get('size', 150.0)
            self.ax.scatter(p['x'], p['y'], marker=marker_shape, color=p['data']['color'], s=p_size, zorder=3)
            
            # Text shifts dynamically based on the size of the icon so it doesn't overlap!
            text_offset = np.sqrt(p_size) / 4.0
            self.ax.text(p['x'], p['y'] + text_offset, p['data']['name'], color=p['data']['color'], fontsize=9, ha='center', zorder=4)

        # Plot Lines
        for line in self.lines:
            self.ax.plot([line[0][0], line[1][0]], [line[0][1], line[1][1]], color=line_color, linewidth=line_thickness, linestyle=linestyle, zorder=1)

        if self.current_star:
            self.ax.scatter(self.current_star[0], self.current_star[1], facecolors='none', edgecolors='red', s=100, zorder=5)

        # Restore Viewport Zoom
        if xlim != (0.0, 1.0): 
            self.ax.set_xlim(xlim); self.ax.set_ylim(ylim)
        else:
            self.ax.set_xlim(-100, 100); self.ax.set_ylim(-100, 100)

        self.canvas.draw()

    def on_click(self, event):
        if self.toolbar.mode != '': return
        if event.inaxes != self.ax or self.visible_stars is None: return
            
        click_x, click_y = event.xdata, event.ydata
        
        all_x, all_y = list(self.visible_stars[:, 0]), list(self.visible_stars[:, 1])
        for p in self.custom_projected:
            all_x.append(p['x']); all_y.append(p['y'])
            
        target_x, target_y = np.array(all_x), np.array(all_y)
        distances = np.sqrt((target_x - click_x)**2 + (target_y - click_y)**2)
        
        if len(distances) == 0: return
        nearest_idx = np.argmin(distances)
        
        if distances[nearest_idx] < 5:
            selected_star = (float(target_x[nearest_idx]), float(target_y[nearest_idx]))
            
            if self.current_star is None:
                self.current_star = selected_star
            else:
                if self.current_star != selected_star:
                    line_to_remove = None
                    for line in self.lines:
                        if (line[0] == self.current_star and line[1] == selected_star) or (line[1] == self.current_star and line[0] == selected_star):
                            line_to_remove = line; break
                    if line_to_remove: self.lines.remove(line_to_remove)
                    else: self.lines.append((self.current_star, selected_star))
                    self.set_dirty()
                self.current_star = None 
            self.redraw(self.saved_sizes)

    def undo_line(self):
        if self.lines: self.lines.pop(); self.set_dirty(); self.redraw(self.saved_sizes)
            
    def clear_lines(self):
        self.lines, self.current_star = [], None
        self.set_dirty(); self.redraw(self.saved_sizes)

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
                "line_style": self.line_style_var.get(),
                "lines": self.lines, "custom_points": self.custom_points,
                "viewport": {"zoom_x": self.ax.get_xlim(), "zoom_y": self.ax.get_ylim()}
            }
            try:
                with open(file_path, 'w') as f: json.dump(project_data, f)
                messagebox.showinfo("Success", f"Project saved to\n{file_path}")
                self.is_dirty = False
                return True
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save project: {e}")
                return False
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
                set_entry(self.line_color_entry, data.get("line_color", "#00FFFF"))
                set_entry(self.line_thick_entry, data.get("line_thick", "1.5"))
                
                loaded_line_style = data.get("line_style", "Solid (—)")
                if loaded_line_style == "Solid (-)": loaded_line_style = "Solid (—)"
                if loaded_line_style == "Dotted (:)": loaded_line_style = "Dotted (ᐧᐧᐧ)"
                self.line_style_var.set(loaded_line_style)

                self.custom_points = data.get("custom_points", [])
                self.refresh_cp_listbox()
                self.lines = [((l[0][0], l[0][1]), (l[1][0], l[1][1])) for l in data.get("lines", [])]
                
                self.update_map()
                
                if "viewport" in data:
                    self.ax.set_xlim(data["viewport"]["zoom_x"]); self.ax.set_ylim(data["viewport"]["zoom_y"])
                    self.canvas.draw()
                
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
    if '.app/Contents/Resources' in os.path.abspath(__file__):
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        
    root = tk.Tk()
    app = ConstellationDrawerApp(root, None)
    root.createcommand("::tk::mac::OpenDocument", mac_open_document)
    root.mainloop()