<h1 align="center">
  <img src="public/logo.svg" alt="WeatherOS Logo" width="96" />
  <br />
  WeatherOS
</h1>

<p align="center">
  A modern desktop weather application that provides real-time weather information with a clean and intuitive interface.
</p>

---

## What is WeatherOS?

**WeatherOS is a simple and modern weather application designed to provide fast access to real-time weather information:**

- Search weather information by city name
- View current temperature and weather conditions
- Display wind speed and additional weather details
- Convert weather data into clear user-friendly information
- Provide a simple and responsive desktop experience

**`A lightweight weather application focused on simplicity, speed, and usability.`**

---

## How It Works

Getting started with WeatherOS is fast:

1. **Enter a Location** — Search for any city you want to check.
2. **Find Coordinates** — WeatherOS converts the city name into geographic coordinates.
3. **Fetch Weather Data** — The application retrieves current weather information.
4. **Process Information** — Weather data is formatted into readable information.
5. **Display Results** — Current conditions are shown through the application interface.

> [!TIP]
> Make sure you have an active internet connection to retrieve the latest weather information.

---

## Installation

### macOS

```bash
git clone https://github.com/nikomarinovic/WeatherOS.git

cd WeatherOS

python3 -m pip install --user --break-system-packages -r requirements.txt

python3 main.py
```

> [!NOTE]
> On modern macOS with Homebrew Python, a plain `pip install` may fail with an
> `externally-managed-environment` error. The `--break-system-packages` flag
> above installs the dependencies for your user account only and avoids this.
> If you have multiple Python versions installed, run `which python3` first
> to confirm `python3` points to the version you want to use.

### Linux

```bash
git clone https://github.com/nikomarinovic/WeatherOS.git

cd WeatherOS

python3 -m pip install --user --break-system-packages -r requirements.txt

python3 main.py
```

### Windows

```bash
git clone https://github.com/nikomarinovic/WeatherOS.git

cd WeatherOS

py -m pip install --user -r requirements.txt

py main.py
```

---

## Features

- **Real-Time Weather Data** — Retrieve current weather information from online weather services.
- **City-Based Search** — Search for weather conditions by entering any city name.
- **Current Conditions Overview** — View temperature, wind speed, and weather status in one place.
- **Clean User Interface** — Enjoy a simple and intuitive design focused on usability.
- **Lightweight Desktop Experience** — A fast and efficient application designed for everyday weather checks.

---

## Screenshots

<p align="center">
  <img src="public/screenshot-1.png" alt="WeatherOS Screenshot 1" width="700" />
</p>

---

## Data & Privacy

WeatherOS only uses location information provided by the user to retrieve weather data. The application does not store personal information or collect user data.

> [!NOTE]
> Weather information is provided through external weather services and may depend on API availability.

> [!WARNING]
> WeatherOS requires an internet connection to retrieve current weather information.

---

<h3 align="center">
WeatherOS does not accept feature implementations via pull requests. Feature requests and bug reports are welcome through GitHub issues.
</h3>

---

<p align="center">
  © 2026 Niko Marinović. All rights reserved.
</p>