# Erθ View

Application for integrating Eroview with the Rural Environmental Registry System (SICAR), allowing rural properties to be searched using geographic coordinates instead of the CAR code.

## Features

- Search rural properties by geographic coordinates (latitude/longitude)
- Support for different input formats (direct coordinates, Google Maps URLs)
- View property boundaries highlighted in yellow
- Download property maps

## Requirements

- Python 3.6 or higher
- Python libraries listed in requirements.txt
- Compatible web browser (Chrome recommended)
- Internet connection for accessing the SICAR portal

## Installation

1. Clone or download this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Configure environment variables (optional):
   - `SICAR_HEADLESS`: Defines whether the browser should run in headless mode (without graphical interface)
   - `SICAR_DEV_MODE`: Enables development features
   - `SICAR_BROWSER`: Defines which browser to use (chrome or opera)

## Usage

### Test Coordinates
For testing, we recommend using the coordinates: -23.276064, -53.266292 (located in Douradina, Paraná)

### Starting the Application
```
python eroview_sicar_app.py
```

### Usando a interface web
1. Access the application through the browser at the indicated address (usually http://localhost:5000)
2. In the "SICAR Map Viewer" interface, enter the geographic coordinates
3. Click "Search Property"
4. Wait for processing and view the results

## Troubleshooting Common Issues

### The browser does not open inside the iframe
- Check if the browser’s security settings allow embedding)
- Ensure that the embed_browser parameter is set to True

### The cursor appears in the wrong position
- Ensure that the coordinate format is correct (decimal degrees)
- Check if the coordinates are within Brazilian territory

### The state is not selected correctly
- The system uses multiple methods to select the state. Check the logs to understand which method failed

## Project Structure

- `eroview_sicar_app.py` - Main application with graphical interface
- `sicar_connector.py` - Module for communication with SICAR
- `requirements.txt` - List of project dependencies

## Next Steps

- Implement geolocation on Android
- Manage shapefiles
- Geospatial processing (area, perimeter calculations)
- Improvements in SICAR connection
- Field testing

## Contribution

Contributions are welcome! Please follow these steps:
1. Fork the repository
2. Create a branch for your feature (git checkout -b feature/new-feature)
3. Commit your changes (git commit -am 'Adds new feature')
4. Push to the repository (git push origin feature/new-feature)
5. Create a Pull Request

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.
