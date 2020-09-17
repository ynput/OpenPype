<a name="2.11.0"></a>
## 2.11.0 ##

_**release date:** 27 July 2020_

**new:**
- _(blender)_ namespace support [\#341](https://github.com/pypeclub/pype/pull/341)
- _(blender)_ start end frames [\#330](https://github.com/pypeclub/pype/pull/330)
- _(blender)_ camera asset [\#322](https://github.com/pypeclub/pype/pull/322)
- _(pype)_ toggle instances per family in pyblish GUI [\#320](https://github.com/pypeclub/pype/pull/320)
- _(pype)_ current release version is now shown in the tray menu [#379](https://github.com/pypeclub/pype/pull/379)


**improved:**
- _(resolve)_ tagging for publish [\#239](https://github.com/pypeclub/pype/issues/239)
- _(pype)_ Support publishing a subset of shots with standalone editorial [\#336](https://github.com/pypeclub/pype/pull/336)
- _(harmony)_ Basic support for palettes [\#324](https://github.com/pypeclub/pype/pull/324)
- _(photoshop)_ Flag outdated containers on startup and publish. [\#309](https://github.com/pypeclub/pype/pull/309)
- _(harmony)_ Flag Outdated containers [\#302](https://github.com/pypeclub/pype/pull/302)
- _(photoshop)_ Publish review [\#298](https://github.com/pypeclub/pype/pull/298)
- _(pype)_ Optional Last workfile launch [\#365](https://github.com/pypeclub/pype/pull/365)


**fixed:**
- _(premiere)_ workflow fixes [\#346](https://github.com/pypeclub/pype/pull/346)
- _(pype)_ pype-setup does not work with space in path [\#327](https://github.com/pypeclub/pype/issues/327)
- _(ftrack)_ Ftrack delete action cause circular error [\#206](https://github.com/pypeclub/pype/issues/206)
- _(nuke)_ Priority was forced to 50 [\#345](https://github.com/pypeclub/pype/pull/345)
- _(nuke)_ Fix ValidateNukeWriteKnobs [\#340](https://github.com/pypeclub/pype/pull/340)
- _(maya)_ If camera attributes are connected, we can ignore them. [\#339](https://github.com/pypeclub/pype/pull/339)
- _(pype)_ stop appending of tools environment to existing env [\#337](https://github.com/pypeclub/pype/pull/337)
- _(ftrack)_ Ftrack timeout needs to look at AVALON\_TIMEOUT [\#325](https://github.com/pypeclub/pype/pull/325)
- _(harmony)_ Only zip files are supported. [\#310](https://github.com/pypeclub/pype/pull/310)
- _(pype)_ hotfix/Fix event server mongo uri [\#305](https://github.com/pypeclub/pype/pull/305)
- _(photoshop)_ Subset was not named or validated correctly. [\#304](https://github.com/pypeclub/pype/pull/304)



<a name="2.10.0"></a>
## 2.10.0 ##

_**release date:** 17 June 2020_

**new:**
- _(harmony)_ **Toon Boom Harmony** has been greatly extended to support rigging, scene build, animation and rendering workflows. [#270](https://github.com/pypeclub/pype/issues/270) [#271](https://github.com/pypeclub/pype/issues/271) [#190](https://github.com/pypeclub/pype/issues/190) [#191](https://github.com/pypeclub/pype/issues/191) [#172](https://github.com/pypeclub/pype/issues/172) [#168](https://github.com/pypeclub/pype/issues/168)
- _(pype)_ Added support for rudimentary **edl publishing** into individual shots. [#265](https://github.com/pypeclub/pype/issues/265)
- _(celaction)_ Simple **Celaction** integration has been added with support for workfiles and rendering. [#255](https://github.com/pypeclub/pype/issues/255)
- _(maya)_ Support for multiple job types when submitting to the farm. We can now render Maya or Standalone render jobs for Vray and Arnold (limited support for arnold) [#204](https://github.com/pypeclub/pype/issues/204)
- _(photoshop)_ Added initial support for Photoshop [#232](https://github.com/pypeclub/pype/issues/232)

**improved:**
- _(blender)_ Updated support for rigs and added support Layout family [#233](https://github.com/pypeclub/pype/issues/233) [#226](https://github.com/pypeclub/pype/issues/226)
- _(premiere)_ It is now possible to choose different storage root for workfiles of different task types. [#255](https://github.com/pypeclub/pype/issues/255)
- _(maya)_ Support for unmerged AOVs in Redshift multipart EXRs [#197](https://github.com/pypeclub/pype/issues/197)
- _(pype)_ Pype repository has been refactored in preparation for 3.0 release [#169](https://github.com/pypeclub/pype/issues/169)
- _(deadline)_ All file dependencies are now passed to deadline from maya to prevent premature start of rendering if caches or textures haven't been coppied over yet. [#195](https://github.com/pypeclub/pype/issues/195)
- _(nuke)_ Script validation can now be made optional. [#194](https://github.com/pypeclub/pype/issues/194)
- _(pype)_ Publishing can now be stopped at any time. [#194](https://github.com/pypeclub/pype/issues/194)

**fix:**
- _(pype)_ Pyblish-lite has been integrated into pype repository, plus various publishing GUI fixes. [#274](https://github.com/pypeclub/pype/issues/274) [#275](https://github.com/pypeclub/pype/issues/275) [#268](https://github.com/pypeclub/pype/issues/268) [#227](https://github.com/pypeclub/pype/issues/227) [#238](https://github.com/pypeclub/pype/issues/238)
- _(maya)_ Alembic extractor was getting wrong frame range type in certain scenarios [#254](https://github.com/pypeclub/pype/issues/254)
- _(maya)_ Attaching a render to subset in maya was not passing validation in certain scenarios  [#256](https://github.com/pypeclub/pype/issues/256)
- _(ftrack)_ Various small fixes to ftrack sync [#263](https://github.com/pypeclub/pype/issues/263) [#259](https://github.com/pypeclub/pype/issues/259)
- _(maya)_ Look extraction is now able to skp invalid connections in shaders [#207](https://github.com/pypeclub/pype/issues/207)



<a name="2.9.0"></a>
## 2.9.0 ##

_**release date:** 25 May 2020_

**new:**
- _(pype)_ Support for **Multiroot projects**. You can now store project data on multiple physical or virtual storages and target individual publishes to these locations. For instance render can be stored on a faster storage than the rest of the project. [#145](https://github.com/pypeclub/pype/issues/145), [#38](https://github.com/pypeclub/pype/issues/38)
- _(harmony)_ Basic implementation of **Toon Boom Harmony** has been added. [#142](https://github.com/pypeclub/pype/issues/142)
- _(pype)_ OSX support is in public beta now. There are issues to be expected, but the main implementation should be functional. [#141](https://github.com/pypeclub/pype/issues/141)


**improved:**

- _(pype)_ **Review extractor** has been completely rebuilt. It now supports granular filtering so you can create **multiple outputs** for different tasks, families or hosts. [#103](https://github.com/pypeclub/pype/issues/103), [#166](https://github.com/pypeclub/pype/issues/166), [#165](https://github.com/pypeclub/pype/issues/165)
- _(pype)_ **Burnin** generation had been extended to **support same multi-output filtering** as review extractor [#103](https://github.com/pypeclub/pype/issues/103)
- _(pype)_ Publishing file templates can now be specified in config for each individual family [#114](https://github.com/pypeclub/pype/issues/114)
- _(pype)_ Studio specific plugins can now be appended to pype standard publishing plugins. [#112](https://github.com/pypeclub/pype/issues/112)
- _(nukestudio)_ Reviewable clips no longer need to be previously cut, exported and re-imported to timeline. **Pype can now dynamically cut reviewable quicktimes** from continuous offline footage during publishing. [#23](https://github.com/pypeclub/pype/issues/23)
- _(deadline)_ Deadline can now correctly differentiate between staging and production pype. [#154](https://github.com/pypeclub/pype/issues/154)
- _(deadline)_ `PYPE_PYTHON_EXE` env variable can now be used to direct publishing to explicit python installation. [#120](https://github.com/pypeclub/pype/issues/120)
- _(nuke)_ Nuke now check for new version of loaded data on file open. [#140](https://github.com/pypeclub/pype/issues/140)
- _(nuke)_ frame range and limit checkboxes are now exposed on write node. [#119](https://github.com/pypeclub/pype/issues/119)



**fix:**

- _(nukestudio)_ Project Location was using backslashes which was breaking nukestudio native exporting in certains configurations [#82](https://github.com/pypeclub/pype/issues/82)
- _(nukestudio)_ Duplicity in hierarchy tags was prone to throwing publishing error [#130](https://github.com/pypeclub/pype/issues/130), [#144](https://github.com/pypeclub/pype/issues/144)
- _(ftrack)_ multiple stability improvements [#157](https://github.com/pypeclub/pype/issues/157), [#159](https://github.com/pypeclub/pype/issues/159), [#128](https://github.com/pypeclub/pype/issues/128), [#118](https://github.com/pypeclub/pype/issues/118), [#127](https://github.com/pypeclub/pype/issues/127)
- _(deadline)_ multipart EXRs were stopping review publishing on the farm. They are still not supported for automatic review generation, but the publish will go through correctly without the quicktime. [#155](https://github.com/pypeclub/pype/issues/155)
- _(deadline)_ If deadline is non-responsive it will no longer freeze host when publishing [#149](https://github.com/pypeclub/pype/issues/149)
- _(deadline)_ Sometimes deadline was trying to launch render before all the source data was coppied over. [#137](https://github.com/pypeclub/pype/issues/137) _(harmony)_ Basic implementation of **Toon Boom Harmony** has been added. [#142](https://github.com/pypeclub/pype/issues/142)
- _(nuke)_ Filepath knob wasn't updated properly. [#131](https://github.com/pypeclub/pype/issues/131)
- _(maya)_ When extracting animation, the "Write Color Set" options on the instance were not respected. [#108](https://github.com/pypeclub/pype/issues/108)
- _(maya)_ Attribute overrides for AOV only worked for the legacy render layers. Now it works for new render setup as well [#132](https://github.com/pypeclub/pype/issues/132)
- _(maya)_ Stability and usability improvements in yeti workflow [#104](https://github.com/pypeclub/pype/issues/104)



<a name="2.8.0"></a>
## 2.8.0 ##

_**release date:** 20 April 2020_

**new:**

- _(pype)_ Option to generate slates from json templates. [PYPE-628] [#26](https://github.com/pypeclub/pype/issues/26)
- _(pype)_ It is now possible to automate loading of published subsets into any scene. Documentation will follow :). [PYPE-611] [#24](https://github.com/pypeclub/pype/issues/24)

**fix:**

- _(maya)_ Some Redshift render tokens could break publishing. [PYPE-778] [#33](https://github.com/pypeclub/pype/issues/33)
- _(maya)_ Publish was not preserving maya file extension. [#39](https://github.com/pypeclub/pype/issues/39)
- _(maya)_ Rig output validator was failing on nodes without shapes. [#40](https://github.com/pypeclub/pype/issues/40)
- _(maya)_ Yeti caches can now be properly versioned up in the scene inventory. [#40](https://github.com/pypeclub/pype/issues/40)
- _(nuke)_ Build first workfiles was not accepting jpeg sequences. [#34](https://github.com/pypeclub/pype/issues/34)
- _(deadline)_ Trying to generate ffmpeg review from multipart EXRs no longer crashes publishing. [PYPE-781]
- _(deadline)_ Render publishing is more stable in multiplatform environments. [PYPE-775]



<a name="2.7.0"></a>
## 2.7.0 ##

_**release date:** 30 March 2020_

**new:**

- _(maya)_ Artist can now choose to load multiple references of the same subset at once [PYPE-646, PYPS-81]
- _(nuke)_ Option to use named OCIO colorspaces for review colour baking. [PYPS-82]
- _(pype)_ Pype can now work with `master` versions for publishing and loading. These are non-versioned publishes that are overwritten with the latest version during publish. These are now supported in all the GUIs, but their publishing is deactivated by default. [PYPE-653]
- _(blender)_ Added support for basic blender workflow. We currently support `rig`, `model` and `animation` families. [PYPE-768]
- _(pype)_ Source timecode can now be used in burn-ins. [PYPE-777]
- _(pype)_ Review outputs profiles can now specify delivery resolution different than project setting [PYPE-759]
- _(nuke)_ Bookmark to current context is now added automatically to all nuke browser windows. [PYPE-712]

**change:**

- _(maya)_ It is now possible to publish camera without. baking. Keep in mind that unbaked cameras can't be guaranteed to work in other hosts. [PYPE-595]
- _(maya)_ All the renders from maya are now grouped in the loader by their Layer name. [PYPE-482]
- _(nuke/hiero)_ Any publishes from nuke and hiero can now be versioned independently of the workfile. [PYPE-728]


**fix:**

- _(nuke)_ Mixed slashes caused issues in ocio config path.
- _(pype)_ Intent field in pyblish GUI was passing label instead of value to ftrack. [PYPE-733]
- _(nuke)_ Publishing of pre-renders was inconsistent. [PYPE-766]
- _(maya)_ Handles and frame ranges were inconsistent in various places during publishing.
- _(nuke)_ Nuke was crashing if it ran into certain missing knobs. For example DPX output missing `autocrop` [PYPE-774]
- _(deadline)_ Project overrides were not working properly with farm render publishing.
- _(hiero)_ Problems with single frame plates publishing.
- _(maya)_ Redshift RenderPass token were breaking render publishing. [PYPE-778]
- _(nuke)_ Build first workfile was not accepting jpeg sequences.
- _(maya)_ Multipart (Multilayer) EXRs were breaking review publishing due to FFMPEG incompatiblity [PYPE-781]


<a name="2.6.0"></a>
## 2.6.0 ##

_**release date:** 9 March 2020_

**change:**
- _(maya)_ render publishing has been simplified and made more robust. Render setup layers are now automatically added to publishing subsets and `render globals` family has been replaced with simple `render` [PYPE-570]
- _(avalon)_ change context and workfiles apps, have been merged into one, that allows both actions to be performed at the same time. [PYPE-747]
- _(pype)_ thumbnails are now automatically propagate to asset from the last published subset in the loader
- _(ftrack)_ publishing comment and intent are now being published to ftrack note as well as describtion. [PYPE-727]
- _(pype)_ when overriding existing version new old representations are now overriden, instead of the new ones just being appended. (to allow this behaviour, the version validator need to be disabled. [PYPE-690])
- _(pype)_ burnin preset has been significantly simplified. It now doesn't require passing function to each field, but only need the actual text template. to use this, all the current burnin PRESETS MUST BE UPDATED for all the projects.
- _(ftrack)_ credentials are now stored on a per server basis, so it's possible to switch between ftrack servers without having to log in and out. [PYPE-723]


**new:**
- _(pype)_ production and development deployments now have different colour of the tray icon. Orange for Dev and Green for production [PYPE-718]
- _(maya)_ renders can now be attached to a publishable subset rather than creating their own subset. For example it is possible to create a reviewable `look` or `model` render and have it correctly attached as a representation of the subsets [PYPE-451]
- _(maya)_ after saving current scene into a new context (as a new shot for instance), all the scene publishing subsets data gets re-generated automatically to match the new context [PYPE-532]
- _(pype)_ we now support project specific publish, load and create plugins [PYPE-740]
- _(ftrack)_ new action that allow archiving/deleting old published versions. User can keep how many of the latest version to keep when the action is ran. [PYPE-748, PYPE-715]
- _(ftrack)_ it is now possible to monitor and restart ftrack event server using ftrack action. [PYPE-658]
- _(pype)_ validator that prevent accidental overwrites of previously published versions. [PYPE-680]
- _(avalon)_ avalon core updated to version 5.6.0
- _(maya)_ added validator to make sure that relative paths are used when publishing arnold standins.
- _(nukestudio)_ it is now possible to extract and publish audio family from clip in nuke studio [PYPE-682]

**fix**:
- _(maya)_ maya set framerange button was ignoring handles [PYPE-719]
- _(ftrack)_ sync to avalon was sometime crashing when ran on empty project
- _(nukestudio)_ publishing same shots after they've been previously archived/deleted would result in a crash. [PYPE-737]
- _(nuke)_ slate workflow was breaking in certain scenarios. [PYPE-730]
- _(pype)_ rendering publish workflow has been significantly improved to prevent error resulting from implicit render collection. [PYPE-665, PYPE-746]
- _(pype)_ launching application on a non-synced project resulted in obscure [PYPE-528]
- _(pype)_ missing keys in burnins no longer result in an error. [PYPE-706]
- _(ftrack)_ create folder structure action was sometimes failing for project managers due to wrong permissions.
- _(Nukestudio)_ using `source` in the start frame tag could result in wrong frame range calculation
- _(ftrack)_ sync to avalon action and event have been improved by catching more edge cases and provessing them properly.


<a name="2.5"></a>
## 2.5.0 ##

_**release date:** 11 Feb 2020_

**change:**
- _(pype)_ added many logs for easier debugging
- _(pype)_ review presets can now be separated between 2d and 3d renders [PYPE-693]
- _(pype)_ anatomy module has been greatly improved to allow for more dynamic pulblishing and faster debugging [PYPE-685]
- _(pype)_ avalon schemas have been moved from `pype-config` to `pype` repository, for simplification. [PYPE-670]
- _(ftrack)_ updated to latest ftrack API
- _(ftrack)_ publishing comments now appear in ftrack also as a note on version with customisable category [PYPE-645]
- _(ftrack)_ delete asset/subset action had been improved. It is now able to remove multiple entities and descendants of the selected entities [PYPE-361, PYPS-72]
- _(workfiles)_ added date field to workfiles app [PYPE-603]
- _(maya)_ old deprecated loader have been removed in favour of a single unified reference loader (old scenes will upgrade automatically to the new loader upon opening) [PYPE-633, PYPE-697]
- _(avalon)_ core updated to 5.5.15 [PYPE-671]
- _(nuke)_ library loader is now available in nuke [PYPE-698]


**new:**
- _(pype)_ added pype render wrapper to allow rendering on mixed platform farms. [PYPE-634]
- _(pype)_ added `pype launch` command. It let's admin run applications with dynamically built environment based on the given context. [PYPE-634]
- _(pype)_ added support for extracting review sequences with burnins [PYPE-657]
- _(publish)_ users can now set intent next to a comment when publishing. This will then be reflected on an attribute in ftrack. [PYPE-632]
- _(burnin)_ timecode can now be added to burnin
- _(burnin)_ datetime keys can now be added to burnin and anatomy [PYPE-651]
- _(burnin)_ anatomy templates can now be used in burnins. [PYPE=626]
- _(nuke)_ new validator for render resolution
- _(nuke)_ support for attach slate to nuke renders [PYPE-630]
- _(nuke)_ png sequences were added to loaders
- _(maya)_ added maya 2020 compatibility [PYPE-677]
- _(maya)_ ability to publish and load .ASS standin sequences [PYPS-54]
- _(pype)_ thumbnails can now be published and are visible in the loader. `AVALON_THUMBNAIL_ROOT` environment variable needs to be set for this to work  [PYPE-573, PYPE-132]
- _(blender)_ base implementation of blender was added with publishing and loading of .blend files [PYPE-612]
- _(ftrack)_ new action for preparing deliveries [PYPE-639]


**fix**:
- _(burnin)_ more robust way of finding ffmpeg for burnins.
- _(pype)_ improved UNC paths remapping when sending to farm.
- _(pype)_ float frames sometimes made their way to representation context in database, breaking loaders [PYPE-668]
- _(pype)_ `pype install --force` was failing sometimes [PYPE-600]
- _(pype)_ padding in published files got calculated wrongly sometimes. It is now instead being always read from project anatomy. [PYPE-667]
- _(publish)_ comment publishing was failing in certain situations
- _(ftrack)_ multiple edge case scenario fixes in auto sync and sync-to-avalon action
- _(ftrack)_ sync to avalon now works on empty projects
- _(ftrack)_ thumbnail update event was failing when deleting entities [PYPE-561]
- _(nuke)_ loader applies proper colorspaces from Presets
- _(nuke)_ publishing handles didn't always work correctly [PYPE-686]
- _(maya)_ assembly publishing and loading wasn't working correctly




<a name="2.4.0"></a>
## 2.4.0 ##

_**release date:** 9 Dec 2019_

**change:**
- _(ftrack)_ version to status ftrack event can now be configured from Presets
  - based on preset `presets/ftracc/ftrack_config.json["status_version_to_task"]`
- _(ftrack)_ sync to avalon event has been completely re-written. It now supports most of the project management situations on ftrack including moving, renaming and deleting entities, updating attributes and working with tasks.
- _(ftrack)_ sync to avalon action has been also re-writen. It is now much faster (up to 100 times depending on a project structure), has much better logging and reporting on encountered problems, and is able to handle much more complex situations.
- _(ftrack)_ sync to avalon trigger by checking `auto-sync` toggle on ftrack [PYPE-504]
- _(pype)_ various new features in the REST api
- _(pype)_ new visual identity used across pype
- _(pype)_ started moving all requirements to pip installation rather than vendorising them in pype repository. Due to a few yet unreleased packages, this means that pype can temporarily be only installed in the offline mode.

**new:**
- _(nuke)_ support for publishing gizmos and loading them as viewer processes
- _(nuke)_ support for publishing nuke nodes from backdrops and loading them back
- _(pype)_ burnins can now work with start and end frames as keys
  - use keys `{frame_start}`, `{frame_end}` and `{current_frame}` in burnin preset to use them. [PYPS-44,PYPS-73, PYPE-602]
- _(pype)_ option to filter logs by user and level in loggin GUI
- _(pype)_ image family added to standalone publisher [PYPE-574]
- _(pype)_ matchmove family added to standalone publisher [PYPE-574]
- _(nuke)_ validator for comparing arbitrary knobs with values from presets
- _(maya)_ option to force maya to copy textures in the new look publish rather than hardlinking them
- _(pype)_ comments from pyblish GUI are now being added to ftrack version
- _(maya)_ validator for checking outdated containers in the scene
- _(maya)_ option to publish and load arnold standin sequence [PYPE-579, PYPS-54]

**fix**:
- _(pype)_ burnins were not respecting codec of the input video
- _(nuke)_ lot's of various nuke and nuke studio fixes across the board [PYPS-45]
- _(pype)_ workfiles app is not launching with the start of the app by default [PYPE-569]
- _(ftrack)_ ftrack integration during publishing was failing under certain situations [PYPS-66]
- _(pype)_ minor fixes in REST api
- _(ftrack)_ status change event was crashing when the target status was missing [PYPS-68]
- _(ftrack)_ actions will try to reconnect if they fail for some reason
- _(maya)_ problems with fps mapping when using float FPS values
- _(deadline)_ overall improvements to deadline publishing
- _(setup)_ environment variables are now remapped on the fly based on the platform pype is running on. This fixes many issues in mixed platform environments.


<a name="2.3.6"></a>
## 2.3.6 #

_**release date:** 27 Nov 2019_

**hotfix**:
- _(ftrack)_ was hiding important debug logo
- _(nuke)_ crashes during workfile publishing
- _(ftrack)_ event server crashes because of signal problems
- _(muster)_ problems with muster render submissions
- _(ftrack)_ thumbnail update event syntax errors


## 2.3.0 ##
_release date: 6 Oct 2019_

**new**:
- _(maya)_ support for yeti rigs and yeti caches
- _(maya)_ validator for comparing arbitrary attributes against ftrack
- _(pype)_ burnins can now show current date and time
- _(muster)_ pools can now be set in render globals in maya
- _(pype)_ Rest API has been implemented in beta stage
- _(nuke)_ LUT loader has been added
- _(pype)_ rudimentary user module has been added as preparation for user management
- _(pype)_ a simple logging GUI has been added to pype tray
- _(nuke)_ nuke can now bake input process into mov
- _(maya)_ imported models now have selection handle displayed by defaulting
- _(avalon)_ it's is now possible to load multiple assets at once using loader
- _(maya)_ added ability to automatically connect yeti rig to a mesh upon loading

**changed**:
- _(ftrack)_ event server now runs two parallel processes and is able to keep queue of events to process.
- _(nuke)_ task name is now added to all rendered subsets
- _(pype)_ adding more families to standalone publisher
- _(pype)_ standalone publisher now uses pyblish-lite
- _(pype)_ standalone publisher can now create review quicktimes
- _(ftrack)_ queries to ftrack were sped up
- _(ftrack)_ multiple ftrack action have been deprecated
- _(avalon)_ avalon upstream has been updated to 5.5.0
- _(nukestudio)_ published transforms can now be animated
-

**fix**:
- _(maya)_ fps popup button didn't work in some cases
- _(maya)_ geometry instances and references in maya were losing shader assignments
- _(muster)_ muster rendering templates were not working correctly
- _(maya)_ arnold tx texture conversion wasn't respecting colorspace set by the artist
- _(pype)_ problems with avalon db sync
- _(maya)_ ftrack was rounding FPS making it inconsistent
- _(pype)_ wrong icon names in Creator
- _(maya)_ scene inventory wasn't showing anything if representation was removed from database after it's been loaded to the scene
- _(nukestudio)_ multiple bugs squashed
- _(loader)_ loader was taking long time to show all the loading action when first launcher in maya

## 2.2.0 ##
_release date: 8 Sept 2019_

**new**:
- _(pype)_ add customisable workflow for creating quicktimes from renders or playblasts
- _(nuke)_ option to choose deadline chunk size on write nodes
- _(nukestudio)_ added option to publish soft effects (subTrackItems) from NukeStudio as subsets including LUT files. these can then be loaded in nuke or NukeStudio
- _(nuke)_ option to build nuke script from previously published latest versions of plate and render subsets.
- _(nuke)_ nuke writes now have deadline tab.
- _(ftrack)_ Prepare Project action can now be used for creating the base folder structure on disk and in ftrack, setting up all the initial project attributes and it automatically prepares `pype_project_config` folder for the given project.
- _(clockify)_ Added support for time tracking in clockify. This currently in addition to ftrack time logs, but does not completely replace them.
- _(pype)_ any attributes in Creator and Loader plugins can now be customised using pype preset system

**changed**:
- nukestudio now uses workio API for workfiles
- _(maya)_ "FIX FPS" prompt in maya now appears in the middle of the screen
- _(muster)_ can now be configured with custom templates
- _(pype)_ global publishing plugins can now be configured using presets as well as host specific ones


**fix**:
- wrong version retrieval from path in certain scenarios
- nuke reset resolution wasn't working in certain scenarios

## 2.1.0 ##
_release date: 6 Aug 2019_

A large cleanup release. Most of the change are under the hood.

**new**:
- _(pype)_ add customisable workflow for creating quicktimes from renders or playblasts
- _(pype)_ Added configurable option to add burnins to any generated quicktimes
- _(ftrack)_ Action that identifies what machines pype is running on.
- _(system)_ unify subprocess calls
- _(maya)_ add audio to review quicktimes
- _(nuke)_ add crop before write node to prevent overscan problems in ffmpeg
- **Nuke Studio** publishing and workfiles support
- **Muster** render manager support
- _(nuke)_ Framerange, FPS and Resolution are set automatically at startup
- _(maya)_ Ability to load published sequences as image planes
- _(system)_ Ftrack event that sets asset folder permissions based on task assignees in ftrack.
- _(maya)_ Pyblish plugin that allow validation of maya attributes
- _(system)_ added better startup logging to tray debug, including basic connection information
- _(avalon)_ option to group published subsets to groups in the loader
- _(avalon)_ loader family filters are working now

**changed**:
- change multiple key attributes to unify their behaviour across the pipeline
  - `frameRate` to `fps`
  - `startFrame` to `frameStart`
  - `endFrame` to `frameEnd`
  - `fstart` to `frameStart`
  - `fend` to `frameEnd`
  - `handle_start` to `handleStart`
  - `handle_end` to `handleEnd`
  - `resolution_width` to `resolutionWidth`
  - `resolution_height` to `resolutionHeight`
  - `pixel_aspect` to `pixelAspect`

- _(nuke)_ write nodes are now created inside group with only some attributes editable by the artist
- rendered frames are now deleted from temporary location after their publishing is finished.
- _(ftrack)_ RV action can now be launched from any entity
- after publishing only refresh button is now available in pyblish UI
- added context instance pyblish-lite so that artist knows if context plugin fails
- _(avalon)_ allow opening selected files using enter key
- _(avalon)_ core updated to v5.2.9 with our forked changes on top

**fix**:
- faster hierarchy retrieval from db
- _(nuke)_ A lot of stability enhancements
- _(nuke studio)_ A lot of stability enhancements
- _(nuke)_ now only renders a single write node on farm
- _(ftrack)_ pype would crash when launcher project level task
- work directory was sometimes not being created correctly
- major pype.lib cleanup. Removing of unused functions, merging those that were doing the same and general house cleaning.
- _(avalon)_ subsets in maya 2019 weren't behaving correctly in the outliner
