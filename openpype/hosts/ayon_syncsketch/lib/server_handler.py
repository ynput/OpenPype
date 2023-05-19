# -*- coding: utf-8 -*-
import json
import os
import time
import requests
import logging

try:
    # Python 3
    from urllib.parse import urlparse, urlencode
except ImportError:
    # Python 2
    from urlparse import urlparse
    from urllib import urlencode

log = logging.getLogger(__name__)


class ServerCommunication:
    """
    A class used to represent the server communication

    Attributes:
        user_auth (str): The user authentication.
        api_key (str): The API key.
        api_params (dict): The API parameters.
        headers (dict): The headers for the requests.
        api_version (str): The version of the API.
        debug (bool): Debug mode status.
        HOST (str): The host URL.
    """

    def __init__(
        self,
        auth,
        api_key,
        host="https://www.syncsketch.com",
        use_expiring_token=False,
        debug=False,
        api_version="v1",
        use_header_auth=False,
    ):
        """
        Constructs all the necessary attributes for the
        ServerCommunication object.

        Args:
            auth (str): The user authentication.
            api_key (str): The API key.
            host (str, optional): The host URL.
                Defaults to "https://www.syncsketch.com".
            use_expiring_token (bool, optional): Use of expiring token.
                Defaults to False.
            debug (bool, optional): Debug mode status.
                Defaults to False.
            api_version (str, optional): The version of the API.
                Defaults to "v1".
            use_header_auth (bool, optional): Use of header authentication.
                Defaults to False.
        """

        # set initial values
        self.user_auth = auth
        self.api_key = api_key
        self.api_params = {}
        self.headers = {}
        auth_type = "apikey"

        if use_expiring_token:
            auth_type = "token"

        if use_header_auth:
            # This will be the preferred way to connect
            # once we fix headers on live
            self.headers = {
                "Authorization": "{} {}:{}".format(
                    auth_type, self.user_auth, self.api_key
                )
            }
        elif use_expiring_token:
            self.api_params = {
                "token": self.api_key,
                "email": self.user_auth
            }
        else:
            self.api_params = {
                "api_key": self.api_key,
                "username": self.user_auth
            }

        self.api_version = api_version
        self.debug = debug
        self.HOST = host

    def get_api_base_url(self, api_version=None):
        """
        Get the base URL of the API.

        Args:
            api_version (str, optional): The version of the API.
                Defaults to None.

        Returns:
            str: The base URL of the API.
        """
        return self.join_url_path(
            self.HOST, "/api/{}/".format(api_version or self.api_version)
        )

    @staticmethod
    def join_url_path(base, *path_segments):
        """
        Join and normalize URL path segments.

        Args:
            base (str): The base URL.
            *path_segments (str): The path segments.

        Returns:
            str: The joined and normalized URL path.
        """
        path_segments = []
        path_segments.append(base.rstrip("/"))
        path_segments.extend(
            segment.strip("/") for segment in path_segments
        )
        path_segments.append("")

        return "/".join(path_segments)

    def _get_unversioned_api_url(self, path):
        """
        Get the unversioned API URL.

        Args:
            path (str): The API path.

        Returns:
            str: The unversioned API URL.
        """
        return self.join_url_path(self.HOST, path)

    def _get_json_response(
        self,
        url,
        method=None,
        get_data=None,
        post_data=None,
        patch_data=None,
        put_data=None,
        content_type="application/json",
        raw_response=False,
    ):
        """
        Function to get a JSON response from the server.

        Args:
            url (str): The URL.
            method (str, optional): The HTTP method. Defaults to None.
            get_data (dict, optional): GET data. Defaults to None.
            post_data (dict, optional): POST data. Defaults to None.
            patch_data (dict, optional): PATCH data. Defaults to None.
            put_data (dict, optional): PUT data. Defaults to None.
            content_type (str, optional): The content type.
                Defaults to "application/json".
            raw_response (bool, optional): Raw response flag.
                Defaults to False.

        Returns:
            dict or requests.Response: The JSON response or raw response.
        """
        url = self._get_unversioned_api_url(url)
        params = self.api_params.copy()
        headers = self.headers.copy()
        headers["Content-Type"] = content_type

        if get_data:
            params.update(get_data)

        if self.debug:
            log.debug("URL: {}, params: {}".format(url, params))

        if post_data or method == "post":
            result = requests.post(
                url, params=params,
                data=json.dumps(post_data),
                headers=headers
            )
        elif patch_data or method == "patch":
            result = requests.patch(
                url,
                params=params,
                json=patch_data,
                headers=headers
            )
        elif put_data or method == "put":
            result = requests.put(
                url,
                params=params,
                json=put_data,
                headers=headers
            )
        elif method == "delete":
            result = requests.patch(
                url,
                params=params,
                data={"active": False},
                headers=headers
            )
        else:
            result = requests.get(url, params=params, headers=headers)

        if raw_response:
            return result

        try:
            return result.json()
        except Exception as e:
            if self.debug:
                log.error(e)

            log.error("Error: {}".format(result.text))

            return {"objects": []}

    def is_connected(self):
        """
        Convenience function to check if the API is connected to SyncSketch.
        Checks against Status Code 200 and returns False if not.

        Returns:
            bool: The connection status.
        """
        url = "/api/{}/person/connected/".format(self.api_version)
        params = self.api_params.copy()

        if self.debug:
            log.debug("URL: {}, params: {}".format(url, params))

        result = self._get_json_response(url, raw_response=True)
        return result.status_code == 200

    def get_projects(
        self,
        include_deleted=False,
        include_archived=False,
        include_tags=False,
        include_connections=False,
        limit=100,
        offset=0
    ):
        """
        Get a list of currently active projects

        Args:
            include_deleted (bool, optional): Include deleted projects.
                Defaults to False.
            include_archived (bool, optional): Include archived projects.
                Defaults to False.
            include_tags (bool, optional): Include tag list on
                the project object.
                Defaults to False.
            include_connections (bool, optional): Include connections.
                Defaults to False.
            limit (int, optional): The number of projects to return.
                Defaults to 100.
            offset (int, optional): The offset. Defaults to 0.

        Returns:
            dict: Dictionary with meta information and an array
                  of found projects.
        """
        get_params = {
            "active": 1,
            "is_archived": 0,
            "account__active": 1,
            "limit": limit,
            "offset": offset,
        }

        if include_connections:
            get_params["withFullConnections"] = True

        if include_deleted:
            del get_params["active"]

        if include_archived:
            del get_params["active"]
            del get_params["is_archived"]

        if include_tags:
            get_params["include_tags"] = 1

        return self._get_json_response(
            "/api/{}/project/".format(self.api_version),
            get_data=get_params
        )

    def get_projects_by_name(self, name):
        """
        Get a project by name regardless of status

        Args:
            name (str): The name of the project.

        Returns:
            dict: Dictionary with meta information and an array
                  of found projects.
        """
        get_params = {"name__istartswith": name}
        return self._get_json_response(
            "/api/{}/project/".format(self.api_version),
            get_data=get_params
        )

    def get_project_by_id(self, project_id):
        """
        Get single project by id

        Args:
            project_id (int): The id of the project.

        Returns:
            dict: The project.
        """
        return self._get_json_response(
            "/api/{}/project/{}/".format(self.api_version, project_id)
        )

    def get_project_storage(self, project_id):
        """
        Get project storage usage in bytes

        Args:
            project_id (int): The id of the project.

        Returns:
            dict: The project storage.
        """
        return self._get_json_response(
            "/api/v2/project/{}/storage/".format(project_id)
        )

    def update_project(self, project_id, data):
        """
        Update a project

        Args:
            project_id (int): The id of the project.
            data (dict): Dictionary with data for the project.

        Returns:
            dict: The updated project.
        """
        if not isinstance(data, dict):
            log.debug("Please make sure you pass a dict as data")
            return False

        return self._get_json_response(
            "/api/{}/project/{}/".format(self.api_version, project_id),
            patch_data=data
        )

    def delete_project(self, project_id):
        """
        Delete a project by id. This method sets the "active" attribute
        of the project to False.

        Args:
            project_id (int): The ID of the project.

        Returns:
            dict: The response from the API call.
        """
        return self._get_json_response(
            "/api/{}/project/{}/".format(self.api_version, project_id),
            patch_data=dict(active=False)
        )

    def duplicate_project(self, project_id, name=None, copy_reviews=False,
                          copy_users=False, copy_settings=False):
        """
        Create a new project from an existing project.

        Args:
            project_id (int): The ID of the project to duplicate.
            name (str, optional): The name of the new project.
            copy_reviews (bool, optional): Whether to copy reviews.
                Defaults to False.
            copy_users (bool, optional): Whether to copy users.
                Defaults to False.
            copy_settings (bool, optional): Whether to copy settings.
                Defaults to False.

        Returns:
            dict: The new project data.
        """
        # Construct the configuration for the new project
        config = dict(
            reviews=copy_reviews,
            users=copy_users,
            settings=copy_settings,
        )
        if name:
            config["name"] = name

        return self._get_json_response(
            "/api/v2/project/{}/duplicate/".format(project_id),
            post_data=config
        )

    def archive_project(self, project_id):
        """
        Archive a project by id. This method sets the "is_archived"
        attribute of the project to True.

        Args:
            project_id (int): The ID of the project.

        Returns:
            dict: The response from the API call.
        """
        return self._get_json_response(
            "/api/{}/project/{}/".format(self.api_version, project_id),
            patch_data=dict(is_archived=True)
        )

    def restore_project(self, project_id):
        """
        Restore (unarchive) a project by id. This method sets the
        "is_archived" attribute of the project to False.

        Args:
            project_id (int): The ID of the project.

        Returns:
            dict: The response from the API call.
        """
        return self._get_json_response(
            "/api/{}/project/{}/".format(self.api_version, project_id),
            patch_data=dict(is_archived=False)
        )

    def create_review(self, project_id, name, description="", data=None):
        """
        Create a review for a specific project.

        Args:
            project_id (int): The ID of the project.
            name (str): The name of the review.
            description (str, optional): The description of the review.
                Defaults to "".
            data (dict, optional): Additional data for the review.
                Defaults to None.

        Returns:
            dict: The response from the API call.
        """
        if data is None:
            data = {}

        post_data = {
            "project": "/api/{}/project/{}/".format(
                self.api_version, project_id
            ),
            "name": name,
            "description": description,
        }

        post_data.update(data)

        return self._get_json_response(
            "/api/{}/review/".format(self.api_version),
            post_data=post_data
        )

    def get_reviews_by_project_id(self, project_id, limit=100, offset=0):
        """
        Get list of reviews by project id.

        Args:
            project_id (int): The ID of the project.
            limit (int, optional): The maximum number of reviews to retrieve.
                Defaults to 100.
            offset (int, optional): The number of reviews to skip
                before starting to collect.
            Defaults to 0.

        Returns:
            dict: Meta information and an array of found projects.
        """
        get_params = {
            "project__id": project_id,
            "project__active": 1,
            "project__is_archived": 0,
            "limit": limit,
            "offset": offset
        }
        return self._get_json_response(
            "/api/{}/review/".format(self.api_version),
            get_data=get_params
        )

    def get_review_by_name(self, name):
        """
        Get reviews by name using a case insensitive startswith query.

        Args:
            name (str): The name of the review.

        Returns:
            dict: Meta information and an array of found projects.
        """
        get_params = {"name__istartswith": name}
        return self._get_json_response(
            "/api/{}/review/".format(self.api_version),
            get_data=get_params
        )

    def get_review_by_id(self, review_id):
        """
        Get single review by id.

        Args:
            review_id (int): The ID of the review.

        Returns:
            dict: The review data.
        """
        return self._get_json_response(
            "/api/{}/review/{}/".format(self.api_version, review_id))

    def get_review_storage(self, review_id):
        """
        Get review storage usage in bytes.

        Args:
            review_id (int): The ID of the review.

        Returns:
            dict: The response from the API call.
        """
        return self._get_json_response(
            "/api/v2/review/{}/storage/".format(review_id)
        )

    def update_review(self, review_id, data):
        """
        Update a review by id.

        Args:
            review_id (int): The ID of the review.
            data (dict): The new data for the review.

        Returns:
            dict/bool: The response from the API call if the data is a dict,
            False otherwise.
        """
        if not isinstance(data, dict):
            log.debug("Please make sure you pass a dict as data")
            return False

        return self._get_json_response(
            "/api/{}/review/{}/".format(self.api_version, review_id),
            patch_data=data
        )

    def get_item(self, item_id, data=None):
        """
        Get single item by id.

        Args:
            item_id (int): The ID of the item.
            data (dict, optional): Additional data for the item.
                Defaults to None.

        Returns:
            dict: The item data.
        """
        return self._get_json_response(
            "/api/{}/item/{}/".format(self.api_version, item_id),
            get_data=data
        )

    def update_item(self, item_id, data):
        """
        Update an item by id.

        Args:
            item_id (int): The ID of the item.
            data (dict): The new data for the item.

        Returns:
            dict/bool: The response from the API call if the data is a dict,
                False otherwise.
        """
        if not isinstance(data, dict):
            log.debug("Please make sure you pass a dict as data")
            return False

        return self._get_json_response(
            "/api/{}/item/{}/".format(self.api_version, item_id),
            patch_data=data
        )

    def add_media(self, review_id, filepath, artist_name="", file_name="",
                  noConvertFlag=False, itemParentId=False):
        """
        Convenience function to upload a file to a review. It will
        automatically create an Item and attach it to the review.

        Args:
            review_id (int): Required review_id
            filepath (str): Path for the file on disk e.g /tmp/movie.webm
            artist_name (str, optional): The name of the artist you want
                associated with this media file. Defaults to "".
            file_name (str, optional): The name of the file. Please make
                sure to pass the correct file extension. Defaults to "".
            noConvertFlag (bool, optional): The video you are uploading
                is already in a browser compatible format. Defaults to False.
            itemParentId (int, optional): Set when you want to add a new
                version of an item. itemParentId is the id of the item you want
                to upload a new version for. Defaults to False.

        Returns:
            dict: The response from the API call.
        """
        get_params = self.api_params.copy()

        if noConvertFlag:
            get_params.update({"noConvertFlag": 1})

        if itemParentId:
            get_params.update({"itemParentId": itemParentId})

        uploadURL = "/items/uploadToReview/{}?{}".format(
            review_id, urlencode(get_params)
        )

        files = {"reviewFile": open(filepath, "rb")}
        result = requests.post(
            uploadURL,
            files=files,
            data=dict(artist=artist_name, name=file_name),
            headers=self.headers
        )

        try:
            return json.loads(result.text)
        except Exception:
            log.error(result.text)

    def get_media_by_review_id(self, review_id):
        """
        Get all media by review id.

        Args:
            review_id (int): The ID of the review.

        Returns:
            dict: The response from the API call.
        """
        get_params = {"reviews__id": review_id, "active": 1}
        return self._get_json_response(
            "/api/{}/item/".format(self.api_version),
            get_data=get_params
        )

    def move_items(self, new_review_id, item_data):
        """
        Move items to a new review.

        Args:
            new_review_id (int): The ID of the new review.
            item_data (dict): The item data.

        Returns:
            dict: The response from the API call.
        """
        return self._get_json_response(
            "/api/v2/move-review-items/",
            method="post",
            post_data={"new_review_id": new_review_id, "item_data": item_data},
            raw_response=True,
        )

    def add_comment(self, item_id, text, review_id, frame=0):
        """
        Add a comment to an item in a review.

        Args:
            item_id (int): The ID of the item.
            text (str): The comment text.
            review_id (int): The ID of the review.
            frame (int, optional): The frame to which the comment refers.
                Defaults to 0.

        Returns:
            dict: The response from the API call.
        """
        item = self.get_item(item_id, data={"review_id": review_id})

        # Ugly method of getting revision id from item data,
        # should fix this with api v2
        revision_id = item.get("revision_id")
        if not revision_id:
            return "error"

        post_data = dict(
            item="/api/{}/item/{}/".format(
                self.api_version, item_id),
            frame=frame,
            revision="/api/{}/revision/{}/".format(
                self.api_version, revision_id),
            type="comment",
            text=text
        )

        return self._get_json_response(
            "/api/{}/frame/".format(self.api_version),
            method="post",
            post_data=post_data
        )

    def get_annotations(self, item_id, revisionId=False, review_id=False):
        """
        Get annotations of an item.

        Args:
            item_id (int): The ID of the item.
            revisionId (bool, optional): The ID of the revision.
                Defaults to False.
            review_id (bool, optional): The ID of the review.
                Defaults to False.

        Returns:
            dict: The response from the API call.
        """
        get_params = {"item__id": item_id, "active": 1}

        if revisionId:
            get_params["revision__id"] = revisionId

        if review_id:
            get_params["revision__review_id"] = review_id

        return self._get_json_response(
            "/api/{}/frame/".format(self.api_version),
            get_data=get_params
        )

    def get_flattened_annotations(self, review_id, item_id,
                                  with_tracing_paper=False,
                                  return_as_base64=False, api_version=None):
        """
        Get flattened annotations of an item in a review.

        Args:
            review_id (int): The ID of the review.
            item_id (int): The ID of the item.
            with_tracing_paper (bool, optional): Include tracing paper in
                the response. Defaults to False.
            return_as_base64 (bool, optional): Return the response as base64.
                Defaults to False.
            api_version (str, optional): The API version to use.
                Defaults to None

        Returns:
            dict: The response from the API call.
        """
        api_version = api_version or "v2"

        get_data_ = {
            "include_data": 1,
            "tracingpaper": 1 if with_tracing_paper else 0,
            "base64": 1 if return_as_base64 else 0,
            "async": 0
        }

        url = "/api/{}/downloads/flattenedSketches/{}/{}/".format(
            api_version, review_id, item_id)

        return self._get_json_response(
            url,
            method="post",
            get_data=get_data_
        )

    def get_grease_pencil_overlays(self, review_id, item_id, homedir=None,
                                   api_version=None):
        """
        Fetches grease pencil overlays of a specific item from a specific
        review. The result will be a .zip file.

        Args:
            review_id (int): ID of the review.
            item_id (int): ID of the item.
            homedir (str, optional): Home directory where the .zip file
                is to be stored. If not provided, it will default
                to "/tmp/" directory.
            api_version (str, optional): The API version to use.
                Defaults to None

        Returns:
            str: Local path to the .zip file with grease pencil
                 overlays or False if the request failed.
        """
        api_version = api_version or "v2"

        url = "/api/{}/downloads/greasePencil/{}/{}".format(
            api_version, review_id, item_id)
        result = self._get_json_response(
            url,
            method="post"
        )
        celery_task_id = result.json()

        # Check the celery task
        check_celery_url = "/api/{}/downloads/greasePencil/{}/".format(
            api_version, celery_task_id)
        result = self._get_json_response(
            check_celery_url
        )

        request_processing = True
        while request_processing:
            result_json = result.json()

            if result_json.get("status") == "done":
                data = result_json.get("data")

                # Store the file locally
                local_filename = "/tmp/{}.zip".format(data["fileName"])
                if homedir:
                    local_filename = os.path.join(
                        homedir, "{}.zip".format(data["fileName"]))
                result_s3 = requests.get(data["s3Path"], stream=True)
                with open(local_filename, "wb") as f:
                    for chunk in result_s3.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)

                request_processing = False
                return local_filename

            if result_json.get("status") == "failed":
                request_processing = False
                return False

            # Wait a bit before checking again
            time.sleep(1)

            # Check the URL again
            result = self._get_json_response(
                check_celery_url
            )

    def get_users_by_project_id(self, project_id):
        """
        Get all users by project id.

        Args:
            project_id (int): The ID of the project.

        Returns:
            dict: The response from the API call.
        """
        return self._get_json_response(
            "/api/v2/all-project-users/{}".format(project_id))

    def get_connections_by_user_id(self, user_id, account_id,
                                   include_inactive=None,
                                   include_archived=None):
        """
        Get all project and account connections for a user. Good for
        checking access for a user that might have left...

        Args:
            user_id (int): The ID of the user.
            account_id (int): The ID of the account.
            include_inactive (bool, optional): Include inactive connections.
                Defaults to None.
            include_archived (bool, optional): Include archived connections.
                Defaults to None.

        Returns:
            dict: The response from the API call.
        """
        data = {}
        if include_inactive is not None:
            data["include_inactive"] = "true" if include_inactive else "false"
        if include_archived is not None:
            data["include_archived"] = "true" if include_archived else "false"
        return self._get_json_response(
            "/api/v2/user/{}/connections/account/{}/".format(
                user_id, account_id),
            get_data=data,
        )

    def get_user_by_id(self, userId):
        """
        Get user by user id.

        Args:
            userId (int): The ID of the user.

        Returns:
            dict: The response from the API call.
        """
        return self._get_json_response(
            "/api/{}/simpleperson/{}".format(self.api_version, userId))

    def get_current_user(self):
        """
        Get the current user.

        Returns:
            dict: The response from the API call.
        """
        return self._get_json_response(
            "/api/{}/simpleperson/currentUser/".format(self.api_version)
        )
