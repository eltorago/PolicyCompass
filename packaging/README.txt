PolicyCompass for Windows

Open PolicyCompass.exe to start the application in your default browser.
No Python installation, terminal command or account is needed.

First use
1. Open Framework updates and download the frameworks you want to use.
2. For AESCSF, download the Core workbook from the linked AEMO page and import it.
3. Choose New comparison, describe the documents in scope and select your files.
4. Choose your frameworks and select Compare and save.

Files and results
Policy documents and comparisons stay on this computer. Framework downloads
need internet access. Comparisons work offline after those downloads finish.
Use Saved comparisons to reopen results or import a .policycompass file.
Use Download comparison to save a copy outside the application workspace.
Reports can be downloaded as HTML, CSV, Markdown or JSON.

Closing
Select Quit PolicyCompass in the browser to stop the local application.
If all its browser tabs are closed, it stops after ten minutes without use,
once any active work finishes. Opening the shortcut again reuses a running app.

Storage
Comparisons and settings: %LOCALAPPDATA%\PolicyCompass\browser
Framework cache: %LOCALAPPDATA%\PolicyCompass\frameworks
The app does not encrypt saved files. Uninstalling leaves user data in place.
Temporary copies of selected files are removed after the operation.

Portable edition
Extract the entire ZIP before opening PolicyCompass.exe. Keep the core and
licenses folders beside the launcher. The portable edition uses the same local
user data folders as the installed edition.

Command line
The core\policycompass.exe program accepts the documented command-line options.
Run core\policycompass.exe --help for the list. The original desktop interface
is available with core\policycompass.exe open.

This is an unsigned Windows 64-bit pilot. Example policies, publisher documents
and saved comparisons are not included in the release files.

Documentation and updates: https://github.com/eltorago/PolicyCompass
Releases: https://github.com/eltorago/PolicyCompass/releases
Third-party licence notices are in the licenses directory.
