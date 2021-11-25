from Qt import QtCore


DEFAULT_PROJECT_LABEL = "< Default >"
PROJECT_NAME_ROLE = QtCore.Qt.UserRole + 101
PROJECT_IS_ACTIVE_ROLE = QtCore.Qt.UserRole + 102

LOCAL_PROVIDER_ROLE = QtCore.Qt.UserRole + 500  # provider of active site
REMOTE_PROVIDER_ROLE = QtCore.Qt.UserRole + 501  # provider of remote site
LOCAL_PROGRESS_ROLE = QtCore.Qt.UserRole + 502   # percentage downld on active
REMOTE_PROGRESS_ROLE = QtCore.Qt.UserRole + 503  # percentage upload on remote
LOCAL_AVAILABILITY_ROLE = QtCore.Qt.UserRole + 504  # ratio of presence active
REMOTE_AVAILABILITY_ROLE = QtCore.Qt.UserRole + 505
LOCAL_DATE_ROLE = QtCore.Qt.UserRole + 506  # created_dt on active site
REMOTE_DATE_ROLE = QtCore.Qt.UserRole + 507
LOCAL_FAILED_ROLE = QtCore.Qt.UserRole + 508
REMOTE_FAILED_ROLE = QtCore.Qt.UserRole + 509
HEADER_NAME_ROLE = QtCore.Qt.UserRole + 510
EDIT_ICON_ROLE = QtCore.Qt.UserRole + 511
STATUS_ROLE = QtCore.Qt.UserRole + 512
PATH_ROLE = QtCore.Qt.UserRole + 513
LOCAL_SITE_NAME_ROLE = QtCore.Qt.UserRole + 514
REMOTE_SITE_NAME_ROLE = QtCore.Qt.UserRole + 515
ERROR_ROLE = QtCore.Qt.UserRole + 516
TRIES_ROLE = QtCore.Qt.UserRole + 517
