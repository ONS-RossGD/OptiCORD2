# OptiCORD
OptiCORD is a tool for quickly, reliably and repeatedly QA'ing data changes on CORD - but if you're here, you probably already knew that.

OptiCORD uses PyQt5 to create and manage the interface, as well as the threading. The interface is loaded from defualt Qt elements saved in .ui files, then custom elements and functionality is built on top. As a general rule of thumb, any .ui file inside of the ui folder will have a .py file assosicated with the same name. The ui files can be created and edited using QtDesigner, which is installed with Anaconda by default and can be loaded by typing
```
designer
```
in an Anaconda Prompt.

There is a lot of code behind OptiCORD and unfortunately I haven't had chance to document it all, so you'll have to work through most of it the hard way. I did however try my best to leave as many helpful comments as I could when building it.

You can run the main interface as you would do from the exe by running main.py

To make changes to the code please branch off and merge back into main once code has been tested.

If you introduce an new packages please remeber to update requirements.txt by
```
pip list > requirements.txt
```
<b>*IMPORTANT: When updating requirements.txt make sure you're in a virtual environment with only packages required to run OptiCORD installed. The more packages installed the longer it takes the exe to open.*</b>


# Setup
OptiCORD uses packages not included with Anaconda, so you'll first need to set up your access to the office Artifactory if you haven't already. I'd also recommend setting all of this up in a virtual environment. For info of either of those things, see the [coding getting started](http://np2rvlapxx507/BPI/coding-getting-started-guide/-/wikis/home) page.

Once you've cloned this repo to a folder and set up the virtual environment do
```
pip install requirements.txt
```
This will download and install all required packages.

I'd recommend you use [VS Code](http://np2rvlapxx507/BPI/coding-getting-started-guide/-/wikis/code-editors) to work on OptiCORD, but ultimately it's your preference. 

# Design Changes
In anaconda prompt, cd to BreezeStylesheets

1. Add custom svg files to template
2. Update icon theme formatting in template/icons.json
3. Edit stylesheet formatting for all themes by editing template/stylesheet.qss.in
4. Define themes by editting the json files in /theme
5. Build themes using command: 
```python configure.py --styles=all --resource qt_resources.qrc```
6. Build resource initializer using: ```pyrcc5 dist/qt_resources.qrc -o resource_init.py```

7. Copy files from /dist to OptiCORD/ui/resources
8. Copy resource_init.py from / to OptiCORD/ui/resources

For changes to take effect you need to reselect the theme in ui once OptiCORD has loaded.

# Compiling into EXE
You can re-compile the python code into a .exe file by typing the following into a terminal at OptiCORD source folder:<br>
```
pyinstaller onefile.spec
```
*Note onedir.spec was explored, but sharepoint falsely flags the generated exe as a virus...  which didn't go down well.*