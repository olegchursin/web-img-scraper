import os
import re
import time
import random
import logging
import requests
from urllib.parse import urljoin, urlparse, parse_qs, unquote
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)


class WebsiteScraper:
    def __init__(self, base_url, output_dir='downloaded_images',
                 min_delay=1, max_delay=3, max_retries=3):
        """
        Initialize the web scraper with rate limiting and retry mechanisms.
        """
        self.base_url = base_url
        self.output_dir = output_dir
        self.visited_urls = set()
        self.domain = urlparse(base_url).netloc
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_retries = max_retries

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Setup more robust headers to mimic a browser request
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': base_url,
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

    def is_valid_url(self, url):
        """
        Check if the URL is valid and belongs to the same domain.
        """
        try:
            parsed = urlparse(url)
            return (parsed.netloc == self.domain or not parsed.netloc) and \
                   (url.startswith('http://') or url.startswith('https://'))
        except Exception as e:
            logging.error(f"Error validating URL {url}: {e}")
            return False

    def extract_actual_image_url(self, image_url):
        """
        Extract the actual image URL from various dynamic serving mechanisms.
        """
        # Parse the URL
        parsed_url = urlparse(image_url)

        # Handle query parameter image sources
        if parsed_url.query:
            query_params = parse_qs(parsed_url.query)

            # Check for common image source parameters
            image_params = ['src', 'source', 'img', 'image', 'url']
            for param in image_params:
                if param in query_params:
                    # Decode and get the first match
                    actual_url = unquote(query_params[param][0])

                    # If it's a relative URL, make it absolute
                    if not actual_url.startswith(('http://', 'https://')):
                        actual_url = urljoin(self.base_url, actual_url)

                    return actual_url

        # If no query parameter works, return the original URL
        return image_url

    def to_dash_case(self, text):
        """
        Convert a string to dash-case (kebab-case).
        Removes non-alphanumeric characters and converts to lowercase.
        """
        if not text:
            return ""

        # Remove non-alphanumeric characters and replace with dash
        text = re.sub(r'[^a-zA-Z0-9]+', '-', text)

        # Remove leading/trailing dashes and convert to lowercase
        return text.strip('-').lower()

    def generate_filename(self, image_url, img_element):
        """
        Generate a filename for the image based on title or URL.
        """
        # Try to get title attribute
        title = img_element.get('title')

        # If title exists, convert to dash-case
        if title:
            dash_title = self.to_dash_case(title)
            if dash_title:
                # Get file extension from the original image URL
                file_ext = os.path.splitext(
                    urlparse(image_url).path)[1] or '.jpg'
                return f"{dash_title}{file_ext}"

        # Fallback to URL-based filename
        return os.path.basename(urlparse(image_url).path).replace('/', '_')

    def download_image(self, image_url, img_element):
        """
        Download an image from a given URL with retry mechanism and URL extraction.
        """
        # First, try to extract the actual image URL
        actual_image_url = self.extract_actual_image_url(image_url)

        for attempt in range(self.max_retries):
            try:
                # Apply rate limiting before each request
                time.sleep(random.uniform(self.min_delay, self.max_delay))

                response = requests.get(
                    actual_image_url,
                    headers=self.headers,
                    timeout=10,
                    verify=False
                )

                # Check content type to ensure it's an image
                content_type = response.headers.get('Content-Type', '').lower()
                if 'image' not in content_type:
                    logging.warning(f"Not an image: {
                                    actual_image_url}. Content-Type: {content_type}")
                    return

                if response.status_code == 200:
                    # Generate a unique filename using title or URL
                    filename = os.path.join(
                        self.output_dir,
                        self.generate_filename(actual_image_url, img_element)
                    )

                    # Prevent overwriting by adding a number if file exists
                    base, ext = os.path.splitext(filename)
                    counter = 1
                    while os.path.exists(filename):
                        filename = f"{base}_{counter}{ext}"
                        counter += 1

                    # Save the image
                    with open(filename, 'wb') as f:
                        f.write(response.content)
                    logging.info(f"Downloaded: {
                                 actual_image_url} (Filename: {filename})")
                    return

                # If status code is not 200, wait and retry
                logging.warning(f"Failed to download {actual_image_url}. Status code: {
                                response.status_code}")
                time.sleep(1)

            except requests.RequestException as e:
                logging.error(f"Error downloading {actual_image_url} (Attempt {
                              attempt + 1}/{self.max_retries}): {e}")

                # Wait longer between retry attempts
                time.sleep(2 ** attempt)

        logging.error(f"Failed to download {actual_image_url} after {
                      self.max_retries} attempts")

    def crawl(self, url=None, depth=3):
        """
        Recursively crawl a website, finding and downloading images.
        """
        # Prevent excessive recursion
        if depth <= 0:
            return

        # Use base URL if no URL is provided
        url = url or self.base_url

        # Prevent revisiting URLs
        if url in self.visited_urls:
            return
        self.visited_urls.add(url)

        try:
            # Apply rate limiting before each request
            time.sleep(random.uniform(self.min_delay, self.max_delay))

            # Fetch the webpage with more robust request
            response = requests.get(
                url,
                headers=self.headers,
                timeout=10,
                verify=False
            )

            if response.status_code != 200:
                logging.error(f"Failed to fetch {url}. Status code: {
                              response.status_code}")
                logging.error(f"Response content: {response.text[:500]}...")
                return

            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Download images on this page
            images = soup.find_all('img')
            for img in images:
                img_url = img.get('src') or img.get('data-src')
                if img_url:
                    # Convert relative URLs to absolute
                    full_img_url = urljoin(url, img_url)
                    if self.is_valid_url(full_img_url):
                        self.download_image(full_img_url, img)

            # Find all links on the page
            links = soup.find_all('a', href=True)
            for link in links:
                full_link = urljoin(url, link['href'])

                # Only crawl links within the same domain
                if self.is_valid_url(full_link):
                    logging.info(f"Crawling: {full_link}")
                    # Recursively crawl with reduced depth
                    self.crawl(full_link, depth - 1)

        except requests.RequestException as e:
            logging.error(f"Error crawling {url}: {e}")
        except Exception as e:
            logging.error(f"Unexpected error crawling {url}: {e}")


def main():
    # Disable SSL warnings if you're ignoring SSL verification
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    base_url = 'https://www.unionsquarewines.com/spirits/?page=1&sortby=sort_item_order&l=100&item_type=spirits'
    scraper = WebsiteScraper(
        base_url,
        min_delay=1,    # Minimum 1 second between requests
        max_delay=3,    # Maximum 3 seconds between requests
        max_retries=3   # Retry failed requests up to 3 times
    )
    scraper.crawl(depth=3)  # Limit crawling to 3 levels deep


if __name__ == '__main__':
    main()
