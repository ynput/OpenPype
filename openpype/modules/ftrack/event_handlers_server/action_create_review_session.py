import threading
import datetime
import copy
import collections

import ftrack_api

from openpype.lib import get_datetime_data
from openpype.api import get_project_settings
from openpype_modules.ftrack.lib import ServerAction


class CreateDailyReviewSessionServerAction(ServerAction):
    """Create daily review session object per project.

    Action creates review sessions based on settings. Settings define if is
    action enabled and what is a template for review session name. Logic works
    in a way that if review session with the name already exists then skip
    process. If review session for current day does not exist but yesterdays
    review exists and is empty then yesterdays is renamed otherwise creates
    new review session.

    Also contains cycle creation of dailies which is triggered each morning.
    This option must be enabled in project settings. Cycle creation is also
    checked on registration of action.
    """

    identifier = "create.daily.review.session"
    #: Action label.
    label = "OpenPype Admin"
    variant = "- Create Daily Review Session (Server)"
    #: Action description.
    description = "Manually create daily review session"
    role_list = {"Pypeclub", "Administrator", "Project Manager"}

    settings_key = "create_daily_review_session"
    default_template = "{yy}{mm}{dd}"

    def __init__(self, *args, **kwargs):
        super(CreateDailyReviewSessionServerAction, self).__init__(
            *args, **kwargs
        )

        self._cycle_timer = None
        self._last_cyle_time = None
        self._day_delta = datetime.timedelta(days=1)

    def discover(self, session, entities, event):
        """Show action only on AssetVersions."""

        valid_selection = False
        for ent in event["data"]["selection"]:
            # Ignore entities that are not tasks or projects
            if ent["entityType"].lower() in (
                "show", "task", "reviewsession", "assetversion"
            ):
                valid_selection = True
                break
            else:
                self.log.info(ent["entityType"])

        if not valid_selection:
            return False
        return self.valid_roles(session, entities, event)

    def launch(self, session, entities, event):
        project_entity = self.get_project_from_entity(entities[0], session)
        project_name = project_entity["full_name"]
        project_settings = self.get_project_settings_from_event(
            event, project_name
        )
        action_settings = self._extract_action_settings(project_settings)
        project_name_by_id = {
            project_entity["id"]: project_name
        }
        settings_by_project_id = {
            project_entity["id"]: action_settings
        }
        self._process_review_session(
            session, settings_by_project_id, project_name_by_id
        )
        return True

    def register(self, *args, **kwargs):
        """Override register to be able trigger """
        # Register server action as would be normally
        super(CreateDailyReviewSessionServerAction, self).register(
            *args, **kwargs
        )

        # Create threading timer which will trigger creation of report
        #   at the 00:00:01 of next day
        # - callback will trigger another timer which will have 1 day offset
        now = datetime.datetime.now()
        # Create object of today morning
        today_morning = datetime.datetime(
            now.year, now.month, now.day, 0, 0, 1
        )
        # Add a day delta (to calculate next day date)
        next_day_morning = today_morning + self._day_delta
        # Calculate first delta in seconds for first threading timer
        first_delta = (next_day_morning - now).total_seconds()
        # Store cycle time which will be used to create next timer
        self._last_cyle_time = next_day_morning
        # Create timer thread
        self._cycle_timer = threading.Timer(first_delta, self._timer_callback)
        self._cycle_timer.start()

        self._check_review_session()

    def _timer_callback(self):
        if (
            self._cycle_timer is not None
            and self._last_cyle_time is not None
        ):
            now = datetime.datetime.now()
            while self._last_cyle_time < now:
                self._last_cyle_time = self._last_cyle_time + self._day_delta

            delay = (self._last_cyle_time - now).total_seconds()

            self._cycle_timer = threading.Timer(delay, self._timer_callback)
            self._cycle_timer.start()
        self._check_review_session()

    def _check_review_session(self):
        session = ftrack_api.Session(
            server_url=self.session.server_url,
            api_key=self.session.api_key,
            api_user=self.session.api_user,
            auto_connect_event_hub=False
        )
        project_entities = session.query(
            "select id, full_name from Project"
        ).all()
        project_names_by_id = {
            project_entity["id"]: project_entity["full_name"]
            for project_entity in project_entities
        }

        action_settings_by_project_id = self._get_action_settings(
            project_names_by_id
        )
        enabled_action_settings_by_project_id = {}
        for item in action_settings_by_project_id.items():
            project_id, action_settings = item
            if action_settings.get("cycle_enabled"):
                enabled_action_settings_by_project_id[project_id] = (
                    action_settings
                )

        if not enabled_action_settings_by_project_id:
            self.log.info((
                "There are no projects that have enabled"
                " cycle review sesison creation"
            ))

        else:
            self._process_review_session(
                session,
                enabled_action_settings_by_project_id,
                project_names_by_id
            )

        session.close()

    def _process_review_session(
        self, session, settings_by_project_id, project_names_by_id
    ):
        review_sessions = session.query((
            "select id, name, project_id"
            " from ReviewSession where project_id in ({})"
        ).format(self.join_query_keys(settings_by_project_id))).all()

        review_sessions_by_project_id = collections.defaultdict(list)
        for review_session in review_sessions:
            project_id = review_session["project_id"]
            review_sessions_by_project_id[project_id].append(review_session)

        # Prepare fill data for today's review sesison and yesterdays
        now = datetime.datetime.now()
        today_obj = datetime.datetime(
            now.year, now.month, now.day, 0, 0, 0
        )
        yesterday_obj = today_obj - self._day_delta

        today_fill_data = get_datetime_data(today_obj)
        yesterday_fill_data = get_datetime_data(yesterday_obj)

        # Loop through projects and try to create daily reviews
        for project_id, action_settings in settings_by_project_id.items():
            review_session_template = (
                action_settings["review_session_template"]
            ).strip() or self.default_template

            today_project_fill_data = copy.deepcopy(today_fill_data)
            yesterday_project_fill_data = copy.deepcopy(yesterday_fill_data)
            project_name = project_names_by_id[project_id]
            today_project_fill_data["project_name"] = project_name
            yesterday_project_fill_data["project_name"] = project_name

            today_session_name = self._fill_review_template(
                review_session_template, today_project_fill_data
            )
            yesterday_session_name = self._fill_review_template(
                review_session_template, yesterday_project_fill_data
            )
            # Skip if today's session name could not be filled
            if not today_session_name:
                continue

            # Find matchin review session
            project_review_sessions = review_sessions_by_project_id[project_id]
            todays_session = None
            yesterdays_session = None
            for review_session in project_review_sessions:
                session_name = review_session["name"]
                if session_name == today_session_name:
                    todays_session = review_session
                    break
                elif session_name == yesterday_session_name:
                    yesterdays_session = review_session

            # Skip if today's session already exist
            if todays_session is not None:
                self.log.debug((
                    "Todays ReviewSession \"{}\""
                    " in project \"{}\" already exists"
                ).format(today_session_name, project_name))
                continue

            # Check if there is yesterday's session and is empty
            # - in that case just rename it
            if (
                yesterdays_session is not None
                and len(yesterdays_session["review_session_objects"]) == 0
            ):
                self.log.debug((
                    "Renaming yesterdays empty review session \"{}\" to \"{}\""
                    " in project \"{}\""
                ).format(
                    yesterday_session_name, today_session_name, project_name
                ))
                yesterdays_session["name"] = today_session_name
                session.commit()
                continue

            # Create new review session with new name
            self.log.debug((
                "Creating new review session \"{}\" in project \"{}\""
            ).format(today_session_name, project_name))
            session.create("ReviewSession", {
                "project_id": project_id,
                "name": today_session_name
            })
            session.commit()

    def _get_action_settings(self, project_names_by_id):
        settings_by_project_id = {}
        for project_id, project_name in project_names_by_id.items():
            project_settings = get_project_settings(project_name)
            action_settings = self._extract_action_settings(project_settings)
            settings_by_project_id[project_id] = action_settings
        return settings_by_project_id

    def _extract_action_settings(self, project_settings):
        return (
            project_settings
            .get("ftrack", {})
            .get(self.settings_frack_subkey, {})
            .get(self.settings_key)
        ) or {}

    def _fill_review_template(self, template, data):
        output = None
        try:
            output = template.format(**data)
        except Exception:
            self.log.warning(
                (
                    "Failed to fill review session template {} with data {}"
                ).format(template, data),
                exc_info=True
            )
        return output


def register(session):
    '''Register plugin. Called when used as an plugin.'''
    CreateDailyReviewSessionServerAction(session).register()
