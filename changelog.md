# Pype changelog #
Welcome to pype changelog

## 2.1 ##

A large cleanup release. Most of the change are under the hood.

**new**:
- _(pype)_ add customisable workflow for creating quicktimes from renders or playblasts
- _(pype)_ Added configurable option to add burnins to any generated quicktimes
- _(ftrack)_ Action that identifies what machines pype is running on.
- _(system)_ unify subprocess calls
- _(maya)_ add audio to review quicktimes
- _(nuke)_ add crop before write node to prevent overscan problems in ffmpeg
- Nuke Studio publishing and workfiles support
- Muster render manager support
- _(nuke)_ Framerange, FPS and Resolution are set automatically at startup
- _(maya)_ Ability to load published sequences as image planes
- _(system)_ Ftrack event that sets asset folder permissions based on task assignees in ftrack.
- _(maya)_ Pyblish plugin that allow validation of maya attributes

**changed**:
- change multiple key attributes to unify their behaviour across the pipeline
- (nuke) write nodes are now created inside group with only some attributes editable by the artist
- rendered frames are now deleted from temporary location after their publishing is finished.
- (ftrack) RV action can now be launched from any entity

**fix**:
- faster hierarchy retrieval from db
- (nuke) A lot of stability enhancements
- (nuke studio) A lot of stability enhancements
- (nuke) now only renders a single write node on farm
- (ftrack) pype would crash when launcher project level task

**deprecated**:
- following attributes are considered deprecated as of 2.1 release
  -
