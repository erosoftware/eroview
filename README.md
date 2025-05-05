Erθ View

Erθ View is a smart application that integrates with Brazil’s Rural Environmental Registry System (SICAR), allowing users to easily search for rural property data using geographic coordinates instead of CAR codes.


---

Key Features

Search for rural properties using latitude and longitude

Accepts multiple input formats (raw coordinates, Google Maps URLs)

Visualizes property boundaries, highlighted in yellow

Download property maps quickly and easily



---

Requirements

Python 3.6 or higher

Required libraries listed in requirements.txt

Modern web browser (Chrome recommended)

Internet connection (for accessing SICAR)



---

Installation

1. Clone or download this repository


2. Install the dependencies:

pip install -r requirements.txt


3. (Optional) Configure environment variables:

SICAR_HEADLESS: Run browser in headless mode (no UI)

SICAR_DEV_MODE: Enable development/debug features

SICAR_BROWSER: Choose your browser (chrome or opera)





---

How to Use

Test Coordinates

Try with: -23.276064, -53.266292 (Douradina, Paraná)

Running the App

python eroview_sicar_app.py

Using the Web Interface

1. Open your browser and go to http://localhost:5000


2. In the "SICAR Map Viewer", enter your coordinates


3. Click "Search Property"


4. Wait for processing and explore the map results




---

Troubleshooting

Browser doesn’t load in the iframe

Check your browser’s embedding permissions

Ensure embed_browser=True in the settings


Cursor position is off

Confirm coordinates are in decimal degrees

Ensure the location is within Brazil


State not selected properly

Multiple detection methods are used — check logs for the failure source



---

Project Structure

eroview_sicar_app.py: Main application and GUI

sicar_connector.py: Handles SICAR data interactions

requirements.txt: Dependency list



---

Roadmap

Android support with GPS geolocation

Shapefile management

Spatial calculations (area, perimeter)

SICAR connectivity improvements

Field validation tests



---

Contributing

We’d love your help!

1. Fork this repo


2. Create a new branch (git checkout -b feature/your-feature)


3. Commit your work (git commit -am 'Add awesome feature')


4. Push to your fork (git push origin feature/your-feature)


5. Submit a Pull Request




---

License

Licensed under the Apache License 2.0.

