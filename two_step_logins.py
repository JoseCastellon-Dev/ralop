import os
import sys
import time
import requests
from base64 import b64encode,b64decode
import traceback
sys.path.append(os.path.join(os.getcwd(),os.path.normpath('modules/ActionsHandler/libs')))
from actionsHandler.PyAutoGui import pyautogui
from selenium import webdriver as webdriver2
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchWindowException
sys.path.append(os.path.join(os.getcwd(), os.path.normpath('modules/DentalRobot/libs')))
import api_connection.creds as api_creds
sys.path.append(os.path.join(os.getcwd(), os.path.normpath('modules/dr-workflow')))
from module.business import remember as rem, alerts as alt
from module import global_path, get_vars, sys, os, get_info, print_log, ERROR, INFO, set_var, re
from workflowlog import set_var, get_info, conv, print_log, set_status, gpvars
from module.business.workflow_config_manager import get_config
sys.path.append(os.path.join(os.getcwd(), os.path.normpath('modules/dr-workflow/libs')))
from workflow_lib.data.carriers_data_center.classes import Bot
from workflow_lib.data.carriers_data_center import ApiConnection, OfficeClient, ApiResponse


driver = None

token = GetVar("carriers_token")

token = api_creds.needs_decode(token)
clinic_id:str = GetVar("clinicId")

max_wait_time = 120

   

API_URL_BASE = "https://carriers.dentalautomation.ai"

class endpoints:
    BOTSTATUS = "/api/clinicbots/"
    BOTSTATUSES = "/api/clinicbots/status/all"
    BOTNAME ="/api/clinicbots/clinic"
    TOKEN="/api/token"
    SIGNIN="/api/signin"
    RV = "/api/rv/formatted"
    BK="/api/bookmarks"

color_mapping = {
    'RESET': "\033[0m",
    'BLACK': "\033[30m",
    'RED': "\033[31m",
    'GREEN': "\033[32m",
    'YELLOW': "\033[33m",
    'BLUE': "\033[34m",
    'MAGENTA': "\033[35m",
    'CYAN': "\033[36m",
    'WHITE': "\033[37m",
    'BLACK_BG': "\033[40m",
    'RED_BG': "\033[41m",
    'GREEN_BG': "\033[42m",
    'YELLOW_BG': "\033[43m",
    'BLUE_BG': "\033[44m",
    'MAGENTA_BG': "\033[45m",
    'CYAN_BG': "\033[46m",
    'WHITE_BG': "\033[47m",
    'BOLD': "\033[1m",
    'UNDERLINE': "\033[4m"
}


def wait_for_dashboard(driver, by, selector, wait_time=max_wait_time):
    for _ in range(wait_time):
        time.sleep(1)
        try:
            element = driver.find_element(by, selector)
            if element:
                return True
               
        except NoSuchElementException:
            pass
    return False

def special_print(text, color):
    color_code = color_mapping.get(color.upper(), color_mapping['RESET'])
    print(f"{color_code}{text}{color_mapping['RESET']}")


def send_status(token, data = None):
    try:
        global getApiCredentials,api_creds,b64encode,b64decode,get_statuses,API_URL_BASE,endpoints
        bot_data:dict = api_creds.getApiCredentials(data['bot'],data['clinic'],b64encode(token.encode()).decode())
        assert 'id' in bot_data.keys()
        status_text_map:dict = {1: 'Active', 2: '2FA', 3: 'Security Question',4: 'Locked', 5: 'Bad Credentials',6: 'Could not verify'}       
        default_status:str = 'Disabled'
        txt:str = status_text_map.get(data['status'], default_status)

        status:list = [sts['_id'] for sts in get_statuses(token) if txt in sts['description']]
        assert status and len(status) > 0
        url:str = API_URL_BASE + endpoints.BOTSTATUS + bot_data['id']
        #print('url:',url )
        data:dict = {'status':status[0]}
        #print("data:",data)
        request = requests.put(url,json=data,headers= {'x-access-token':token})
        if txt == 'Active':
            special_print(f"Credentials status updated to {txt} in CCC... API RESPONSE: {request.status_code}, {request.reason}, {request.text if len(request.text) < 50 or request.text.endswith('.') else ''}\n",'GREEN_BG')
        elif txt == '2FA' or txt == 'Locked':
            special_print(f"Credentials status updated to {txt} in CCC... API RESPONSE: {request.status_code}, {request.reason}, {request.text if len(request.text) < 50 or request.text.endswith('.') else ''}\n",'RED_BG')
        else:
            print(f"Credentials status updated to {txt} in CCC... API RESPONSE: {request.status_code}, {request.reason}, {request.text if len(request.text) < 50 or request.text.endswith('.') else ''}\n")


        return request
    
    except Exception as ex:
        print(ex.__traceback__.tb_lineno, ex)

def get_statuses(token):
    request = requests.get(API_URL_BASE + endpoints.BOTSTATUSES, headers={'x-access-token': token})
    return request.json() if request.status_code == 200 else []


def init_contexts():
    global rem
    global api_connection,ApiConnection
    carriers_token = GetVar('carriers_token')
    carriers_token = carriers_token if carriers_token != 'ERROR_NOT_VAR' else None
    rem.init_context()
    api_connection = ApiConnection(carriers_token, rem)

def get_carriers_per_client():
    global get_vars,OfficeClient,ApiResponse,ApiConnection,get_config,get_info,api_connection,init_contexts
    practice_name:str = get_vars('practice')
    client_id:str = rem.get_data('clinicId')
    if not client_id:
        iv_config = get_config(rem.get_data('base_pathP'))
        client_response:ApiResponse = api_connection.get_client_by_name(
            get_info(iv_config,'project_name')
        )
        if client_response.status_code != 200:
            print_log(ERROR,'Error getting client id')
            return None
        client_id = get_info(client_response.data,'_id', def_value=None)
        rem.set_data('client_id', client_id)
    if not client_id: alt.start('Error getting client id',type='error')
    practice_response:ApiResponse = api_connection.get_info_office_client(
        client_id, 
        practice_name
    )
    if practice_response.status_code != 200:
        print_log(ERROR,'Error getting practice id')
        return None
    return OfficeClient(practice_response.data)



def get_bots_credentials_ccc(bot_name:str):
    global api_creds
    clinic_id:str = GetVar("clinicId")
    token:str = GetVar("carriers_token")

    api_clinic: dict = api_creds.getApiCredentials(bot_name,clinic_id,token)
    
    password:str = api_clinic['password']
    username:str = api_clinic['username']
    return [username,password]


def initialize_browser()-> webdriver2.Chrome or None:
    global driver,webdriver2,time,open_url,send_status,clinic_id,token,get_statuses,wait_for_dashboard
    try:
        # Path to store the browser profile
        profile_path:str = os.path.normpath(r"C:\DentalRobot\Projects\IVF\nav_profile")
        
        # Chrome browser options configuration
        chrome_options = webdriver2.ChromeOptions()
        chrome_options.add_argument('--start-maximized')  # Maximize the browser window
        chrome_options.add_argument('--user-data-dir=' + profile_path)  # Path to browser profile
        time.sleep(2)
        
        # Path to the Chrome driver executable
        chrome_driver = os.path.join(
            os.path.abspath(os.getcwd()), 
            os.path.normpath(r"drivers\win\chrome"), 
            "chromedriver.exe"
        )
        
        # Initialize the Chrome browser
        driver = webdriver2.Chrome(executable_path=chrome_driver, options=chrome_options)
        
        return driver
    
    
    except Exception as e:
        print(f"Error initializing browser: {str(e)}")
        return None

def open_url(driver, url):
    try:
        # Open the provided URL in the browser
        driver.get(url)
    except Exception as e:
        print(f"Error opening URL: {str(e)}")

def exists(driver, by, search)-> bool:
    from selenium.common.exceptions import NoSuchElementException
    try:
        wait = WebDriverWait(driver,5)
        wait.until(EC.presence_of_element_located((by, search)))
        return True
    except NoSuchElementException:
        return False

 
def skygen_login():
    bot_name:str = "Skygen"
    driver = initialize_browser()
    credentials:dict = get_bots_credentials_ccc(bot_name)
    url:str = 'https://app.dentalhub.com/app/login'

    if driver:
        open_url(driver, url)
        try:
            time.sleep(2)
            wait = WebDriverWait(driver, 20)
            login_button = wait.until(EC.presence_of_element_located((By.ID, "btnOidcLogin")))
            login_button.click()

            time.sleep(2)
            email = wait.until(EC.presence_of_element_located((By.ID, "signInName")))
            email.click()
            email.send_keys(credentials[0])  # Username

            password = wait.until(EC.presence_of_element_located((By.ID, "password")))
            password.click()
            password.send_keys(credentials[1])  # Password

            signin_button = wait.until(EC.element_to_be_clickable((By.ID, "next")))
            signin_button.click()

            try:
                dashboard = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.navbar-button')))
                special_print('Active', 'GREEN')
                send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 1})
            except TimeoutException:
                email_radio_button = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, "extension_mfaByPhoneOrEmail_email")))
                if email_radio_button.is_displayed():
                    email_radio_button.click()
                    special_print('2FA required', 'YELLOW')
                    input_element = wait.until(EC.element_to_be_clickable((By.ID, "continue")))
                    input_element.click()

                    send_button = wait.until(EC.element_to_be_clickable((By.ID, "readOnlyEmail_ver_but_send")))
                    send_button.click()
                  
                    dashboard = wait_for_dashboard(driver,By.CSS_SELECTOR,'div.navbar-button')
                    if dashboard:
                        special_print('Active', 'GREEN')
                        send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 1})
                    else:
                        special_print('2FA unsuccessful', 'RED')
                        send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 2})


                
        except TimeoutException:
            special_print('2FA unsuccessful', 'RED')
            send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 2})
        except NoSuchWindowException:
            special_print('2FA unsuccessful', 'RED')
            send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 2})
        except Exception as e:
            special_print(f"Error during 2FA: {str(e)}", 'RED')
            traceback.print_exc()


def lincoln_financial_login():
    bot_name:str = "Lincoln Financial"
    driver = initialize_browser()
    url:str = 'https://provider.mylincolnportal.com/dental/login'
    credentials:dict = get_bots_credentials_ccc(bot_name)

    if driver:
        open_url(driver, url)
        try:

            try:
                accept_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "truste-consent-button")))
                accept_button.click()
            except TimeoutException:
                pass 

            wait = WebDriverWait(driver, 10)

            input_element = wait.until(EC.presence_of_element_located((By.ID, "email")))
            input_element.click()
            input_element.send_keys(credentials[0])  # Username

            time.sleep(3)
            password_input = driver.find_element_by_id("password")
            password_input.click()
            password_input.send_keys(credentials[1])  # Password

            time.sleep(3)
            element = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="root"]/div/div/div[3]/div/div[2]/div/div/div/div/div[1]/div/div/form/div/button')))
            element.click()

            try:
                dashboard = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[aria-label="Header Menu"]')))
                special_print("Active", 'GREEN')
                send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 1})

            except TimeoutException:
                two_step = wait.until(EC.presence_of_element_located((By.ID, 'code')))
                special_print('2FA required', 'YELLOW')
                
                if two_step:
                    remember_checkbox = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CLASS_NAME, "c5732b6df")))    
                    remember_checkbox.click()
                    try:
                        dashboard = wait_for_dashboard(driver,By.CSS_SELECTOR,'[aria-label="Header Menu"]')
                        if dashboard:
                            special_print("Active", 'GREEN')
                            send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 1})
                        else:
                            special_print(f'Dashboard not found after {max_wait_time} seconds', 'RED')
                            special_print('2FA unsuccessful', 'RED')
                            send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 2})
                                
                    except NoSuchElementException:
                        special_print('2FA unsuccessful', 'RED')
                        send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 2})
                           
                           
           
        except NoSuchWindowException:
            special_print('2FA unsuccessful', 'RED')
            send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 2})
        except Exception as e:
            special_print(f"Error during 2FA: {str(e)}", 'RED')
            traceback.print_exc()

                

def ameritas_login():
    bot_name:str = "Ameritas"
    driver = initialize_browser()
    credentials:dict = get_bots_credentials_ccc(bot_name)

    url:str = 'https://www.ameritas.com/employee-benefits/'
    url2:str = "https://www.ameritas.com/applications/group/provider"
    

    if driver:
           
            open_url(driver, url2)
            wait = WebDriverWait(driver, 10)
            try:            
        
                user_input = wait.until(EC.presence_of_element_located((By.ID,"ontUser")))
                user_input.click()
                user_input.send_keys(credentials[0])#Username
                
                password_input = wait.until(EC.presence_of_element_located((By.ID,"ontPassword")))
                password_input.click()
                password_input.send_keys(credentials[1])#Password
                
                sign_in = wait.until(EC.presence_of_element_located((By.ID,"Submit")))
                sign_in.click()
                
                try:
                    dashboard = wait.until(EC.visibility_of_element_located((By.XPATH, "//span[text()='Sign Out']")))
                    if dashboard:
                        special_print("Active", 'GREEN')
                        send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 1})
                except TimeoutException:
                    try:
                        two_step = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@type="checkbox"][@class="CheckBox CheckBox-outline"]')))
                        if two_step:
                            special_print('2FA required', 'YELLOW')
                            two_step.click()
                            try:
                                dashboard = wait_for_dashboard(driver,By.XPATH, "//span[text()='Sign Out']")
                                if dashboard:
                                    special_print("Active", 'GREEN')
                                    send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 1})
                                else:
                                    special_print(f'Dashboard not found after {max_wait_time} seconds', 'RED')
                                    special_print('2FA unsuccessful', 'RED')
                                    send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 2})
                            
                            except TimeoutException:
                                special_print('2FA unsuccessful', 'RED')
                                send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 2})  
                                
                    except TimeoutException:
                        special_print('2FA unsuccessful', 'RED')
                        send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 2})                            

            except NoSuchWindowException:
                special_print('2FA unsuccessful', 'RED')
                send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 2})
            except Exception as e:
                special_print(f"Error during 2FA: {str(e)}", 'RED')
                traceback.print_exc()
                    


def united_health_care_login():
    bot_name:str = "United HealthCare"
    driver = initialize_browser()
    credentials:dict = get_bots_credentials_ccc(bot_name)
    url:str = 'https://identity.onehealthcareid.com/oneapp/index.html#/login'
    wait:int = WebDriverWait(driver,10)

    if driver:
            open_url(driver, url)
            try:        
        
                
                input_element = wait.until(EC.presence_of_element_located((By.ID,"username")))
                input_element.click()
                input_element.send_keys(credentials[0])#Username
                input_element = wait.until(EC.presence_of_element_located((By.ID,"btnLogin")))
                input_element.click()
                
             
                input_element = wait.until(EC.presence_of_element_located((By.ID,"login-pwd")))
                input_element.click()
                input_element.send_keys(credentials[1])#Password
        
                input_element = wait.until(EC.presence_of_element_located((By.ID,"btnLogin")))
                input_element.click()

                try:
                    dashboard = exists(driver,By.ID, "icon-userfullname-arrow-down")
                    if dashboard:
                        special_print("Active", 'GREEN')
                        send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 1})
                except TimeoutException:
                    try:
                        bad_credentials = exists(driver,By.XPATH, "//span[@class='error-msg'][@data-cy='data-loginerrorsummary-error']")
                        if bad_credentials:
                            special_print("Bad Credentials", 'YELLOW')
                            send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 5})
                    except TimeoutException:
                        try:
                            locked = exists(driver, By.XPATH, "//h1[@id='page-title'][@data-cy='data-page-title-field'][@tabindex='-1'][@aria-live='assertive']")
                            if locked:
                                special_print("Locked", 'RED')
                                send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 4})
                        except TimeoutException:
                            special_print('2FA required', 'YELLOW')
                            try:
                                dashboard = wait_for_dashboard(driver,By.ID, "icon-userfullname-arrow-down")
                                if dashboard:
                                    special_print("Active", 'GREEN')
                                    send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 1})
                            
                                else:
                                    special_print(f'Dashboard not found after {max_wait_time} seconds', 'RED')
                                    special_print('2FA unsuccessful', 'RED')
                                    send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 2}) 
                                
                            except NoSuchElementException:
                                special_print('2FA unsuccessful', 'RED')
                                send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 2})
                                                       

                    
            except NoSuchWindowException:
                special_print('2FA unsuccessful', 'RED')
                send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 2})
            except Exception as e:
                special_print(f"Error during 2FA: {str(e)}", 'RED')
                traceback.print_exc()
               

def new_health_choice():
    united_health_care_login()


def cigna_login():
    bot_name:str = "Cigna API"
    driver = initialize_browser()
    credentials:dict = get_bots_credentials_ccc(bot_name)
    url:str = 'https://cignaforhcp.cigna.com/app/login'

    if driver:
        open_url(driver, url)
        try:
            wait = WebDriverWait(driver, 10)
            username_input = wait.until(EC.presence_of_element_located((By.ID, 'username')))
            username_input.click()
            username_input.send_keys(credentials[0])

            password_input = wait.until(EC.presence_of_element_located((By.ID, 'password')))
            password_input.click()
            password_input.send_keys(credentials[1])

            login_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[value='Login']")))
            login_button.click()

            time.sleep(10)
            currentUrl = driver.current_url
            time.sleep(5)
            print(currentUrl)
            if 'dashboard' in currentUrl:
                special_print('Active', 'GREEN')
                send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 1})
            elif 'verify-code' in currentUrl:
                special_print('2FA required', 'YELLOW')
                
                radio_button = WebDriverWait(driver,2).until(EC.element_to_be_clickable((By.XPATH, "/html/body/cigna-root/cigna-layout-wrapper/cigna-layout-public/main/cigna-wrapper-code/div/cigna-verify-code/form/div[4]/label/i")))
                radio_button.click()
                
                for _ in range(max_wait_time):
                    time.sleep(1)
                    currentUrl = driver.current_url
                    try:
                        if 'dashboard' in currentUrl:
                            special_print('Active', 'GREEN')
                            send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 1})
                            break
                    except Exception as e:
                        special_print(f"Error during 2FA: {str(e)}", 'RED')
                else:
                    special_print('2FA unsuccessful', 'RED')
                    send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 2})
                    
            elif 'loginerror' in currentUrl:
                special_print('Bad credentials', 'YELLOW')
                send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 5})

        except NoSuchWindowException:
            special_print('2FA unsuccessful', 'RED')
            send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 2})

        except Exception as e:
            special_print(f"Error during 2FA: {str(e)}", 'RED')
            traceback.print_exc()


      
      
def availity_login():
    bot_name:str = "Humana Availity"
    driver = initialize_browser()
    credentials:dict = get_bots_credentials_ccc(bot_name)
    url:str = 'https://apps.availity.com/public/apps/home/#!/'
    wait:int = WebDriverWait(driver,10)
    if driver:
            open_url(driver, url)
            try:
                
                log_in_to_availity_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#av-modal-id001 > div > div > timer-modal > div.modal-footer > a'))).click()
                user = wait.until(EC.presence_of_element_located((By.ID, 'userId'))).send_keys(credentials[0])
                password =  wait.until(EC.presence_of_element_located((By.ID, 'password'))).send_keys(credentials[1])
                login_subtmit_button = wait.until(EC.presence_of_element_located((By.ID, "loginFormSubmit"))).click()
                dashboard = None
                time.sleep(7)
                currentUrl = driver.current_url
                
                try:
                    dashboard = exists(driver, By.CSS_SELECTOR, "a[title='Logout']") 
                    print('Active')
                    send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 1})
                except NoSuchElementException:
                    if 'two-step-authentication' in currentUrl: 
                        print('2FA required')
                        try:
                            dashboard = wait_for_dashboard(driver,By.CSS_SELECTOR,"a[title='Logout']")
                            if dashboard:
                                    special_print('Active', 'GREEN')
                                    send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 1})
                            else:
                                special_print(f'Dashboard not found after {max_wait_time} seconds', 'RED')
                                special_print('2FA unsuccessful', 'RED')
                                send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 2})                        
                                        
                        except NoSuchElementException:
                            special_print('2FA unsuccessful', 'RED')
                            send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 2})
                    

                    elif exists(driver, By.CSS_SELECTOR, '#the_feedback > ul > li > span > a'): 
                        print('Bad credentials')
                        send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 5})
            except Exception as e:
                special_print(f"Error during 2FA: {str(e)}", 'RED')
                traceback.print_exc()
                


def guardian_login():
    bot_name:str = "Guardian"
    driver = initialize_browser()
    credentials:dict = get_bots_credentials_ccc(bot_name)
    url:str = 'https://signin.guardianlife.com/signin' 
    wait:int = WebDriverWait(driver, 10)
    
    
    if driver:
        open_url(driver, url)
        try:
            username = wait.until(EC.presence_of_element_located((By.ID, 'username'))).send_keys(credentials[0])  # Username
            signin_button = wait.until(EC.presence_of_element_located((By.ID, "signin-button"))).click()
            
            password = wait.until(EC.presence_of_element_located((By.ID, 'current-password'))).send_keys(credentials[1])  # Password
            
            signin_button = wait.until(EC.presence_of_element_located((By.ID, "signin-button"))).click()

            time.sleep(10)
            try:
                dashboard = exists(driver, By.CSS_SELECTOR, ".icon-profile-use")
                if dashboard: 
                    print('Active')
                    send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 1})
            except TimeoutException:
                two_step = exists(driver, By.ID, 'mfaChallengeButton')
                if two_step:
                    special_print('2FA required', 'YELLOW')
                    
                    dashboard = wait_for_dashboard(driver,By.CSS_SELECTOR, ".icon-profile-use")
                    if dashboard:
                        special_print("Active", 'GREEN')
                        send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 1})

                    else:
                        special_print(f'Dashboard not found after {max_wait_time} seconds', 'RED')
                        special_print('2FA unsuccessful', 'RED')
                        send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 2})

            except TimeoutException:
                bad_credentials = exists(driver, By.CSS_SELECTOR, '.login-error-message')
                if bad_credentials:
                    print('Bad credentials','YELLOW')
                    send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 5})
        except Exception as e:
            special_print(f"Error during 2FA: {str(e)}", 'RED')
            traceback.print_exc()
    

                    


def sun_life_login():
   
    bot_name:str = "Sunlife"
    driver = initialize_browser()
    credentials:dict = get_bots_credentials_ccc(bot_name)
    wait:int = WebDriverWait(driver,10)
    url:str = 'https://login.sunlifeconnect.com/commonlogin/#/login/10'
    dashboard = None
    if driver:
            open_url(driver, url)
            try:              
                username = wait.until(EC.presence_of_element_located((By.ID, 'USERNAME'))).send_keys(credentials[0])
                password = wait.until(EC.presence_of_element_located((By.ID, 'PASSWORD'))).send_keys(credentials[1])
                submit_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[type='submit']"))).click()

                wait = WebDriverWait(driver, 20)
                element = None
                try:
                    element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-p-rmsg='Member ID or SSN required']")))
                    if element: 
                        print('Active')
                        send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 1})
                except TimeoutException:
                    try:             
                                
                        two_step = exists(driver, By.ID, 'input39')
                        if two_step:
                            special_print('2FA required', 'YELLOW') 
                            dashboard = wait_for_dashboard(driver, By.CSS_SELECTOR, ".icon-profile-use")
                            if dashboard:
                                special_print("Active", 'GREEN')
                                send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 1})
                               
                            else:
                                special_print(f'Dashboard not found after {max_wait_time} seconds', 'RED')
                                special_print('2FA unsuccessful', 'RED')
                                send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 2})


                    except TimeoutException:
                        bad_credentials = exists(driver, By.ID, 'ERROR_HTML_invalidUserNamePassword')
                        if bad_credentials:
                            special_print('Bad credentials','YELLOW')
                            send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 5})
                                 
                    
            except NoSuchWindowException:
                special_print('2FA unsuccessful', 'RED')
                send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 2})
            except Exception as e:
                special_print(f"Error: {str(e)}", 'RED')
                traceback.print_exc()


def fep_dental_blue_login():
    bot_name:str = "FEP Dental Blue"
    driver = initialize_browser()
    credentials:dict = get_bots_credentials_ccc(bot_name)
    wait:int = WebDriverWait(driver,10)
    url:str = 'https://www.bcbsfepdental.com/'
    dashboard = None
    if driver:
        open_url(driver, url)
        try:

            try:
                accept_button = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "btn--primary")))
                accept_button.click()
            except TimeoutException:
                pass
            except: pass

            provider_login = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/header/div[2]/div/div[1]/div/div[2]/div/div[2]/a"))).click()

            # Switch the focus of Selenium to the new tab (secondary window)
            driver.switch_to.window(driver.window_handles[1])

            try:
                continue_button = wait.until(EC.element_to_be_clickable((By.NAME, "continueImg"))).click()
            except TimeoutException:
                pass

            username_input = WebDriverWait(driver,5).until(EC.presence_of_element_located((By.NAME, "username")))
            username_input.send_keys(credentials[0])

            password_input = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="password"]')))
            password_input.send_keys(credentials[1])

            submit_button = wait.until(EC.element_to_be_clickable((By.ID, "submit_button"))).click()

            try:
                dashboard = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="header-menu-id"]/a')))
                if dashboard:
                    special_print("Active", 'GREEN')
                    send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 1})
            
            except TimeoutException:
                try:
                    locked = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="pwchangeform"]/div/center/table/tbody/tr/td/table/tbody/tr[4]/td/font/font')))
                    if locked:
                        special_print('Locked', 'RED')
                        send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 4})

                except TimeoutException:
                    try:     
                        two_step = WebDriverWait(driver,5).until(EC.element_to_be_clickable((By.ID, "EMAIL")))
                        if two_step:
                            special_print('2FA required', 'YELLOW')
                            dashboard = wait_for_dashboard(driver,By.XPATH, '//*[@id="header-menu-id"]/a')
                            if dashboard:
                                special_print("Active", 'GREEN')
                                send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 1})
                            else:
                                special_print(f'Dashboard not found after {max_wait_time} seconds', 'RED')
                                special_print('2FA unsuccessful', 'RED')
                                send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 2})                           

                    except TimeoutException:
                        special_print('2FA unsuccessful', 'RED')
                        send_status(token, data={'bot': bot_name, 'clinic': clinic_id, 'status': 2})

                   
                              
        except Exception as e:
            special_print(f"Error: {str(e)}", 'RED')
            traceback.print_exc()

def always_assist_login():
    bot_name:str = "Always Assist"
    driver = initialize_browser()
    credentials:dict = get_bots_credentials_ccc(bot_name)
    url:str = 'https://unumdentalpwp.skygenusasystems.com/Account/Login'
    wait = WebDriverWait(driver,10)

    if driver:
        open_url(driver, url)
        try:
            
            username_input = wait.until(EC.presence_of_element_located((By.ID, 'userNameTextBox')))
            username_input.send_keys(credentials[0])
            password_input = wait.until(EC.presence_of_element_located((By.ID,'passwordTextBox')))
            password_input.send_keys(credentials[1])
            
            login_button = wait.until(EC.presence_of_element_located((By.ID,'failed_login_submit_btn')))
            login_button.click()
           

                
        
        except Exception as e:
            special_print(f"Error during 2FA: {str(e)}", 'RED')
            traceback.print_exc()

    
 

def main():
    global driver,get_carriers_per_client,init_contexts,initialize_browser,get_bots_credentials_ccc

    init_contexts()
    office:dict = get_carriers_per_client()
    #print(dir(office))
    special_print(f'Office Name: {office.office_name}','BOLD')
    special_print(f'Office ID: {office.office_id}','BOLD')
   

    #names_bots_2fa = []
    #names_bots_2fa = ['FEP Dental Blue']
    #names_bots_2fa = ['Lincoln Financial']
    #names_bots_2fa = ['Skygen']
    #names_bots_2fa = ['Ameritas']
    #names_bots_2fa = ['Sunlife']
    #names_bots_2fa = ['Humana Availity']
    #names_bots_2fa = ['Cigna API']
    names_bots_2fa = ['Always Assist']

   


    '''for bot in office.bots:
            bot_info = vars(bot)
            status = bot_info.get('status')
            if status and status[0] == '63779e5529096ea72ab23c5b' and status[1] == '2FA':
                name = bot_info.get('name')
                if name:
                    names_bots_2fa.append(name)'''

    
    custom_sort= ["Skygen", "Cigna API"]
    names_bots_2fa.sort(key=lambda x: custom_sort.index(x) if x in custom_sort else len(custom_sort))


    special_print("Bots with '2FA' status:","MAGENTA_BG")
    special_print(f'{names_bots_2fa}',"CYAN")
    

    



    for idx,bot_name in enumerate(names_bots_2fa):
        
        if idx != 0:

            time.sleep(5)
            print(f"Press Enter to start the next login process...")
            if driver:
                driver.quit() 

        if bot_name == "Skygen":
            skygen_login()
        elif bot_name == "Lincoln Financial":
            lincoln_financial_login()
        elif bot_name == "Ameritas":
            ameritas_login()
        elif bot_name == "United HealthCare":
            united_health_care_login()
        elif bot_name == "Cigna API":
            cigna_login()
        elif bot_name == "Humana Availity":
            availity_login()
        elif bot_name == "Guardian":
            guardian_login()
        elif bot_name == "Sunlife":
            sun_life_login()
        elif bot_name == "New Health Choice":
            new_health_choice()
        elif bot_name == "FEP Dental Blue":
            fep_dental_blue_login()
        elif bot_name == "Always Assist":
            always_assist_login()
    
        else:
            special_print(f"Login for {bot_name} not developed.",'YELLOW_BG')


    if driver:
        print("All logins completed.")
        time.sleep(5)
        driver.quit()
        print("Session closed.")
        '''user_input = input("Do you want to quit the session? (y/n): ")
        if user_input.lower() == "y":
            driver.quit()
            print("Session closed.")
        else:
            print("Session not closed.")'''
      

main()
  