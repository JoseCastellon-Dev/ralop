import re, os, sys, traceback
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
from time import sleep

### LIB WORKFLOW
from workflowlog import set_var, init_log, print_log, get_platform_vars, get_info,conv, gpvars
from workflowlog import DEFAULT, SUCCESS, ERROR, WARNING, INFO

### MODULE DR_WORKFLOW FUNCTIONS
sys.path.append(os.path.join(os.getcwd(),os.path.normpath('modules/dr-workflow')))
from module.business.carriers_manager import get_regex_for_types
from module.business import remember as rem, Gspreadsheet as gsheet, alerts

### GET LIB TO MANAGE THE APP
sys.path.append(os.path.join(os.getcwd(),os.path.normpath('modules/ActionsHandler/libs')))
from actionsHandler.PyAutoGui import pyautogui as pg
from actionsHandler.WinAction import WinAction
from actionsHandler.ImgAction import ImgAction
from actionsHandler import utils as ut
from utils import loadJson
global winAction, imgAction, schema, wins
from rocketbot import SetVar, GetVar



winAction = WinAction()
imgAction = ImgAction()

schema = loadJson(GetVar("selectors_path"))


# declaration of variables
PRE_CONFIG_DATA = {
    "CtrlID_list" : [
        "primMemberTextEdit",
        "secMemberTextEdit",
        "medicaidIdTextEdit",
        "insuranceIdTextEdit",
        "relationLookupEdit"
    ]
}


### Get window scopes dictionary
wins = schema["SD_V19"]



### Start SOFTDENT V19
def login_softdent_v19():
    global iv_config, get_info
    app = False
    user = "Jose"
    sleep(3)
    pg.press('win')
    sleep(3)
    pg.typewrite("CS SoftDent Software")
    sleep(3)
    pg.press('Enter')



    print_log(SUCCESS, "Softdent executed successfully!")
    winAction.windowScope(get_info(wins,"login_window",def_value= "empty"), 10)
    login = winAction.waitObject(get_info(schema,"login.exist_login"), 2)

    if login:        
        winAction.selectItem(get_info(schema,"login.user_txt"),5,user)
        app = winAction.windowScope(get_info(wins,"main_window",def_value= "empty"), 10)
        

    return app