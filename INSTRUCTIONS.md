# Constellation Drawer - Official User Guide 🌌

Welcome to Constellation Drawer, the ultimate application for creating scientifically accurate, highly customizable, and fully interactive stellar cartography. Whether you are mapping a historic sky, plotting comets, or designing beautiful vector art for a poster, this guide covers everything you need to know.

# 1. Setting the Scene

*Before you start drawing, you need to tell the app where and when you are looking.*

**Observer Location:** Enter the Latitude and Longitude of your viewing spot. You can use decimal degrees (e.g., 40.7128 for NYC). Alternatively, click Use My Location to instantly ping your IP address and fill in your current coordinates.

**Date and Time (UTC):** The night sky changes every second. Enter the Year, Month, Day, and Hour in UTC (Universal Time Coordinated) to generate the exact historical or future sky you want.

**Update Sky Map:** Whenever you change location or time, click this button to calculate and render the new stars.

# 2. Display Settings & Aesthetics

*Open the 'Show Advanced Features ▼' drawer to fully customize the look of your map.*

**Limiting Magnitude:** Controls how many stars are visible. A lower number (like 4.0) shows only the brightest stars, great for minimal city-sky maps. A higher number (like 6.5) shows thousands of faint stars.

**Reference Mag & Size:** These controls allow you to fine-tune the scaling of the star dots.

**Hex Colors:** Customize the map's background, star dots, and constellation lines using standard hex color codes *(e.g., #000000 for black, #FFFFFF for white).*

**Line Style:** Choose how your constellations look: Solid (—), Dashed (--), or Dotted (ᐧᐧᐧ), along with line thickness.

# 3. The Solar System & Moon Phases

*Want to plot the wandering planets?*

Check Show Solar System Objects in the Advanced drawer.

Select which bodies you want to see (Sun, Moon, Mars, Jupiter, etc.).

Choose your style:

**Dots (●):** Color-coded spheres. The Moon will be drawn with its exact geometric phase and tilt!

**Icons (♃):** Beautiful, scalable astronomical symbols.

Scale them automatically by magnitude ("Relative Scale") or set your own size ("Custom Size").

# 4. Custom Points (Comets, Galaxies, & Radiants)

*If an object isn't in the standard star catalog, you can add it manually using the Custom Point Adder.*

Enter a Name (e.g., "Comet NEOWISE").

Enter its Right Ascension (RA) (e.g., 12h 30m or decimal 185.5) and Declination (Dec) (e.g., +45d 30m or 45.5).

Select a marker style:

**Preset Shapes:** Use a Dot, Triangle (perfect for meteor radiants), or Square.

**Custom SVG:** Select a local .svg file! The app will magically extract the vector path and plot your custom shape perfectly onto the map. It must a plain .svg using only one path.

Set the color and size, then click + Add Object.

# 5. Drawing Your Constellations

*This is where the magic happens.*

**Connecting the Dots:** Simply click any star, planet, or custom point on the map. It will highlight with a red ring. Click a second object, and a line will instantly connect them!

**Sticky Lines:** If you draw a line to a Planet, that line becomes "tethered" to it. If you change the Date/Time and update the map, the line will dynamically stretch to follow the planet across the sky!

**Undo/Clear:** Use the buttons in the left panel to undo your last line or wipe the canvas clean.

# 6. Saving, Loading, & Exporting

**Save Project (.strmp):** Saves your exact location, time, lines, custom points, colors, and even your current zoom level into a tiny file. *Note: Custom SVG icons are saved directly inside this file, so you can share it with anyone!* .strmp files are only suppeorted in our app. Use **'Load Project (.strmp)'** to continue on your project!

**Export as .SVG:** Once your map is beautiful, export it as an SVG. This generates a flawless, infinitely scalable vector file. You can open this file in Inkscape or Adobe Illustrator to add text, frames, glowing nebulae, or print it as a massive, high-quality poster.

[Download now for MacOS!](https://github.com/pashakih/ConstellationDrawer/releases/tag/v1.2.0)
