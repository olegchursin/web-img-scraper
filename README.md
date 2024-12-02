# Website Image Scraper

## Overview

A Python script to crawl a website and download images from all pages.

## Prerequisites

- Python 3.9+
- Poetry

## Installation

1. Clone the repository
2. Install dependencies:

   ```bash
   poetry install
   ```

## Usage

1. Set the base URL in `src/website_image_scraper/scraper.py`
2. Run the script:

  ```bash
  poetry run python src/scraper.py
  ```

## Development

- Run tests: `poetry run pytest`
- Lint code: `poetry run flake8`
- Format code: `poetry run black .`