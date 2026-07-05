# Amazon Web Scraper & Analyzer

A resilient, testable web scraping pipeline for Amazon search results and
product pages, built with the **`scrapling`** framework. It searches for a
keyword, visits each result's product page for full detail, stores
everything in SQLite (with CSV export), and generates an analysis
report with charts.

🔗 **Live Demo:** [View Live Streamlit App (Placeholder - Replace with your deployment link)](https://your-demo-link.streamlit.app/)

## How It Works: Step-by-Step

This project takes a user's search query, gathers detailed data, saves it safely, and produces visual reports. Here is the visual flow and step-by-step breakdown of how data travels through the system:

```mermaid
flowchart TD
    %% Styling
    classDef inputStyle fill:#E3F2FD,stroke:#1E88E5,stroke-width:2px,color:#0D47A1;
    classDef processStyle fill:#F5F5F5,stroke:#424242,stroke-width:2px,color:#212121;
    classDef storageStyle fill:#E8F5E9,stroke:#43A047,stroke-width:2px,color:#1B5E20;
    classDef reportStyle fill:#FFFDE7,stroke:#FBC02D,stroke-width:2px,color:#F57F17;

    User([⌨️ User Input: Keyword]):::inputStyle
    
    subgraph Scraping [1. Polite Scraper Layer]
        Search[🔍 Search Amazon Results]:::processStyle
        Detail[📖 Fetch Individual Product Pages]:::processStyle
    end
    
    subgraph Parsing [2. HTML Parser Layer]
        ParseHTML[🧩 Extract ASIN, Title, Price, Ratings, Availability, Specifications]:::processStyle
    end
    
    subgraph Storage [3. Storage & Export]
        SQLite[(💾 SQLite DB - upsert updates)]:::storageStyle
        CSV[📄 Export CSV Spreadsheet]:::storageStyle
    end
    
    subgraph Analytics [4. Analysis & Reports]
        Pandas[📊 Pandas calculates stats]:::reportStyle
        Matplotlib[📈 Matplotlib draws charts]:::reportStyle
        Report[📝 Markdown summary report]:::reportStyle
    end

    %% Connections
    User --> Search
    Search -->|Extract ASIN list| Detail
    Detail -->|Raw HTML| ParseHTML
    ParseHTML --> SQLite
    SQLite --> CSV
    SQLite --> Pandas
    Pandas --> Matplotlib
    Matplotlib --> Report
```

### The 5-Step Pipeline Lifecycle

For example, when you run: `python cli.py run --keyword "wireless mouse" --max-results 10`

---

#### 1. 🔍 Step 1: Search & Discovery
* **What happens:** The scraper visits Amazon's search results page for the keyword `"wireless mouse"`.
* **What is extracted:** The parser reads the search results page to identify individual product listings and extracts:
  * **ASIN** (Amazon's unique product identifier, e.g., `B084226C1M`)
  * **Title** (Short product title)
  * **URL** (Link to the product detail page)
  * **Initial Price & Ratings**
* **The output:** A list of the top 10 discovered products.

---

#### 2. 📖 Step 2: Deep Detail Enrichment
* **What happens:** The scraper visits each discovered product's detail page (e.g., `amazon.com/dp/B084226C1M`) one-by-one.
* **Why it does this:** Search result pages omit a lot of detail. By visiting the individual product page, the parser extracts:
  * **Bullet Points** (Product features, technical specs)
  * **Exact Availability** (e.g., "In Stock", "Only 2 left in stock")
  * **High-Res Images**
* **Politeness:** To avoid getting blocked, the scraper randomizes headers and pauses (adds dynamic delays) between requests.

---

#### 3. 💾 Step 3: Storage & Isolation
* **Storage Layer:** Both CLI and Web App mode now store the data locally using SQLite (`output/amazon_data.db`) via upsert logic.
* **Local Isolation:** Since the `output/` directory is in `.gitignore`, the database is not committed to GitHub. Any new user cloning the repository will start with an empty local database with no data.
* **CSV Export:** Streamlit offers a direct in-memory CSV download button, while the CLI saves a clean spreadsheet directly to `output/products.csv`.

---

#### 4. 📊 Step 4: Calculations & Charts
* **Calculations:** Pandas reads the scraped dataset and calculates summary statistics (mean, median, range, ratings, total review count).
* **Visualization:** Matplotlib creates three visual insights:
  1. Price spread histogram
  2. Ratings vs. Price scatter plot
  3. Top 10 most-reviewed products bar chart
* **Rendering:** The Web App renders these figures dynamically directly into the browser viewport via `st.pyplot(fig)`. The CLI exports them as physical `.png` files under `output/report/`.

---

#### 5. 📝 Step 5: Report Generation & Control
* **Web App Mode:** The markdown report is constructed dynamically from the database and formatted directly on the dashboard tab using `st.markdown()`. Additionally, a "Clear Scraped Data" button allows you to delete all saved database records with one click to scrape fresh data.
* **CLI Mode:** A static markdown document summarizing all stats and linking the charts is written to `output/report/report.md`. A clean `python cli.py clear` command is also available.


---

## Why this project is structured the way it is

Amazon is one of the harder sites to scrape reliably: markup changes
often, and aggressive bot detection can return CAPTCHA pages instead of
content. Rather than pretend that away, this project is built around it:

- **Parsing is decoupled from networking** (`parser.py` has zero network
  code). This is the single most important design choice here — it means
  the extraction logic is unit-tested against saved HTML fixtures, so the
  test suite is fast, deterministic, and doesn't depend on Amazon being
  reachable at test time.
- **The scraper detects soft-blocks** (CAPTCHA / bot-check pages) and logs
  them explicitly rather than silently returning garbage data.
- **Retries use exponential backoff with jitter**, and requests are spaced
  out with randomised delays — polite by default, not a hammer.
- **Every layer has a single responsibility** (network → parse → store →
  analyze), which is what makes each layer independently testable and
  replaceable (e.g. swapping SQLite for Postgres only touches `storage.py`).
## Tech Stack & Choice of Libraries

Here is a breakdown of which library is used in which area of the project, and why it was selected over alternatives:

### 1. Web Scraping & DOM Parsing: `scrapling`
* **Where it is used:** Used inside the Streamlit dashboard app (`app.py`), the parser (`parser.py`), and scraper (`scraper.py`).
* **Why this library:** 
  * **Stealth Bypass:** Standard libraries like `requests` or `urllib` send generic Python client headers and handshakes that Amazon's bot detection blocks instantly. `scrapling` uses `curl_cffi` under the hood to perform browser TLS/JA3 fingerprint impersonation, making requests appear indistinguishable from real web browsers.
  * **Unified DOM Selectors:** It provides a Scrapy-like CSS/XPath selector API (`Selector`) that is extremely fast, chainable, and clean compared to BeautifulSoup.
  * **Robust Fallback:** Supports dynamic fetching and header generators out-of-the-box.

### 2. Under-the-Hood Impersonation: `curl_cffi`
* **Where it is used:** Implicitly called by `scrapling.Fetcher` during HTTP requests.
* **Why this library:** Traditional Python request libraries cannot spoof TLS fingerprints. `curl_cffi` compiles curl with mimicked Chrome/Firefox TLS handshakes. Without this, scraping Amazon is virtually impossible without immediately hitting CAPTCHAs.

### 3. Header Generation: `browserforge`
* **Where it is used:** Implicitly called by Scrapling to generate request headers.
* **Why this library:** It automatically generates realistic user agents, screen dimensions, and matching headers to mimic real browser footprints.

### 4. Data Processing: `pandas`
* **Where it is used:** Analytics and reporting calculations.
* **Why this library:** It is the industry standard for fast, high-performance data manipulation in Python. It simplifies loading database queries into dataframes, running calculations (mean, median, ranges), and cleaning null values.

### 5. Plotting & Visualizations: `matplotlib`
* **Where it is used:** Generating visual plots.
* **Why this library:** It allows headless rendering (`matplotlib.use("Agg")` backend). The Web App displays figures directly in the browser using `st.pyplot()`, while the CLI exports them as PNG images, both without requiring a graphics server.

### 6. Relational Storage: `sqlite3`
* **Where it is used:** Saving and retrieving scraped data (both CLI and Web App).
* **Why this library:** SQLite is serverless, lightweight, and built into Python. By routing both the CLI and Web App data through SQLite, all scraped products are stored locally in `output/amazon_data.db`. Because `output/` is ignored by Git, developers get a clean repository setup with zero pre-loaded database records.

### 7. Interactive Web UI: `streamlit`
* **Where it is used:** Serving the dashboard UI (`app.py`).
* **Why this library:** Streamlit allows writing pure-Python web interfaces. We integrate it with the local SQLite storage so that you can view and query persisted products, analyze market trends, download CSV exports, and clear/reset your dataset directly from the sidebar.



## Architecture

```mermaid
flowchart LR
    CLI["cli.py\n(argparse entry point)"] --> Scraper
    subgraph Scraper["scraper.py"]
        direction TB
        Fetch["_get()\nretries + rate limit + block detection"]
    end
    Fetch --> Parser["parser.py\npure HTML → dict functions"]
    Parser --> Storage["storage.py\nSQLite upsert + CSV export"]
    Storage --> Analysis["analysis.py\npandas stats + matplotlib charts"]
    Analysis --> Report["output/report/\nreport.md + PNG charts"]

    Fixtures["tests/fixtures/*.html"] -.offline test input.-> Parser
```

## Project layout

```
amazon_scraper/
├── amazon_scraper/
│   ├── config.py       # headers, delays, retry policy, storage paths
│   ├── utils.py         # logging, retry/backoff decorator, rate limiter
│   ├── parser.py        # pure HTML → structured data (the tested core)
│   ├── scraper.py       # HTTP layer: sessions, retries, block detection
│   ├── storage.py       # SQLite upsert + CSV export
│   └── analysis.py      # pandas summary stats + matplotlib charts
├── tests/
│   ├── fixtures/         # saved HTML samples used for offline parser tests
│   ├── test_parser.py
│   ├── test_storage.py
│   └── test_utils.py
├── cli.py                # command-line entry point
├── requirements.txt
├── .env.example
└── output/                # generated at runtime: db, csv, charts, report
```

## Setup & Installation

### 1. Check Python Installation and Location
To locate your installed Python path or verify Python is installed, run the following commands:
* **Windows (PowerShell or Command Prompt):**
  ```powershell
  python --version
  where.exe python
  ```
* **macOS / Linux:**
  ```bash
  python3 --version
  which python3
  ```
Make sure you are using Python 3.10 or newer.

---

### 2. Create the Virtual Environment (`venv`)
A virtual environment keeps the project dependencies isolated from your global system. To create it, run:
* **Windows / macOS / Linux:**
  ```bash
  python -m venv venv
  ```
This will create a `venv/` directory inside the project folder.

---

### 3. Activate the Virtual Environment
Before installing dependencies or running the scripts, you must activate the virtual environment so your terminal uses the local project context:
* **Windows (PowerShell):**
  ```powershell
  venv\Scripts\Activate.ps1
  ```
  *(Note: If you get an execution policy error, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process` first)*
* **Windows (CMD):**
  ```cmd
  venv\Scripts\activate.bat
  ```
* **macOS / Linux:**
  ```bash
  source venv/bin/activate
  ```
When activated, you will see `(venv)` prefixing your command line prompt.

---

### 4. Install Dependencies
With the virtual environment activated, install all required packages:
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

### 5. Environment Configuration
Copy the template `.env.example` file to `.env` to configure optional settings:
* **Windows:**
  ```powershell
  copy .env.example .env
  ```
* **macOS / Linux:**
  ```bash
  cp .env.example .env
  ```

---

## Usage

You can run the project either inside your activated virtual environment or by calling the virtual environment executables directly.

### Option A: Web App Dashboard (Streamlit)
The Streamlit app provides a dashboard to scrape products, view the database explorer, see statistical analysis, and download CSV files.

* **Method 1: Run with virtual environment activated (Recommended):**
  ```bash
  streamlit run app.py
  ```
* **Method 2: Run directly via venv path (Without activating):**
  * **Windows:**
    ```powershell
    venv\Scripts\streamlit run app.py
    ```
  * **macOS / Linux:**
    ```bash
    venv/bin/streamlit run app.py
    ```

Once started, open [http://localhost:8501](http://localhost:8501) in your browser.

---

### Option B: Terminal Command-Line (CLI)

The CLI tool allows you to perform scraping, analyzing, exporting, and clearing directly from the console.

#### 1. Run the Scraper Pipeline (Search + Enrich + Store + Analyze):
* **With activated venv:**
  ```bash
  python cli.py run --keyword "wireless mouse" --max-results 15
  ```
* **Directly via venv path (Windows):**
  ```powershell
  venv\Scripts\python cli.py run --keyword "wireless mouse" --max-results 15
  ```

#### 2. Re-run Analytics on existing DB data (without doing new scrapes):
* **With activated venv:**
  ```bash
  python cli.py analyze
  ```
* **Directly via venv path (Windows):**
  ```powershell
  venv\Scripts\python cli.py analyze
  ```

#### 3. Export DB records to a CSV spreadsheet:
* **With activated venv:**
  ```bash
  python cli.py export
  ```
* **Directly via venv path (Windows):**
  ```powershell
  venv\Scripts\python cli.py export
  ```

#### 4. Clear/Delete all saved scraped data from the SQLite DB:
* **With activated venv:**
  ```bash
  python cli.py clear
  ```
* **Directly via venv path (Windows):**
  ```powershell
  venv\Scripts\python cli.py clear
  ```

Output files will land in the `output/` directory:
* `output/amazon_data.db` (The local SQLite database)
* `output/products.csv` (The CSV export)
* `output/report/` (The markdown analysis summary and plots)

---

## Testing

To run the offline test suite against saved HTML fixtures:
* **With activated venv:**
  ```bash
  pytest tests/ -v
  ```
* **Directly via venv path (Windows):**
  ```powershell
  venv\Scripts\python -m pytest tests/ -v
  ```


All 30 tests run offline against saved HTML fixtures in
`tests/fixtures/` — no network access or live Amazon connection is
required or used in the test suite.

## Known limitations (read before running against live Amazon)

- **Bot detection.** Amazon may serve a CAPTCHA/bot-check page instead of
  real content, especially with sustained or high-frequency requests.
  `scraper.py` detects this pattern and logs it rather than saving junk
  data, but it does not attempt to solve CAPTCHAs or route around blocks.
- **Markup drift.** Amazon's HTML structure changes periodically. If
  fields start coming back empty, the CSS selectors in `parser.py` are
  the first place to check — that's exactly why they're isolated in one
  file.
- **Scale.** Reliable scraping at volume typically requires residential
  proxies and slower, more human-like pacing than most portfolio projects
  need to demonstrate. `SCRAPER_PROXY` is wired up for this but no proxy
  provider is bundled or endorsed.
- **Terms of Service.** Amazon's terms restrict automated data collection.
  This project is intended for personal learning/demonstration on a small
  number of requests with polite rate-limiting, not production or
  commercial use. Check current ToS and `robots.txt` before scraping any
  site, and consider official APIs (e.g. Amazon's Product Advertising
  API) for real applications.

## Possible extensions (good "next steps" talking points in an interview)

- Swap SQLite for Postgres and containerize with Docker Compose.
- Add Selenium/Playwright fallback for JS-rendered edge cases.
- Schedule recurring scrapes (cron / Airflow) to track price history over
  time and chart trends.
- Add a lightweight Flask/FastAPI endpoint to serve the analysis report.
