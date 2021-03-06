# Copyright (c) 2010 Harry Tormey <harry@snaptic.com>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.


'''A python interface to the Snaptic API'''

__author__ = 'harry@snaptic.com'
__version__ = '0.4-devel'

import mimetypes
import base64
import httplib
import os
import simplejson as json
import sys
from urllib import urlencode
import urlparse

def Property(func):
    return property(**func())

class SnapticError(Exception):
  """
  Base class for Snaptic errors.

  The SnaptiError class exposes the following properties::

    snaptic_error.message # read only
    snaptic_error.status # read only
    snaptic_error.response # read only
  """

  @property
  def message(self):
    """Returns the first argument used to construct this error."""
    return self.args[0]

  @property
  def status(self):
    """Returns the HTTP status code used to construct this error."""
    return self.args[1]

  @property
  def response(self):
    """Returns HTTP response body used to construct this error."""
    return self.args[2]

class User(object):
    """
    A class representing the User structure used by the Snaptic API.

     The User class exposes the following properties::
       user.id # read only
       user.user_name # read only
       user.created_at # read only
       user.email # read only
    """

    def __init__(self, id=None, user_name=None, created_at=None, email=None):
        self._id             = id
        self._user_name      = user_name
        self._created_at     = created_at
        self._email          = email

    @property
    def id(self):
        return self._id

    @property
    def user_name(self):
        return self._user_name

    @property
    def created_at(self):
        return self._created_at

    @property
    def email(self):
        return self._email

#Perhaps I should refactor this into a class hierarchy and subclass for image/sound/etc? -htormey
class Image(object):
    """
    A class representing the Image structure which is an attribute of a note retruned via the Snaptic API.

     The Image structure exposes the following properties::

        image.type
        image.md5
        image.id
        image.width
        image.height
        image.src
        image.data
    """

    def __init__(self, type="image", md5=None, id=None, revision_id=None, width=0, height=0, src=None, data=None):
        self.type           = type
        self.md5            = md5
        self.id             = id
        self.revision_id    = revision_id
        self.width          = width
        self.height         = height
        self.src            = src
        self.data           = data

class Note(object):
    """
    A class representing the Note structure used by the Snaptic API.

    The Note structure exposes the following properties::

        note.created_at
        note.modified_at
        note.reminder_at
        note.note_id
        note.text
        note.summary
        note.source
        note.source_url
        note.user
        note.children
        note.media
        note.tags
        note.location
        note.has_media # read only
        note.dictionary # read only
    """

    def __init__(self, created_at, modified_at, reminder_at, note_id, text,
                 summary, source, source_url, user, children, media = [], tags = [], location = []):
        self.created_at   = created_at
        self.modified_at  = modified_at
        self.reminder_at  = reminder_at
        self.note_id      = note_id
        self.text         = text
        self.summary      = summary
        self.source       = source
        self.source_url   = source_url
        self.user         = user
        self.children     = children
        self.media        = media
        self.tags         = tags
        self.location     = location

    @property
    def has_media(self):
        """
        Check to see if Note has any media (images) associated with it.

        Returns:
            True/False
        """
        return len(self.media) > 0

    @property
    def dictionary(self):
        """
        Returns text from the note packaged as a dictionary.

        Returns: 
            A dictionary containing selected attributes from the note.
        """
        #Working on adding dates/location/media and other fields to this dictionary. Right now you can just update text. -htormey
        return dict(text=self.text)

class Api(object):
    """
       Example usage:

           To create an instance of the snaptic.Api class with basic authentication:

               >>> import snaptic
               >>> api = snaptic.Api("username", "password")

           To fetch all users notes and print an attribute:

               >>> [n.created_at for n in api.notes]
               ['2010-03-08T17:49:08.850Z', '2010-03-06T20:02:32.501Z', '2010-03-06T01:35:14.851Z', '2010-03-05T04:13:00.616Z', '2010-03-01T00:09:38.566Z', '2010-02-18T04:09:55.471Z', '2010-02-18T02:26:35.990Z', 
               '2010-02-12T23:28:22.612Z', '2010-02-10T03:06:50.590Z', '2010-02-10T06:02:57.068Z', '2010-02-08T05:14:07.000Z', '2010-02-08T02:28:20.391Z', '2010-02-05T06:57:54.323Z', '2010-02-07T07:26:34.469Z', 
               '2010-01-25T02:11:24.075Z', '2010-01-24T23:37:07.411Z']

           To fetch a subset of a users notes use a cursor. To get the first 20 notes and print an attribute:

               >>> [n.text for n in api.get_notes_from_cursor(-1)]
               ['Harry says snaptic is da bomb #food #ice', 'Harry says snaptic is da bomb #food #ice', 'Harry says snaptic is da bomb', 'Harry says snaptic is da bomb', 'post number 99', 'post number 98', 
               'post number 97', 'post number 96', 'post number 95', 'post number 94', 'post number 93', 'post number 92', 'post number 91', 'post number 90', 'post number 89', 'post number 88', 'post number 87', 
               'post number 86', 'post number 85', 'post number 84']

           To get the next 20 notes use cursor 1 (cursor 0 returns all notes in a users account):

               >>> [n.text for n in api.get_notes_from_cursor(1)]
               ['post number 83', 'post number 82', 'post number 81', 'post number 80', 'post number 79', 'post number 78', 'post number 77', 'post number 76', 'post number 75', 'post number 74', 'post number 73', 
               'post number 72', 'post number 71', post number 70', 'post number 69', 'post number 68', 'post number 67', 'post number 66', 'post number 65', 'post number 64']

           To post a note:

               >>> api.post_note("Harry says snaptic is da bomb")
               {
                "notes":[
                    {
                        "summary":"Harry says snaptic is da bomb",
                        "user": { 
                            "user_name":"harry12",
                            "id":1813083},
                            "created_at":"2010-04-22T04:19:16.543Z",
                            "mode":"private",
                            "modified_at":"2010-04-22T04:19:16.543Z",
                            "reminder_at":null,
                            "id":2276722,
                            "text":"Harry says snaptic is da bomb",
                            "tags":[],
                            "source":"3banana",
                            "location":null,
                            "source_url":"https://snaptic.com/",
                            "children":0
                    }]}

           To delete a note:

               >>> id        = api.notes[1].note_id
               >>> api.delete_note(id)

           To add an image to the above note

               >>> id        = api.notes[1].note_id
               >>> api.load_image_and_add_to_note_with_id("myimage.jpg", id)

           To edit a note:

               >>> n[0].text='Harry says coolio'
               >>> api.edit_note(n[0])

           To download image data from a note:

              >>> api.notes[1].has_media
              True
              >>> id = api.notes[1].note_id
              >>> d = api.get_image_with_id(id)
              >>> filename = "/Users/harrytormey/%s.jpg" % id
              >>> fout = open(filename, "wb")
              >>> fout.write(d)
              >>> fout.close()

           To get a json object of a users tags

             >>> api.get_tags()
             {
             "tags":[
                {
                    "name":"food",
                    "count":"1",
                },
                {
                    "name":"ice",
                    "count":"1",
                },
             ]}
    """

    API_SERVER                  = "api.snaptic.com"
    API_VERSION                 = "v1"
    HTTP_GET                    = "GET"
    HTTP_POST                   = "POST"
    HTTP_DELETE                 = "DELETE"
    API_ENDPOINT_NOTES_JSON     = "/notes.json"
    API_ENDPOINT_TAGS_JSON      = "/tags/tags.json"
    API_ENDPOINT_NOTES          = "/notes/"
    API_ENDPOINT_IMAGES         = "/images/"
    API_ENDPOINT_IMAGES_VIEW    = "/viewImage.action?viewNodeId="
    API_ENDPOINT_USER_JSON      = "/user.json"
    API_ENDPOINT_CURSOR         = "?cursor="

    def __init__(self, username=None, password=None, url=API_SERVER,
                 use_ssl=True, port=443, timeout=10, cookie_epass=None):
        """
        Args:
            username: The username of the snaptic account.
            password: The password of the snaptic account.
            url: The url of the api server which will handle the http(s) API requests.
            use_ssl: Use ssl for basic auth or not.
            port: The port to make http(s) requests on.
            timeout: number of seconds to wait before giving up on a request.
        """
        self._url       = url
        self._use_ssl   = use_ssl
        self._port      = port
        self._timeout   = timeout
        self._user      = None
        self._notes     = None
        self._json      = None
        if cookie_epass:
            self.set_credentials(cookie_epass=cookie_epass)
        else:
            self.set_credentials(username=username, password=password)

    def set_credentials(self, username=None, password=None, cookie_epass=None):
        """
        Set username/password or cookie.

        Args:
            username: 
                snaptic username.
            password: 
                snaptic password.
            cookie_epass:
                snaptic authentication cookie
        """
        if username and password:
            self._username = username
            self._password = password
        elif cookie_epass:
            self._cookie_epass = cookie_epass
        else:
            raise SnapticError("No username/password combination\
                                or cookie authentication provided")

    def load_image_and_add_to_note_with_id(self, filename, id):
        """
        Load image from filename and append to note.

        Args::

            filename: filename of image to load data from.
            id: id of note to which image will be appended.
        """
        try: 
            fin     = open(filename, 'r')
            data    = fin.read()
            self.add_image_to_note_with_id(filename, data, id)
        except IOError:
            raise SnapticError("Error reading filename")

    def add_image_to_note_with_id(self, filename, data, id):
        """
        Add image data to note.

        Args::

            filename: filename of image.
            data: loaded image data to be appended to note.
            id: id of note to which image data will be appended.

        Returns:
            The server's response page.
        """
        page                = "/" + self.API_VERSION + self.API_ENDPOINT_IMAGES + str(id) +".json"
        return self._post_multi_part(self._url, page, [("image", filename, data)])

    def _post_multi_part(self, host, selector, files):
        """
        Post files to an http host as multipart/form-data.

        Args::

            host: server to send request to
            selector: API endpoint to send to the server
            files: sequence of (name, filename, value) elements for data to be uploaded as files

        Returns:
            Return the server's response page.
        """
        content_type, body = self._encode_multi_part_form_data(files)
        handler = httplib.HTTPConnection(host)
        headers = self._get_auth_headers()
        h = {
            'User-Agent': 'INSERT USERAGENTNAME',#Change this to library version? -htormey
            'Content-Type': content_type
            }
        headers.update(h)
        handler.request(self.HTTP_POST, selector, body, headers)
        response = handler.getresponse()
        data     = response.read()
        handler.close()
        if response.status != 200:
            raise SnapticError("Error posting files ", response.status, data)

    def _encode_multi_part_form_data(self, files):
        """
        Encode multi part form data to be posted to server.

        Args:
            Files is a sequence of (name, filename, value) elements for data to be uploaded as files
        Return:
            sequence of (content_type, body) ready for httplib.HTTPConnection instance
        """
        BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
        CRLF = '\r\n'
        L = []
        for (key, filename, value) in files:
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
            L.append('Content-Type: %s' % self._get_content_type(filename))
            L.append('')
            L.append(value)
        L.append('--' + BOUNDARY + '--')
        L.append('')
        body = CRLF.join(L)
        content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
        return content_type, body

    def _get_content_type(self, filename):
        """
        Attempt to guess mimetype of file.

        Args:
            filename: filename to be guessed.
        Returns:
            File type or default value.
        """
        return mimetypes.guess_type(filename)[0] or 'application/octet-stream'

    def delete_note(self, id):#Change this to just take a note
        """
        Delete a note.

        Args:
            id: id of note to be deleted.
        Returns:
            The server's response page.
        """
        return self._request(self.HTTP_DELETE, id)

    def edit_note(self, note):
        """
        Edit a note.

        Args:
            note: note object to be edited
        Returns:
            The server's response page.
        """
        return self._request(self.HTTP_POST, note)

    def post_note(self, note):
        """
        Post a note.

        Args:
            note: text of note to be posted.
        Returns:
            The server's response page.
        """
        return self._request(self.HTTP_POST, note) #change this to note_text to be a little clearer -htormey

    def _request(self, http_method, note): #Clean this up a little -htormey
        """
        Perform a http request on a note.

        Args:
            http_metod: what kind of http request is being made (i.e POST/DELETE/GET)
        Returns:
            The server's response page.
        """
        if http_method == self.HTTP_POST:
            headers     = { 'Content-type' : "application/x-www-form-urlencoded" }
            if isinstance(note, Note):
                #Edit an existing note
                params         = urlencode(note.dictionary)
                page           = "/" + self.API_VERSION + self.API_ENDPOINT_NOTES + str(note.note_id) + '.json'
            else:
                params      = urlencode(dict(text=note))
                page        = "/" + self.API_VERSION + self.API_ENDPOINT_NOTES_JSON
            handle      = self._basic_auth_request(page, headers=headers, method=self.HTTP_POST, params=params)
        elif http_method == self.HTTP_DELETE:
            page            = "/" + self.API_VERSION + self.API_ENDPOINT_NOTES + str(note)
            handle         = self._basic_auth_request(page, method=self.HTTP_DELETE)
 
        response    = handle.getresponse()
        data        = response.read()
        handle.close()

        if response.status != 200:
            raise SnapticError("Http error posting/editing/deleting note ", response.status, data)
        return data

    def get_image_with_id(self, id):
        """
        Get image data associated with a given id.

        Args:
            id: id of image to be fetched.
        Returns:
            Data associated with image id.
        """
        url = self.API_ENDPOINT_IMAGES_VIEW  + str(id)
        return self._fetch_url(url)

    def get_user_id(self):
        """
        Get ID of API user.

        Returns: 
            Id of snaptic user associated with API instance.
        """
        if self._user:
            return self._user.id
        else:
            raise SnapticError("Error user id not set, try calling GetNotes.")

    @Property
    def notes():
        doc = "A parsed list of note objects"
        def fget(self):
            if self._notes:
                return self._notes
            else:
                return self.get_notes()
        return locals()

    def get_notes(self):
        """
        Get notes and update the Api's internal cache.

        Returns:
            A list of Note objects from the snaptic users account.
        """
        url          = "/" + self.API_VERSION + self.API_ENDPOINT_NOTES_JSON
        json_notes   = self._fetch_url(url)
        self._notes  = self._parse_notes(json_notes)
        return self._notes

    def get_notes_from_cursor(self, cursor_position):
        """
        Get a batch of upto 20 notes from a given cursor position. See
        description given for json_cursor for further details on how 
        cursors work with snaptic.

        Args:
            cursor_position: cursor position to grab 20 notes from (i.e -1 is most recent 20)
        Returns:
            A list of note objects based on the contents of the users account.
        """
        json_notes   = self.json_cursor(cursor_position)
        notes  = self._parse_notes(json_notes)
        return notes

    def get_cursor_information(self, cursor_position):
        """
        Gets information about cursor at a given position. See json_cursor for further 
        details on how cursors work with snaptic.

        Args:
            cursor_position: cursor position you want to find out about.
        Returns:
            A dictionary containing previous_cursor, next_cursor and note count.
        """
        json_notes   = self.json_cursor(cursor_position)
        return self._parse_cursor_info(json_notes)

    def _parse_cursor_info(self, source):
        """
        Parse cursor information with notes returned from snaptic.

        Args:
            source: A json object consisting of notes and cursor information
        Returns:
            A dictionary containing previous_cursor, next_cursor and note count.
        """
        cursor_info   = json.loads(source)
        if 'next_cursor' in cursor_info and 'previous_cursor' in cursor_info and 'count' in cursor_info:
            return {"previous_cursor": cursor_info['previous_cursor'], "next_cursor": cursor_info['next_cursor'], "count": cursor_info['count'] }
        else:
            SnapticError("Error keys missing from source JSON passed to _parse_cursor_info")

    def get_user(self):
        """
        Get user info.

        Returns:
            A user object.
        """
        url          = "/" + self.API_VERSION + self.API_ENDPOINT_USER_JSON
        user_info    = self._fetch_url(url)
        self._parse_user_info(user_info)
        return self._user

    @Property
    def json():
        doc = "Json object of notes stored in account."
        def fget(self):
            if self._json:
                return self._json #should I return json.load(sef._json) ? -htormey
            else:
                return self.get_json()
        return locals()

    def get_json(self):
        """
        Get json object and update the cache.

        Returns:
            A json object representing all notes in a users account.
        """
        url         = "/" + self.API_VERSION + self.API_ENDPOINT_NOTES_JSON
        self._json  = self._fetch_url(url)
        return self._json

    def get_tags(self):
        """
        Fetch json object containing tags from users account.

        Returns:
            A json object containing tags and related information (number of notes per tag, etc).
        """
        url         = "/" + self.API_VERSION + self.API_ENDPOINT_TAGS_JSON
        tags        = self._fetch_url(url)
        return tags

    def json_cursor(self, cursor_position):
        """
        Get batches of 20 notes in JSON format from a given cursor position i.e -1, 1,
        etc. For example: -1 returns the most recent 20 notes, 1 returns the previous 20
        before that, etc. One exeption to note is that 0 returns a JSON object for all
        notes in a given account.

        Args:
            cursor_position: cursor position to grab 20 notes from (i.e -1 is most recent 20).
        Returns:
            A json object containing notes from cursor position requested.
        """
        url         =  "/" + self.API_VERSION + self.API_ENDPOINT_NOTES_JSON + self.API_ENDPOINT_CURSOR + str(cursor_position)
        cursor      = self._fetch_url(url)
        return cursor

    def _fetch_url(self, url):
        """
        Perform a basic auth request on a given snaptic API endpoint.

        Args:
            url: Snaptic Api endpoint (i.e /v1/notes.json etc).
        Returns:
            The server's response page.
        """
        handler       = self._basic_auth_request(url)
        response      = handler.getresponse()
        data          = response.read()
        handler.close()
        if response.status != 200:
            raise SnapticError("Http error", response.status, data)
        return data

    def _get_auth_headers(self):
        """
        Switch between basic auth and cookie auth depending on which properties
        self has.
        """
        if hasattr(self, "_username") and hasattr(self, "_password"):
            return self._make_basic_auth_headers(self._username, self._password)
        elif hasattr(self, "_cookie_epass"):
            return self._make_cookie_auth_headers(self._cookie_epass)
        else:
            raise SnapticError("No username/password combination\
                                or cookie authentication provided")

    def _make_basic_auth_headers(self, username, password):
        """
        Encode headers for basic auth request.

        Args::

            username: snaptic username to be used.
            password: password to be used.

        Returns:
            Dictionary with encoded basic auth values.
        """
        if username and password:
            headers = dict(Authorization="Basic %s"
                    %(base64.b64encode("%s:%s" %(username, password))))
        else:
            raise SnapticError("Error making basic auth headers with username: %s, password: %s" % (username, password))
        return headers

    def _make_cookie_auth_headers(self, cookie_epass):
        """
        Encode headers for cookie auth request.

        Args::

            cookie_epass: cookie auth token to be used.

        Returns:
            Dictionary with encoded basic auth values.
        """
        if cookie_epass:
            return {
                "Cookie": "cookie_epass={0}".format(cookie_epass)
            }
        else:
            raise SnapticError("Error making cookie auth headers with\
                               cookie:{0}".format(cookie_epass))

    def _basic_auth_request(self, path, method=HTTP_GET, headers={}, params={}):
        """
        Make a HTTP request with basic auth header and supplied method.
        Defaults to operating over SSL. 

        Args::

            path: Snaptic API endpoint
            metthod: which http method to use (PUT/DELETE/GET)
            headers: Additional header to use with request.
            params: Other parameters to use

        Returns:
            The server's response page.
        """
        h = self._get_auth_headers()
        h.update(headers)
        if self._use_ssl:
            handler = httplib.HTTPSConnection
        else:
            handler = httplib.HTTPConnection

        # 'timeout' parameter is only available in Python 2.6+
        if sys.version_info[:2] < (2, 6):
            conn = handler(self._url, self._port)
        else:
            conn = handler(self._url, self._port, timeout=self._timeout)
        conn.request(method, path, params, headers=h)
        return conn

    def _parse_user_info(self, source):
        """
        Parse JSON user returned from snaptic, instantiate a User object from it.

        Args:
            source: Json object representing a user
        Returns:
            A User object.
        """
        user_info   = json.loads(source)

        if 'user' in user_info:
            self._user = User(user_info['user']['id'], user_info['user']['user_name'], user_info['user']['created_at'], user_info['user']['email'])
        else:
            SnapticError("Error no user key found in source JSON passed to _parse_user_info")

    def _parse_notes( self, source, get_image_data=False):
        """
        parse JSON notes returned from snaptic, instantiate a list of note objects from it.

        Args::

            source: A json object representing a list of notes.
            get_images: if images are associated with notes, download them now.
        Returns:
            A list of note objects.
        """

        notes       = []
        json_notes  = json.loads(source)

        for note in json_notes['notes']:
            media           = []
            location        = []
            tags            = []
            user            = None
            source          = None

            if 'id' in note:
                if 'user' in note:
                    if self._user == None:
                        self. get_user()
                        user = self._user.id
                    user = self._user.id
                if 'location' in note:
                    pass 
                if 'tags' in note:
                    for tag in note['tags']:
                        tags.append(tag)
                if 'media' in note:
                    for item in note['media']:
                        if item['type'] == 'image':
                            image_data = None
                            if get_image_data:
                                image_data = self._fetch_url(item['src'])
                            media.append(Image(item['type'], None, item['id'], item['revision_id'], item['width'], item['height'], item['src'], image_data))

                notes.append(Note(note['created_at'], note['modified_at'], note['reminder_at'], note['id'], note['text'], note['summary'], note['source'], 
                                note['source_url'], user, note['children'], media, tags, location))
        return notes
