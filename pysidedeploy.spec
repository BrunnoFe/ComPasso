[app]

# title of your application
title = ComPasso

# project root directory. default = The parent directory of input_file
project_dir = .

# source file entry point path. default = main.py
input_file = main.py

# directory where the executable output is generated
exec_directory = dist\nuitka

# path to the project file relative to project_dir
project_file = 

# application icon
icon = assets\icon.ico

[python]

# python path
python_path = C:\Users\shaulimdoplim\Documents\GitHub\Compasso\.venv\Scripts\python.exe

# python packages to install
packages = Nuitka

# buildozer = for deploying Android application
android_packages = buildozer==1.5.0,cython==0.29.33

[qt]

# paths to required qml files. comma separated
# normally all the qml files required by the project are added automatically
# design studio projects include the qml files using qt resources
qml_files = src\compasso\gui_qt\qml\AppMenuBar.qml,src\compasso\gui_qt\qml\AppWindow.qml,src\compasso\gui_qt\qml\Main.qml,src\compasso\gui_qt\qml\TitleBar.qml,src\compasso\gui_qt\qml\components\AppButton.qml,src\compasso\gui_qt\qml\components\AppComboBox.qml,src\compasso\gui_qt\qml\components\AppSlider.qml,src\compasso\gui_qt\qml\components\AppSwitch.qml,src\compasso\gui_qt\qml\components\AppTextField.qml,src\compasso\gui_qt\qml\components\Caption.qml,src\compasso\gui_qt\qml\components\Card.qml,src\compasso\gui_qt\qml\components\ConfirmDialog.qml,src\compasso\gui_qt\qml\components\Dica.qml,src\compasso\gui_qt\qml\components\Equalizer.qml,src\compasso\gui_qt\qml\components\ErroCampo.qml,src\compasso\gui_qt\qml\components\FormSection.qml,src\compasso\gui_qt\qml\components\GhostButton.qml,src\compasso\gui_qt\qml\components\LogoMark.qml,src\compasso\gui_qt\qml\components\MessageDialog.qml,src\compasso\gui_qt\qml\components\SplashOverlay.qml,src\compasso\gui_qt\qml\components\ThemeToggle.qml,src\compasso\gui_qt\qml\components\UpdateDialog.qml,src\compasso\gui_qt\qml\views\CartaoConfig.qml,src\compasso\gui_qt\qml\views\ConnectionView.qml,src\compasso\gui_qt\qml\views\FooterView.qml,src\compasso\gui_qt\qml\views\MainContent.qml,src\compasso\gui_qt\qml\views\PlayerBarView.qml,src\compasso\gui_qt\qml\views\SignalChartView.qml,src\compasso\gui_qt\qml\views\StepperView.qml,src\compasso\gui_qt\qml\windows\AppSettingsWindow.qml,src\compasso\gui_qt\qml\windows\CalibrationWindow.qml,src\compasso\gui_qt\qml\windows\ExperimentConfigWindow.qml,src\compasso\gui_qt\qml\windows\GraphSettingsWindow.qml

# excluded qml plugin binaries
excluded_qml_plugins = QtCharts,QtSensors,QtWebEngine

# qt modules used. comma separated
modules = Core,Gui,Multimedia,Qml,Quick,QuickControls2

# qt plugins used by the application. only relevant for desktop deployment
# for qt plugins used in android application see [android][plugins]
plugins = accessiblebridge,egldeviceintegrations,generic,iconengines,imageformats,multimedia,platforminputcontexts,platforms,platforms/darwin,platformthemes,qmllint,qmltooling,scenegraph,vectorimageformats,wayland-decoration-client,wayland-graphics-integration-client,wayland-shell-integration,xcbglintegrations

[android]

# path to pyside wheel
wheel_pyside = 

# path to shiboken wheel
wheel_shiboken = 

# plugins to be copied to libs folder of the packaged application. comma separated
plugins = 

[nuitka]

# usage description for permissions requested by the app as found in the info.plist file
# of the app bundle. comma separated
# eg = extra_args = --show-modules --follow-stdlib
macos.permissions = 

# mode of using nuitka. accepts standalone or onefile. default = onefile
mode = onefile

# specify any extra nuitka arguments
extra_args = --noinclude-qt-translations --assume-yes-for-downloads

[buildozer]

# build mode
# possible values = ["aarch64", "armv7a", "i686", "x86_64"]
# release creates a .aab, while debug creates a .apk
mode = debug

# path to pyside6 and shiboken6 recipe dir
recipe_dir = 

# path to extra qt android .jar files to be loaded by the application
jars_dir = 

# if empty, uses default ndk path downloaded by buildozer
ndk_path = 

# if empty, uses default sdk path downloaded by buildozer
sdk_path = 

# other libraries to be loaded at app startup. comma separated.
local_libs = 

# architecture of deployed platform
arch = 

