# Constellation Drawer 🌌🖋️

An interactive, native macOS desktop application designed to generate, customize, and draw custom constellations on beautiful, scientifically accurate star maps. 

Easily input your coordinates and observation time, connect stars to design custom patterns, and export your maps to crisp, scalable `.svg` files perfect for vector editing in Inkscape.

## Features
* **Scientific Precision:** Computes star coordinates based on Hipparcos catalog data and Skyfield orbital mechanics.
* **Interactive Sky Canvas:** Click on stars on the interactive Matplotlib canvas to draw and toggle custom constellation lines.
* **Custom Project Files (`.strmp`):** Save and load your drawing progress across sessions natively.
* **Custom vector exporting (`.svg`):** Bring your designs straight into Inkscape or Illustrator to add glowing mesh nebulae, vector text, and custom frames.
* **Zero Cost & Open Source:** Free to use, modify, and distribute under the MIT License.

## How to Install (No Python Required!)
1. Go to the [Releases]((https://github.com/pashakih/ConstellationDrawer/releases/tag/v1.0.0)) page.
2. Download `ConstellationDrawer.dmg`.
3. Open the `.dmg` file and drag **Constellation Drawer** into your **Applications** folder.
4. *Note:* Because this app is self-signed, the first time you run it, **right-click (or Control-click) the app icon and select "Open"** to bypass macOS Gatekeeper.

## Developer Quickstart
If you want to run or modify the raw code:
1. Clone the repository:
   ```bash
   git clone https://github.com/pashakih/ConstellationDrawer.git
   cd constellation-drawer
