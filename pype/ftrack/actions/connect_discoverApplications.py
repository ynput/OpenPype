def _discoverApplications(self):
    '''Return a list of applications that can be launched from this host.

    An application should be of the form:

        dict(
            'identifier': 'name_version',
            'label': 'Name',
            'variant': 'version',
            'description': 'description',
            'path': 'Absolute path to the file',
            'version': 'Version of the application',
            'icon': 'URL or name of predefined icon'
        )

    '''
    applications = []

    if sys.platform == 'darwin':
        prefix = ['/', 'Applications']

    elif sys.platform == 'win32':
        prefix = ['C:\\', 'Program Files.*']

    self.logger.debug(
        'Discovered applications:\n{0}'.format(
            pprint.pformat(applications)
        )
    )

    return applications

class ApplicationLauncher(object):
    '''Launch applications described by an application store.

    Launched applications are started detached so exiting current process will
    not close launched applications.

    '''

    def __init__(self, applicationStore):
        '''Instantiate launcher with *applicationStore* of applications.

        *applicationStore* should be an instance of :class:`ApplicationStore`
        holding information about applications that can be launched.

        '''
        super(ApplicationLauncher, self).__init__()
        self.logger = logging.getLogger(
            __name__ + '.' + self.__class__.__name__
        )

        self.applicationStore = applicationStore

    def launch(self, applicationIdentifier, context=None):
        '''Launch application matching *applicationIdentifier*.

        *context* should provide information that can guide how to launch the
        application.

        Return a dictionary of information containing:

            success - A boolean value indicating whether application launched
                      successfully or not.
            message - Any additional information (such as a failure message).

        '''
        # Look up application.
        applicationIdentifierPattern = applicationIdentifier
        if applicationIdentifierPattern == 'hieroplayer':
            applicationIdentifierPattern += '*'

        application = self.applicationStore.getApplication(
            applicationIdentifierPattern
        )

        if application is None:
            return {
                'success': False,
                'message': (
                    '{0} application not found.'
                    .format(applicationIdentifier)
                )
            }

        # Construct command and environment.
        command = self._getApplicationLaunchCommand(application, context)
        environment = self._getApplicationEnvironment(application, context)

        # Environment must contain only strings.
        self._conformEnvironment(environment)

        success = True
        message = '{0} application started.'.format(application['label'])

        try:
            options = dict(
                env=environment,
                close_fds=True
            )

            # Ensure that current working directory is set to the root of the
            # application being launched to avoid issues with applications
            # locating shared libraries etc.
            applicationRootPath = os.path.dirname(application['path'])
            options['cwd'] = applicationRootPath

            # Ensure subprocess is detached so closing connect will not also
            # close launched applications.
            if sys.platform == 'win32':
                options['creationflags'] = subprocess.CREATE_NEW_CONSOLE
            else:
                options['preexec_fn'] = os.setsid

            launchData = dict(
                command=command,
                options=options,
                application=application,
                context=context
            )
            ftrack.EVENT_HUB.publish(
                ftrack.Event(
                    topic='ftrack.connect.application.launch',
                    data=launchData
                ),
                synchronous=True
            )
            ftrack_connect.session.get_shared_session().event_hub.publish(
                ftrack_api.event.base.Event(
                    topic='ftrack.connect.application.launch',
                    data=launchData
                ),
                synchronous=True
            )

            # Reset variables passed through the hook since they might
            # have been replaced by a handler.
            command = launchData['command']
            options = launchData['options']
            application = launchData['application']
            context = launchData['context']

            self.logger.debug(
                'Launching {0} with options {1}'.format(command, options)
            )
            process = subprocess.Popen(command, **options)

        except (OSError, TypeError):
            self.logger.exception(
                '{0} application could not be started with command "{1}".'
                .format(applicationIdentifier, command)
            )

            success = False
            message = '{0} application could not be started.'.format(
                application['label']
            )

        else:
            self.logger.debug(
                '{0} application started. (pid={1})'.format(
                    applicationIdentifier, process.pid
                )
            )

        return {
            'success': success,
            'message': message
        }
