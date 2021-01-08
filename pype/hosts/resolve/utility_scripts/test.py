#! python3
import sys
import DaVinciResolveScript as bmdvr


def main():
    resolve = bmdvr.scriptapp('Resolve')
    print(f"resolve: {resolve}")
    project_manager = resolve.GetProjectManager()
    project = project_manager.GetCurrentProject()
    media_pool = project.GetMediaPool()
    root_folder = media_pool.GetRootFolder()
    ls_folder = root_folder.GetClipList()
    timeline = project.GetCurrentTimeline()
    timeline_name = timeline.GetName()
    for tl in ls_folder:
        if tl.GetName() not in timeline_name:
            continue
        print(tl.GetName())
        print(tl.GetMetadata())
        print(tl.GetClipProperty())


if __name__ == "__main__":
    result = main()
    sys.exit(not bool(result))
