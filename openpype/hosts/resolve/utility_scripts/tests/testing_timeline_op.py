#! python3
from openpype.pipeline import install_host
from openpype.hosts.resolve import api as bmdvr
from openpype.hosts.resolve.api.lib import get_current_project

if __name__ == "__main__":
    install_host(bmdvr)
    project = get_current_project()
    timeline_count = project.GetTimelineCount()
    print(f"Timeline count: {timeline_count}")
    timeline = project.GetTimelineByIndex(timeline_count)
    print(f"Timeline name: {timeline.GetName()}")
    print(timeline.GetTrackCount("video"))
