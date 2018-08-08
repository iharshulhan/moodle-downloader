# Automatic Moodle course files Downloader

The `moodle.py` script downloads all the files posted in the course page of all the courses in your moodle page. Files with the same name in a course are not downloaded and are ignored.

Set the following in the file `config.ini` before running the script

- `username` : LDAP Username
- `password` : LDAP Password
- `url` : URL for moodle authentication

All the files are stored in their respective directories inside the `courses` directory with the names as in moodle.

`Cannot connect to moodle` : Authentication failure.


#### REQUIREMENTS

- Python 3
- Beautifulsoup - `pip install beautifulsoup4`
