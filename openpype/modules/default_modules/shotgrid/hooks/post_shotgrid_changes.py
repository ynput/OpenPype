from openpype.lib import PostLaunchHook


class PostShotgridHook(PostLaunchHook):
    order = None

    def execute(self, *args, **kwargs):
        print(args, kwargs)
        pass
