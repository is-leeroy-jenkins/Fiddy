# Fiddy Installation Guide

This guide explains how to install and run **Fiddy**, the AI-assisted alcohol label verification application, on a local computer.

It is written for users who may have little or no Python experience. Follow the steps in order and copy one command block at a time.

---

## Table of Contents

- [What You Are Installing](#what-you-are-installing)
- [Before You Start](#before-you-start)
- [Recommended Folder Location](#recommended-folder-location)
- [Windows Installation](#windows-installation)
- [macOS Installation](#macos-installation)
- [Linux Installation](#linux-installation)
- [Create the Environment File](#create-the-environment-file)
- [Install Python Packages](#install-python-packages)
- [Run Fiddy](#run-fiddy)
- [Stop Fiddy](#stop-fiddy)
- [Run Tests](#run-tests)
- [Update the Application Later](#update-the-application-later)
- [Dependency Reference](#dependency-reference)
- [Troubleshooting](#troubleshooting)
- [Command Cheat Sheet](#command-cheat-sheet)

---

## What You Are Installing

Fiddy is a local Streamlit web application. It runs in your browser, but the processing runs on your computer.

Fiddy uses:

- **Python** to run the application.
- **Streamlit** to display the web interface.
- **Tesseract OCR** to read text from label images.
- **Poppler** to convert PDF label artwork into images before OCR.
- **OpenCV, Pillow, and NumPy** to process and evaluate label artwork.
- **Pandas** to read manifests and produce review tables.
- **RapidFuzz** to compare text with minor variations.

---

## Before You Start

You need these tools installed:

| Tool | Required? | Why It Is Needed |
| --- | --- | --- |
| Git | Recommended | Downloads or updates the project from GitHub. |
| Python 3.11 or newer | Required | Runs the Fiddy application. |
| Tesseract OCR | Required | Reads text from uploaded label images. |
| Poppler | Recommended | Required for PDF label artwork. |
| VS Code, PyCharm, or another editor | Optional | Useful if you want to inspect or edit files. |

If you only plan to upload image files such as PNG or JPG, Poppler is not strictly required. If you plan to upload PDFs, install Poppler.

---

## Recommended Folder Location

For a simple local setup, place the project in a folder such as:

```text
C:\Projects\fiddy
```

Avoid paths with special characters or cloud-sync conflicts when possible. For example, avoid installing the project directly inside OneDrive if OneDrive aggressively locks files on your machine.

---

## Windows Installation

These instructions assume Windows 10 or Windows 11.

### Step 1 — Open PowerShell

1. Click the Windows Start button.
2. Type `PowerShell`.
3. Open **Windows PowerShell** or **Windows Terminal**.

You do not normally need to run PowerShell as Administrator unless you are installing system tools.

---

### Step 2 — Check Whether Python Is Installed

Run:

```powershell
py --version
```

You should see something like:

```text
Python 3.11.x
```

If that works, also run:

```powershell
py -3.11 --version
```

If Python is not found, install Python 3.11 or newer from the official Python website or through your approved software center. During installation, select the option that says **Add python.exe to PATH**.

After installing Python, close PowerShell, reopen it, and run the version command again.

---

### Step 3 — Check Whether Git Is Installed

Run:

```powershell
git --version
```

You should see something like:

```text
git version 2.x.x
```

If Git is not found, install Git from the official Git website or through your approved software center.

---

### Step 4 — Install Tesseract OCR

Fiddy needs Tesseract OCR to read label text from images.

#### Option A — Install with Windows Package Manager

Try:

```powershell
winget install --id UB-Mannheim.TesseractOCR -e
```

After installation, close PowerShell and reopen it.

Then verify Tesseract:

```powershell
tesseract --version
```

#### Option B — Install Manually

If `winget` is not available, install Tesseract manually using an approved Windows installer.

The common installation location is:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

After installation, verify:

```powershell
& "C:\Program Files\Tesseract-OCR\tesseract.exe" --version
```

If that works, you can tell Fiddy exactly where Tesseract is by setting an environment variable:

```powershell
setx TESSERACT_CMD "C:\Program Files\Tesseract-OCR\tesseract.exe"
```

Close PowerShell and reopen it after running `setx`.

---

### Step 5 — Install Poppler for PDF Support

Poppler is needed when uploaded label artwork is a PDF.

#### Option A — Install with Windows Package Manager

Try:

```powershell
winget install --id oschwartz10612.Poppler -e
```

Close PowerShell and reopen it.

Then verify Poppler:

```powershell
pdfinfo -v
```

#### Option B — Install Manually

If `winget` is not available, install Poppler manually using an approved Windows build.

After installation, add the Poppler `bin` folder to your Windows `PATH`.

A typical Poppler `bin` folder may look similar to:

```text
C:\Program Files\poppler\Library\bin
```

After adding the folder to `PATH`, close PowerShell, reopen it, and run:

```powershell
pdfinfo -v
```

---

### Step 6 — Download the Fiddy Repository

Choose a location for projects:

```powershell
mkdir C:\Projects
cd C:\Projects
```

Clone the repository:

```powershell
git clone <repository-url> fiddy
cd fiddy
```

Replace `<repository-url>` with the actual GitHub repository URL.

If you downloaded the repository as a ZIP file instead of using Git, unzip it, then use `cd` to enter the unzipped project folder.

---

### Step 7 — Confirm You Are in the Correct Folder

Run:

```powershell
dir
```

You should see files and folders similar to:

```text
app.py
config.py
requirements.txt
src
assets
samples
tests
```

If you do not see `app.py` and `requirements.txt`, you are probably in the wrong folder.

---

### Step 8 — Create a Python Virtual Environment

A virtual environment keeps Fiddy's Python packages separate from the rest of your computer.

Run:

```powershell
py -3.11 -m venv .venv
```

If `py -3.11` does not work but `py` works, run:

```powershell
py -m venv .venv
```

---

### Step 9 — Activate the Virtual Environment

Run:

```powershell
.\.venv\Scripts\Activate.ps1
```

Your prompt should now begin with:

```text
(.venv)
```

That means the virtual environment is active.

If PowerShell blocks activation with a script execution error, run:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then activate again:

```powershell
.\.venv\Scripts\Activate.ps1
```

---

## macOS Installation

These instructions assume you are using Terminal.

### Step 1 — Install Homebrew

If Homebrew is already installed, skip this step.

Verify Homebrew:

```bash
brew --version
```

If it is not installed, install it using the official Homebrew instructions approved for your machine.

---

### Step 2 — Install System Tools

Run:

```bash
brew install python git tesseract poppler
```

Verify the tools:

```bash
python3 --version
git --version
tesseract --version
pdfinfo -v
```

---

### Step 3 — Download the Repository

Run:

```bash
mkdir -p ~/Projects
cd ~/Projects
git clone <repository-url> fiddy
cd fiddy
```

Replace `<repository-url>` with the actual GitHub repository URL.

---

### Step 4 — Create and Activate the Virtual Environment

Run:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Your prompt should begin with:

```text
(.venv)
```

---

## Linux Installation

These instructions assume Ubuntu or Debian Linux.

### Step 1 — Install System Packages

Run:

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip git tesseract-ocr poppler-utils
```

Verify the tools:

```bash
python3 --version
git --version
tesseract --version
pdfinfo -v
```

---

### Step 2 — Download the Repository

Run:

```bash
mkdir -p ~/Projects
cd ~/Projects
git clone <repository-url> fiddy
cd fiddy
```

Replace `<repository-url>` with the actual GitHub repository URL.

---

### Step 3 — Create and Activate the Virtual Environment

Run:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Your prompt should begin with:

```text
(.venv)
```

---

## Create the Environment File

Fiddy reads configuration values from `config.py` and may also read values from a `.env` file.

Create a file named:

```text
.env
```

Place it in the same folder as `app.py` and `requirements.txt`.

Recommended starter `.env` file:

```env
APP_NAME=Fiddy
APP_TITLE=Label Verification
APP_ICON=🥃
APP_LAYOUT=wide
OCR_ENGINE=tesseract
OCR_LANGUAGE=eng
OCR_TIMEOUT_SECONDS=5
MAX_UPLOAD_MB=25
MAX_BATCH_FILES=25
BRAND_MATCH_THRESHOLD=90.0
CLASS_TYPE_MATCH_THRESHOLD=85.0
LOW_CONFIDENCE_THRESHOLD=70.0
REPORT_FILENAME_PREFIX=fiddy_report
LOG_PATH=logging/Exceptions.db
LOG_FILE=Exceptions
```

On Windows, add this line if Tesseract is not already on your `PATH`:

```env
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

Do not commit `.env` files that contain secrets, credentials, or production configuration values.

---

## Install Python Packages

Make sure the virtual environment is active.

Your terminal prompt should start with:

```text
(.venv)
```

Upgrade `pip`:

### Windows

```powershell
python -m pip install --upgrade pip
```

### macOS / Linux

```bash
python -m pip install --upgrade pip
```

Install the project dependencies:

```bash
pip install -r requirements.txt
```

The installation may take several minutes the first time.

---

## Run Fiddy

Make sure you are in the project folder and the virtual environment is active.

Run:

```bash
streamlit run app.py
```

Streamlit should display a local URL similar to:

```text
Local URL: http://localhost:8501
```

Open the local URL in your browser.

If the browser does not open automatically, copy and paste the local URL into Chrome, Edge, Firefox, or Safari.

---

## Basic First Run Checklist

After the application opens:

1. Confirm the page title shows **Fiddy** or **Label Verification**.
2. Upload a manifest CSV, if using batch mode.
3. Upload one or more label artwork files.
4. If no manifest is uploaded, enter values in the CAV application data form.
5. Confirm the app changes from **Not Ready** to a ready state.
6. Click **Run Verification**.
7. Review the results.
8. Download any needed CSV, JSON, or Markdown outputs.

---

## Stop Fiddy

Go back to the terminal where Streamlit is running.

Press:

```text
Ctrl+C
```

If prompted to confirm, press `Y` and then `Enter`.

---

## Run Tests

Make sure the virtual environment is active.

Run:

```bash
pytest
```

If tests are organized inside a `tests` folder, this command should discover and run them automatically.

---

## Update the Application Later

If the repository was cloned with Git, update it with:

```bash
git pull
```

Then reinstall dependencies in case `requirements.txt` changed:

```bash
pip install -r requirements.txt
```

Then run the app again:

```bash
streamlit run app.py
```

---

## Dependency Reference

The Python packages are listed in `requirements.txt`.

| Package | Version | Purpose |
| --- | ---: | --- |
| `streamlit` | `1.45.1` | Runs the web application interface. |
| `pandas` | `2.2.3` | Reads CSV manifests and builds review/export tables. |
| `numpy` | `2.2.6` | Supports numeric and image-analysis operations. |
| `pillow` | `11.2.1` | Loads and manipulates image files. |
| `opencv-python-headless` | `4.11.0.86` | Supports image preprocessing and visual-quality analysis. |
| `pytesseract` | `0.3.13` | Connects Python to the local Tesseract OCR engine. |
| `rapidfuzz` | `3.13.0` | Performs fuzzy text matching. |
| `pydantic` | `2.11.5` | Defines structured application, OCR, result, and report models. |
| `python-dotenv` | `1.1.0` | Loads configuration values from `.env`. |
| `pytest` | `8.3.5` | Runs automated tests. |
| `pdf2image` | `1.17.0` | Converts PDF pages to images for OCR. |

System-level dependencies:

| Tool | Purpose |
| --- | --- |
| Tesseract OCR | Required for OCR text extraction. |
| Poppler | Required for PDF label artwork support. |
| Git | Recommended for cloning and updating the repository. |
| Python 3.11+ | Required to run the application. |

---

## Troubleshooting

### Problem: `python` or `py` is not recognized

Python is not installed or is not on your `PATH`.

Fix:

1. Install Python 3.11 or newer.
2. Select **Add python.exe to PATH** during installation.
3. Close and reopen your terminal.
4. Run:

```powershell
py --version
```

---

### Problem: PowerShell blocks `.venv` activation

You may see an error about scripts being disabled.

Fix:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then run:

```powershell
.\.venv\Scripts\Activate.ps1
```

---

### Problem: `tesseract is not installed or it is not in your PATH`

Tesseract is not installed, or Fiddy cannot find it.

Fix on Windows:

```powershell
setx TESSERACT_CMD "C:\Program Files\Tesseract-OCR\tesseract.exe"
```

Close and reopen PowerShell.

Then verify:

```powershell
& "C:\Program Files\Tesseract-OCR\tesseract.exe" --version
```

Also confirm your `.env` file includes:

```env
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

---

### Problem: PDF uploads fail

Poppler may not be installed or may not be on your `PATH`.

Verify Poppler:

```bash
pdfinfo -v
```

If the command is not found, install Poppler and make sure its `bin` folder is on your `PATH`.

---

### Problem: `ModuleNotFoundError`

The Python dependencies may not be installed in the active virtual environment.

Fix:

```bash
pip install -r requirements.txt
```

Also confirm that the virtual environment is active:

```text
(.venv)
```

---

### Problem: `No module named src`

You are probably running the command from the wrong folder.

Fix:

1. Go to the folder that contains `app.py`.
2. Run Streamlit from that folder:

```bash
streamlit run app.py
```

---

### Problem: Streamlit says the port is already in use

Another Streamlit app may already be running.

Option 1: Stop the other app with `Ctrl+C`.

Option 2: Run Fiddy on another port:

```bash
streamlit run app.py --server.port 8502
```

Then open:

```text
http://localhost:8502
```

---

### Problem: The app opens, but OCR results are poor

This usually means the uploaded artwork is difficult for OCR.

Try:

1. Use a higher-resolution image.
2. Avoid glare.
3. Crop closer to the label.
4. Use a straight-on image.
5. Avoid dark or low-contrast photos.
6. Try PNG or JPG before PDF if the PDF is image-heavy or low quality.

---

## Command Cheat Sheet

### Windows Quick Start

```powershell
cd C:\Projects\fiddy
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

### macOS Quick Start

```bash
cd ~/Projects/fiddy
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

### Linux Quick Start

```bash
cd ~/Projects/fiddy
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

---

## Successful Installation Criteria

The installation is successful when all of the following are true:

- `python --version` works inside the virtual environment.
- `pip install -r requirements.txt` completes without errors.
- `tesseract --version` works, or `TESSERACT_CMD` points to the Tesseract executable.
- `pdfinfo -v` works if PDF processing is needed.
- `streamlit run app.py` starts the application.
- The app opens in a browser at `http://localhost:8501` or another Streamlit port.

