import maya.cmds as cmds
import os

modString = """
+ PLATFORM:win64 bm 1.0 MODULE_LOC
MYMODULE_SHADERS_LOCATION:=shaders 
MYMODULE_INCLUDE_LOCATION:=shaders/include 
MOD_PLUG_IN_PATH+:=bin/image 
PATH+:=bin 
icons: ../icons 
presets: ../presets 
scripts: ../scripts 

+ PLATFORM:mac bm 1.0 MODULE_LOC 
MYMODULE_SHADERS_LOCATION:=shaders 
MYMODULE_INCLUDE_LOCATION:=shaders/include 
MOD_PLUG_IN_PATH+:=bin/image 
PATH+:=bin 
icons: ../icons 
presets: ../presets 
scripts: ../scripts 
"""


def easyInstall():
    mayaAppDir = cmds.internalVar(userAppDir=1)
    try:
        # have the user browse for the package directory on their system
        packageDir = cmds.fileDialog2(okCaption="Set Path",
                                       fileMode=3,
                                       caption="Browse to Scripts Folder")[0]
    except TypeError:
        # will happen if the user exits the file dialog
        failMessage = "Install of the bm module failed.\n\nPlease drag the file back into Maya to install."
        print "\n" + failMessage
        cmds.confirmDialog(title="Error", message=failMessage)
        return

    # make the \modules directory if it doesn't already exist
    if not os.path.exists(os.path.join(mayaAppDir, "modules")):
        os.makedirs(os.path.join(mayaAppDir, "modules"))

    # create our mod file in the user's maya modules directory
    modFile = open(os.path.join(mayaAppDir, "modules", "bm.mod"), "w+")

    writeString = modString.replace("MODULE_LOC", packageDir)

    # write the contents of our package file
    modFile.write(writeString)
    modFile.close()

    successMessage = "Successfully installed the bm module.\n\nPlease restart Maya to finish installation."
    print "\n" + successMessage
    cmds.confirmDialog(title="Success", message=successMessage)


easyInstall()
