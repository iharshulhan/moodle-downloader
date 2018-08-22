"""
Automatic Moodle course files downloader
"""
from configparser import ConfigParser
from multiprocessing import Pool
from multiprocessing.pool import ThreadPool
import requests
import os
import os.path
import re

from urllib.parse import unquote
from bs4 import BeautifulSoup

NUM_OF_THREADS = 15
thread_pool = None

NUM_OF_PROCESSES = 10
process_pool = None

PRINT_MESSAGES_TO_CONSOLE = True


def log(message: str):
    """
    Print a message to console if PRINT_MESSAGES_TO_CONSOLE is set to True
    :param message: the message to be printed
    :return: Nothing
    """
    if PRINT_MESSAGES_TO_CONSOLE:
        print(message)


def execute_function_in_parallel(func, list_args, processes=False,
                                 local_pool=False, num_threads=NUM_OF_THREADS,
                                 num_processes=NUM_OF_PROCESSES):
    """
    Execute a function in parallel using ThreadPool or ProcessPool
    :param local_pool: create a new pool of threads/processes
    :param num_processes: a num of processes to create
    :param num_threads: a num of threads to create
    :param processes: execute tasks in separate processes
    :param func: a func to call
    :param list_args: an array containing calling params
    :return: an array with results
    """
    if not (func and list_args):
        return []

    if local_pool:
        pool = ThreadPool(num_threads) if not processes else Pool(num_processes)
    else:
        global process_pool
        if processes:
            if not process_pool:
                process_pool = Pool(NUM_OF_PROCESSES)
            pool = process_pool
        else:
            global thread_pool
            if not thread_pool:
                thread_pool = ThreadPool(NUM_OF_THREADS)
            pool = thread_pool
    results_tmp = pool.starmap_async(func, list_args)
    results = [result for result in results_tmp.get() if result is not None]
    if local_pool:
        pool.close()
    return results


# Get credentials from config file
conf = ConfigParser()
project_dir = os.path.dirname(os.path.abspath(__file__))
conf.read(os.path.join(project_dir, 'config.ini'))

username = conf.get("auth", "username")
password = conf.get("auth", "password")
authentication_url = conf.get("auth", "url").strip('\'"')

# Create session for requests
session = requests.Session()

# Input parameters we are going to send
payload = {
    'username': username,
    'password': password
}

# Authenticate
response = session.post(authentication_url, data=payload)
contents = response.text

# Verify the contents
if 'My courses' not in contents:
    raise Exception(f'Cannot connect to Moodle.')

courses = contents.split('<span tabindex="0">My courses</span>')[1]

regex = re.compile('<li class="type_course depth_3 collapsed contains_branch" aria-expanded="false">(.*?)</li>')
course_list = regex.findall(courses)
courses = []

for course_string in course_list:
    soup = BeautifulSoup(course_string, 'lxml')
    a = soup.find('a')
    course_name = a.text
    course_link = a.get('href')
    courses.append([course_name, course_link])

dirname = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'courses')
if not os.path.isdir(dirname):
    os.mkdir(dirname)


def get_valid_filename(s):
    s = str(s).strip().replace(' ', '_')
    return re.sub(r'(?u)[^-\w.]', '', s)


def check_course(course):
    # Create a directory for course
    course_dirname = os.path.join(dirname, get_valid_filename(course[0]))
    if not os.path.isdir(course_dirname):
        os.mkdir(course_dirname)

    course_page = session.get(course[1])
    scrap = course_page.text

    soup = BeautifulSoup(scrap, 'lxml')
    topics = soup.find(class_='course-content').find_all(class_='section main clearfix')

    course_links = []
    for topic in topics:
        links = topic.find_all('a')
        if links:
            course_links.extend(links)

    def download_file(link):
        href = link.get('href')

        # Checking only resources... Ignoring forum and folders, etc
        if 'resource' in href:
            log(f'Downloading {href}')
            try:
                webFile = session.get(href, timeout=20)
                webFile.raise_for_status()
            except Exception as e:
                log(f'Could not download link {href}. Error {e}')
                return None

            url = webFile.url

            file_name = get_valid_filename(unquote(url.split('/')[-1].split('?')[0]))
            file_loc = os.path.join(course_dirname, file_name)
            if os.path.isfile(file_loc):
                log(f'File found : {file_name}')
                return

            log(f'Creating file : {file_name}')
            pdfFile = open(file_loc, 'wb')
            for chunk in webFile.iter_content(chunk_size=512 * 1024):
                if chunk:  # filter out keep-alive new chunks
                    pdfFile.write(chunk)
            pdfFile.close()

    execute_function_in_parallel(download_file, [(link,) for link in course_links], local_pool=True, num_threads=10)


execute_function_in_parallel(check_course, [(course,) for course in courses], local_pool=True, num_threads=10)
log('Finished')
