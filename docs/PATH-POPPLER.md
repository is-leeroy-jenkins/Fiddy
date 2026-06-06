# Add Poppler to the Windows PATH Environment Variable

These instructions show how to add a folder such as:

```text
C:\Program Files\poppler\Library\bin
```

to the Windows `PATH` environment variable.

Adding this folder to `PATH` allows Windows, Python, PowerShell, Command Prompt, and other tools to
find Poppler command-line utilities such as `pdftoppm.exe` and `pdfinfo.exe`.

---

## 1. Confirm the Poppler Folder Exists

Open File Explorer and browse to:

```text
C:\Program Files\poppler\Library\bin
```

Confirm that the folder contains Poppler executable files, such as:

```text
pdfinfo.exe
pdftoppm.exe
pdftocairo.exe
```

If the folder does not exist, confirm where Poppler was installed and use the correct `bin` folder
path.

---

## 2. Open Windows Environment Variables

1. Press `Windows + S`.
2. Search for:

```text
environment variables
```

3. Select:

```text
Edit the system environment variables
```

4. In the **System Properties** window, select the **Advanced** tab.
5. Click:

```text
Environment Variables...
```

---

## 3. Choose User PATH or System PATH

In the **Environment Variables** window, there are two main sections:

```text
User variables
System variables
```

### Recommended Option

Use **User variables** if only your Windows account needs Poppler.

Use **System variables** if all users on the computer need Poppler.

For most local development setups, adding Poppler to the **User Path** is sufficient.

---

## 4. Edit the PATH Variable

1. Under **User variables**, select:

```text
Path
```

2. Click:

```text
Edit...
```

3. Click:

```text
New
```

4. Paste the Poppler `bin` path:

```text
C:\Program Files\poppler\Library\bin
```

5. Click:

```text
OK
```

6. Click **OK** again to close the Environment Variables window.
7. Click **OK** again to close System Properties.

---

## 5. Restart Your Terminal or IDE

Close and reopen any tools that need to use Poppler, such as:

* Command Prompt
* PowerShell
* Windows Terminal
* VS Code
* PyCharm
* Jupyter Notebook
* Streamlit terminal sessions

Environment variable changes are not always visible to already-open terminals or IDEs.

---

## 6. Verify Poppler Is Available

Open a new Command Prompt or PowerShell window and run:

```powershell
pdfinfo -v
```

or:

```powershell
pdftoppm -h
```

If the PATH was updated correctly, Windows should find the Poppler executable and display version or
help information.

---

## 7. Troubleshooting

### Error: Command Not Recognized

If you see something like:

```text
'pdfinfo' is not recognized as an internal or external command
```

then Windows still cannot find Poppler.

Check the following:

1. Confirm the path is correct:

```text
C:\Program Files\poppler\Library\bin
```

2. Confirm the folder contains:

```text
pdfinfo.exe
pdftoppm.exe
```

3. Close and reopen your terminal.
4. Restart your IDE.
5. Restart Windows if the PATH still does not refresh.

---

## 8. Verify PATH from PowerShell

You can inspect your current PATH using:

```powershell
$env:Path
```

To make the output easier to read, use:

```powershell
$env:Path -split ';'
```

Look for this entry:

```text
C:\Program Files\poppler\Library\bin
```

---

## 9. Temporary PATH Update for the Current PowerShell Session

If you only want to add Poppler temporarily for the current PowerShell session, run:

```powershell
$env:Path += ";C:\Program Files\poppler\Library\bin"
```

Then test:

```powershell
pdfinfo -v
```

This change only lasts until the PowerShell window is closed.

---

## 10. Python Usage Example

After Poppler is available on `PATH`, Python libraries such as `pdf2image` can use it automatically.

Example:

```python
from pdf2image import convert_from_path

pages = convert_from_path("sample.pdf", dpi=300)

for index, page in enumerate(pages, start=1):
    page.save(f"page_{index}.png", "PNG")
```

If Poppler is not on `PATH`, some libraries may require the path explicitly:

```python
from pdf2image import convert_from_path

pages = convert_from_path(
    "sample.pdf",
    dpi=300,
    poppler_path=r"C:\Program Files\poppler\Library\bin"
)
```

---

# Summary

Add this folder to the Windows `Path` variable:

```text
C:\Program Files\poppler\Library\bin
```

Then restart your terminal or IDE and verify with:

```powershell
pdfinfo -v
```
