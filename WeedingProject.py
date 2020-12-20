import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException,StaleElementReferenceException,WebDriverException
from datetime import datetime, timedelta
from time import time
from re import sub

now = datetime.now()
month = now.month
year = now.year
present_code = now.year*12 + month

worldcat_base = "https://hpu.on.worldcat.org/atoztitles/journals?issn="
ulrich_base = "https://ulrichsweb.serialssolutions.com/"
librarian_url = 'https://www.hpu.edu/libraries/about/subject-specialists.html'

bad_subject_words = ["And","Study","Studies","Program","Programs","Change","General","Science","Sciences"]
delimiter = ";"
    
def add_range(array,a):#Assuming a[0] >= b[0]
    
    is_change = False
    if a != None:
        is_add = False#Is it within any ranges
        remove_element = False
        for i in range(len(array)):
            b = array[i]
            if is_change:
                if a[1] <= b[0]:
                    if a[1] < b[1]:
                        a[1] = b[1]
                    b = None
                    remove_element = True
                else:
                    break
            elif a[0] - b[1] <= 1:#a[0] may be one month after b[1] or anytime earlier
                is_add = True
                if a[1] > b[1]:#a in not completely within b
                    b[1] = a[1]
                    is_change = True
        if not is_add:
            array.append(a)
            is_change = True
        if remove_element:
            final_array = []
            for i in array:
                if i != None:
                    final_array.append(i)
            array = final_array
    return array,is_change

def convert_date(date,index = 0):
    if date == "present":
        return present_code
    elif "daysago" in date:
        d = datetime.today() - timedelta(days=int(date.replace("daysago","")))
        return d.year*12 + d.month
    elif "monthsago" in date:
        return present_code - int(date.replace("monthsago",""))
    elif "yearago" in date:
        return present_code - 12
    elif "yearsago" in date:
        return present_code - int(date.replace("yearsago",""))*12
    sep = date.split("-")
    return int(sep[0])*12 + (index*11 + 1 if len(sep) == 1 else int(sep[1]))

def convert_range(s):
    if s[0] == "~":
        return 100000 * convert_date(s.replace("~","")) + present_code

    dates = s.split(";")[0].split("~")
    return 100000 * convert_date(dates[0]) + convert_date(dates[1],1)

def get_ranges(panel,section_class_name,row_class_name,collection_class_name,is_print):
    ranges = []
    collection_string = ""

    this_panel = panel.find('div', attrs={'class': section_class_name})
    if this_panel != None:

        coverages = []
        collections = []
        for row in this_panel.find_all(class_ = row_class_name):
            for collection_section in row.find_all(class_ = collection_class_name):
                collection = collection_section.contents[0].replace("  ","").replace("\n","")
                if not is_print or "Microfiche" in collection:
                    collections.append(collection)
                    coverage = row.find('li')
                    if coverage != None:
                        coverages.append(convert_range(coverage.contents[0].replace(" ", "").replace("\n","")))
        coverages.sort()
        
        for i in range(len(coverages)):
            coverage = str(coverages[i])
            ranges,add_collection = add_range(ranges,[int(coverage[:5]),int(coverage[5:])])
            if add_collection and i < len(collections):
                collection_string += collections[i] + "|"
    return ranges,collection_string if len(collection_string) > 0 else "None"

def get_overlap(r1,r2):
    overlap = []
    for a in r1:
        for b in r2:
            #print(display_range(a) + " + " + display_range(b))
            if a[0] >= b[0] and a[0] <= b[1]:
                if a[1] >= b[0] and a[1] <= b[1]:
                    overlap.append(a)
                else:
                    overlap.append([a[0],b[1]])
            elif a[0] < b[0] and a[1] >= b[0]:
                if a[1] >= b[0] and a[1] <= b[1]:
                    overlap.append([b[0],a[1]])
                else:
                    overlap.append(b)
    return overlap

def decode_date(date):
    month = date % 12
    if month == 0:
        month = 12
    return int((date - month)/12),month

def display_range(r):
    y1,m1 = decode_date(r[0])
    y2,m2 = decode_date(r[1])
    if year == y2:
        return "from " + str(y1)
    return str(y1) + "-" + str(y2)

def display_ranges(r):
    if len(r) == 0:
        return "None"
    line = display_range(r[0])
    for i in range(1,len(r)):
        line += " " + display_range(r[i])
    return line

def click_driver(driver,button_field,button_field_type,button_xpath,next_field,next_field_type):
    WebDriverWait(driver,10).until(EC.presence_of_element_located((By.XPATH,button_xpath)))
    WebDriverWait(driver,10).until(EC.presence_of_element_located((button_field_type,button_field))).click()
    same_page = True
    while same_page:
        try:
            driver.find_element(next_field_type,next_field)
            same_page = False
        except:
            driver.find_element(button_field_type,button_field).click()

def input_driver(driver,field,text,press_enter = True):
    WebDriverWait(driver,10).until(EC.presence_of_element_located((By.NAME,field)))
    search = driver.find_element_by_name(field)
    search.clear()
    search.send_keys(text)
    if press_enter:
        search.send_keys(Keys.RETURN)

def get_driver():
    print("-Loading Search Page-")
    driver = webdriver.Firefox()
    driver.get(ulrich_base)
    if 'Please enter your Institutional Login credentials.' in driver.page_source:
        driver.find_element_by_class_name('loginContainer')
        ulrich_login = "https://login.hpu.idm.oclc.org/login?url=http://www.ulrichsweb.serialssolutions.com/"
        driver.get(ulrich_login)
        input_driver(driver,'user',input("Username: "),False)
        input_driver(driver,'pass',input("Password: "))
        while("The username or password you entered was incorrect. Please try again." in driver.page_source):
            print("-Incorrect username or password-")
            input_driver(driver,'user',input("Username: "),False)
            input_driver(driver,'pass',input("Password: "))
    WebDriverWait(driver,15).until(EC.presence_of_element_located((By.ID,'query')))
    print("-Search Page Loaded-")
    return driver

def get_alphanumeric(s):
    return sub(r'\W+','',s)

def isStale(element):
    try:
        element.location
        return False
    except StaleElementReferenceException:
        return True

def row_contains(row,id):
    try:
        row.find_element_by_id(id)
        return True
    except:
        return False

def get_call_num_row(row):
    items = []
    for item in row.find_element_by_tag_name('td').get_attribute("innerText").replace("  ","").split("\n\n"):
        if len(item) > 0:
            items.append(item)
    return items

def get_subject_librarian(items):
    for item in items:
        for word in item.split(" "):
            word = get_alphanumeric(word).capitalize()
            if word in librarian_dict:
                print("\tLibrarian " + librarian_dict[word] + " for " + word)
                return item,librarian_dict[word]
    print("\tNo Librarian: " + str(items))
    return items[0].title(),None

def get_librarian_info(driver,query):
    try:
        input_driver(driver,'query',query)
        
        try:
            click_driver(driver,'titleDetailsLink',By.CLASS_NAME,'//*[@role="gridcell"]','title_subject',By.ID)
        except TimeoutException:
            if ('Your search returned no results.' in driver.page_source):
                print("\t-Results Not Found-")
                return "No Call #","All"
    
        table =  driver.find_element_by_xpath("//*[@id='subjectClassificationsContainer']/table/tbody")
        while(isStale(table)):
            table =  driver.find_element_by_xpath("//*[@id='subjectClassificationsContainer']/table/tbody")

        subject= None
        lc = None
        librarian = None
        count = 0
        
        for row in table.find_elements_by_tag_name("tr"):
            count += 1
            if row_contains(row,"title_subject"):
                subject,librarian = get_subject_librarian(get_call_num_row(row))
            elif row_contains(row,"title_lc"):
                lc = get_call_num_row(row)[0]
        return subject if lc == None else lc,"All" if librarian == None else librarian
    except WebDriverException:
        print("WebDriverException: Cannot load page. Trying again -Maybe call get_driver()?-")
        return get_librarian_info(driver,query)

def get_librarian_dict():
    librarian_dict = {}
    page = requests.get(librarian_url)
    soup = BeautifulSoup(page.text, 'html.parser')
    for row in soup.find_all('tr'):
        subjects = row.find_next('td')
        for subject in subjects.text.split("/"):
            for word in subject.replace("\n","").split(" "):
                word = get_alphanumeric(word).capitalize()
                if len(word) >= 3 and word not in bad_subject_words:
                    librarian_dict[word] = subjects.find_next('td').text.replace("\n","")
    print('-Loaded Subject Specialists-')
    return librarian_dict

run_all = True
run_count = 5
start_run = 0



open_file = open("Library/Assets/JournalList.txt",'r')
lines = []
all_issn = open_file.readlines()
if not run_all:
    all_issn =  all_issn[start_run:start_run + run_count]

start_time = time()
print("-Received: " + str(len(all_issn)) + " entries-")
print("-Estimate Running Time: " + str(round(len(all_issn)*0.10944)) + " minutes-")
driver = get_driver()
librarian_dict = get_librarian_dict()
for i in range(len(all_issn)):
    issn = all_issn[i].replace("\n","")
    soup = BeautifulSoup(requests.get(worldcat_base + issn).text, 'html.parser')
    for panel in soup.find_all('section', attrs={'class': 'side-panel-sec'}):
        name = panel.find('div', attrs={'class': 'displayTitle hide-for-small'}).text
        print(str(i+1) + ". " + name + " | " + issn)
        print_ranges,print_collection = get_ranges(panel,'hide-for-small contentSection contentSectionWithDivider inTheLibrary','print-info','hide-for-small fulltextItem',True)
        if len(print_ranges) > 0:
            online_ranges,online_collection = get_ranges(panel,'contentSection contentSectionWithDivider viewFullText','fullTextRecord','resource-record collection-link',False)
            weed_ranges = get_overlap(online_ranges,print_ranges)

            call,librarian = get_librarian_info(driver, issn)

            #print("\tOnline Ranges: " + str(online_ranges))
            #print("\tPrint Ranges: " + str(print_ranges))
            print("\tWeed Ranges: " + str(display_ranges(weed_ranges)))
            print("\tCall: " + call)

            # print(call)
            # print(librarian)
            # print(name)
            # print(display_ranges(weed_ranges))
            # print(display_ranges(online_ranges))
            # print(display_ranges(print_ranges))
            # print(collection)
            lines.append((name[4:].lower() if name[:4].lower() == "the " else name.lower(), call + delimiter + librarian + delimiter + name + delimiter + display_ranges(weed_ranges) + delimiter + display_ranges(online_ranges) + delimiter + display_ranges(print_ranges) + delimiter + online_collection + "\n"))
        else:
            print("\t-No microfiche coverage-")
driver.close()
open_file.close()
print("-Saving to File-")
write = "Call #" + delimiter + "Librarian" + delimiter + "TITLE" + delimiter + "WEED ISSUES" + delimiter + "Available Online" + delimiter + "PL Microfiche Holdings" + delimiter + "Online Collection\n"
lines.sort(key=lambda tup: tup[0])
for line in lines:
    write += line[1]
with open("OnlineWeedList.csv", 'w', encoding="utf-8") as saveFile:
    saveFile.write(write)
    saveFile.close()
print("DONE!!")
print("Time Lapsed: " + str(round((time()-start_time)/60,2)) + " minutes")