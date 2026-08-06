# MACSima Parser

**MACSima Parser** helps you turn experiment data from a MACSima imaging run (in `.json` format) into a clear Excel file you can open in Excel, Google Sheets, or similar tools.

## Version History

### v2.0.0 (Current)
- **Multiple procedures support**: Each procedure now gets its own Excel sheet, named after the procedure
- Previously, all procedures were merged into a single "Blocks" sheet, which made it difficult to distinguish between experiments run on different regions of interest (ROIs)
- Shared data (Experiment, Racks, ROIs, Samples) remains in common sheets

### v1.x (Previous)
- All procedure blocks were combined into a single "Blocks" sheet
- This worked well for single-procedure experiments but did not clearly separate multiple procedures

---

You do not need to know Python to use this tool!
Try the UI here: [https://macsima-parser.onrender.com/](https://macsima-parser.onrender.com/)

---

## 1. Setup

### 1.1 Install Python (if you don’t have it)

* **Windows/macOS:** Download and install Python 3.10 from [python.org/downloads](https://www.python.org/downloads/release/python-3100/).

  * During install, make sure to check the box **“Add Python to PATH”**.
* **Linux:** Usually Python 3 is already installed.
* You can check if Python is installed by typing `python3 --version` in Terminal.

### 1.2 Install Miniconda (if you don’t have it)

We recommend using Miniconda for managing Python versions and dependencies in a virtual environment. Download and install Miniconda from [[Miniconda installers](https://docs.conda.io/en/latest/miniconda.html)](https://www.anaconda.com/docs/getting-started/miniconda/install)

NOTE: make sure conda is added to your PATH. Ignore warning message in installer.

### 1.3 Create a virtual environment using Miniconda 

**Once Miniconda is installed**, create your virtual environment.

```sh
conda create -n macsima python=3.10
```
This will prompt you to type y (yes) to proceed.
### 1.4 Activate your virtual environment

```sh
conda activate macsima
```

You’ll see your terminal prompt change to show `(macsima)` at the start, which means the environment is active.
Link to tutorial for more info e.g. how to see active env

---

### 1.5 Install dependencies

With your environment activated, install the required libraries:

```sh
pip install -r requirements.txt
```

This will install pandas, xlsxwriter, flask, and werkzeug (for the web interface).

### 1.6 Download this code

Click the green **“Code”** button (top right) and select **Download ZIP**.
Unzip it to a folder of your choice.

---

## 2. Usage Options

You can use MACSima Parser in two ways:

### Option A: Web Interface (Recommended for most users)

1. **Start the web app:**
   ```sh
   python app.py
   ```

2. **Open your browser** and go to: `http://localhost:5000`

3. **Upload your JSON file** using the drag-and-drop interface

4. **Download your Excel report** automatically

### Option B: Command Line (For advanced users)

#### 2.1 Open a Terminal / Command Prompt

* **Windows:** Open "Anaconda Prompt" (if you have Anaconda/Miniconda), or just "Command Prompt".
* **macOS:** Open Terminal.
* **Linux:** Open your favorite Terminal.

Navigate to the folder containing the code. 

e.g.
```
cd /Users/username/folder/path/to/macsima-parser-main
```

#### 2.2 Prepare your data

Copy your `.json` MACSima file to the same folder as this script, or note its path.

Note: check if your file names have any whitespace and remove it if so. e.g. if your file name is:

`my data.json`

change it to:

`my_data.json` or `my-data.json`

#### 2.3 Run the code

In Terminal/Command Prompt, run:

```sh
python src/macsima_parser.py path_to_your_file.json
```

If you forget the file path, the program will **ask you to enter it**.

**Output**
A new Excel file (with the same name as your JSON file, but ending with `.xlsx`) will be created in the same folder.

Open it in Excel, Google Sheets, or similar!

---

## 3. Online Deployment (Optional)

Want to share this tool with others? You can deploy it for free on Render:

1. **Push your code to GitHub**
2. **Connect to Render** at https://render.com
3. **Deploy as a web service**

See `DEPLOYMENT.md` for detailed instructions.

---

## Run Tests (Optional)

If you want to make sure the parser works correctly, you can run:
```sh
pip install pytest
```

```sh
pytest src/test_macsima_parser.py
```

---

## Troubleshooting

* **"python: command not found"**
  Make sure you installed Python and followed step 1.
* **"No module named pandas" or similar**
  Make sure you ran the `pip install -r requirements.txt` command with your environment activated.
* **Web interface not loading**
  Make sure you have activated your conda environment before running `python app.py`.
* **Excel file not created**
  Double-check that your input JSON file is correct and in the right location.
* **Any errors?**
  Please copy the error message and open an [issue](https://github.com/lmcassidy/macsima-parser/issues).

---

## About

Developer: Lauren Cassidy
Project Manager: Féaron Cassidy.
This script is open-source. Improvements are welcome!

---
