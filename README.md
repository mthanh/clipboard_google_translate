# _clipboard translate google python_

------------------
This is a simple sample about google translate copy text. Select any text and copy them, it will automatically translate for you.
Copying an **image** (e.g. a screenshot from `Win+Shift+S`) also works: the
app OCRs it with Windows' built-in OCR engine, then translates the result.
It is using tkinter gui. 
It may currently working only on Windows. 

1. translate from browser

![Alt text](assert/copy_from_browser.png) 


2. translate from pdf

![Alt text](assert/copy_from_pdf.png) 


3. translate from pdf + REMOVE_ENTER_PDF

![Alt text](assert/copy_from_pdf_remove_enter.png) 


4. put text into the window

![Alt text](assert/put_text_to_window.png) 










## Note : Translate google
Older versions of this project used `googletrans==3.1.0a0`, which broke
often (`NoneType object has no attribute group`) whenever Google tweaked
its translate endpoint:
https://stackoverflow.com/questions/52455774/googletrans-stopped-working-with-error-nonetype-object-has-no-attribute-group

The app now uses [`deep-translator`](https://github.com/nidhaloff/deep-translator)'s
`GoogleTranslator`, which talks to the same free public endpoint (no API
key needed) but is actively maintained.

```sh
$ pip install deep-translator==1.11.4
```



# A. Setup

## Quick setup (Windows)
Already have Python installed? Just double-click `setup.bat` (or run it
from a terminal) -- it installs everything in `requirements.txt` and
prints how to run the app when it's done.

The steps below are the manual/from-scratch version of what that script does.

## 1. Install Python3.x (If python3 is not installed yet)

- Check if python is installed?
```sh
$ python --version
$ python3 --version
```
![Alt text](assert/python_version.png) 

=> use python3

- If not installed --> Download here https://www.python.org/downloads/

## 2. Install pip3  (If pip3 is not installed yet)

- Check if pip3 is installed?
```sh
$ pip3 --version
```

![Alt text](assert/pip_version.png) 

- If not installed --> try this below
```sh
$ curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
$ python3 get-pip.py
```

## 3. Install pakages from requirement.txt 
```sh
$ cd <Path to Project>
$ pip3 install -r requirements.txt
```

```sh
# for developer : create requirements.txt
$ pipreqs . --force
```

## 4. Install setup from setup.py (optional, for a `clipboard-google-translate` command)
```sh
$ cd <Path to Project>
$ pip3 install -e .
```


# B. Run
## 5. Run and build
1. run by double click main.exe inside dist. (need to do 6. first)
2. `python3 run.py` (from the project root)
3. if installed via step 4 above: `clipboard-google-translate`
4. build by using pycharm, eclipse or something else

## 6. Deploy to application
```sh
$ cd <Path to Project>

#reset
$ rm -rf build/ dist/

# build
$ pyinstaller run.py
```

## 7. Run tests
```sh
$ pip3 install -r requirements-dev.txt
$ pytest
```
