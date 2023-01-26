# Changelog

## [3.15.0](https://github.com/ynput/OpenPype/tree/3.15.0)

[Full Changelog](https://github.com/ynput/OpenPype/compare/3.14.10...3.15.0)

**Deprecated:**

- General: Fill default values of new publish template profiles [\#4245](https://github.com/ynput/OpenPype/pull/4245)

### 📖 Documentation

- documentation: Split tools into separate entries [\#4342](https://github.com/ynput/OpenPype/pull/4342)
- Documentation: Fix harmony docs [\#4301](https://github.com/ynput/OpenPype/pull/4301)
- Remove staging logic set by OpenPype version [\#3979](https://github.com/ynput/OpenPype/pull/3979)

**🆕 New features**

- General: Push to studio library [\#4284](https://github.com/ynput/OpenPype/pull/4284)
- Colorspace Management and Distribution [\#4195](https://github.com/ynput/OpenPype/pull/4195)
- Nuke: refactor to latest publisher workfow [\#4006](https://github.com/ynput/OpenPype/pull/4006)
- Update to Python 3.9 [\#3546](https://github.com/ynput/OpenPype/pull/3546)

**🚀 Enhancements**

- Unreal: Don't use mongo queries in 'ExistingLayoutLoader' [\#4356](https://github.com/ynput/OpenPype/pull/4356)
- General: Loader and Creator plugins can be disabled [\#4310](https://github.com/ynput/OpenPype/pull/4310)
- General: Unbind poetry version [\#4306](https://github.com/ynput/OpenPype/pull/4306)
- General: Enhanced enum def items [\#4295](https://github.com/ynput/OpenPype/pull/4295)
- Git: add pre-commit hooks [\#4289](https://github.com/ynput/OpenPype/pull/4289)
- Tray Publisher: Improve Online family functionality [\#4263](https://github.com/ynput/OpenPype/pull/4263)
- General: Update MacOs to PySide6 [\#4255](https://github.com/ynput/OpenPype/pull/4255)
- Build: update to Gazu in toml [\#4208](https://github.com/ynput/OpenPype/pull/4208)
- Global: adding imageio to settings [\#4158](https://github.com/ynput/OpenPype/pull/4158)
- Blender: added project settings for validator no colons in name [\#4149](https://github.com/ynput/OpenPype/pull/4149)
- Dockerfile for Debian Bullseye [\#4108](https://github.com/ynput/OpenPype/pull/4108)
- AfterEffects: publish multiple compositions [\#4092](https://github.com/ynput/OpenPype/pull/4092)
- AfterEffects: make new publisher default [\#4056](https://github.com/ynput/OpenPype/pull/4056)
- Photoshop: make new publisher default [\#4051](https://github.com/ynput/OpenPype/pull/4051)
- Feature/multiverse [\#4046](https://github.com/ynput/OpenPype/pull/4046)
- Tests: add support for deadline for automatic tests [\#3989](https://github.com/ynput/OpenPype/pull/3989)
- Add version to shortcut name [\#3906](https://github.com/ynput/OpenPype/pull/3906)
- TrayPublisher: Removed from experimental tools [\#3667](https://github.com/ynput/OpenPype/pull/3667)

**🐛 Bug fixes**

- change 3.7 to 3.9 in folder name [\#4354](https://github.com/ynput/OpenPype/pull/4354)
- PushToProject: Fix hierarchy of project change [\#4350](https://github.com/ynput/OpenPype/pull/4350)
- Fix photoshop workfile save-as [\#4347](https://github.com/ynput/OpenPype/pull/4347)
- Nuke Input process node sourcing improvements [\#4341](https://github.com/ynput/OpenPype/pull/4341)
- New publisher: Some validation plugin tweaks [\#4339](https://github.com/ynput/OpenPype/pull/4339)
- Harmony: fix unable to change workfile on Mac [\#4334](https://github.com/ynput/OpenPype/pull/4334)
- Global: fixing in-place source publishing for editorial [\#4333](https://github.com/ynput/OpenPype/pull/4333)
- General: Use class constants of QMessageBox [\#4332](https://github.com/ynput/OpenPype/pull/4332)
- TVPaint: Fix plugin for TVPaint 11.7 [\#4328](https://github.com/ynput/OpenPype/pull/4328)
- Exctract OTIO review has improved quality [\#4325](https://github.com/ynput/OpenPype/pull/4325)
- Ftrack: fix typos causing bugs in sync [\#4322](https://github.com/ynput/OpenPype/pull/4322)
- General: Python 2 compatibility of instance collector [\#4320](https://github.com/ynput/OpenPype/pull/4320)
- Slack: user groups speedup [\#4318](https://github.com/ynput/OpenPype/pull/4318)
- Maya: Bug - Multiverse extractor executed on plain animation family [\#4315](https://github.com/ynput/OpenPype/pull/4315)
- Fix run\_documentation.ps1 [\#4312](https://github.com/ynput/OpenPype/pull/4312)
- Nuke: new creators fixes [\#4308](https://github.com/ynput/OpenPype/pull/4308)
- General: missing comment on standalone and tray publisher [\#4303](https://github.com/ynput/OpenPype/pull/4303)
- AfterEffects: Fix for audio from mp4 layer [\#4296](https://github.com/ynput/OpenPype/pull/4296)
- General: Update gazu in poetry lock [\#4247](https://github.com/ynput/OpenPype/pull/4247)
- Bug: Fixing version detection and filtering in Igniter [\#3914](https://github.com/ynput/OpenPype/pull/3914)
- Bug: Create missing version dir [\#3903](https://github.com/ynput/OpenPype/pull/3903)

**🔀 Refactored code**

- Remove redundant export\_alembic method. [\#4293](https://github.com/ynput/OpenPype/pull/4293)
- Igniter: Use qtpy modules instead of Qt [\#4237](https://github.com/ynput/OpenPype/pull/4237)

**Merged pull requests:**

- Sort families by alphabetical order in the Create plugin [\#4346](https://github.com/ynput/OpenPype/pull/4346)
- Global: Validate unique subsets [\#4336](https://github.com/ynput/OpenPype/pull/4336)
- Maya: Collect instances preserve handles even if frameStart + frameEnd matches context [\#3437](https://github.com/ynput/OpenPype/pull/3437)


## [3.14.10](https://github.com/ynput/OpenPype/tree/3.14.10)

[Full Changelog](https://github.com/ynput/OpenPype/compare/3.14.9...3.14.10)

**🆕 New features**

- Global | Nuke: Creator placeholders in workfile template builder [\#4266](https://github.com/ynput/OpenPype/pull/4266)
- Slack: Added dynamic message [\#4265](https://github.com/ynput/OpenPype/pull/4265)
- Blender: Workfile Loader [\#4234](https://github.com/ynput/OpenPype/pull/4234)
- Unreal: Publishing and Loading for UAssets [\#4198](https://github.com/ynput/OpenPype/pull/4198)
- Publish: register publishes without copying them [\#4157](https://github.com/ynput/OpenPype/pull/4157)

**🚀 Enhancements**

- General: Added install method with docstring to HostBase [\#4298](https://github.com/ynput/OpenPype/pull/4298)
- Traypublisher: simple editorial multiple edl [\#4248](https://github.com/ynput/OpenPype/pull/4248)
- General: Extend 'IPluginPaths' to have more available methods [\#4214](https://github.com/ynput/OpenPype/pull/4214)
- Refactorization of folder coloring [\#4211](https://github.com/ynput/OpenPype/pull/4211)
- Flame - loading multilayer with controlled layer names [\#4204](https://github.com/ynput/OpenPype/pull/4204)

**🐛 Bug fixes**

- Unreal: fix missing `maintained_selection` call [\#4300](https://github.com/ynput/OpenPype/pull/4300)
- Ftrack: Fix receive of host ip on MacOs [\#4288](https://github.com/ynput/OpenPype/pull/4288)
- SiteSync: sftp connection failing when shouldnt be tested [\#4278](https://github.com/ynput/OpenPype/pull/4278)
- Deadline: fix default value for passing mongo url [\#4275](https://github.com/ynput/OpenPype/pull/4275)
- Scene Manager: Fix variable name [\#4268](https://github.com/ynput/OpenPype/pull/4268)
- Slack: notification fails because of missing published path [\#4264](https://github.com/ynput/OpenPype/pull/4264)
- hiero: creator gui with min max  [\#4257](https://github.com/ynput/OpenPype/pull/4257)
- NiceCheckbox: Fix checker positioning in Python 2 [\#4253](https://github.com/ynput/OpenPype/pull/4253)
- Publisher: Fix 'CreatorType' not equal for Python 2 DCCs [\#4249](https://github.com/ynput/OpenPype/pull/4249)
- Deadline: fix dependencies [\#4242](https://github.com/ynput/OpenPype/pull/4242)
- Houdini: hotfix instance data access [\#4236](https://github.com/ynput/OpenPype/pull/4236)
- bugfix/image plane load error [\#4222](https://github.com/ynput/OpenPype/pull/4222)
- Hiero: thumbnail from multilayer exr [\#4209](https://github.com/ynput/OpenPype/pull/4209)

**🔀 Refactored code**

- Resolve: Use qtpy in Resolve [\#4254](https://github.com/ynput/OpenPype/pull/4254)
- Houdini: Use qtpy in Houdini [\#4252](https://github.com/ynput/OpenPype/pull/4252)
- Max: Use qtpy in Max [\#4251](https://github.com/ynput/OpenPype/pull/4251)
- Maya: Use qtpy in Maya [\#4250](https://github.com/ynput/OpenPype/pull/4250)
- Hiero: Use qtpy in Hiero [\#4240](https://github.com/ynput/OpenPype/pull/4240)
- Nuke: Use qtpy in Nuke [\#4239](https://github.com/ynput/OpenPype/pull/4239)
- Flame: Use qtpy in flame [\#4238](https://github.com/ynput/OpenPype/pull/4238)
- General: Legacy io not used in global plugins [\#4134](https://github.com/ynput/OpenPype/pull/4134)

**Merged pull requests:**

- Bump json5 from 1.0.1 to 1.0.2 in /website [\#4292](https://github.com/ynput/OpenPype/pull/4292)
- Maya: Fix validate frame range repair + fix create render with deadline disabled [\#4279](https://github.com/ynput/OpenPype/pull/4279)


## [3.14.9](https://github.com/pypeclub/OpenPype/tree/3.14.9)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.14.8...3.14.9)

### 📖 Documentation

- Documentation: Testing on Deadline [\#4185](https://github.com/pypeclub/OpenPype/pull/4185)
- Consistent Python version [\#4160](https://github.com/pypeclub/OpenPype/pull/4160)

**🆕 New features**

- Feature/op 4397 gl tf extractor for maya [\#4192](https://github.com/pypeclub/OpenPype/pull/4192)
- Maya: Extractor for Unreal SkeletalMesh [\#4174](https://github.com/pypeclub/OpenPype/pull/4174)
- 3dsmax: integration [\#4168](https://github.com/pypeclub/OpenPype/pull/4168)
- Blender: Extract Alembic Animations [\#4128](https://github.com/pypeclub/OpenPype/pull/4128)
- Unreal: Load Alembic Animations [\#4127](https://github.com/pypeclub/OpenPype/pull/4127)

**🚀 Enhancements**

- Houdini: Use new interface class name for publish host [\#4220](https://github.com/pypeclub/OpenPype/pull/4220)
- General: Default command for headless mode is interactive [\#4203](https://github.com/pypeclub/OpenPype/pull/4203)
- Maya: Enhanced ASS publishing [\#4196](https://github.com/pypeclub/OpenPype/pull/4196)
- Feature/op 3924 implement ass extractor [\#4188](https://github.com/pypeclub/OpenPype/pull/4188)
- File transactions: Source path is destination path [\#4184](https://github.com/pypeclub/OpenPype/pull/4184)
- Deadline: improve environment processing [\#4182](https://github.com/pypeclub/OpenPype/pull/4182)
- General: Comment per instance in Publisher [\#4178](https://github.com/pypeclub/OpenPype/pull/4178)
- Ensure Mongo database directory exists in Windows. [\#4166](https://github.com/pypeclub/OpenPype/pull/4166)
- Note about unrestricted execution on Windows. [\#4161](https://github.com/pypeclub/OpenPype/pull/4161)
- Maya: Enable thumbnail transparency on extraction. [\#4147](https://github.com/pypeclub/OpenPype/pull/4147)
- Maya: Disable viewport Pan/Zoom on playblast extraction. [\#4146](https://github.com/pypeclub/OpenPype/pull/4146)
- Maya: Optional viewport refresh on pointcache extraction [\#4144](https://github.com/pypeclub/OpenPype/pull/4144)
- CelAction: refactory integration to current openpype [\#4140](https://github.com/pypeclub/OpenPype/pull/4140)
- Maya: create and publish bounding box geometry [\#4131](https://github.com/pypeclub/OpenPype/pull/4131)
- Changed the UOpenPypePublishInstance to use the UDataAsset class [\#4124](https://github.com/pypeclub/OpenPype/pull/4124)
- General: Collection Audio speed up [\#4110](https://github.com/pypeclub/OpenPype/pull/4110)
- Maya: keep existing AOVs when creating render instance [\#4087](https://github.com/pypeclub/OpenPype/pull/4087)
- General: Oiio conversion multipart fix [\#4060](https://github.com/pypeclub/OpenPype/pull/4060)

**🐛 Bug fixes**

- Publisher: Signal type issues in Python 2 DCCs [\#4230](https://github.com/pypeclub/OpenPype/pull/4230)
- Blender: Fix Layout Family Versioning [\#4228](https://github.com/pypeclub/OpenPype/pull/4228)
- Blender: Fix Create Camera "Use selection" [\#4226](https://github.com/pypeclub/OpenPype/pull/4226)
- TrayPublisher - join needs list [\#4224](https://github.com/pypeclub/OpenPype/pull/4224)
- General: Event callbacks pass event to callbacks as expected [\#4210](https://github.com/pypeclub/OpenPype/pull/4210)
- Build:Revert .toml update of Gazu [\#4207](https://github.com/pypeclub/OpenPype/pull/4207)
- Nuke: fixed imageio node overrides subset filter [\#4202](https://github.com/pypeclub/OpenPype/pull/4202)
- Maya: pointcache [\#4201](https://github.com/pypeclub/OpenPype/pull/4201)
- Unreal: Support for Unreal Engine 5.1 [\#4199](https://github.com/pypeclub/OpenPype/pull/4199)
- General: Integrate thumbnail looks for thumbnail to multiple places [\#4181](https://github.com/pypeclub/OpenPype/pull/4181)
- Various minor bugfixes [\#4172](https://github.com/pypeclub/OpenPype/pull/4172)
- Nuke/Hiero: Remove tkinter library paths before launch [\#4171](https://github.com/pypeclub/OpenPype/pull/4171)
- Flame: vertical alignment of layers [\#4169](https://github.com/pypeclub/OpenPype/pull/4169)
- Nuke: correct detection of viewer and display [\#4165](https://github.com/pypeclub/OpenPype/pull/4165)
- Settings UI: Don't create QApplication if already exists [\#4156](https://github.com/pypeclub/OpenPype/pull/4156)
- General: Extract review handle start offset of sequences [\#4152](https://github.com/pypeclub/OpenPype/pull/4152)
- Maya: Maintain time connections on Alembic update. [\#4143](https://github.com/pypeclub/OpenPype/pull/4143)

**🔀 Refactored code**

- General: Use qtpy in modules and hosts UIs which are running in OpenPype process [\#4225](https://github.com/pypeclub/OpenPype/pull/4225)
- Tools: Use qtpy instead of Qt in standalone tools [\#4223](https://github.com/pypeclub/OpenPype/pull/4223)
- General: Use qtpy in settings UI [\#4215](https://github.com/pypeclub/OpenPype/pull/4215)

**Merged pull requests:**

- layout publish more than one container issue [\#4098](https://github.com/pypeclub/OpenPype/pull/4098)

## [3.14.8](https://github.com/pypeclub/OpenPype/tree/3.14.8)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.14.7...3.14.8)

**🚀 Enhancements**

- General: Refactored extract hierarchy plugin [\#4139](https://github.com/pypeclub/OpenPype/pull/4139)
- General: Find executable enhancement [\#4137](https://github.com/pypeclub/OpenPype/pull/4137)
- Ftrack: Reset session before instance processing [\#4129](https://github.com/pypeclub/OpenPype/pull/4129)
- Ftrack: Editorial asset sync issue [\#4126](https://github.com/pypeclub/OpenPype/pull/4126)
- Deadline: Build version resolving [\#4115](https://github.com/pypeclub/OpenPype/pull/4115)
- Houdini: New Publisher [\#3046](https://github.com/pypeclub/OpenPype/pull/3046)
- Fix: Standalone Publish Directories [\#4148](https://github.com/pypeclub/OpenPype/pull/4148)

**🐛 Bug fixes**

- Ftrack: Fix occational double parents issue [\#4153](https://github.com/pypeclub/OpenPype/pull/4153)
- General: Maketx executable issue [\#4136](https://github.com/pypeclub/OpenPype/pull/4136)
- Maya: Looks - add all connections [\#4135](https://github.com/pypeclub/OpenPype/pull/4135)
- General: Fix variable check in collect anatomy instance data [\#4117](https://github.com/pypeclub/OpenPype/pull/4117)

## [3.14.7](https://github.com/pypeclub/OpenPype/tree/3.14.7)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.14.6...3.14.7)

**🆕 New features**

- Hiero: loading effect family to timeline [\#4055](https://github.com/pypeclub/OpenPype/pull/4055)

**🚀 Enhancements**

- Photoshop: bug with pop-up window on Instance Creator [\#4121](https://github.com/pypeclub/OpenPype/pull/4121)
- Publisher: Open on specific tab [\#4120](https://github.com/pypeclub/OpenPype/pull/4120)
- Publisher: Hide unknown publish values [\#4116](https://github.com/pypeclub/OpenPype/pull/4116)
- Ftrack: Event server status give more information about version locations [\#4112](https://github.com/pypeclub/OpenPype/pull/4112)
- General: Allow higher numbers in frames and clips [\#4101](https://github.com/pypeclub/OpenPype/pull/4101)
- Publisher: Settings for validate frame range [\#4097](https://github.com/pypeclub/OpenPype/pull/4097)
- Publisher: Ignore escape button [\#4090](https://github.com/pypeclub/OpenPype/pull/4090)
- Flame: Loading clip with native colorspace resolved from mapping [\#4079](https://github.com/pypeclub/OpenPype/pull/4079)
- General: Extract review single frame output [\#4064](https://github.com/pypeclub/OpenPype/pull/4064)
- Publisher: Prepared common function for instance data cache [\#4063](https://github.com/pypeclub/OpenPype/pull/4063)
- Publisher: Easy access to publish page from create page [\#4058](https://github.com/pypeclub/OpenPype/pull/4058)
- General/TVPaint: Attribute defs dialog [\#4052](https://github.com/pypeclub/OpenPype/pull/4052)
- Publisher: Better reset defer [\#4048](https://github.com/pypeclub/OpenPype/pull/4048)
- Publisher: Add thumbnail sources [\#4042](https://github.com/pypeclub/OpenPype/pull/4042)

**🐛 Bug fixes**

- General: Move default settings for template name [\#4119](https://github.com/pypeclub/OpenPype/pull/4119)
- Slack: notification fail in new tray publisher [\#4118](https://github.com/pypeclub/OpenPype/pull/4118)
- Nuke: loaded nodes set to first tab [\#4114](https://github.com/pypeclub/OpenPype/pull/4114)
- Nuke: load image first frame [\#4113](https://github.com/pypeclub/OpenPype/pull/4113)
- Files Widget: Ignore case sensitivity of extensions [\#4096](https://github.com/pypeclub/OpenPype/pull/4096)
- Webpublisher: extension is lowercased in Setting and in uploaded files [\#4095](https://github.com/pypeclub/OpenPype/pull/4095)
- Publish Report Viewer: Fix small bugs [\#4086](https://github.com/pypeclub/OpenPype/pull/4086)
- Igniter: fix regex to match semver better [\#4085](https://github.com/pypeclub/OpenPype/pull/4085)
- Maya: aov filtering [\#4083](https://github.com/pypeclub/OpenPype/pull/4083)
- Flame/Flare: Loading to multiple batches [\#4080](https://github.com/pypeclub/OpenPype/pull/4080)
- hiero: creator from settings with set maximum [\#4077](https://github.com/pypeclub/OpenPype/pull/4077)
- Nuke: resolve hashes in file name only for frame token [\#4074](https://github.com/pypeclub/OpenPype/pull/4074)
- Publisher: Fix cache of asset docs [\#4070](https://github.com/pypeclub/OpenPype/pull/4070)
- Webpublisher: cleanup wp extract thumbnail [\#4067](https://github.com/pypeclub/OpenPype/pull/4067)
- Settings UI: Locked setting can't bypass lock [\#4066](https://github.com/pypeclub/OpenPype/pull/4066)
- Loader: Fix comparison of repre name [\#4053](https://github.com/pypeclub/OpenPype/pull/4053)
- Deadline: Extract environment subprocess failure [\#4050](https://github.com/pypeclub/OpenPype/pull/4050)

**🔀 Refactored code**

- General: Collect entities plugin minor changes [\#4089](https://github.com/pypeclub/OpenPype/pull/4089)
- General: Direct interfaces import [\#4065](https://github.com/pypeclub/OpenPype/pull/4065)

**Merged pull requests:**

- Bump loader-utils from 1.4.1 to 1.4.2 in /website [\#4100](https://github.com/pypeclub/OpenPype/pull/4100)
- Online family for Tray Publisher [\#4093](https://github.com/pypeclub/OpenPype/pull/4093)
- Bump loader-utils from 1.4.0 to 1.4.1 in /website [\#4081](https://github.com/pypeclub/OpenPype/pull/4081)
- remove underscore from subset name [\#4059](https://github.com/pypeclub/OpenPype/pull/4059)
- Alembic Loader as Arnold Standin [\#4047](https://github.com/pypeclub/OpenPype/pull/4047)

## [3.14.6](https://github.com/pypeclub/OpenPype/tree/3.14.6)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.14.5...3.14.6)

### 📖 Documentation

- Documentation: Minor updates to dev\_requirements.md [\#4025](https://github.com/pypeclub/OpenPype/pull/4025)

**🆕 New features**

- Nuke: add 13.2 variant [\#4041](https://github.com/pypeclub/OpenPype/pull/4041)

**🚀 Enhancements**

- Publish Report Viewer: Store reports locally on machine [\#4040](https://github.com/pypeclub/OpenPype/pull/4040)
- General: More specific error in burnins script [\#4026](https://github.com/pypeclub/OpenPype/pull/4026)
- General: Extract review does not crash with old settings overrides [\#4023](https://github.com/pypeclub/OpenPype/pull/4023)
- Publisher: Convertors for legacy instances [\#4020](https://github.com/pypeclub/OpenPype/pull/4020)
- workflows: adding milestone creator and assigner [\#4018](https://github.com/pypeclub/OpenPype/pull/4018)
- Publisher: Catch creator errors [\#4015](https://github.com/pypeclub/OpenPype/pull/4015)

**🐛 Bug fixes**

- Hiero - effect collection fixes [\#4038](https://github.com/pypeclub/OpenPype/pull/4038)
- Nuke - loader clip correct hash conversion in path [\#4037](https://github.com/pypeclub/OpenPype/pull/4037)
- Maya: Soft fail when applying capture preset [\#4034](https://github.com/pypeclub/OpenPype/pull/4034)
- Igniter: handle missing directory [\#4032](https://github.com/pypeclub/OpenPype/pull/4032)
- StandalonePublisher: Fix thumbnail publishing [\#4029](https://github.com/pypeclub/OpenPype/pull/4029)
- Experimental Tools: Fix publisher import [\#4027](https://github.com/pypeclub/OpenPype/pull/4027)
- Houdini: fix wrong path in ASS loader [\#4016](https://github.com/pypeclub/OpenPype/pull/4016)

**🔀 Refactored code**

- General: Import lib functions from lib [\#4017](https://github.com/pypeclub/OpenPype/pull/4017)

## [3.14.5](https://github.com/pypeclub/OpenPype/tree/3.14.5) (2022-10-24)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.14.4...3.14.5)

**🚀 Enhancements**

- Maya: add OBJ extractor to model family [\#4021](https://github.com/pypeclub/OpenPype/pull/4021)
- Publish report viewer tool [\#4010](https://github.com/pypeclub/OpenPype/pull/4010)
- Nuke | Global: adding custom tags representation filtering [\#4009](https://github.com/pypeclub/OpenPype/pull/4009)
- Publisher: Create context has shared data for collection phase [\#3995](https://github.com/pypeclub/OpenPype/pull/3995)
- Resolve: updating to v18 compatibility [\#3986](https://github.com/pypeclub/OpenPype/pull/3986)

**🐛 Bug fixes**

- TrayPublisher: Fix missing argument [\#4019](https://github.com/pypeclub/OpenPype/pull/4019)
- General: Fix python 2 compatibility of ffmpeg and oiio tools discovery [\#4011](https://github.com/pypeclub/OpenPype/pull/4011)

**🔀 Refactored code**

- Maya: Removed unused imports [\#4008](https://github.com/pypeclub/OpenPype/pull/4008)
- Unreal: Fix import of moved function [\#4007](https://github.com/pypeclub/OpenPype/pull/4007)
- Houdini: Change import of RepairAction [\#4005](https://github.com/pypeclub/OpenPype/pull/4005)
- Nuke/Hiero: Refactor openpype.api imports [\#4000](https://github.com/pypeclub/OpenPype/pull/4000)
- TVPaint: Defined with HostBase [\#3994](https://github.com/pypeclub/OpenPype/pull/3994)

**Merged pull requests:**

- Unreal: Remove redundant Creator stub [\#4012](https://github.com/pypeclub/OpenPype/pull/4012)
- Unreal: add `uproject` extension to Unreal project template [\#4004](https://github.com/pypeclub/OpenPype/pull/4004)
- Unreal: fix order of includes [\#4002](https://github.com/pypeclub/OpenPype/pull/4002)
- Fusion: Implement backwards compatibility \(+/- Fusion 17.2\) [\#3958](https://github.com/pypeclub/OpenPype/pull/3958)

## [3.14.4](https://github.com/pypeclub/OpenPype/tree/3.14.4) (2022-10-19)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.14.3...3.14.4)

**🆕 New features**

- Webpublisher: use max next published version number  for all items in batch [\#3961](https://github.com/pypeclub/OpenPype/pull/3961)
- General: Control Thumbnail integration via explicit configuration profiles [\#3951](https://github.com/pypeclub/OpenPype/pull/3951)

**🚀 Enhancements**

- Publisher: Multiselection in card view [\#3993](https://github.com/pypeclub/OpenPype/pull/3993)
- TrayPublisher: Original Basename cause crash too early [\#3990](https://github.com/pypeclub/OpenPype/pull/3990)
- Tray Publisher: add `originalBasename` data to simple creators [\#3988](https://github.com/pypeclub/OpenPype/pull/3988)
- General: Custom paths to ffmpeg and OpenImageIO tools [\#3982](https://github.com/pypeclub/OpenPype/pull/3982)
- Integrate: Preserve existing subset group if instance does not set it for new version [\#3976](https://github.com/pypeclub/OpenPype/pull/3976)
- Publisher: Prepare publisher controller  for remote publishing [\#3972](https://github.com/pypeclub/OpenPype/pull/3972)
- Maya: new style dataclasses in maya deadline submitter plugin [\#3968](https://github.com/pypeclub/OpenPype/pull/3968)
- Maya: Define preffered Qt bindings for Qt.py and qtpy [\#3963](https://github.com/pypeclub/OpenPype/pull/3963)
- Settings: Move imageio from project anatomy to project settings \[pypeclub\] [\#3959](https://github.com/pypeclub/OpenPype/pull/3959)
- TrayPublisher: Extract thumbnail for other families [\#3952](https://github.com/pypeclub/OpenPype/pull/3952)
- Publisher: Pass instance to subset name method on update [\#3949](https://github.com/pypeclub/OpenPype/pull/3949)
- General: Set root environments before DCC launch [\#3947](https://github.com/pypeclub/OpenPype/pull/3947)
- Refactor: changed legacy way to update database for Hero version integrate [\#3941](https://github.com/pypeclub/OpenPype/pull/3941)
- Maya: Moved plugin from global to maya [\#3939](https://github.com/pypeclub/OpenPype/pull/3939)
- Publisher: Create dialog is part of main window [\#3936](https://github.com/pypeclub/OpenPype/pull/3936)
- Fusion: Implement Alembic and FBX mesh loader [\#3927](https://github.com/pypeclub/OpenPype/pull/3927)

**🐛 Bug fixes**

- TrayPublisher: Disable sequences in batch mov creator [\#3996](https://github.com/pypeclub/OpenPype/pull/3996)
- Fix - tags might be missing on representation [\#3985](https://github.com/pypeclub/OpenPype/pull/3985)
- Resolve: Fix usage of functions from lib [\#3983](https://github.com/pypeclub/OpenPype/pull/3983)
- Maya: remove invalid prefix token for non-multipart outputs [\#3981](https://github.com/pypeclub/OpenPype/pull/3981)
- Ftrack: Fix schema cache for Python 2 [\#3980](https://github.com/pypeclub/OpenPype/pull/3980)
- Maya: add object to attr.s declaration [\#3973](https://github.com/pypeclub/OpenPype/pull/3973)
- Maya: Deadline OutputFilePath hack regression for Renderman [\#3950](https://github.com/pypeclub/OpenPype/pull/3950)
- Houdini: Fix validate workfile paths for non-parm file references [\#3948](https://github.com/pypeclub/OpenPype/pull/3948)
- Photoshop: missed sync published version of workfile with workfile [\#3946](https://github.com/pypeclub/OpenPype/pull/3946)
- Maya: Set default value for RenderSetupIncludeLights option [\#3944](https://github.com/pypeclub/OpenPype/pull/3944)
- Maya: fix regression of Renderman Deadline hack [\#3943](https://github.com/pypeclub/OpenPype/pull/3943)
- Kitsu: 2 fixes, nb\_frames and Shot type error [\#3940](https://github.com/pypeclub/OpenPype/pull/3940)
- Tray: Change order of attribute changes [\#3938](https://github.com/pypeclub/OpenPype/pull/3938)
- AttributeDefs: Fix crashing multivalue of files widget [\#3937](https://github.com/pypeclub/OpenPype/pull/3937)
- General: Fix links query on hero version [\#3900](https://github.com/pypeclub/OpenPype/pull/3900)
- Publisher: Files Drag n Drop cleanup [\#3888](https://github.com/pypeclub/OpenPype/pull/3888)

**🔀 Refactored code**

- Flame: Import lib functions from lib [\#3992](https://github.com/pypeclub/OpenPype/pull/3992)
- General: Fix deprecated warning in legacy creator [\#3978](https://github.com/pypeclub/OpenPype/pull/3978)
- Blender: Remove openpype api imports [\#3977](https://github.com/pypeclub/OpenPype/pull/3977)
- General: Use direct import of resources [\#3964](https://github.com/pypeclub/OpenPype/pull/3964)
- General: Direct settings imports [\#3934](https://github.com/pypeclub/OpenPype/pull/3934)
- General: import 'Logger' from 'openpype.lib' [\#3926](https://github.com/pypeclub/OpenPype/pull/3926)
- General: Remove deprecated functions from lib [\#3907](https://github.com/pypeclub/OpenPype/pull/3907)

**Merged pull requests:**

- Maya + Yeti: Load Yeti Cache fix frame number recognition [\#3942](https://github.com/pypeclub/OpenPype/pull/3942)
- Fusion: Implement callbacks to Fusion's event system thread [\#3928](https://github.com/pypeclub/OpenPype/pull/3928)
- Photoshop: create single frame image in Ftrack as review [\#3908](https://github.com/pypeclub/OpenPype/pull/3908)

## [3.14.3](https://github.com/pypeclub/OpenPype/tree/3.14.3) (2022-10-03)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.14.2...3.14.3)

**🚀 Enhancements**

- Publisher: Enhancement proposals [\#3897](https://github.com/pypeclub/OpenPype/pull/3897)

**🐛 Bug fixes**

- Maya: Fix Render single camera validator [\#3929](https://github.com/pypeclub/OpenPype/pull/3929)
- Flame: loading multilayer exr to batch/reel is working [\#3901](https://github.com/pypeclub/OpenPype/pull/3901)
- Hiero: Fix inventory check on launch [\#3895](https://github.com/pypeclub/OpenPype/pull/3895)
- WebPublisher: Fix import after refactor [\#3891](https://github.com/pypeclub/OpenPype/pull/3891)

**🔀 Refactored code**

- Maya: Remove unused 'openpype.api' imports in plugins [\#3925](https://github.com/pypeclub/OpenPype/pull/3925)
- Resolve: Use new Extractor location [\#3918](https://github.com/pypeclub/OpenPype/pull/3918)
- Unreal: Use new Extractor location [\#3917](https://github.com/pypeclub/OpenPype/pull/3917)
- Flame: Use new Extractor location [\#3916](https://github.com/pypeclub/OpenPype/pull/3916)
- Houdini: Use new Extractor location [\#3894](https://github.com/pypeclub/OpenPype/pull/3894)
- Harmony: Use new Extractor location [\#3893](https://github.com/pypeclub/OpenPype/pull/3893)

**Merged pull requests:**

- Maya: Fix Scene Inventory possibly starting off-screen due to maya preferences [\#3923](https://github.com/pypeclub/OpenPype/pull/3923)

## [3.14.2](https://github.com/pypeclub/OpenPype/tree/3.14.2) (2022-09-12)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.14.1...3.14.2)

### 📖 Documentation

- Documentation: Anatomy templates [\#3618](https://github.com/pypeclub/OpenPype/pull/3618)

**🆕 New features**

- Nuke: Build workfile by template [\#3763](https://github.com/pypeclub/OpenPype/pull/3763)
- Houdini: Publishing workfiles [\#3697](https://github.com/pypeclub/OpenPype/pull/3697)
- Global: making collect audio plugin global [\#3679](https://github.com/pypeclub/OpenPype/pull/3679)

**🚀 Enhancements**

- Flame: Adding Creator's retimed shot and handles switch [\#3826](https://github.com/pypeclub/OpenPype/pull/3826)
- Flame: OpenPype submenu to batch and media manager [\#3825](https://github.com/pypeclub/OpenPype/pull/3825)
- General: Better pixmap scaling [\#3809](https://github.com/pypeclub/OpenPype/pull/3809)
- Photoshop: attempt to speed up ExtractImage [\#3793](https://github.com/pypeclub/OpenPype/pull/3793)
- SyncServer: Added cli commands for sync server [\#3765](https://github.com/pypeclub/OpenPype/pull/3765)
- Kitsu: Drop 'entities root' setting. [\#3739](https://github.com/pypeclub/OpenPype/pull/3739)
- git: update gitignore [\#3722](https://github.com/pypeclub/OpenPype/pull/3722)
- Blender: Publisher collect workfile representation [\#3670](https://github.com/pypeclub/OpenPype/pull/3670)
- Maya: move set render settings menu entry [\#3669](https://github.com/pypeclub/OpenPype/pull/3669)
- Scene Inventory: Maya add actions to select from or to scene [\#3659](https://github.com/pypeclub/OpenPype/pull/3659)
- Scene Inventory: Add subsetGroup column [\#3658](https://github.com/pypeclub/OpenPype/pull/3658)

**🐛 Bug fixes**

- General: Fix Pattern access in client code [\#3828](https://github.com/pypeclub/OpenPype/pull/3828)
- Launcher: Skip opening last work file works for groups [\#3822](https://github.com/pypeclub/OpenPype/pull/3822)
- Maya: Publishing data key change [\#3811](https://github.com/pypeclub/OpenPype/pull/3811)
- Igniter: Fix status handling when version is already installed [\#3804](https://github.com/pypeclub/OpenPype/pull/3804)
- Resolve: Addon import is Python 2 compatible [\#3798](https://github.com/pypeclub/OpenPype/pull/3798)
- Hiero: retimed clip publishing is working [\#3792](https://github.com/pypeclub/OpenPype/pull/3792)
- nuke: validate write node is not failing due wrong type [\#3780](https://github.com/pypeclub/OpenPype/pull/3780)
- Fix - changed format of version string in pyproject.toml [\#3777](https://github.com/pypeclub/OpenPype/pull/3777)
- Ftrack status fix typo prgoress -\> progress [\#3761](https://github.com/pypeclub/OpenPype/pull/3761)
- Fix version resolution [\#3757](https://github.com/pypeclub/OpenPype/pull/3757)
- Maya: `containerise` dont skip empty values [\#3674](https://github.com/pypeclub/OpenPype/pull/3674)

**🔀 Refactored code**

- Photoshop: Use new Extractor location [\#3789](https://github.com/pypeclub/OpenPype/pull/3789)
- Blender: Use new Extractor location [\#3787](https://github.com/pypeclub/OpenPype/pull/3787)
- AfterEffects: Use new Extractor location [\#3784](https://github.com/pypeclub/OpenPype/pull/3784)
- General: Remove unused teshost [\#3773](https://github.com/pypeclub/OpenPype/pull/3773)
- General: Copied 'Extractor' plugin to publish pipeline [\#3771](https://github.com/pypeclub/OpenPype/pull/3771)
- General: Move queries of asset and representation links [\#3770](https://github.com/pypeclub/OpenPype/pull/3770)
- General: Move create project folders to pipeline [\#3768](https://github.com/pypeclub/OpenPype/pull/3768)
- General: Create project function moved to client code [\#3766](https://github.com/pypeclub/OpenPype/pull/3766)
- Maya: Refactor submit deadline to use AbstractSubmitDeadline [\#3759](https://github.com/pypeclub/OpenPype/pull/3759)
- General: Change publish template settings location [\#3755](https://github.com/pypeclub/OpenPype/pull/3755)
- General: Move hostdirname functionality into host [\#3749](https://github.com/pypeclub/OpenPype/pull/3749)
- General: Move publish utils to pipeline [\#3745](https://github.com/pypeclub/OpenPype/pull/3745)
- Houdini: Define houdini as addon [\#3735](https://github.com/pypeclub/OpenPype/pull/3735)
- Fusion: Defined fusion as addon [\#3733](https://github.com/pypeclub/OpenPype/pull/3733)
- Flame: Defined flame as addon [\#3732](https://github.com/pypeclub/OpenPype/pull/3732)
- Resolve: Define resolve as addon [\#3727](https://github.com/pypeclub/OpenPype/pull/3727)

**Merged pull requests:**

- Standalone Publisher: Ignore empty labels, then still use name like other asset models [\#3779](https://github.com/pypeclub/OpenPype/pull/3779)
- Kitsu - sync\_all\_project - add list ignore\_projects [\#3776](https://github.com/pypeclub/OpenPype/pull/3776)

## [3.14.1](https://github.com/pypeclub/OpenPype/tree/3.14.1) (2022-08-30)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.14.0...3.14.1)

### 📖 Documentation

- Documentation: Few updates [\#3698](https://github.com/pypeclub/OpenPype/pull/3698)
- Documentation: Settings development [\#3660](https://github.com/pypeclub/OpenPype/pull/3660)

**🆕 New features**

- Webpublisher:change create flatten image into tri state [\#3678](https://github.com/pypeclub/OpenPype/pull/3678)
- Blender: validators code correction with settings and defaults [\#3662](https://github.com/pypeclub/OpenPype/pull/3662)

**🚀 Enhancements**

- General: Thumbnail can use project roots [\#3750](https://github.com/pypeclub/OpenPype/pull/3750)
- Settings: Remove settings lock on tray exit [\#3720](https://github.com/pypeclub/OpenPype/pull/3720)
- General: Added helper getters to modules manager [\#3712](https://github.com/pypeclub/OpenPype/pull/3712)
- Unreal: Define unreal as module and use host class [\#3701](https://github.com/pypeclub/OpenPype/pull/3701)
- Settings: Lock settings UI session [\#3700](https://github.com/pypeclub/OpenPype/pull/3700)
- General: Benevolent context label collector [\#3686](https://github.com/pypeclub/OpenPype/pull/3686)
- Ftrack: Store ftrack entities on hierarchy integration to instances [\#3677](https://github.com/pypeclub/OpenPype/pull/3677)
- Ftrack: More logs related to auto sync value change [\#3671](https://github.com/pypeclub/OpenPype/pull/3671)
- Blender: ops refresh manager after process events [\#3663](https://github.com/pypeclub/OpenPype/pull/3663)

**🐛 Bug fixes**

- Maya: Fix typo in getPanel argument `with_focus` -\> `withFocus` [\#3753](https://github.com/pypeclub/OpenPype/pull/3753)
- General: Smaller fixes of imports [\#3748](https://github.com/pypeclub/OpenPype/pull/3748)
- General: Logger tweaks [\#3741](https://github.com/pypeclub/OpenPype/pull/3741)
- Nuke: missing job dependency if multiple bake streams [\#3737](https://github.com/pypeclub/OpenPype/pull/3737)
- Nuke: color-space settings from anatomy is working [\#3721](https://github.com/pypeclub/OpenPype/pull/3721)
- Settings: Fix studio default anatomy save [\#3716](https://github.com/pypeclub/OpenPype/pull/3716)
- Maya: Use project name instead of project code [\#3709](https://github.com/pypeclub/OpenPype/pull/3709)
- Settings: Fix project overrides save [\#3708](https://github.com/pypeclub/OpenPype/pull/3708)
- Workfiles tool: Fix published workfile filtering [\#3704](https://github.com/pypeclub/OpenPype/pull/3704)
- PS, AE: Provide default variant value for workfile subset [\#3703](https://github.com/pypeclub/OpenPype/pull/3703)
- RoyalRender: handle host name that is not set [\#3695](https://github.com/pypeclub/OpenPype/pull/3695)
- Flame: retime is working on clip publishing [\#3684](https://github.com/pypeclub/OpenPype/pull/3684)
- Webpublisher: added check for empty context [\#3682](https://github.com/pypeclub/OpenPype/pull/3682)

**🔀 Refactored code**

- General: Move delivery logic to pipeline [\#3751](https://github.com/pypeclub/OpenPype/pull/3751)
- General: Host addons cleanup [\#3744](https://github.com/pypeclub/OpenPype/pull/3744)
- Webpublisher: Webpublisher is used as addon [\#3740](https://github.com/pypeclub/OpenPype/pull/3740)
- Photoshop: Defined photoshop as addon [\#3736](https://github.com/pypeclub/OpenPype/pull/3736)
- Harmony: Defined harmony as addon [\#3734](https://github.com/pypeclub/OpenPype/pull/3734)
- General: Module interfaces cleanup [\#3731](https://github.com/pypeclub/OpenPype/pull/3731)
- AfterEffects: Move AE functions from general lib [\#3730](https://github.com/pypeclub/OpenPype/pull/3730)
- Blender: Define blender as module [\#3729](https://github.com/pypeclub/OpenPype/pull/3729)
- AfterEffects: Define AfterEffects as module [\#3728](https://github.com/pypeclub/OpenPype/pull/3728)
- General: Replace PypeLogger with Logger [\#3725](https://github.com/pypeclub/OpenPype/pull/3725)
- Nuke: Define nuke as module [\#3724](https://github.com/pypeclub/OpenPype/pull/3724)
- General: Move subset name functionality [\#3723](https://github.com/pypeclub/OpenPype/pull/3723)
- General: Move creators plugin getter [\#3714](https://github.com/pypeclub/OpenPype/pull/3714)
- General: Move constants from lib to client [\#3713](https://github.com/pypeclub/OpenPype/pull/3713)
- Loader: Subset groups using client operations [\#3710](https://github.com/pypeclub/OpenPype/pull/3710)
- TVPaint: Defined as module [\#3707](https://github.com/pypeclub/OpenPype/pull/3707)
- StandalonePublisher: Define StandalonePublisher as module [\#3706](https://github.com/pypeclub/OpenPype/pull/3706)
- TrayPublisher: Define TrayPublisher as module [\#3705](https://github.com/pypeclub/OpenPype/pull/3705)
- General: Move context specific functions to context tools [\#3702](https://github.com/pypeclub/OpenPype/pull/3702)

**Merged pull requests:**

- Hiero: Define hiero as module [\#3717](https://github.com/pypeclub/OpenPype/pull/3717)
- Deadline: better logging for DL webservice failures [\#3694](https://github.com/pypeclub/OpenPype/pull/3694)
- Photoshop: resize saved images in ExtractReview for ffmpeg [\#3676](https://github.com/pypeclub/OpenPype/pull/3676)
- Nuke: Validation refactory to new publisher [\#3567](https://github.com/pypeclub/OpenPype/pull/3567)

## [3.14.0](https://github.com/pypeclub/OpenPype/tree/3.14.0) (2022-08-18)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.13.0...3.14.0)

**🆕 New features**

- Maya: Build workfile by template [\#3578](https://github.com/pypeclub/OpenPype/pull/3578)
- Maya: Implementation of JSON layout for Unreal workflow [\#3353](https://github.com/pypeclub/OpenPype/pull/3353)
- Maya: Build workfile by template [\#3315](https://github.com/pypeclub/OpenPype/pull/3315)

**🚀 Enhancements**

- Ftrack: Addiotional component metadata [\#3685](https://github.com/pypeclub/OpenPype/pull/3685)
- Ftrack: Set task status on farm publishing [\#3680](https://github.com/pypeclub/OpenPype/pull/3680)
- Ftrack: Set task status on task creation in integrate hierarchy [\#3675](https://github.com/pypeclub/OpenPype/pull/3675)
- Maya: Disable rendering of all lights for render instances submitted through Deadline. [\#3661](https://github.com/pypeclub/OpenPype/pull/3661)
- General: Optimized OCIO configs [\#3650](https://github.com/pypeclub/OpenPype/pull/3650)

**🐛 Bug fixes**

- General: Switch from hero version to versioned works [\#3691](https://github.com/pypeclub/OpenPype/pull/3691)
- General: Fix finding of last version [\#3656](https://github.com/pypeclub/OpenPype/pull/3656)
- General: Extract Review can scale with pixel aspect ratio [\#3644](https://github.com/pypeclub/OpenPype/pull/3644)
- Maya: Refactor moved usage of CreateRender settings [\#3643](https://github.com/pypeclub/OpenPype/pull/3643)
- General: Hero version representations have full context [\#3638](https://github.com/pypeclub/OpenPype/pull/3638)
- Nuke: color settings for render write node is working now [\#3632](https://github.com/pypeclub/OpenPype/pull/3632)
- Maya: FBX support for update in reference loader [\#3631](https://github.com/pypeclub/OpenPype/pull/3631)

**🔀 Refactored code**

- General: Use client projects getter [\#3673](https://github.com/pypeclub/OpenPype/pull/3673)
- Resolve: Match folder structure to other hosts [\#3653](https://github.com/pypeclub/OpenPype/pull/3653)
- Maya: Hosts as modules [\#3647](https://github.com/pypeclub/OpenPype/pull/3647)
- TimersManager: Plugins are in timers manager module [\#3639](https://github.com/pypeclub/OpenPype/pull/3639)
- General: Move workfiles functions into pipeline [\#3637](https://github.com/pypeclub/OpenPype/pull/3637)
- General: Workfiles builder using query functions [\#3598](https://github.com/pypeclub/OpenPype/pull/3598)

**Merged pull requests:**

- Deadline: Global job pre load is not Pype 2 compatible [\#3666](https://github.com/pypeclub/OpenPype/pull/3666)
- Maya: Remove unused get current renderer logic [\#3645](https://github.com/pypeclub/OpenPype/pull/3645)
- Kitsu|Fix: Movie project type fails & first loop children names [\#3636](https://github.com/pypeclub/OpenPype/pull/3636)
- fix the bug of failing to extract look when UDIMs format used in AiImage [\#3628](https://github.com/pypeclub/OpenPype/pull/3628)

## [3.13.0](https://github.com/pypeclub/OpenPype/tree/3.13.0) (2022-08-09)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.12.2...3.13.0)

**🆕 New features**

- Support for mutliple installed versions - 3.13 [\#3605](https://github.com/pypeclub/OpenPype/pull/3605)
- Traypublisher: simple editorial publishing [\#3492](https://github.com/pypeclub/OpenPype/pull/3492)

**🚀 Enhancements**

- Editorial: Mix audio use side file for ffmpeg filters [\#3630](https://github.com/pypeclub/OpenPype/pull/3630)
- Ftrack: Comment template can contain optional keys [\#3615](https://github.com/pypeclub/OpenPype/pull/3615)
- Ftrack: Add more metadata to ftrack components [\#3612](https://github.com/pypeclub/OpenPype/pull/3612)
- General: Add context to pyblish context [\#3594](https://github.com/pypeclub/OpenPype/pull/3594)
- Kitsu: Shot&Sequence name with prefix over appends [\#3593](https://github.com/pypeclub/OpenPype/pull/3593)
- Photoshop: implemented {layer} placeholder in subset template [\#3591](https://github.com/pypeclub/OpenPype/pull/3591)
- General: Python module appdirs from git [\#3589](https://github.com/pypeclub/OpenPype/pull/3589)
- Ftrack: Update ftrack api to 2.3.3 [\#3588](https://github.com/pypeclub/OpenPype/pull/3588)
- General: New Integrator small fixes [\#3583](https://github.com/pypeclub/OpenPype/pull/3583)
- Maya: Render Creator has configurable options. [\#3097](https://github.com/pypeclub/OpenPype/pull/3097)

**🐛 Bug fixes**

- Maya:  fix aov separator in Redshift [\#3625](https://github.com/pypeclub/OpenPype/pull/3625)
- Fix for multi-version build on Mac [\#3622](https://github.com/pypeclub/OpenPype/pull/3622)
- Ftrack: Sync hierarchical attributes can handle new created entities [\#3621](https://github.com/pypeclub/OpenPype/pull/3621)
- General: Extract review aspect ratio scale is calculated by ffmpeg [\#3620](https://github.com/pypeclub/OpenPype/pull/3620)
- Maya: Fix types of default settings [\#3617](https://github.com/pypeclub/OpenPype/pull/3617)
- Integrator: Don't force to have dot before frame [\#3611](https://github.com/pypeclub/OpenPype/pull/3611)
- AfterEffects: refactored integrate doesnt work formulti frame publishes [\#3610](https://github.com/pypeclub/OpenPype/pull/3610)
- Maya look data contents fails with custom attribute on group [\#3607](https://github.com/pypeclub/OpenPype/pull/3607)
- TrayPublisher: Fix wrong conflict merge [\#3600](https://github.com/pypeclub/OpenPype/pull/3600)
- Bugfix: Add OCIO as submodule to prepare for handling `maketx` color space conversion. [\#3590](https://github.com/pypeclub/OpenPype/pull/3590)
- Fix general settings environment variables resolution [\#3587](https://github.com/pypeclub/OpenPype/pull/3587)
- Editorial publishing workflow improvements [\#3580](https://github.com/pypeclub/OpenPype/pull/3580)
- General: Update imports in start script [\#3579](https://github.com/pypeclub/OpenPype/pull/3579)
- Nuke: render family integration consistency  [\#3576](https://github.com/pypeclub/OpenPype/pull/3576)
- Ftrack: Handle missing published path in integrator [\#3570](https://github.com/pypeclub/OpenPype/pull/3570)
- Nuke: publish existing frames with slate with correct range [\#3555](https://github.com/pypeclub/OpenPype/pull/3555)

**🔀 Refactored code**

- General: Plugin settings handled by plugins [\#3623](https://github.com/pypeclub/OpenPype/pull/3623)
- General: Naive implementation of document create, update, delete [\#3601](https://github.com/pypeclub/OpenPype/pull/3601)
- General: Use query functions in general code [\#3596](https://github.com/pypeclub/OpenPype/pull/3596)
- General: Separate extraction of template data into more functions [\#3574](https://github.com/pypeclub/OpenPype/pull/3574)
- General: Lib cleanup [\#3571](https://github.com/pypeclub/OpenPype/pull/3571)

**Merged pull requests:**

- Webpublisher: timeout for PS studio processing [\#3619](https://github.com/pypeclub/OpenPype/pull/3619)
- Core: translated validate\_containers.py into New publisher style [\#3614](https://github.com/pypeclub/OpenPype/pull/3614)
- Enable write color sets on animation publish automatically [\#3582](https://github.com/pypeclub/OpenPype/pull/3582)

## [3.12.2](https://github.com/pypeclub/OpenPype/tree/3.12.2) (2022-07-27)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.12.1...3.12.2)

### 📖 Documentation

- Update website with more studios [\#3554](https://github.com/pypeclub/OpenPype/pull/3554)
- Documentation: Update publishing dev docs [\#3549](https://github.com/pypeclub/OpenPype/pull/3549)

**🚀 Enhancements**

- General: Global thumbnail extractor is ready for more cases [\#3561](https://github.com/pypeclub/OpenPype/pull/3561)
- Maya: add additional validators to Settings [\#3540](https://github.com/pypeclub/OpenPype/pull/3540)
- General: Interactive console in cli [\#3526](https://github.com/pypeclub/OpenPype/pull/3526)
- Ftrack: Automatic daily review session creation can define trigger hour [\#3516](https://github.com/pypeclub/OpenPype/pull/3516)
- Ftrack: add source into Note [\#3509](https://github.com/pypeclub/OpenPype/pull/3509)
- Ftrack: Trigger custom ftrack topic of project structure creation [\#3506](https://github.com/pypeclub/OpenPype/pull/3506)
- Settings UI: Add extract to file action on project view [\#3505](https://github.com/pypeclub/OpenPype/pull/3505)
- Add pack and unpack convenience scripts [\#3502](https://github.com/pypeclub/OpenPype/pull/3502)
- General: Event system [\#3499](https://github.com/pypeclub/OpenPype/pull/3499)
- NewPublisher: Keep plugins with mismatch target in report [\#3498](https://github.com/pypeclub/OpenPype/pull/3498)
- Nuke: load clip with options from settings [\#3497](https://github.com/pypeclub/OpenPype/pull/3497)
- TrayPublisher: implemented render\_mov\_batch  [\#3486](https://github.com/pypeclub/OpenPype/pull/3486)
- Migrate basic families to the new Tray Publisher [\#3469](https://github.com/pypeclub/OpenPype/pull/3469)
- Enhance powershell build scripts [\#1827](https://github.com/pypeclub/OpenPype/pull/1827)

**🐛 Bug fixes**

- Maya: fix Review image plane attribute  [\#3569](https://github.com/pypeclub/OpenPype/pull/3569)
- Maya: Fix animated attributes \(ie. overscan\) on loaded cameras breaking review publishing. [\#3562](https://github.com/pypeclub/OpenPype/pull/3562)
- NewPublisher: Python 2 compatible html escape [\#3559](https://github.com/pypeclub/OpenPype/pull/3559)
- Remove invalid submodules from `/vendor` [\#3557](https://github.com/pypeclub/OpenPype/pull/3557)
- General: Remove hosts filter on integrator plugins [\#3556](https://github.com/pypeclub/OpenPype/pull/3556)
- Settings: Clean default values of environments [\#3550](https://github.com/pypeclub/OpenPype/pull/3550)
- Module interfaces: Fix import error [\#3547](https://github.com/pypeclub/OpenPype/pull/3547)
- Workfiles tool: Show of tool and it's flags [\#3539](https://github.com/pypeclub/OpenPype/pull/3539)
- General: Create workfile documents works again [\#3538](https://github.com/pypeclub/OpenPype/pull/3538)
- Additional fixes for powershell scripts [\#3525](https://github.com/pypeclub/OpenPype/pull/3525)
- Maya: Added wrapper around cmds.setAttr [\#3523](https://github.com/pypeclub/OpenPype/pull/3523)
- Nuke: double slate [\#3521](https://github.com/pypeclub/OpenPype/pull/3521)
- General: Fix hash of centos oiio archive [\#3519](https://github.com/pypeclub/OpenPype/pull/3519)
- Maya: Renderman display output fix [\#3514](https://github.com/pypeclub/OpenPype/pull/3514)
- TrayPublisher: Simple creation enhancements and fixes [\#3513](https://github.com/pypeclub/OpenPype/pull/3513)
- NewPublisher: Publish attributes are properly collected [\#3510](https://github.com/pypeclub/OpenPype/pull/3510)
- TrayPublisher: Make sure host name is filled [\#3504](https://github.com/pypeclub/OpenPype/pull/3504)
- NewPublisher: Groups work and enum multivalue [\#3501](https://github.com/pypeclub/OpenPype/pull/3501)

**🔀 Refactored code**

- General: Use query functions in integrator [\#3563](https://github.com/pypeclub/OpenPype/pull/3563)
- General: Mongo core connection moved to client [\#3531](https://github.com/pypeclub/OpenPype/pull/3531)
- Refactor Integrate Asset [\#3530](https://github.com/pypeclub/OpenPype/pull/3530)
- General: Client docstrings cleanup [\#3529](https://github.com/pypeclub/OpenPype/pull/3529)
- General: Move load related functions into pipeline [\#3527](https://github.com/pypeclub/OpenPype/pull/3527)
- General: Get current context document functions [\#3522](https://github.com/pypeclub/OpenPype/pull/3522)
- Kitsu: Use query function from client [\#3496](https://github.com/pypeclub/OpenPype/pull/3496)
- TimersManager: Use query functions [\#3495](https://github.com/pypeclub/OpenPype/pull/3495)
- Deadline: Use query functions [\#3466](https://github.com/pypeclub/OpenPype/pull/3466)
- Refactor Integrate Asset [\#2898](https://github.com/pypeclub/OpenPype/pull/2898)

**Merged pull requests:**

- Maya: fix active pane loss [\#3566](https://github.com/pypeclub/OpenPype/pull/3566)

## [3.12.1](https://github.com/pypeclub/OpenPype/tree/3.12.1) (2022-07-13)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.12.0...3.12.1)

### 📖 Documentation

- Docs: Added minimal permissions for MongoDB [\#3441](https://github.com/pypeclub/OpenPype/pull/3441)

**🆕 New features**

- Maya: Add VDB to Arnold loader [\#3433](https://github.com/pypeclub/OpenPype/pull/3433)

**🚀 Enhancements**

- TrayPublisher: Added more options for grouping of instances [\#3494](https://github.com/pypeclub/OpenPype/pull/3494)
- NewPublisher: Align creator attributes from top to bottom [\#3487](https://github.com/pypeclub/OpenPype/pull/3487)
- NewPublisher: Added ability to use label of instance [\#3484](https://github.com/pypeclub/OpenPype/pull/3484)
- General: Creator Plugins have access to project [\#3476](https://github.com/pypeclub/OpenPype/pull/3476)
- General: Better arguments order in creator init [\#3475](https://github.com/pypeclub/OpenPype/pull/3475)
- Ftrack: Trigger custom ftrack events on project creation and preparation [\#3465](https://github.com/pypeclub/OpenPype/pull/3465)
- Windows installer: Clean old files and add version subfolder [\#3445](https://github.com/pypeclub/OpenPype/pull/3445)
- Blender: Bugfix - Set fps properly on open [\#3426](https://github.com/pypeclub/OpenPype/pull/3426)
- Hiero: Add custom scripts menu [\#3425](https://github.com/pypeclub/OpenPype/pull/3425)
- Blender: pre pyside install for all platforms [\#3400](https://github.com/pypeclub/OpenPype/pull/3400)
- Maya: Add additional playblast options to review Extractor. [\#3384](https://github.com/pypeclub/OpenPype/pull/3384)
- Maya: Ability to set resolution for playblasts from asset, and override through review instance. [\#3360](https://github.com/pypeclub/OpenPype/pull/3360)
- Maya: Redshift Volume Loader Implement update, remove, switch + fix vdb sequence support [\#3197](https://github.com/pypeclub/OpenPype/pull/3197)
- Maya: Implement `iter_visible_nodes_in_range` for extracting Alembics [\#3100](https://github.com/pypeclub/OpenPype/pull/3100)

**🐛 Bug fixes**

- TrayPublisher: Keep use instance label in list view [\#3493](https://github.com/pypeclub/OpenPype/pull/3493)
- General: Extract review use first frame of input sequence [\#3491](https://github.com/pypeclub/OpenPype/pull/3491)
- General: Fix Plist loading for application launch [\#3485](https://github.com/pypeclub/OpenPype/pull/3485)
- Nuke: Workfile tools open on start [\#3479](https://github.com/pypeclub/OpenPype/pull/3479)
- New Publisher: Disabled context change allows creation [\#3478](https://github.com/pypeclub/OpenPype/pull/3478)
- General: thumbnail extractor fix [\#3474](https://github.com/pypeclub/OpenPype/pull/3474)
- Kitsu: bugfix with sync-service ans publish plugins [\#3473](https://github.com/pypeclub/OpenPype/pull/3473)
- Flame: solved problem with multi-selected loading [\#3470](https://github.com/pypeclub/OpenPype/pull/3470)
- General: Fix query function in update logic [\#3468](https://github.com/pypeclub/OpenPype/pull/3468)
- Resolve: removed few bugs [\#3464](https://github.com/pypeclub/OpenPype/pull/3464)
- General: Delete old versions is safer when ftrack is disabled [\#3462](https://github.com/pypeclub/OpenPype/pull/3462)
- Nuke: fixing metadata slate TC difference [\#3455](https://github.com/pypeclub/OpenPype/pull/3455)
- Nuke: prerender reviewable fails [\#3450](https://github.com/pypeclub/OpenPype/pull/3450)
- Maya: fix hashing in Python 3 for tile rendering [\#3447](https://github.com/pypeclub/OpenPype/pull/3447)
- LogViewer: Escape html characters in log message [\#3443](https://github.com/pypeclub/OpenPype/pull/3443)
- Nuke: Slate frame is integrated [\#3427](https://github.com/pypeclub/OpenPype/pull/3427)
- Maya: Camera extra data - additional fix for \#3304 [\#3386](https://github.com/pypeclub/OpenPype/pull/3386)
- Maya: Handle excluding `model` family from frame range validator. [\#3370](https://github.com/pypeclub/OpenPype/pull/3370)

**🔀 Refactored code**

- Maya: Merge animation + pointcache extractor logic [\#3461](https://github.com/pypeclub/OpenPype/pull/3461)
- Maya: Re-use `maintained_time` from lib [\#3460](https://github.com/pypeclub/OpenPype/pull/3460)
- General: Use query functions in global plugins [\#3459](https://github.com/pypeclub/OpenPype/pull/3459)
- Clockify: Use query functions in clockify actions [\#3458](https://github.com/pypeclub/OpenPype/pull/3458)
- General: Use query functions in rest api calls [\#3457](https://github.com/pypeclub/OpenPype/pull/3457)
- General: Use query functions in openpype lib functions [\#3454](https://github.com/pypeclub/OpenPype/pull/3454)
- General: Use query functions in load utils [\#3446](https://github.com/pypeclub/OpenPype/pull/3446)
- General: Move publish plugin and publish render abstractions [\#3442](https://github.com/pypeclub/OpenPype/pull/3442)
- General: Use Anatomy after move to pipeline [\#3436](https://github.com/pypeclub/OpenPype/pull/3436)
- General: Anatomy moved to pipeline [\#3435](https://github.com/pypeclub/OpenPype/pull/3435)
- Fusion: Use client query functions [\#3380](https://github.com/pypeclub/OpenPype/pull/3380)
- Resolve: Use client query functions [\#3379](https://github.com/pypeclub/OpenPype/pull/3379)
- General: Host implementation defined with class [\#3337](https://github.com/pypeclub/OpenPype/pull/3337)

## [3.12.0](https://github.com/pypeclub/OpenPype/tree/3.12.0) (2022-06-28)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.11.1...3.12.0)

### 📖 Documentation

- Fix typo in documentation: pyenv on mac [\#3417](https://github.com/pypeclub/OpenPype/pull/3417)
- Linux: update OIIO package [\#3401](https://github.com/pypeclub/OpenPype/pull/3401)

**🆕 New features**

- Shotgrid: Add production beta of shotgrid integration [\#2921](https://github.com/pypeclub/OpenPype/pull/2921)

**🚀 Enhancements**

- Webserver: Added CORS middleware [\#3422](https://github.com/pypeclub/OpenPype/pull/3422)
- Attribute Defs UI: Files widget show what is allowed to drop in [\#3411](https://github.com/pypeclub/OpenPype/pull/3411)
- General: Add ability to change user value for templates [\#3366](https://github.com/pypeclub/OpenPype/pull/3366)
- Hosts: More options for in-host callbacks [\#3357](https://github.com/pypeclub/OpenPype/pull/3357)
- Multiverse: expose some settings to GUI [\#3350](https://github.com/pypeclub/OpenPype/pull/3350)
- Maya: Allow more data to be published along camera 🎥  [\#3304](https://github.com/pypeclub/OpenPype/pull/3304)
- Add root keys and project keys to create starting folder [\#2755](https://github.com/pypeclub/OpenPype/pull/2755)

**🐛 Bug fixes**

- NewPublisher: Fix subset name change on change of creator plugin [\#3420](https://github.com/pypeclub/OpenPype/pull/3420)
- Bug: fix invalid avalon import [\#3418](https://github.com/pypeclub/OpenPype/pull/3418)
- Nuke: Fix keyword argument in query function [\#3414](https://github.com/pypeclub/OpenPype/pull/3414)
- Houdini: fix loading and updating vbd/bgeo sequences [\#3408](https://github.com/pypeclub/OpenPype/pull/3408)
- Nuke: Collect representation files based on Write [\#3407](https://github.com/pypeclub/OpenPype/pull/3407)
- General: Filter representations before integration start [\#3398](https://github.com/pypeclub/OpenPype/pull/3398)
- Maya: look collector typo [\#3392](https://github.com/pypeclub/OpenPype/pull/3392)
- TVPaint: Make sure exit code is set to not None [\#3382](https://github.com/pypeclub/OpenPype/pull/3382)
- Maya: vray device aspect ratio fix [\#3381](https://github.com/pypeclub/OpenPype/pull/3381)
- Flame: bunch of publishing issues [\#3377](https://github.com/pypeclub/OpenPype/pull/3377)
- Harmony: added unc path to zifile command in Harmony [\#3372](https://github.com/pypeclub/OpenPype/pull/3372)
- Standalone: settings improvements [\#3355](https://github.com/pypeclub/OpenPype/pull/3355)
- Nuke: Load full model hierarchy by default [\#3328](https://github.com/pypeclub/OpenPype/pull/3328)
- Nuke: multiple baking streams with correct slate [\#3245](https://github.com/pypeclub/OpenPype/pull/3245)
- Maya: fix image prefix warning in validator [\#3128](https://github.com/pypeclub/OpenPype/pull/3128)

**🔀 Refactored code**

- Unreal: Use client query functions [\#3421](https://github.com/pypeclub/OpenPype/pull/3421)
- General: Move editorial lib to pipeline [\#3419](https://github.com/pypeclub/OpenPype/pull/3419)
- Kitsu: renaming to plural func sync\_all\_projects [\#3397](https://github.com/pypeclub/OpenPype/pull/3397)
- Houdini: Use client query functions [\#3395](https://github.com/pypeclub/OpenPype/pull/3395)
- Hiero: Use client query functions [\#3393](https://github.com/pypeclub/OpenPype/pull/3393)
- Nuke: Use client query functions [\#3391](https://github.com/pypeclub/OpenPype/pull/3391)
- Maya: Use client query functions [\#3385](https://github.com/pypeclub/OpenPype/pull/3385)
- Harmony: Use client query functions [\#3378](https://github.com/pypeclub/OpenPype/pull/3378)
- Celaction: Use client query functions [\#3376](https://github.com/pypeclub/OpenPype/pull/3376)
- Photoshop: Use client query functions [\#3375](https://github.com/pypeclub/OpenPype/pull/3375)
- AfterEffects: Use client query functions [\#3374](https://github.com/pypeclub/OpenPype/pull/3374)
- TVPaint: Use client query functions [\#3340](https://github.com/pypeclub/OpenPype/pull/3340)
- Ftrack: Use client query functions [\#3339](https://github.com/pypeclub/OpenPype/pull/3339)
- Standalone Publisher: Use client query functions [\#3330](https://github.com/pypeclub/OpenPype/pull/3330)

**Merged pull requests:**

- Sync Queue: Added far future value for null values for dates [\#3371](https://github.com/pypeclub/OpenPype/pull/3371)
- Maya - added support for single frame playblast review [\#3369](https://github.com/pypeclub/OpenPype/pull/3369)
- Houdini: Implement Redshift Proxy Export [\#3196](https://github.com/pypeclub/OpenPype/pull/3196)

## [3.11.1](https://github.com/pypeclub/OpenPype/tree/3.11.1) (2022-06-20)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.11.0...3.11.1)

**🆕 New features**

- Flame: custom export temp folder [\#3346](https://github.com/pypeclub/OpenPype/pull/3346)
- Nuke: removing third-party plugins   [\#3344](https://github.com/pypeclub/OpenPype/pull/3344)

**🚀 Enhancements**

- Pyblish Pype: Hiding/Close issues [\#3367](https://github.com/pypeclub/OpenPype/pull/3367)
- Ftrack: Removed requirement of pypeclub role from default settings [\#3354](https://github.com/pypeclub/OpenPype/pull/3354)
- Kitsu: Prevent crash on missing frames information [\#3352](https://github.com/pypeclub/OpenPype/pull/3352)
- Ftrack: Open browser from tray [\#3320](https://github.com/pypeclub/OpenPype/pull/3320)
- Enhancement: More control over thumbnail processing. [\#3259](https://github.com/pypeclub/OpenPype/pull/3259)

**🐛 Bug fixes**

- Nuke: bake streams with slate on farm [\#3368](https://github.com/pypeclub/OpenPype/pull/3368)
- Harmony: audio validator has wrong logic [\#3364](https://github.com/pypeclub/OpenPype/pull/3364)
- Nuke: Fix missing variable in extract thumbnail [\#3363](https://github.com/pypeclub/OpenPype/pull/3363)
- Nuke: Fix precollect writes [\#3361](https://github.com/pypeclub/OpenPype/pull/3361)
- AE- fix validate\_scene\_settings and renderLocal [\#3358](https://github.com/pypeclub/OpenPype/pull/3358)
- deadline: fixing misidentification of revieables [\#3356](https://github.com/pypeclub/OpenPype/pull/3356)
- General: Create only one thumbnail per instance [\#3351](https://github.com/pypeclub/OpenPype/pull/3351)
- nuke: adding extract thumbnail settings 3.10 [\#3347](https://github.com/pypeclub/OpenPype/pull/3347)
- General: Fix last version function [\#3345](https://github.com/pypeclub/OpenPype/pull/3345)
- Deadline: added OPENPYPE\_MONGO to filter [\#3336](https://github.com/pypeclub/OpenPype/pull/3336)
- Nuke: fixing farm publishing if review is disabled [\#3306](https://github.com/pypeclub/OpenPype/pull/3306)
- Maya: Fix Yeti errors on Create, Publish and Load [\#3198](https://github.com/pypeclub/OpenPype/pull/3198)

**🔀 Refactored code**

- Webpublisher: Use client query functions [\#3333](https://github.com/pypeclub/OpenPype/pull/3333)

## [3.11.0](https://github.com/pypeclub/OpenPype/tree/3.11.0) (2022-06-17)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.10.0...3.11.0)

### 📖 Documentation

- Documentation: Add app key to template documentation [\#3299](https://github.com/pypeclub/OpenPype/pull/3299)
- doc: adding royal render and multiverse to the web site [\#3285](https://github.com/pypeclub/OpenPype/pull/3285)
- Module: Kitsu module [\#2650](https://github.com/pypeclub/OpenPype/pull/2650)

**🆕 New features**

- Multiverse: fixed composition write, full docs, cosmetics [\#3178](https://github.com/pypeclub/OpenPype/pull/3178)

**🚀 Enhancements**

- Settings: Settings can be extracted from UI [\#3323](https://github.com/pypeclub/OpenPype/pull/3323)
- updated poetry installation source [\#3316](https://github.com/pypeclub/OpenPype/pull/3316)
- Ftrack: Action to easily create daily review session [\#3310](https://github.com/pypeclub/OpenPype/pull/3310)
- TVPaint: Extractor use mark in/out range to render [\#3309](https://github.com/pypeclub/OpenPype/pull/3309)
- Ftrack: Delivery action can work on ReviewSessions [\#3307](https://github.com/pypeclub/OpenPype/pull/3307)
- Maya: Look assigner UI improvements [\#3298](https://github.com/pypeclub/OpenPype/pull/3298)
- Ftrack: Action to transfer values of hierarchical attributes [\#3284](https://github.com/pypeclub/OpenPype/pull/3284)
- Maya: better handling of legacy review subsets names [\#3269](https://github.com/pypeclub/OpenPype/pull/3269)
- General: Updated windows oiio tool [\#3268](https://github.com/pypeclub/OpenPype/pull/3268)
- Unreal: add support for skeletalMesh and staticMesh to loaders [\#3267](https://github.com/pypeclub/OpenPype/pull/3267)
- Maya: reference loaders could store placeholder in referenced url [\#3264](https://github.com/pypeclub/OpenPype/pull/3264)
- TVPaint: Init file for TVPaint worker also handle guideline images [\#3250](https://github.com/pypeclub/OpenPype/pull/3250)
- Nuke: Change default icon path in settings [\#3247](https://github.com/pypeclub/OpenPype/pull/3247)
- Maya: publishing of animation and pointcache on a farm [\#3225](https://github.com/pypeclub/OpenPype/pull/3225)
- Maya: Look assigner UI improvements [\#3208](https://github.com/pypeclub/OpenPype/pull/3208)
- Nuke: add pointcache and animation to loader [\#3186](https://github.com/pypeclub/OpenPype/pull/3186)
- Nuke: Add a gizmo menu [\#3172](https://github.com/pypeclub/OpenPype/pull/3172)
- Support for Unreal 5 [\#3122](https://github.com/pypeclub/OpenPype/pull/3122)

**🐛 Bug fixes**

- General: Handle empty source key on instance [\#3342](https://github.com/pypeclub/OpenPype/pull/3342)
- Houdini: Fix Houdini VDB manage update wrong file attribute name [\#3322](https://github.com/pypeclub/OpenPype/pull/3322)
- Nuke: anatomy compatibility issue hacks [\#3321](https://github.com/pypeclub/OpenPype/pull/3321)
- hiero: otio p3 compatibility issue - metadata on effect use update 3.11 [\#3314](https://github.com/pypeclub/OpenPype/pull/3314)
- General: Vendorized modules for Python 2 and update poetry lock [\#3305](https://github.com/pypeclub/OpenPype/pull/3305)
- Fix - added local targets to install host [\#3303](https://github.com/pypeclub/OpenPype/pull/3303)
- Settings: Add missing default settings for nuke gizmo [\#3301](https://github.com/pypeclub/OpenPype/pull/3301)
- Maya: Fix swaped width and height in reviews [\#3300](https://github.com/pypeclub/OpenPype/pull/3300)
- Maya: point cache publish handles Maya instances [\#3297](https://github.com/pypeclub/OpenPype/pull/3297)
- Global: extract review slate issues [\#3286](https://github.com/pypeclub/OpenPype/pull/3286)
- Webpublisher: return only active projects in ProjectsEndpoint [\#3281](https://github.com/pypeclub/OpenPype/pull/3281)
- Hiero: add support for task tags 3.10.x [\#3279](https://github.com/pypeclub/OpenPype/pull/3279)
- General: Fix Oiio tool path resolving [\#3278](https://github.com/pypeclub/OpenPype/pull/3278)
- Maya: Fix udim support for e.g. uppercase \<UDIM\> tag [\#3266](https://github.com/pypeclub/OpenPype/pull/3266)
- Nuke: bake reformat was failing on string type [\#3261](https://github.com/pypeclub/OpenPype/pull/3261)
- Maya: hotfix Pxr multitexture in looks [\#3260](https://github.com/pypeclub/OpenPype/pull/3260)
- Unreal: Fix Camera Loading if Layout is missing [\#3255](https://github.com/pypeclub/OpenPype/pull/3255)
- Unreal: Fixed Animation loading in UE5 [\#3240](https://github.com/pypeclub/OpenPype/pull/3240)
- Unreal: Fixed Render creation in UE5 [\#3239](https://github.com/pypeclub/OpenPype/pull/3239)
- Unreal: Fixed Camera loading in UE5 [\#3238](https://github.com/pypeclub/OpenPype/pull/3238)
- Flame: debugging [\#3224](https://github.com/pypeclub/OpenPype/pull/3224)
- add silent audio to slate [\#3162](https://github.com/pypeclub/OpenPype/pull/3162)
- Add timecode to slate [\#2929](https://github.com/pypeclub/OpenPype/pull/2929)

**🔀 Refactored code**

- Blender: Use client query functions [\#3331](https://github.com/pypeclub/OpenPype/pull/3331)
- General: Define query functions [\#3288](https://github.com/pypeclub/OpenPype/pull/3288)

**Merged pull requests:**

- Maya: add pointcache family to gpu cache loader [\#3318](https://github.com/pypeclub/OpenPype/pull/3318)
- Maya look: skip empty file attributes [\#3274](https://github.com/pypeclub/OpenPype/pull/3274)

## [3.10.0](https://github.com/pypeclub/OpenPype/tree/3.10.0) (2022-05-26)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.9.8...3.10.0)

### 📖 Documentation

- Docs: add all-contributors config and initial list [\#3094](https://github.com/pypeclub/OpenPype/pull/3094)
- Nuke docs with videos [\#3052](https://github.com/pypeclub/OpenPype/pull/3052)

**🆕 New features**

- General: OpenPype modules publish plugins are registered in host [\#3180](https://github.com/pypeclub/OpenPype/pull/3180)
- General: Creator plugins from addons can be registered [\#3179](https://github.com/pypeclub/OpenPype/pull/3179)
- Ftrack: Single image reviewable [\#3157](https://github.com/pypeclub/OpenPype/pull/3157)
- Nuke: Expose write attributes to settings [\#3123](https://github.com/pypeclub/OpenPype/pull/3123)
- Hiero: Initial frame publish support [\#3106](https://github.com/pypeclub/OpenPype/pull/3106)
- Unreal: Render Publishing [\#2917](https://github.com/pypeclub/OpenPype/pull/2917)
- AfterEffects: Implemented New Publisher [\#2838](https://github.com/pypeclub/OpenPype/pull/2838)
- Unreal: Rendering implementation [\#2410](https://github.com/pypeclub/OpenPype/pull/2410)

**🚀 Enhancements**

- Maya: FBX camera export [\#3253](https://github.com/pypeclub/OpenPype/pull/3253)
- General: updating common vendor `scriptmenu` to 1.5.2 [\#3246](https://github.com/pypeclub/OpenPype/pull/3246)
- Project Manager: Allow to paste Tasks into multiple assets at the same time [\#3226](https://github.com/pypeclub/OpenPype/pull/3226)
- Project manager: Sped up project load [\#3216](https://github.com/pypeclub/OpenPype/pull/3216)
- Loader UI: Speed issues of loader with sync server [\#3199](https://github.com/pypeclub/OpenPype/pull/3199)
- Looks: add basic support for Renderman [\#3190](https://github.com/pypeclub/OpenPype/pull/3190)
- Maya: added clean\_import option to Import loader [\#3181](https://github.com/pypeclub/OpenPype/pull/3181)
- Add the scripts menu definition to nuke [\#3168](https://github.com/pypeclub/OpenPype/pull/3168)
- Maya: add maya 2023 to default applications [\#3167](https://github.com/pypeclub/OpenPype/pull/3167)
- Compressed bgeo publishing in SAP and Houdini loader [\#3153](https://github.com/pypeclub/OpenPype/pull/3153)
- General: Add 'dataclasses' to required python modules [\#3149](https://github.com/pypeclub/OpenPype/pull/3149)
- Hooks: Tweak logging grammar [\#3147](https://github.com/pypeclub/OpenPype/pull/3147)
- Nuke: settings for reformat node in CreateWriteRender node [\#3143](https://github.com/pypeclub/OpenPype/pull/3143)
- Houdini: Add loader for alembic through Alembic Archive node [\#3140](https://github.com/pypeclub/OpenPype/pull/3140)
- Publisher: UI Modifications and fixes [\#3139](https://github.com/pypeclub/OpenPype/pull/3139)
- General: Simplified OP modules/addons import [\#3137](https://github.com/pypeclub/OpenPype/pull/3137)
- Terminal: Tweak coloring of TrayModuleManager logging enabled states [\#3133](https://github.com/pypeclub/OpenPype/pull/3133)
- General: Cleanup some Loader docstrings [\#3131](https://github.com/pypeclub/OpenPype/pull/3131)
- Nuke: render instance with subset name filtered overrides [\#3117](https://github.com/pypeclub/OpenPype/pull/3117)
- Unreal: Layout and Camera update and remove functions reimplemented and improvements [\#3116](https://github.com/pypeclub/OpenPype/pull/3116)
- Settings: Remove environment groups from settings [\#3115](https://github.com/pypeclub/OpenPype/pull/3115)
- TVPaint: Match renderlayer key with other hosts [\#3110](https://github.com/pypeclub/OpenPype/pull/3110)
- Ftrack: AssetVersion status on publish [\#3108](https://github.com/pypeclub/OpenPype/pull/3108)
- Tray publisher: Simple families from settings [\#3105](https://github.com/pypeclub/OpenPype/pull/3105)
- Local Settings UI: Overlay messages on save and reset [\#3104](https://github.com/pypeclub/OpenPype/pull/3104)
- General: Remove repos related logic [\#3087](https://github.com/pypeclub/OpenPype/pull/3087)
- Standalone publisher: add support for bgeo and vdb [\#3080](https://github.com/pypeclub/OpenPype/pull/3080)
- Houdini: Fix FPS + outdated content pop-ups [\#3079](https://github.com/pypeclub/OpenPype/pull/3079)
- General: Add global log verbose arguments [\#3070](https://github.com/pypeclub/OpenPype/pull/3070)
- Flame: extract presets distribution [\#3063](https://github.com/pypeclub/OpenPype/pull/3063)
- Update collect\_render.py [\#3055](https://github.com/pypeclub/OpenPype/pull/3055)
- SiteSync: Added compute\_resource\_sync\_sites to sync\_server\_module [\#2983](https://github.com/pypeclub/OpenPype/pull/2983)
- Maya: Implement Hardware Renderer 2.0 support for Render Products [\#2611](https://github.com/pypeclub/OpenPype/pull/2611)

**🐛 Bug fixes**

- nuke: use framerange issue [\#3254](https://github.com/pypeclub/OpenPype/pull/3254)
- Ftrack: Chunk sizes for queries has minimal condition [\#3244](https://github.com/pypeclub/OpenPype/pull/3244)
- Maya: renderman displays needs to be filtered [\#3242](https://github.com/pypeclub/OpenPype/pull/3242)
- Ftrack: Validate that the user exists on ftrack [\#3237](https://github.com/pypeclub/OpenPype/pull/3237)
- Maya: Fix support for multiple resolutions [\#3236](https://github.com/pypeclub/OpenPype/pull/3236)
- TVPaint: Look for more groups than 12 [\#3228](https://github.com/pypeclub/OpenPype/pull/3228)
- Hiero: debugging frame range and other 3.10 [\#3222](https://github.com/pypeclub/OpenPype/pull/3222)
- Project Manager: Fix persistent editors on project change [\#3218](https://github.com/pypeclub/OpenPype/pull/3218)
- Deadline: instance data overwrite fix [\#3214](https://github.com/pypeclub/OpenPype/pull/3214)
- Ftrack: Push hierarchical attributes action works [\#3210](https://github.com/pypeclub/OpenPype/pull/3210)
- Standalone Publisher: Always create new representation for thumbnail [\#3203](https://github.com/pypeclub/OpenPype/pull/3203)
- Photoshop: skip collector when automatic testing [\#3202](https://github.com/pypeclub/OpenPype/pull/3202)
- Nuke: render/workfile version sync doesn't work on farm [\#3185](https://github.com/pypeclub/OpenPype/pull/3185)
- Ftrack: Review image only if there are no mp4 reviews [\#3183](https://github.com/pypeclub/OpenPype/pull/3183)
- Ftrack: Locations deepcopy issue [\#3177](https://github.com/pypeclub/OpenPype/pull/3177)
- General: Avoid creating multiple thumbnails [\#3176](https://github.com/pypeclub/OpenPype/pull/3176)
- General/Hiero: better clip duration calculation [\#3169](https://github.com/pypeclub/OpenPype/pull/3169)
- General: Oiio conversion for ffmpeg checks for invalid characters [\#3166](https://github.com/pypeclub/OpenPype/pull/3166)
- Fix for attaching render to subset [\#3164](https://github.com/pypeclub/OpenPype/pull/3164)
- Harmony: fixed missing task name in render instance [\#3163](https://github.com/pypeclub/OpenPype/pull/3163)
- Ftrack: Action delete old versions formatting works [\#3152](https://github.com/pypeclub/OpenPype/pull/3152)
- Deadline: fix the output directory [\#3144](https://github.com/pypeclub/OpenPype/pull/3144)
- General: New Session schema [\#3141](https://github.com/pypeclub/OpenPype/pull/3141)
- General: Missing version on headless mode crash properly [\#3136](https://github.com/pypeclub/OpenPype/pull/3136)
- TVPaint: Composite layers in reversed order [\#3135](https://github.com/pypeclub/OpenPype/pull/3135)
- Nuke: fixing default settings for workfile builder loaders [\#3120](https://github.com/pypeclub/OpenPype/pull/3120)
- Nuke: fix anatomy imageio regex default [\#3119](https://github.com/pypeclub/OpenPype/pull/3119)
- General: Python 3 compatibility in queries [\#3112](https://github.com/pypeclub/OpenPype/pull/3112)
- General: TemplateResult can be copied [\#3099](https://github.com/pypeclub/OpenPype/pull/3099)
- General: Collect loaded versions skips not existing representations [\#3095](https://github.com/pypeclub/OpenPype/pull/3095)
- RoyalRender Control Submission - AVALON\_APP\_NAME default [\#3091](https://github.com/pypeclub/OpenPype/pull/3091)
- Ftrack: Update Create Folders action [\#3089](https://github.com/pypeclub/OpenPype/pull/3089)
- Maya: Collect Render fix any render cameras check [\#3088](https://github.com/pypeclub/OpenPype/pull/3088)
- Project Manager: Avoid unnecessary updates of asset documents [\#3083](https://github.com/pypeclub/OpenPype/pull/3083)
- Standalone publisher: Fix plugins install [\#3077](https://github.com/pypeclub/OpenPype/pull/3077)
- General: Extract review sequence is not converted with same names [\#3076](https://github.com/pypeclub/OpenPype/pull/3076)
- Webpublisher: Use variant value [\#3068](https://github.com/pypeclub/OpenPype/pull/3068)
- Nuke: Add aov matching even for remainder and prerender [\#3060](https://github.com/pypeclub/OpenPype/pull/3060)
- Fix support for Renderman in Maya [\#3006](https://github.com/pypeclub/OpenPype/pull/3006)

**🔀 Refactored code**

- Avalon repo removed from Jobs workflow [\#3193](https://github.com/pypeclub/OpenPype/pull/3193)
- General: Remove remaining imports from avalon [\#3130](https://github.com/pypeclub/OpenPype/pull/3130)
- General: Move mongo db logic and remove avalon repository [\#3066](https://github.com/pypeclub/OpenPype/pull/3066)
- General: Move host install [\#3009](https://github.com/pypeclub/OpenPype/pull/3009)

**Merged pull requests:**

- Harmony: message length in 21.1 [\#3257](https://github.com/pypeclub/OpenPype/pull/3257)
- Harmony: 21.1 fix [\#3249](https://github.com/pypeclub/OpenPype/pull/3249)
- Maya: added jpg to filter for Image Plane Loader [\#3223](https://github.com/pypeclub/OpenPype/pull/3223)
- Webpublisher: replace space by underscore in subset names [\#3160](https://github.com/pypeclub/OpenPype/pull/3160)
- StandalonePublisher: removed Extract Background plugins [\#3093](https://github.com/pypeclub/OpenPype/pull/3093)
- Nuke: added suspend\_publish knob [\#3078](https://github.com/pypeclub/OpenPype/pull/3078)
- Bump async from 2.6.3 to 2.6.4 in /website [\#3065](https://github.com/pypeclub/OpenPype/pull/3065)
- SiteSync: Download all workfile inputs [\#2966](https://github.com/pypeclub/OpenPype/pull/2966)
- Photoshop: New Publisher [\#2933](https://github.com/pypeclub/OpenPype/pull/2933)
- Bump pillow from 9.0.0 to 9.0.1 [\#2880](https://github.com/pypeclub/OpenPype/pull/2880)
- AfterEffects: Allow configuration of default variant via Settings [\#2856](https://github.com/pypeclub/OpenPype/pull/2856)

## [3.9.8](https://github.com/pypeclub/OpenPype/tree/3.9.8) (2022-05-19)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.9.7...3.9.8)

## [3.9.7](https://github.com/pypeclub/OpenPype/tree/3.9.7) (2022-05-11)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.9.6...3.9.7)

## [3.9.6](https://github.com/pypeclub/OpenPype/tree/3.9.6) (2022-05-03)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.9.5...3.9.6)

## [3.9.5](https://github.com/pypeclub/OpenPype/tree/3.9.5) (2022-04-25)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.9.4...3.9.5)

## [3.9.4](https://github.com/pypeclub/OpenPype/tree/3.9.4) (2022-04-15)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.9.3...3.9.4)

### 📖 Documentation

- Documentation: more info about Tasks [\#3062](https://github.com/pypeclub/OpenPype/pull/3062)
- Documentation: Python requirements to 3.7.9 [\#3035](https://github.com/pypeclub/OpenPype/pull/3035)
- Website Docs: Remove unused pages [\#2974](https://github.com/pypeclub/OpenPype/pull/2974)

**🆕 New features**

- General: Local overrides for environment variables [\#3045](https://github.com/pypeclub/OpenPype/pull/3045)
- Flame: Flare integration preparation [\#2928](https://github.com/pypeclub/OpenPype/pull/2928)

**🚀 Enhancements**

- TVPaint: Added init file for worker to triggers missing sound file dialog [\#3053](https://github.com/pypeclub/OpenPype/pull/3053)
- Ftrack: Custom attributes can be filled in slate values [\#3036](https://github.com/pypeclub/OpenPype/pull/3036)
- Resolve environment variable in google drive credential path  [\#3008](https://github.com/pypeclub/OpenPype/pull/3008)

**🐛 Bug fixes**

- GitHub: Updated push-protected action in github workflow [\#3064](https://github.com/pypeclub/OpenPype/pull/3064)
- Nuke: Typos in imports from Nuke implementation [\#3061](https://github.com/pypeclub/OpenPype/pull/3061)
- Hotfix: fixing deadline job publishing [\#3059](https://github.com/pypeclub/OpenPype/pull/3059)
- General: Extract Review handle invalid characters for ffmpeg [\#3050](https://github.com/pypeclub/OpenPype/pull/3050)
- Slate Review: Support to keep format on slate concatenation [\#3049](https://github.com/pypeclub/OpenPype/pull/3049)
- Webpublisher: fix processing of workfile [\#3048](https://github.com/pypeclub/OpenPype/pull/3048)
- Ftrack: Integrate ftrack api fix [\#3044](https://github.com/pypeclub/OpenPype/pull/3044)
- Webpublisher - removed wrong hardcoded family [\#3043](https://github.com/pypeclub/OpenPype/pull/3043)
- LibraryLoader: Use current project for asset query in families filter [\#3042](https://github.com/pypeclub/OpenPype/pull/3042)
- SiteSync: Providers ignore that site is disabled [\#3041](https://github.com/pypeclub/OpenPype/pull/3041)
- Unreal: Creator import fixes [\#3040](https://github.com/pypeclub/OpenPype/pull/3040)
- SiteSync: fix transitive alternate sites, fix dropdown in Local Settings [\#3018](https://github.com/pypeclub/OpenPype/pull/3018)
- Maya: invalid review flag on rendered AOVs [\#2915](https://github.com/pypeclub/OpenPype/pull/2915)

**Merged pull requests:**

- Deadline: reworked pools assignment [\#3051](https://github.com/pypeclub/OpenPype/pull/3051)
- Houdini: Avoid ImportError on `hdefereval` when Houdini runs without UI [\#2987](https://github.com/pypeclub/OpenPype/pull/2987)

## [3.9.3](https://github.com/pypeclub/OpenPype/tree/3.9.3) (2022-04-07)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.9.2...3.9.3)

### 📖 Documentation

- Documentation: Added mention of adding My Drive as a root [\#2999](https://github.com/pypeclub/OpenPype/pull/2999)
- Website Docs: Manager Ftrack fix broken links [\#2979](https://github.com/pypeclub/OpenPype/pull/2979)
- Docs: Added MongoDB requirements [\#2951](https://github.com/pypeclub/OpenPype/pull/2951)
- Documentation: New publisher develop docs [\#2896](https://github.com/pypeclub/OpenPype/pull/2896)

**🆕 New features**

- Ftrack: Add description integrator [\#3027](https://github.com/pypeclub/OpenPype/pull/3027)
- nuke: bypass baking [\#2992](https://github.com/pypeclub/OpenPype/pull/2992)
- Publishing textures for Unreal [\#2988](https://github.com/pypeclub/OpenPype/pull/2988)
- Maya to Unreal: Static and Skeletal Meshes [\#2978](https://github.com/pypeclub/OpenPype/pull/2978)
- Multiverse: Initial Support [\#2908](https://github.com/pypeclub/OpenPype/pull/2908)

**🚀 Enhancements**

- General: default workfile subset name for workfile [\#3011](https://github.com/pypeclub/OpenPype/pull/3011)
- Ftrack: Add more options for note text of integrate ftrack note [\#3025](https://github.com/pypeclub/OpenPype/pull/3025)
- Console Interpreter: Changed how console splitter size are reused on show [\#3016](https://github.com/pypeclub/OpenPype/pull/3016)
- Deadline: Use more suitable name for sequence review logic [\#3015](https://github.com/pypeclub/OpenPype/pull/3015)
- Nuke: add concurrency attr to deadline job [\#3005](https://github.com/pypeclub/OpenPype/pull/3005)
- Photoshop: create image without instance [\#3001](https://github.com/pypeclub/OpenPype/pull/3001)
- TVPaint: Render scene family [\#3000](https://github.com/pypeclub/OpenPype/pull/3000)
- Deadline: priority configurable in Maya jobs [\#2995](https://github.com/pypeclub/OpenPype/pull/2995)
- Nuke: ReviewDataMov Read RAW attribute [\#2985](https://github.com/pypeclub/OpenPype/pull/2985)
- General: `METADATA_KEYS` constant as `frozenset` for optimal immutable lookup [\#2980](https://github.com/pypeclub/OpenPype/pull/2980)
- General: Tools with host filters [\#2975](https://github.com/pypeclub/OpenPype/pull/2975)
- Hero versions: Use custom templates [\#2967](https://github.com/pypeclub/OpenPype/pull/2967)
- Slack: Added configurable maximum file size of review upload to Slack [\#2945](https://github.com/pypeclub/OpenPype/pull/2945)
- NewPublisher: Prepared implementation of optional pyblish plugin [\#2943](https://github.com/pypeclub/OpenPype/pull/2943)
- TVPaint: Extractor to convert PNG into EXR [\#2942](https://github.com/pypeclub/OpenPype/pull/2942)
- Workfiles tool: Save as published workfiles [\#2937](https://github.com/pypeclub/OpenPype/pull/2937)
- Workfiles: Open published workfiles [\#2925](https://github.com/pypeclub/OpenPype/pull/2925)
- General: Default modules loaded dynamically [\#2923](https://github.com/pypeclub/OpenPype/pull/2923)
- CI: change the version bump logic [\#2919](https://github.com/pypeclub/OpenPype/pull/2919)
- Deadline: Add headless argument [\#2916](https://github.com/pypeclub/OpenPype/pull/2916)
- Nuke: Add no-audio Tag [\#2911](https://github.com/pypeclub/OpenPype/pull/2911)
- Ftrack: Fill workfile in custom attribute [\#2906](https://github.com/pypeclub/OpenPype/pull/2906)
- Nuke: improving readability [\#2903](https://github.com/pypeclub/OpenPype/pull/2903)
- Settings UI: Add simple tooltips for settings entities [\#2901](https://github.com/pypeclub/OpenPype/pull/2901)

**🐛 Bug fixes**

- General: Fix validate asset docs plug-in filename and class name [\#3029](https://github.com/pypeclub/OpenPype/pull/3029)
- Deadline: Fixed default value of use sequence for review [\#3033](https://github.com/pypeclub/OpenPype/pull/3033)
- Settings UI: Version column can be extended so version are visible [\#3032](https://github.com/pypeclub/OpenPype/pull/3032)
- General: Fix import after movements [\#3028](https://github.com/pypeclub/OpenPype/pull/3028)
- Harmony: Added creating subset name for workfile from template [\#3024](https://github.com/pypeclub/OpenPype/pull/3024)
- AfterEffects: Added creating subset name for workfile from template [\#3023](https://github.com/pypeclub/OpenPype/pull/3023)
- General: Add example addons to ignored [\#3022](https://github.com/pypeclub/OpenPype/pull/3022)
- Maya: Remove missing import [\#3017](https://github.com/pypeclub/OpenPype/pull/3017)
- Ftrack: multiple  reviewable componets [\#3012](https://github.com/pypeclub/OpenPype/pull/3012)
- Tray publisher: Fixes after code movement [\#3010](https://github.com/pypeclub/OpenPype/pull/3010)
- Hosts: Remove path existence checks in 'add\_implementation\_envs' [\#3004](https://github.com/pypeclub/OpenPype/pull/3004)
- Nuke: fixing unicode type detection in effect loaders [\#3002](https://github.com/pypeclub/OpenPype/pull/3002)
- Fix - remove doubled dot in workfile created from template [\#2998](https://github.com/pypeclub/OpenPype/pull/2998)
- Nuke: removing redundant Ftrack asset when farm publishing [\#2996](https://github.com/pypeclub/OpenPype/pull/2996)
- PS: fix renaming subset incorrectly in PS [\#2991](https://github.com/pypeclub/OpenPype/pull/2991)
- Fix: Disable setuptools auto discovery [\#2990](https://github.com/pypeclub/OpenPype/pull/2990)
- AEL: fix opening existing workfile if no scene opened [\#2989](https://github.com/pypeclub/OpenPype/pull/2989)
- Maya: Don't do hardlinks on windows for look publishing [\#2986](https://github.com/pypeclub/OpenPype/pull/2986)
- Settings UI: Fix version completer on linux [\#2981](https://github.com/pypeclub/OpenPype/pull/2981)
- Photoshop: Fix creation of subset names in PS review and workfile [\#2969](https://github.com/pypeclub/OpenPype/pull/2969)
- Slack: Added default for review\_upload\_limit for Slack [\#2965](https://github.com/pypeclub/OpenPype/pull/2965)
- General: OIIO conversion for ffmeg can handle sequences [\#2958](https://github.com/pypeclub/OpenPype/pull/2958)
- Settings: Conditional dictionary avoid invalid logs [\#2956](https://github.com/pypeclub/OpenPype/pull/2956)
- General: Smaller fixes and typos [\#2950](https://github.com/pypeclub/OpenPype/pull/2950)
- LogViewer: Don't refresh on initialization [\#2949](https://github.com/pypeclub/OpenPype/pull/2949)
- nuke: python3 compatibility issue with `iteritems` [\#2948](https://github.com/pypeclub/OpenPype/pull/2948)
- General: anatomy data with correct task short key [\#2947](https://github.com/pypeclub/OpenPype/pull/2947)
- SceneInventory: Fix imports in UI [\#2944](https://github.com/pypeclub/OpenPype/pull/2944)
- Slack: add generic exception [\#2941](https://github.com/pypeclub/OpenPype/pull/2941)
- General: Python specific vendor paths on env injection [\#2939](https://github.com/pypeclub/OpenPype/pull/2939)
- General: More fail safe delete old versions [\#2936](https://github.com/pypeclub/OpenPype/pull/2936)
- Settings UI: Collapsed of collapsible wrapper works as expected [\#2934](https://github.com/pypeclub/OpenPype/pull/2934)
- Maya: Do not pass `set` to maya commands \(fixes support for older maya versions\) [\#2932](https://github.com/pypeclub/OpenPype/pull/2932)
- General: Don't print log record on OSError [\#2926](https://github.com/pypeclub/OpenPype/pull/2926)
- Hiero: Fix import of 'register\_event\_callback' [\#2924](https://github.com/pypeclub/OpenPype/pull/2924)
- Flame: centos related debugging [\#2922](https://github.com/pypeclub/OpenPype/pull/2922)
- Ftrack: Missing Ftrack id after editorial publish [\#2905](https://github.com/pypeclub/OpenPype/pull/2905)
- AfterEffects: Fix rendering for single frame in DL [\#2875](https://github.com/pypeclub/OpenPype/pull/2875)

**🔀 Refactored code**

- General: Move plugins register and discover [\#2935](https://github.com/pypeclub/OpenPype/pull/2935)
- General: Move Attribute Definitions from pipeline [\#2931](https://github.com/pypeclub/OpenPype/pull/2931)
- General: Removed silo references and terminal splash [\#2927](https://github.com/pypeclub/OpenPype/pull/2927)
- General: Move pipeline constants to OpenPype [\#2918](https://github.com/pypeclub/OpenPype/pull/2918)
- General: Move formatting and workfile functions [\#2914](https://github.com/pypeclub/OpenPype/pull/2914)
- General: Move remaining plugins from avalon [\#2912](https://github.com/pypeclub/OpenPype/pull/2912)

**Merged pull requests:**

- Maya: Allow to select invalid camera contents if no cameras found [\#3030](https://github.com/pypeclub/OpenPype/pull/3030)
- Bump paramiko from 2.9.2 to 2.10.1 [\#2973](https://github.com/pypeclub/OpenPype/pull/2973)
- Bump minimist from 1.2.5 to 1.2.6 in /website [\#2954](https://github.com/pypeclub/OpenPype/pull/2954)
- Bump node-forge from 1.2.1 to 1.3.0 in /website [\#2953](https://github.com/pypeclub/OpenPype/pull/2953)
- Maya - added transparency into review creator [\#2952](https://github.com/pypeclub/OpenPype/pull/2952)

## [3.9.2](https://github.com/pypeclub/OpenPype/tree/3.9.2) (2022-04-04)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.9.1...3.9.2)

## [3.9.1](https://github.com/pypeclub/OpenPype/tree/3.9.1) (2022-03-18)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.9.0...3.9.1)

**🚀 Enhancements**

- General: Change how OPENPYPE\_DEBUG value is handled [\#2907](https://github.com/pypeclub/OpenPype/pull/2907)
- nuke: imageio adding ocio config version 1.2 [\#2897](https://github.com/pypeclub/OpenPype/pull/2897)
- Flame: support for comment with xml attribute overrides [\#2892](https://github.com/pypeclub/OpenPype/pull/2892)
- Nuke: ExtractReviewSlate can handle more codes and profiles [\#2879](https://github.com/pypeclub/OpenPype/pull/2879)
- Flame: sequence used for reference video [\#2869](https://github.com/pypeclub/OpenPype/pull/2869)

**🐛 Bug fixes**

- General: Fix use of Anatomy roots [\#2904](https://github.com/pypeclub/OpenPype/pull/2904)
- Fixing gap detection in extract review [\#2902](https://github.com/pypeclub/OpenPype/pull/2902)
- Pyblish Pype - ensure current state is correct when entering new group order [\#2899](https://github.com/pypeclub/OpenPype/pull/2899)
- SceneInventory: Fix import of load function [\#2894](https://github.com/pypeclub/OpenPype/pull/2894)
- Harmony - fixed creator issue [\#2891](https://github.com/pypeclub/OpenPype/pull/2891)
- General: Remove forgotten use of avalon Creator [\#2885](https://github.com/pypeclub/OpenPype/pull/2885)
- General: Avoid circular import [\#2884](https://github.com/pypeclub/OpenPype/pull/2884)
- Fixes for attaching loaded containers \(\#2837\) [\#2874](https://github.com/pypeclub/OpenPype/pull/2874)
- Maya: Deformer node ids validation plugin [\#2826](https://github.com/pypeclub/OpenPype/pull/2826)
- Flame Babypublisher optimalization [\#2806](https://github.com/pypeclub/OpenPype/pull/2806)
- hotfix: OIIO tool path - add extension on windows [\#2618](https://github.com/pypeclub/OpenPype/pull/2618)

**🔀 Refactored code**

- General: Reduce style usage to OpenPype repository [\#2889](https://github.com/pypeclub/OpenPype/pull/2889)
- General: Move loader logic from avalon to openpype [\#2886](https://github.com/pypeclub/OpenPype/pull/2886)

## [3.9.0](https://github.com/pypeclub/OpenPype/tree/3.9.0) (2022-03-14)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.8.2...3.9.0)

**Deprecated:**

- Houdini: Remove unused code [\#2779](https://github.com/pypeclub/OpenPype/pull/2779)
- Loader: Remove default family states for hosts from code [\#2706](https://github.com/pypeclub/OpenPype/pull/2706)
- AssetCreator: Remove the tool [\#2845](https://github.com/pypeclub/OpenPype/pull/2845)

### 📖 Documentation

- Documentation: fixed broken links [\#2799](https://github.com/pypeclub/OpenPype/pull/2799)
- Documentation: broken link fix [\#2785](https://github.com/pypeclub/OpenPype/pull/2785)
- Documentation: link fixes [\#2772](https://github.com/pypeclub/OpenPype/pull/2772)
- Update docusaurus to latest version [\#2760](https://github.com/pypeclub/OpenPype/pull/2760)
- Various testing updates [\#2726](https://github.com/pypeclub/OpenPype/pull/2726)
- documentation: add example to `repack-version` command [\#2669](https://github.com/pypeclub/OpenPype/pull/2669)
- Update docusaurus [\#2639](https://github.com/pypeclub/OpenPype/pull/2639)
- Documentation: Fixed relative links [\#2621](https://github.com/pypeclub/OpenPype/pull/2621)
- Documentation: Change Photoshop & AfterEffects plugin path [\#2878](https://github.com/pypeclub/OpenPype/pull/2878)

**🆕 New features**

- Flame: loading clips to reels [\#2622](https://github.com/pypeclub/OpenPype/pull/2622)
- General: Store settings by OpenPype version [\#2570](https://github.com/pypeclub/OpenPype/pull/2570)

**🚀 Enhancements**

- New: Validation exceptions [\#2841](https://github.com/pypeclub/OpenPype/pull/2841)
- General: Set context environments for non host applications [\#2803](https://github.com/pypeclub/OpenPype/pull/2803)
- Houdini: Remove duplicate ValidateOutputNode plug-in [\#2780](https://github.com/pypeclub/OpenPype/pull/2780)
- Tray publisher: New Tray Publisher host \(beta\) [\#2778](https://github.com/pypeclub/OpenPype/pull/2778)
- Slack: Added regex for filtering on subset names [\#2775](https://github.com/pypeclub/OpenPype/pull/2775)
- Houdini: Implement Reset Frame Range [\#2770](https://github.com/pypeclub/OpenPype/pull/2770)
- Pyblish Pype: Remove redundant new line in installed fonts printing [\#2758](https://github.com/pypeclub/OpenPype/pull/2758)
- Flame: use Shot Name on segment for asset name [\#2751](https://github.com/pypeclub/OpenPype/pull/2751)
- Flame: adding validator source clip [\#2746](https://github.com/pypeclub/OpenPype/pull/2746)
- Work Files: Preserve subversion comment of current filename by default [\#2734](https://github.com/pypeclub/OpenPype/pull/2734)
- Maya: set Deadline job/batch name to original source workfile name instead of published workfile [\#2733](https://github.com/pypeclub/OpenPype/pull/2733)
- Ftrack: Disable ftrack module by default [\#2732](https://github.com/pypeclub/OpenPype/pull/2732)
- Project Manager: Disable add task, add asset and save button when not in a project [\#2727](https://github.com/pypeclub/OpenPype/pull/2727)
- dropbox handle big file [\#2718](https://github.com/pypeclub/OpenPype/pull/2718)
- Fusion Move PR: Minor tweaks to Fusion integration [\#2716](https://github.com/pypeclub/OpenPype/pull/2716)
- RoyalRender: Minor enhancements [\#2700](https://github.com/pypeclub/OpenPype/pull/2700)
- Nuke: prerender with review knob [\#2691](https://github.com/pypeclub/OpenPype/pull/2691)
- Maya configurable unit validator [\#2680](https://github.com/pypeclub/OpenPype/pull/2680)
- General: Add settings for CleanUpFarm and disable the plugin by default [\#2679](https://github.com/pypeclub/OpenPype/pull/2679)
- Project Manager: Only allow scroll wheel edits when spinbox is active [\#2678](https://github.com/pypeclub/OpenPype/pull/2678)
- Ftrack: Sync description to assets [\#2670](https://github.com/pypeclub/OpenPype/pull/2670)
- Houdini: Moved to OpenPype [\#2658](https://github.com/pypeclub/OpenPype/pull/2658)
- Maya: Move implementation to OpenPype [\#2649](https://github.com/pypeclub/OpenPype/pull/2649)
- General: FFmpeg conversion also check attribute string length [\#2635](https://github.com/pypeclub/OpenPype/pull/2635)
- Houdini: Load Arnold .ass procedurals into Houdini [\#2606](https://github.com/pypeclub/OpenPype/pull/2606)
- Deadline: Simplify GlobalJobPreLoad logic [\#2605](https://github.com/pypeclub/OpenPype/pull/2605)
- Houdini: Implement Arnold .ass standin extraction from Houdini \(also support .ass.gz\) [\#2603](https://github.com/pypeclub/OpenPype/pull/2603)
- New Publisher: New features and preparations for new standalone publisher [\#2556](https://github.com/pypeclub/OpenPype/pull/2556)
- Fix Maya 2022 Python 3 compatibility [\#2445](https://github.com/pypeclub/OpenPype/pull/2445)
- TVPaint: Use new publisher exceptions in validators [\#2435](https://github.com/pypeclub/OpenPype/pull/2435)
- Harmony: Added new style validations for New Publisher [\#2434](https://github.com/pypeclub/OpenPype/pull/2434)
- Aftereffects: New style validations for New publisher [\#2430](https://github.com/pypeclub/OpenPype/pull/2430)
- Farm publishing: New cleanup plugin for Maya renders on farm [\#2390](https://github.com/pypeclub/OpenPype/pull/2390)
- General: Subset name filtering in ExtractReview outpus [\#2872](https://github.com/pypeclub/OpenPype/pull/2872)
- NewPublisher: Descriptions and Icons in creator dialog [\#2867](https://github.com/pypeclub/OpenPype/pull/2867)
- NewPublisher: Changing task on publishing instance [\#2863](https://github.com/pypeclub/OpenPype/pull/2863)
- TrayPublisher: Choose project widget is more clear [\#2859](https://github.com/pypeclub/OpenPype/pull/2859)
- Maya: add loaded containers to published instance [\#2837](https://github.com/pypeclub/OpenPype/pull/2837)
- Ftrack: Can sync fps as string [\#2836](https://github.com/pypeclub/OpenPype/pull/2836)
- General: Custom function for find executable [\#2822](https://github.com/pypeclub/OpenPype/pull/2822)
- General: Color dialog UI fixes [\#2817](https://github.com/pypeclub/OpenPype/pull/2817)
- global: letter box calculated on output as last process [\#2812](https://github.com/pypeclub/OpenPype/pull/2812)
- Nuke: adding Reformat to baking mov plugin  [\#2811](https://github.com/pypeclub/OpenPype/pull/2811)
- Manager: Update all to latest button [\#2805](https://github.com/pypeclub/OpenPype/pull/2805)
- Houdini: Move Houdini Save Current File to beginning of ExtractorOrder [\#2747](https://github.com/pypeclub/OpenPype/pull/2747)
- Global: adding studio name/code to anatomy template formatting data [\#2630](https://github.com/pypeclub/OpenPype/pull/2630)

**🐛 Bug fixes**

- Settings UI: Search case sensitivity [\#2810](https://github.com/pypeclub/OpenPype/pull/2810)
- resolve: fixing fusion module loading [\#2802](https://github.com/pypeclub/OpenPype/pull/2802)
- Ftrack: Unset task ids from asset versions before tasks are removed [\#2800](https://github.com/pypeclub/OpenPype/pull/2800)
- Slack: fail gracefully if slack exception [\#2798](https://github.com/pypeclub/OpenPype/pull/2798)
- Flame: Fix version string in default settings [\#2783](https://github.com/pypeclub/OpenPype/pull/2783)
- After Effects: Fix typo in name `afftereffects` -\> `aftereffects` [\#2768](https://github.com/pypeclub/OpenPype/pull/2768)
- Houdini: Fix open last workfile [\#2767](https://github.com/pypeclub/OpenPype/pull/2767)
- Avoid renaming udim indexes [\#2765](https://github.com/pypeclub/OpenPype/pull/2765)
- Maya: Fix `unique_namespace` when in an namespace that is empty [\#2759](https://github.com/pypeclub/OpenPype/pull/2759)
- Loader UI: Fix right click in representation widget [\#2757](https://github.com/pypeclub/OpenPype/pull/2757)
- Harmony: Rendering in Deadline didn't work in other machines than submitter [\#2754](https://github.com/pypeclub/OpenPype/pull/2754)
- Aftereffects 2022 and Deadline [\#2748](https://github.com/pypeclub/OpenPype/pull/2748)
- Flame: bunch of bugs [\#2745](https://github.com/pypeclub/OpenPype/pull/2745)
- Maya: Save current scene on workfile publish [\#2744](https://github.com/pypeclub/OpenPype/pull/2744)
- Version Up: Preserve parts of filename after version number \(like subversion\) on version\_up [\#2741](https://github.com/pypeclub/OpenPype/pull/2741)
- Loader UI: Multiple asset selection and underline colors fixed [\#2731](https://github.com/pypeclub/OpenPype/pull/2731)
- General: Fix loading of unused chars in xml format [\#2729](https://github.com/pypeclub/OpenPype/pull/2729)
- TVPaint: Set objectName with members [\#2725](https://github.com/pypeclub/OpenPype/pull/2725)
- General: Don't use 'objectName' from loaded references [\#2715](https://github.com/pypeclub/OpenPype/pull/2715)
- Settings: Studio Project anatomy is queried using right keys [\#2711](https://github.com/pypeclub/OpenPype/pull/2711)
- Local Settings: Additional applications don't break UI [\#2710](https://github.com/pypeclub/OpenPype/pull/2710)
- Maya: Remove some unused code [\#2709](https://github.com/pypeclub/OpenPype/pull/2709)
- Houdini: Fix refactor of Houdini host move for CreateArnoldAss [\#2704](https://github.com/pypeclub/OpenPype/pull/2704)
- LookAssigner: Fix imports after moving code to OpenPype repository [\#2701](https://github.com/pypeclub/OpenPype/pull/2701)
- Multiple hosts: unify menu style across hosts [\#2693](https://github.com/pypeclub/OpenPype/pull/2693)
- Maya Redshift fixes [\#2692](https://github.com/pypeclub/OpenPype/pull/2692)
- Maya: fix fps validation popup [\#2685](https://github.com/pypeclub/OpenPype/pull/2685)
- Houdini Explicitly collect correct frame name even in case of single frame render when `frameStart` is provided [\#2676](https://github.com/pypeclub/OpenPype/pull/2676)
- hiero: fix effect collector name and order [\#2673](https://github.com/pypeclub/OpenPype/pull/2673)
- Maya: Fix menu callbacks [\#2671](https://github.com/pypeclub/OpenPype/pull/2671)
- hiero: removing obsolete unsupported plugin [\#2667](https://github.com/pypeclub/OpenPype/pull/2667)
- Launcher: Fix access to 'data' attribute on actions [\#2659](https://github.com/pypeclub/OpenPype/pull/2659)
- Maya `vrscene` loader fixes [\#2633](https://github.com/pypeclub/OpenPype/pull/2633)
- Houdini: fix usd family in loader and integrators [\#2631](https://github.com/pypeclub/OpenPype/pull/2631)
- Maya: Add only reference node to look family container like with other families [\#2508](https://github.com/pypeclub/OpenPype/pull/2508)
- General: Missing time function [\#2877](https://github.com/pypeclub/OpenPype/pull/2877)
- Deadline: Fix plugin name for tile assemble [\#2868](https://github.com/pypeclub/OpenPype/pull/2868)
- Nuke: gizmo precollect fix [\#2866](https://github.com/pypeclub/OpenPype/pull/2866)
- General: Fix hardlink for windows [\#2864](https://github.com/pypeclub/OpenPype/pull/2864)
- General: ffmpeg was crashing on slate merge [\#2860](https://github.com/pypeclub/OpenPype/pull/2860)
- WebPublisher: Video file was published with one too many frame [\#2858](https://github.com/pypeclub/OpenPype/pull/2858)
- New Publisher: Error dialog got right styles [\#2857](https://github.com/pypeclub/OpenPype/pull/2857)
- General: Fix getattr clalback on dynamic modules [\#2855](https://github.com/pypeclub/OpenPype/pull/2855)
- Nuke: slate resolution to input video resolution [\#2853](https://github.com/pypeclub/OpenPype/pull/2853)
- WebPublisher: Fix username stored in DB [\#2852](https://github.com/pypeclub/OpenPype/pull/2852)
- WebPublisher: Fix wrong number of frames for video file [\#2851](https://github.com/pypeclub/OpenPype/pull/2851)
- Nuke: Fix family test in validate\_write\_legacy to work with stillImage [\#2847](https://github.com/pypeclub/OpenPype/pull/2847)
- Nuke: fix multiple baking profile farm publishing [\#2842](https://github.com/pypeclub/OpenPype/pull/2842)
- Blender: Fixed parameters for FBX export of the camera [\#2840](https://github.com/pypeclub/OpenPype/pull/2840)
- Maya: Stop creation of reviews for Cryptomattes [\#2832](https://github.com/pypeclub/OpenPype/pull/2832)
- Deadline: Remove recreated event [\#2828](https://github.com/pypeclub/OpenPype/pull/2828)
- Deadline: Added missing events folder [\#2827](https://github.com/pypeclub/OpenPype/pull/2827)
- Settings: Missing document with OP versions may break start of OpenPype [\#2825](https://github.com/pypeclub/OpenPype/pull/2825)
- Deadline: more detailed temp file name for environment json [\#2824](https://github.com/pypeclub/OpenPype/pull/2824)
- General: Host name was formed from obsolete code [\#2821](https://github.com/pypeclub/OpenPype/pull/2821)
- Settings UI: Fix "Apply from" action [\#2820](https://github.com/pypeclub/OpenPype/pull/2820)
- Ftrack: Job killer with missing user [\#2819](https://github.com/pypeclub/OpenPype/pull/2819)
- Nuke: Use AVALON\_APP to get value for "app" key [\#2818](https://github.com/pypeclub/OpenPype/pull/2818)
- StandalonePublisher: use dynamic groups in subset names [\#2816](https://github.com/pypeclub/OpenPype/pull/2816)

**🔀 Refactored code**

- Ftrack: Moved module one hierarchy level higher [\#2792](https://github.com/pypeclub/OpenPype/pull/2792)
- SyncServer: Moved module one hierarchy level higher [\#2791](https://github.com/pypeclub/OpenPype/pull/2791)
- Royal render: Move module one hierarchy level higher [\#2790](https://github.com/pypeclub/OpenPype/pull/2790)
- Deadline: Move module one hierarchy level higher [\#2789](https://github.com/pypeclub/OpenPype/pull/2789)
- Refactor: move webserver tool to openpype [\#2876](https://github.com/pypeclub/OpenPype/pull/2876)
- General: Move create logic from avalon to OpenPype [\#2854](https://github.com/pypeclub/OpenPype/pull/2854)
- General: Add vendors from avalon [\#2848](https://github.com/pypeclub/OpenPype/pull/2848)
- General: Basic event system [\#2846](https://github.com/pypeclub/OpenPype/pull/2846)
- General: Move change context functions [\#2839](https://github.com/pypeclub/OpenPype/pull/2839)
- Tools: Don't use avalon tools code [\#2829](https://github.com/pypeclub/OpenPype/pull/2829)
- Move Unreal Implementation to OpenPype [\#2823](https://github.com/pypeclub/OpenPype/pull/2823)
- General: Extract template formatting from anatomy [\#2766](https://github.com/pypeclub/OpenPype/pull/2766)

**Merged pull requests:**

- Fusion: Moved implementation into OpenPype [\#2713](https://github.com/pypeclub/OpenPype/pull/2713)
- TVPaint: Plugin build without dependencies [\#2705](https://github.com/pypeclub/OpenPype/pull/2705)
- Webpublisher: Photoshop create a beauty png [\#2689](https://github.com/pypeclub/OpenPype/pull/2689)
- Ftrack: Hierarchical attributes are queried properly [\#2682](https://github.com/pypeclub/OpenPype/pull/2682)
- Maya: Add Validate Frame Range settings [\#2661](https://github.com/pypeclub/OpenPype/pull/2661)
- Harmony: move to Openpype [\#2657](https://github.com/pypeclub/OpenPype/pull/2657)
- Maya: cleanup duplicate rendersetup code [\#2642](https://github.com/pypeclub/OpenPype/pull/2642)
- Deadline: Be able to pass Mongo url to job [\#2616](https://github.com/pypeclub/OpenPype/pull/2616)

## [3.8.2](https://github.com/pypeclub/OpenPype/tree/3.8.2) (2022-02-07)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.8.1...3.8.2)

### 📖 Documentation

- Cosmetics: Fix common typos in openpype/website [\#2617](https://github.com/pypeclub/OpenPype/pull/2617)

**🚀 Enhancements**

- TVPaint: Image loaders also work on review family [\#2638](https://github.com/pypeclub/OpenPype/pull/2638)
- General: Project backup tools [\#2629](https://github.com/pypeclub/OpenPype/pull/2629)
- nuke: adding clear button to write nodes [\#2627](https://github.com/pypeclub/OpenPype/pull/2627)
- Ftrack: Family to Asset type mapping is in settings [\#2602](https://github.com/pypeclub/OpenPype/pull/2602)
- Nuke: load color space from representation data [\#2576](https://github.com/pypeclub/OpenPype/pull/2576)

**🐛 Bug fixes**

- Fix pulling of cx\_freeze 6.10 [\#2628](https://github.com/pypeclub/OpenPype/pull/2628)
- Global: fix broken otio review extractor [\#2590](https://github.com/pypeclub/OpenPype/pull/2590)

**Merged pull requests:**

- WebPublisher: fix instance duplicates [\#2641](https://github.com/pypeclub/OpenPype/pull/2641)
- Fix - safer pulling of task name for webpublishing from PS [\#2613](https://github.com/pypeclub/OpenPype/pull/2613)

## [3.8.1](https://github.com/pypeclub/OpenPype/tree/3.8.1) (2022-02-01)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.8.0...3.8.1)

**🚀 Enhancements**

- Webpublisher: Thumbnail extractor [\#2600](https://github.com/pypeclub/OpenPype/pull/2600)
- Loader: Allow to toggle default family filters between "include" or "exclude" filtering [\#2541](https://github.com/pypeclub/OpenPype/pull/2541)
- Launcher: Added context menu to to skip opening last workfile [\#2536](https://github.com/pypeclub/OpenPype/pull/2536)
- Unreal: JSON Layout Loading support [\#2066](https://github.com/pypeclub/OpenPype/pull/2066)

**🐛 Bug fixes**

- Release/3.8.0 [\#2619](https://github.com/pypeclub/OpenPype/pull/2619)
- Settings: Enum does not store empty string if has single item to select [\#2615](https://github.com/pypeclub/OpenPype/pull/2615)
- switch distutils to sysconfig for `get_platform()` [\#2594](https://github.com/pypeclub/OpenPype/pull/2594)
- Fix poetry index and speedcopy update [\#2589](https://github.com/pypeclub/OpenPype/pull/2589)
- Webpublisher: Fix - subset names from processed .psd used wrong value for task [\#2586](https://github.com/pypeclub/OpenPype/pull/2586)
- `vrscene` creator Deadline webservice URL handling [\#2580](https://github.com/pypeclub/OpenPype/pull/2580)
- global: track name was failing if duplicated root word in name [\#2568](https://github.com/pypeclub/OpenPype/pull/2568)
- Validate Maya Rig produces no cycle errors [\#2484](https://github.com/pypeclub/OpenPype/pull/2484)

**Merged pull requests:**

- Bump pillow from 8.4.0 to 9.0.0 [\#2595](https://github.com/pypeclub/OpenPype/pull/2595)
- Webpublisher: Skip version collect [\#2591](https://github.com/pypeclub/OpenPype/pull/2591)
- build\(deps\): bump pillow from 8.4.0 to 9.0.0 [\#2523](https://github.com/pypeclub/OpenPype/pull/2523)

## [3.8.0](https://github.com/pypeclub/OpenPype/tree/3.8.0) (2022-01-24)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.7.0...3.8.0)

### 📖 Documentation

- Variable in docs renamed to proper name [\#2546](https://github.com/pypeclub/OpenPype/pull/2546)

**🆕 New features**

- Flame: extracting segments with trans-coding  [\#2547](https://github.com/pypeclub/OpenPype/pull/2547)
- Maya : V-Ray Proxy - load all ABC files via proxy [\#2544](https://github.com/pypeclub/OpenPype/pull/2544)
- Maya to Unreal: Extended static mesh workflow [\#2537](https://github.com/pypeclub/OpenPype/pull/2537)
- Flame: collecting publishable instances [\#2519](https://github.com/pypeclub/OpenPype/pull/2519)
- Flame: create publishable clips [\#2495](https://github.com/pypeclub/OpenPype/pull/2495)
- Flame: OpenTimelineIO Export Modul [\#2398](https://github.com/pypeclub/OpenPype/pull/2398)

**🚀 Enhancements**

- Webpublisher: Moved error at the beginning of the log [\#2559](https://github.com/pypeclub/OpenPype/pull/2559)
- Ftrack: Use ApplicationManager to get DJV path [\#2558](https://github.com/pypeclub/OpenPype/pull/2558)
- Webpublisher: Added endpoint to reprocess batch through UI [\#2555](https://github.com/pypeclub/OpenPype/pull/2555)
- Settings: PathInput strip passed string [\#2550](https://github.com/pypeclub/OpenPype/pull/2550)
- Global: Exctract Review anatomy fill data with output name [\#2548](https://github.com/pypeclub/OpenPype/pull/2548)
- Cosmetics: Clean up some cosmetics / typos [\#2542](https://github.com/pypeclub/OpenPype/pull/2542)
- General: Validate if current process OpenPype version is requested version [\#2529](https://github.com/pypeclub/OpenPype/pull/2529)
- General: Be able to use anatomy data in ffmpeg output arguments [\#2525](https://github.com/pypeclub/OpenPype/pull/2525)
- Expose toggle publish plug-in settings for Maya Look Shading Engine Naming [\#2521](https://github.com/pypeclub/OpenPype/pull/2521)
- Photoshop: Move implementation to OpenPype [\#2510](https://github.com/pypeclub/OpenPype/pull/2510)
- TimersManager: Move module one hierarchy higher [\#2501](https://github.com/pypeclub/OpenPype/pull/2501)
- Slack: notifications are sent with Openpype logo and bot name [\#2499](https://github.com/pypeclub/OpenPype/pull/2499)
- Slack: Add review to notification message [\#2498](https://github.com/pypeclub/OpenPype/pull/2498)
- Ftrack: Event handlers settings [\#2496](https://github.com/pypeclub/OpenPype/pull/2496)
- Tools: Fix style and modality of errors in loader and creator [\#2489](https://github.com/pypeclub/OpenPype/pull/2489)
- Maya: Collect 'fps' animation data only for "review" instances [\#2486](https://github.com/pypeclub/OpenPype/pull/2486)
- Project Manager: Remove project button cleanup [\#2482](https://github.com/pypeclub/OpenPype/pull/2482)
- Tools: Be able to change models of tasks and assets widgets [\#2475](https://github.com/pypeclub/OpenPype/pull/2475)
- Publish pype: Reduce publish process defering [\#2464](https://github.com/pypeclub/OpenPype/pull/2464)
- Maya: Improve speed of Collect History logic [\#2460](https://github.com/pypeclub/OpenPype/pull/2460)
- Maya: Validate Rig Controllers - fix Error: in script editor [\#2459](https://github.com/pypeclub/OpenPype/pull/2459)
- Maya: Validate NGONs simplify and speed-up [\#2458](https://github.com/pypeclub/OpenPype/pull/2458)
- Maya: Optimize Validate Locked Normals speed for dense polymeshes [\#2457](https://github.com/pypeclub/OpenPype/pull/2457)
- Maya: Refactor missing \_get\_reference\_node method [\#2455](https://github.com/pypeclub/OpenPype/pull/2455)
- Houdini: Remove broken unique name counter [\#2450](https://github.com/pypeclub/OpenPype/pull/2450)
- Maya: Improve lib.polyConstraint performance when Select tool is not the active tool context [\#2447](https://github.com/pypeclub/OpenPype/pull/2447)
- General: Validate third party before build [\#2425](https://github.com/pypeclub/OpenPype/pull/2425)
- Maya : add option to not group reference in ReferenceLoader [\#2383](https://github.com/pypeclub/OpenPype/pull/2383)

**🐛 Bug fixes**

- AfterEffects: Fix - removed obsolete import [\#2577](https://github.com/pypeclub/OpenPype/pull/2577)
- General: OpenPype version updates [\#2575](https://github.com/pypeclub/OpenPype/pull/2575)
- Ftrack: Delete action revision [\#2563](https://github.com/pypeclub/OpenPype/pull/2563)
- Webpublisher: ftrack shows incorrect user names [\#2560](https://github.com/pypeclub/OpenPype/pull/2560)
- General: Do not validate version if build does not support it [\#2557](https://github.com/pypeclub/OpenPype/pull/2557)
- Webpublisher: Fixed progress reporting [\#2553](https://github.com/pypeclub/OpenPype/pull/2553)
- Fix Maya AssProxyLoader version switch [\#2551](https://github.com/pypeclub/OpenPype/pull/2551)
- General: Fix install thread in igniter [\#2549](https://github.com/pypeclub/OpenPype/pull/2549)
- Houdini: vdbcache family preserve frame numbers on publish integration + enable validate version for Houdini [\#2535](https://github.com/pypeclub/OpenPype/pull/2535)
- Maya: Fix Load VDB to V-Ray [\#2533](https://github.com/pypeclub/OpenPype/pull/2533)
- Maya: ReferenceLoader fix not unique group name error for attach to root [\#2532](https://github.com/pypeclub/OpenPype/pull/2532)
- Maya: namespaced context go back to original namespace when started from inside a namespace [\#2531](https://github.com/pypeclub/OpenPype/pull/2531)
- Fix create zip tool - path argument [\#2522](https://github.com/pypeclub/OpenPype/pull/2522)
- Maya: Fix Extract Look with space in names [\#2518](https://github.com/pypeclub/OpenPype/pull/2518)
- Fix published frame content for sequence starting with 0 [\#2513](https://github.com/pypeclub/OpenPype/pull/2513)
- Maya: reset empty string attributes correctly to "" instead of "None" [\#2506](https://github.com/pypeclub/OpenPype/pull/2506)
- Improve FusionPreLaunch hook errors [\#2505](https://github.com/pypeclub/OpenPype/pull/2505)
- General: Settings work if OpenPypeVersion is available [\#2494](https://github.com/pypeclub/OpenPype/pull/2494)
- General: PYTHONPATH may break OpenPype dependencies [\#2493](https://github.com/pypeclub/OpenPype/pull/2493)
- General: Modules import function output fix [\#2492](https://github.com/pypeclub/OpenPype/pull/2492)
- AE: fix hiding of alert window below Publish [\#2491](https://github.com/pypeclub/OpenPype/pull/2491)
- Workfiles tool: Files widget show files on first show [\#2488](https://github.com/pypeclub/OpenPype/pull/2488)
- General: Custom template paths filter fix [\#2483](https://github.com/pypeclub/OpenPype/pull/2483)
- Loader: Remove always on top flag in tray [\#2480](https://github.com/pypeclub/OpenPype/pull/2480)
- General: Anatomy does not return root envs as unicode [\#2465](https://github.com/pypeclub/OpenPype/pull/2465)
- Maya: Validate Shape Zero do not keep fixed geometry vertices selected/active after repair [\#2456](https://github.com/pypeclub/OpenPype/pull/2456)

**Merged pull requests:**

- AfterEffects: Move implementation to OpenPype [\#2543](https://github.com/pypeclub/OpenPype/pull/2543)
- Maya: Remove Maya Look Assigner check on startup [\#2540](https://github.com/pypeclub/OpenPype/pull/2540)
- build\(deps\): bump shelljs from 0.8.4 to 0.8.5 in /website [\#2538](https://github.com/pypeclub/OpenPype/pull/2538)
- build\(deps\): bump follow-redirects from 1.14.4 to 1.14.7 in /website [\#2534](https://github.com/pypeclub/OpenPype/pull/2534)
- Nuke: Merge avalon's implementation into OpenPype [\#2514](https://github.com/pypeclub/OpenPype/pull/2514)
- Maya: Vray fix proxies look assignment [\#2392](https://github.com/pypeclub/OpenPype/pull/2392)
- Bump algoliasearch-helper from 3.4.4 to 3.6.2 in /website [\#2297](https://github.com/pypeclub/OpenPype/pull/2297)

## [3.7.0](https://github.com/pypeclub/OpenPype/tree/3.7.0) (2022-01-04)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.6.4...3.7.0)

**Deprecated:**

- General: Default modules hierarchy n2 [\#2368](https://github.com/pypeclub/OpenPype/pull/2368)

### 📖 Documentation

- docs\[website\]: Add Ellipse Studio \(logo\) as an OpenPype contributor [\#2324](https://github.com/pypeclub/OpenPype/pull/2324)

**🆕 New features**

- Settings UI use OpenPype styles [\#2296](https://github.com/pypeclub/OpenPype/pull/2296)
- Store typed version dependencies for workfiles [\#2192](https://github.com/pypeclub/OpenPype/pull/2192)
- OpenPypeV3: add key task type, task shortname and user to path templating construction [\#2157](https://github.com/pypeclub/OpenPype/pull/2157)
- Nuke: Alembic model workflow [\#2140](https://github.com/pypeclub/OpenPype/pull/2140)
- TVPaint: Load workfile from published. [\#1980](https://github.com/pypeclub/OpenPype/pull/1980)

**🚀 Enhancements**

- General: Workdir extra folders [\#2462](https://github.com/pypeclub/OpenPype/pull/2462)
- Photoshop: New style validations for New publisher [\#2429](https://github.com/pypeclub/OpenPype/pull/2429)
- General: Environment variables groups [\#2424](https://github.com/pypeclub/OpenPype/pull/2424)
- Unreal: Dynamic menu created in Python [\#2422](https://github.com/pypeclub/OpenPype/pull/2422)
- Settings UI: Hyperlinks to settings [\#2420](https://github.com/pypeclub/OpenPype/pull/2420)
- Modules: JobQueue module moved one hierarchy level higher [\#2419](https://github.com/pypeclub/OpenPype/pull/2419)
- TimersManager: Start timer post launch hook [\#2418](https://github.com/pypeclub/OpenPype/pull/2418)
- General: Run applications as separate processes under linux [\#2408](https://github.com/pypeclub/OpenPype/pull/2408)
- Ftrack: Check existence of object type on recreation [\#2404](https://github.com/pypeclub/OpenPype/pull/2404)
- Enhancement: Global cleanup plugin that explicitly remove paths from context [\#2402](https://github.com/pypeclub/OpenPype/pull/2402)
- General: MongoDB ability to specify replica set groups [\#2401](https://github.com/pypeclub/OpenPype/pull/2401)
- Flame: moving `utility_scripts` to api folder also with `scripts` [\#2385](https://github.com/pypeclub/OpenPype/pull/2385)
- Centos 7 dependency compatibility [\#2384](https://github.com/pypeclub/OpenPype/pull/2384)
- Enhancement: Settings: Use project settings values from another project [\#2382](https://github.com/pypeclub/OpenPype/pull/2382)
- Blender 3: Support auto install for new blender version [\#2377](https://github.com/pypeclub/OpenPype/pull/2377)
- Maya add render image path to settings [\#2375](https://github.com/pypeclub/OpenPype/pull/2375)
- Settings: Webpublisher in hosts enum [\#2367](https://github.com/pypeclub/OpenPype/pull/2367)
- Hiero: python3 compatibility [\#2365](https://github.com/pypeclub/OpenPype/pull/2365)
- Burnins: Be able recognize mxf OPAtom format [\#2361](https://github.com/pypeclub/OpenPype/pull/2361)
- Maya: Add is\_static\_image\_plane and is\_in\_all\_views option in imagePlaneLoader [\#2356](https://github.com/pypeclub/OpenPype/pull/2356)
- Local settings: Copyable studio paths [\#2349](https://github.com/pypeclub/OpenPype/pull/2349)
- Assets Widget: Clear model on project change [\#2345](https://github.com/pypeclub/OpenPype/pull/2345)
- General: OpenPype default modules hierarchy [\#2338](https://github.com/pypeclub/OpenPype/pull/2338)
- TVPaint: Move implementation to OpenPype [\#2336](https://github.com/pypeclub/OpenPype/pull/2336)
- General: FFprobe error exception contain original error message [\#2328](https://github.com/pypeclub/OpenPype/pull/2328)
- Resolve: Add experimental button to menu [\#2325](https://github.com/pypeclub/OpenPype/pull/2325)
- Hiero: Add experimental tools action [\#2323](https://github.com/pypeclub/OpenPype/pull/2323)
- Input links: Cleanup and unification of differences [\#2322](https://github.com/pypeclub/OpenPype/pull/2322)
- General: Don't validate vendor bin with executing them [\#2317](https://github.com/pypeclub/OpenPype/pull/2317)
- General: Multilayer EXRs support [\#2315](https://github.com/pypeclub/OpenPype/pull/2315)
- General: Run process log stderr as info log level [\#2309](https://github.com/pypeclub/OpenPype/pull/2309)
- General: Reduce vendor imports [\#2305](https://github.com/pypeclub/OpenPype/pull/2305)
- Tools: Cleanup of unused classes [\#2304](https://github.com/pypeclub/OpenPype/pull/2304)
- Project Manager: Added ability to delete project [\#2298](https://github.com/pypeclub/OpenPype/pull/2298)
- Ftrack: Synchronize input links [\#2287](https://github.com/pypeclub/OpenPype/pull/2287)
- StandalonePublisher: Remove unused plugin ExtractHarmonyZip [\#2277](https://github.com/pypeclub/OpenPype/pull/2277)
- Ftrack: Support multiple reviews [\#2271](https://github.com/pypeclub/OpenPype/pull/2271)
- Ftrack: Remove unused clean component plugin [\#2269](https://github.com/pypeclub/OpenPype/pull/2269)
- Royal Render: Support for rr channels in separate dirs [\#2268](https://github.com/pypeclub/OpenPype/pull/2268)
- Houdini: Add experimental tools action [\#2267](https://github.com/pypeclub/OpenPype/pull/2267)
- Nuke: extract baked review videos presets [\#2248](https://github.com/pypeclub/OpenPype/pull/2248)
- TVPaint: Workers rendering [\#2209](https://github.com/pypeclub/OpenPype/pull/2209)
- OpenPypeV3: Add key parent asset to path templating construction [\#2186](https://github.com/pypeclub/OpenPype/pull/2186)

**🐛 Bug fixes**

- TVPaint: Create render layer dialog is in front [\#2471](https://github.com/pypeclub/OpenPype/pull/2471)
- Short Pyblish plugin path [\#2428](https://github.com/pypeclub/OpenPype/pull/2428)
- PS: Introduced settings for invalid characters to use in ValidateNaming plugin [\#2417](https://github.com/pypeclub/OpenPype/pull/2417)
- Settings UI: Breadcrumbs path does not create new entities [\#2416](https://github.com/pypeclub/OpenPype/pull/2416)
- AfterEffects: Variant 2022 is in defaults but missing in schemas [\#2412](https://github.com/pypeclub/OpenPype/pull/2412)
- Nuke: baking representations was not additive [\#2406](https://github.com/pypeclub/OpenPype/pull/2406)
- General: Fix access to environments from default settings [\#2403](https://github.com/pypeclub/OpenPype/pull/2403)
- Fix: Placeholder Input color set fix [\#2399](https://github.com/pypeclub/OpenPype/pull/2399)
- Settings: Fix state change of wrapper label [\#2396](https://github.com/pypeclub/OpenPype/pull/2396)
- Flame: fix ftrack publisher [\#2381](https://github.com/pypeclub/OpenPype/pull/2381)
- hiero: solve custom ocio path  [\#2379](https://github.com/pypeclub/OpenPype/pull/2379)
- hiero: fix workio and flatten [\#2378](https://github.com/pypeclub/OpenPype/pull/2378)
- Nuke: fixing menu re-drawing during context change  [\#2374](https://github.com/pypeclub/OpenPype/pull/2374)
- Webpublisher: Fix assignment of families of TVpaint instances [\#2373](https://github.com/pypeclub/OpenPype/pull/2373)
- Nuke: fixing node name based on switched asset name [\#2369](https://github.com/pypeclub/OpenPype/pull/2369)
- JobQueue: Fix loading of settings [\#2362](https://github.com/pypeclub/OpenPype/pull/2362)
- Tools: Placeholder color [\#2359](https://github.com/pypeclub/OpenPype/pull/2359)
- Launcher: Minimize button on MacOs [\#2355](https://github.com/pypeclub/OpenPype/pull/2355)
- StandalonePublisher: Fix import of constant [\#2354](https://github.com/pypeclub/OpenPype/pull/2354)
- Houdini: Fix HDA creation [\#2350](https://github.com/pypeclub/OpenPype/pull/2350)
- Adobe products show issue [\#2347](https://github.com/pypeclub/OpenPype/pull/2347)
- Maya Look Assigner: Fix Python 3 compatibility [\#2343](https://github.com/pypeclub/OpenPype/pull/2343)
- Remove wrongly used host for hook [\#2342](https://github.com/pypeclub/OpenPype/pull/2342)
- Tools: Use Qt context on tools show [\#2340](https://github.com/pypeclub/OpenPype/pull/2340)
- Flame: Fix default argument value in custom dictionary [\#2339](https://github.com/pypeclub/OpenPype/pull/2339)
- Timers Manager: Disable auto stop timer on linux platform [\#2334](https://github.com/pypeclub/OpenPype/pull/2334)
- nuke: bake preset single input exception  [\#2331](https://github.com/pypeclub/OpenPype/pull/2331)
- Hiero: fixing multiple templates at a hierarchy parent [\#2330](https://github.com/pypeclub/OpenPype/pull/2330)
- Fix - provider icons are pulled from a folder [\#2326](https://github.com/pypeclub/OpenPype/pull/2326)
- InputLinks: Typo in "inputLinks" key [\#2314](https://github.com/pypeclub/OpenPype/pull/2314)
- Deadline timeout and logging [\#2312](https://github.com/pypeclub/OpenPype/pull/2312)
- nuke: do not multiply representation on class method [\#2311](https://github.com/pypeclub/OpenPype/pull/2311)
- Workfiles tool: Fix task formatting [\#2306](https://github.com/pypeclub/OpenPype/pull/2306)
- Delivery: Fix delivery paths created on windows [\#2302](https://github.com/pypeclub/OpenPype/pull/2302)
- Maya: Deadline - fix limit groups [\#2295](https://github.com/pypeclub/OpenPype/pull/2295)
- Royal Render: Fix plugin order and OpenPype auto-detection [\#2291](https://github.com/pypeclub/OpenPype/pull/2291)
- New Publisher: Fix mapping of indexes [\#2285](https://github.com/pypeclub/OpenPype/pull/2285)
- Alternate site for site sync doesnt work for sequences [\#2284](https://github.com/pypeclub/OpenPype/pull/2284)
- FFmpeg: Execute ffprobe using list of arguments instead of string command [\#2281](https://github.com/pypeclub/OpenPype/pull/2281)
- Nuke: Anatomy fill data use task as dictionary [\#2278](https://github.com/pypeclub/OpenPype/pull/2278)
- Bug: fix variable name \_asset\_id in workfiles application [\#2274](https://github.com/pypeclub/OpenPype/pull/2274)
- Version handling fixes [\#2272](https://github.com/pypeclub/OpenPype/pull/2272)

**Merged pull requests:**

- Maya: Replaced PATH usage with vendored oiio path for maketx utility [\#2405](https://github.com/pypeclub/OpenPype/pull/2405)
- \[Fix\]\[MAYA\] Handle message type attribute within CollectLook [\#2394](https://github.com/pypeclub/OpenPype/pull/2394)
- Add validator to check correct version of extension for PS and AE [\#2387](https://github.com/pypeclub/OpenPype/pull/2387)
- Maya: configurable model top level validation [\#2321](https://github.com/pypeclub/OpenPype/pull/2321)
- Create test publish class for After Effects [\#2270](https://github.com/pypeclub/OpenPype/pull/2270)

## [3.6.4](https://github.com/pypeclub/OpenPype/tree/3.6.4) (2021-11-23)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.6.3...3.6.4)

**🐛 Bug fixes**

- Nuke: inventory update removes all loaded read nodes [\#2294](https://github.com/pypeclub/OpenPype/pull/2294)

## [3.6.3](https://github.com/pypeclub/OpenPype/tree/3.6.3) (2021-11-19)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.6.2...3.6.3)

**🐛 Bug fixes**

- Deadline: Fix publish targets [\#2280](https://github.com/pypeclub/OpenPype/pull/2280)

## [3.6.2](https://github.com/pypeclub/OpenPype/tree/3.6.2) (2021-11-18)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.6.1...3.6.2)

**🚀 Enhancements**

- Tools: Assets widget [\#2265](https://github.com/pypeclub/OpenPype/pull/2265)
- SceneInventory: Choose loader in asset switcher [\#2262](https://github.com/pypeclub/OpenPype/pull/2262)
- Style: New fonts in OpenPype style [\#2256](https://github.com/pypeclub/OpenPype/pull/2256)
- Tools: SceneInventory in OpenPype  [\#2255](https://github.com/pypeclub/OpenPype/pull/2255)
- Tools: Tasks widget [\#2251](https://github.com/pypeclub/OpenPype/pull/2251)
- Tools: Creator in OpenPype [\#2244](https://github.com/pypeclub/OpenPype/pull/2244)
- Added endpoint for configured extensions [\#2221](https://github.com/pypeclub/OpenPype/pull/2221)

**🐛 Bug fixes**

- Tools: Parenting of tools in Nuke and Hiero [\#2266](https://github.com/pypeclub/OpenPype/pull/2266)
- limiting validator to specific editorial hosts [\#2264](https://github.com/pypeclub/OpenPype/pull/2264)
- Tools: Select Context dialog attribute fix [\#2261](https://github.com/pypeclub/OpenPype/pull/2261)
- Maya: Render publishing fails on linux [\#2260](https://github.com/pypeclub/OpenPype/pull/2260)
- LookAssigner: Fix tool reopen [\#2259](https://github.com/pypeclub/OpenPype/pull/2259)
- Standalone: editorial not publishing thumbnails on all subsets [\#2258](https://github.com/pypeclub/OpenPype/pull/2258)
- Burnins: Support mxf metadata [\#2247](https://github.com/pypeclub/OpenPype/pull/2247)
- Maya: Support for configurable AOV separator characters [\#2197](https://github.com/pypeclub/OpenPype/pull/2197)
- Maya: texture colorspace modes in looks [\#2195](https://github.com/pypeclub/OpenPype/pull/2195)

## [3.6.1](https://github.com/pypeclub/OpenPype/tree/3.6.1) (2021-11-16)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.6.0...3.6.1)

**🐛 Bug fixes**

- Loader doesn't allow changing of version before loading [\#2254](https://github.com/pypeclub/OpenPype/pull/2254)

## [3.6.0](https://github.com/pypeclub/OpenPype/tree/3.6.0) (2021-11-15)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.5.0...3.6.0)

### 📖 Documentation

- Add alternative sites for Site Sync [\#2206](https://github.com/pypeclub/OpenPype/pull/2206)
- Add command line way of running site sync server [\#2188](https://github.com/pypeclub/OpenPype/pull/2188)

**🆕 New features**

- Add validate active site button to sync queue on a project [\#2176](https://github.com/pypeclub/OpenPype/pull/2176)
- Maya : Colorspace configuration  [\#2170](https://github.com/pypeclub/OpenPype/pull/2170)
- Blender: Added support for audio [\#2168](https://github.com/pypeclub/OpenPype/pull/2168)
- Flame: a host basic integration [\#2165](https://github.com/pypeclub/OpenPype/pull/2165)
- Houdini: simple HDA workflow [\#2072](https://github.com/pypeclub/OpenPype/pull/2072)
- Basic Royal Render Integration ✨ [\#2061](https://github.com/pypeclub/OpenPype/pull/2061)
- Camera handling between Blender and Unreal [\#1988](https://github.com/pypeclub/OpenPype/pull/1988)
- switch PyQt5 for PySide2 [\#1744](https://github.com/pypeclub/OpenPype/pull/1744)

**🚀 Enhancements**

- Tools: Subset manager in OpenPype [\#2243](https://github.com/pypeclub/OpenPype/pull/2243)
- General: Skip module directories without init file [\#2239](https://github.com/pypeclub/OpenPype/pull/2239)
- General: Static interfaces [\#2238](https://github.com/pypeclub/OpenPype/pull/2238)
- Style: Fix transparent image in style [\#2235](https://github.com/pypeclub/OpenPype/pull/2235)
- Add a "following workfile versioning" option on publish [\#2225](https://github.com/pypeclub/OpenPype/pull/2225)
- Modules: Module can add cli commands [\#2224](https://github.com/pypeclub/OpenPype/pull/2224)
- Webpublisher: Separate webpublisher logic [\#2222](https://github.com/pypeclub/OpenPype/pull/2222)
- Add both side availability on Site Sync sites to Loader [\#2220](https://github.com/pypeclub/OpenPype/pull/2220)
- Tools: Center loader and library loader on show [\#2219](https://github.com/pypeclub/OpenPype/pull/2219)
- Maya : Validate shape zero [\#2212](https://github.com/pypeclub/OpenPype/pull/2212)
- Maya : validate unique names [\#2211](https://github.com/pypeclub/OpenPype/pull/2211)
- Tools: OpenPype stylesheet in workfiles tool [\#2208](https://github.com/pypeclub/OpenPype/pull/2208)
- Ftrack: Replace Queue with deque in event handlers logic [\#2204](https://github.com/pypeclub/OpenPype/pull/2204)
- Tools: New select context dialog [\#2200](https://github.com/pypeclub/OpenPype/pull/2200)
- Maya : Validate mesh ngons [\#2199](https://github.com/pypeclub/OpenPype/pull/2199)
- Dirmap in Nuke [\#2198](https://github.com/pypeclub/OpenPype/pull/2198)
- Delivery: Check 'frame' key in template for sequence delivery [\#2196](https://github.com/pypeclub/OpenPype/pull/2196)
- Settings: Site sync project settings improvement [\#2193](https://github.com/pypeclub/OpenPype/pull/2193)
- Usage of tools code [\#2185](https://github.com/pypeclub/OpenPype/pull/2185)
- Settings: Dictionary based on project roots [\#2184](https://github.com/pypeclub/OpenPype/pull/2184)
- Subset name: Be able to pass asset document to get subset name [\#2179](https://github.com/pypeclub/OpenPype/pull/2179)
- Tools: Experimental tools [\#2167](https://github.com/pypeclub/OpenPype/pull/2167)
- Loader: Refactor and use OpenPype stylesheets [\#2166](https://github.com/pypeclub/OpenPype/pull/2166)
- Add loader for linked smart objects in photoshop [\#2149](https://github.com/pypeclub/OpenPype/pull/2149)
- Burnins: DNxHD profiles handling [\#2142](https://github.com/pypeclub/OpenPype/pull/2142)
- Tools: Single access point for host tools [\#2139](https://github.com/pypeclub/OpenPype/pull/2139)

**🐛 Bug fixes**

- Ftrack: Sync project ftrack id cache issue [\#2250](https://github.com/pypeclub/OpenPype/pull/2250)
- Ftrack: Session creation and Prepare project [\#2245](https://github.com/pypeclub/OpenPype/pull/2245)
- Added queue for studio processing in PS [\#2237](https://github.com/pypeclub/OpenPype/pull/2237)
- Python 2: Unicode to string conversion [\#2236](https://github.com/pypeclub/OpenPype/pull/2236)
- Fix - enum for color coding in PS [\#2234](https://github.com/pypeclub/OpenPype/pull/2234)
- Pyblish Tool: Fix targets handling [\#2232](https://github.com/pypeclub/OpenPype/pull/2232)
- Ftrack: Base event fix of 'get\_project\_from\_entity' method [\#2214](https://github.com/pypeclub/OpenPype/pull/2214)
- Maya : multiple subsets review broken [\#2210](https://github.com/pypeclub/OpenPype/pull/2210)
- Fix - different command used for Linux and Mac OS [\#2207](https://github.com/pypeclub/OpenPype/pull/2207)
- Tools: Workfiles tool don't use avalon widgets [\#2205](https://github.com/pypeclub/OpenPype/pull/2205)
- Ftrack: Fill missing ftrack id on mongo project [\#2203](https://github.com/pypeclub/OpenPype/pull/2203)
- Project Manager: Fix copying of tasks [\#2191](https://github.com/pypeclub/OpenPype/pull/2191)
- StandalonePublisher: Source validator don't expect representations [\#2190](https://github.com/pypeclub/OpenPype/pull/2190)
- Blender: Fix trying to pack an image when the shader node has no texture [\#2183](https://github.com/pypeclub/OpenPype/pull/2183)
- Maya: review viewport settings [\#2177](https://github.com/pypeclub/OpenPype/pull/2177)
- MacOS: Launching of applications may cause Permissions error [\#2175](https://github.com/pypeclub/OpenPype/pull/2175)
- Maya: Aspect ratio [\#2174](https://github.com/pypeclub/OpenPype/pull/2174)
- Blender: Fix 'Deselect All' with object not in 'Object Mode' [\#2163](https://github.com/pypeclub/OpenPype/pull/2163)
- Tools: Stylesheets are applied after tool show [\#2161](https://github.com/pypeclub/OpenPype/pull/2161)
- Maya: Collect render - fix UNC path support 🐛 [\#2158](https://github.com/pypeclub/OpenPype/pull/2158)
- Maya: Fix hotbox broken by scriptsmenu [\#2151](https://github.com/pypeclub/OpenPype/pull/2151)
- Ftrack: Ignore save warnings exception in Prepare project action [\#2150](https://github.com/pypeclub/OpenPype/pull/2150)
- Loader thumbnails with smooth edges [\#2147](https://github.com/pypeclub/OpenPype/pull/2147)
- Added validator for source files for Standalone Publisher [\#2138](https://github.com/pypeclub/OpenPype/pull/2138)

**Merged pull requests:**

- Bump pillow from 8.2.0 to 8.3.2 [\#2162](https://github.com/pypeclub/OpenPype/pull/2162)
- Bump axios from 0.21.1 to 0.21.4 in /website [\#2059](https://github.com/pypeclub/OpenPype/pull/2059)

## [3.5.0](https://github.com/pypeclub/OpenPype/tree/3.5.0) (2021-10-17)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.4.1...3.5.0)

**Deprecated:**

- Maya: Change mayaAscii family to mayaScene [\#2106](https://github.com/pypeclub/OpenPype/pull/2106)

**🆕 New features**

- Added project and task into context change message in Maya [\#2131](https://github.com/pypeclub/OpenPype/pull/2131)
- Add ExtractBurnin to photoshop review [\#2124](https://github.com/pypeclub/OpenPype/pull/2124)
- PYPE-1218 - changed namespace to contain subset name in Maya [\#2114](https://github.com/pypeclub/OpenPype/pull/2114)
- Added running configurable disk mapping command before start of OP [\#2091](https://github.com/pypeclub/OpenPype/pull/2091)
- SFTP provider [\#2073](https://github.com/pypeclub/OpenPype/pull/2073)
- Maya: Validate setdress top group [\#2068](https://github.com/pypeclub/OpenPype/pull/2068)
- Maya: Enable publishing render attrib sets \(e.g. V-Ray Displacement\) with model [\#1955](https://github.com/pypeclub/OpenPype/pull/1955)

**🚀 Enhancements**

- Maya: make rig validators configurable in settings [\#2137](https://github.com/pypeclub/OpenPype/pull/2137)
- Settings: Updated readme for entity types in settings [\#2132](https://github.com/pypeclub/OpenPype/pull/2132)
- Nuke: unified clip loader [\#2128](https://github.com/pypeclub/OpenPype/pull/2128)
- Settings UI: Project model refreshing and sorting [\#2104](https://github.com/pypeclub/OpenPype/pull/2104)
- Create Read From Rendered - Disable Relative paths by default [\#2093](https://github.com/pypeclub/OpenPype/pull/2093)
- Added choosing different dirmap mapping if workfile synched locally [\#2088](https://github.com/pypeclub/OpenPype/pull/2088)
- General: Remove IdleManager module [\#2084](https://github.com/pypeclub/OpenPype/pull/2084)
- Tray UI: Message box about missing settings defaults [\#2080](https://github.com/pypeclub/OpenPype/pull/2080)
- Tray UI: Show menu where first click happened [\#2079](https://github.com/pypeclub/OpenPype/pull/2079)
- Global: add global validators to settings [\#2078](https://github.com/pypeclub/OpenPype/pull/2078)
- Use CRF for burnin when available [\#2070](https://github.com/pypeclub/OpenPype/pull/2070)
- Project manager: Filter first item after selection of project [\#2069](https://github.com/pypeclub/OpenPype/pull/2069)
- Nuke: Adding `still` image family workflow [\#2064](https://github.com/pypeclub/OpenPype/pull/2064)
- Maya: validate authorized loaded plugins [\#2062](https://github.com/pypeclub/OpenPype/pull/2062)
- Tools: add support for pyenv on windows [\#2051](https://github.com/pypeclub/OpenPype/pull/2051)
- SyncServer: Dropbox Provider [\#1979](https://github.com/pypeclub/OpenPype/pull/1979)
- Burnin: Get data from context with defined keys. [\#1897](https://github.com/pypeclub/OpenPype/pull/1897)
- Timers manager: Get task time [\#1896](https://github.com/pypeclub/OpenPype/pull/1896)
- TVPaint: Option to stop timer on application exit. [\#1887](https://github.com/pypeclub/OpenPype/pull/1887)

**🐛 Bug fixes**

- Maya: fix model publishing [\#2130](https://github.com/pypeclub/OpenPype/pull/2130)
- Fix - oiiotool wasn't recognized even if present [\#2129](https://github.com/pypeclub/OpenPype/pull/2129)
- General: Disk mapping group [\#2120](https://github.com/pypeclub/OpenPype/pull/2120)
- Hiero: publishing effect first time makes wrong resources path [\#2115](https://github.com/pypeclub/OpenPype/pull/2115)
- Add startup script for Houdini Core.  [\#2110](https://github.com/pypeclub/OpenPype/pull/2110)
- TVPaint: Behavior name of loop also accept repeat [\#2109](https://github.com/pypeclub/OpenPype/pull/2109)
- Ftrack: Project settings save custom attributes skip unknown attributes [\#2103](https://github.com/pypeclub/OpenPype/pull/2103)
- Blender: Fix NoneType error when animation\_data is missing for a rig [\#2101](https://github.com/pypeclub/OpenPype/pull/2101)
- Fix broken import in sftp provider [\#2100](https://github.com/pypeclub/OpenPype/pull/2100)
- Global: Fix docstring on publish plugin extract review [\#2097](https://github.com/pypeclub/OpenPype/pull/2097)
- Delivery Action Files Sequence fix [\#2096](https://github.com/pypeclub/OpenPype/pull/2096)
- General: Cloud mongo ca certificate issue [\#2095](https://github.com/pypeclub/OpenPype/pull/2095)
- TVPaint: Creator use context from workfile [\#2087](https://github.com/pypeclub/OpenPype/pull/2087)
- Blender: fix texture missing when publishing blend files [\#2085](https://github.com/pypeclub/OpenPype/pull/2085)
- General: Startup validations oiio tool path fix on linux [\#2083](https://github.com/pypeclub/OpenPype/pull/2083)
- Deadline: Collect deadline server does not check existence of deadline key [\#2082](https://github.com/pypeclub/OpenPype/pull/2082)
- Blender: fixed Curves with modifiers in Rigs [\#2081](https://github.com/pypeclub/OpenPype/pull/2081)
- Nuke UI scaling [\#2077](https://github.com/pypeclub/OpenPype/pull/2077)
- Maya: Fix multi-camera renders [\#2065](https://github.com/pypeclub/OpenPype/pull/2065)
- Fix Sync Queue when project disabled [\#2063](https://github.com/pypeclub/OpenPype/pull/2063)

**Merged pull requests:**

- Bump pywin32 from 300 to 301 [\#2086](https://github.com/pypeclub/OpenPype/pull/2086)

## [3.4.1](https://github.com/pypeclub/OpenPype/tree/3.4.1) (2021-09-23)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.4.0...3.4.1)

**🆕 New features**

- Settings: Flag project as deactivated and hide from tools' view [\#2008](https://github.com/pypeclub/OpenPype/pull/2008)

**🚀 Enhancements**

- General: Startup validations [\#2054](https://github.com/pypeclub/OpenPype/pull/2054)
- Nuke: proxy mode validator [\#2052](https://github.com/pypeclub/OpenPype/pull/2052)
- Ftrack: Removed ftrack interface [\#2049](https://github.com/pypeclub/OpenPype/pull/2049)
- Settings UI: Deffered set value on entity [\#2044](https://github.com/pypeclub/OpenPype/pull/2044)
- Loader: Families filtering [\#2043](https://github.com/pypeclub/OpenPype/pull/2043)
- Settings UI: Project view enhancements [\#2042](https://github.com/pypeclub/OpenPype/pull/2042)
- Settings for Nuke IncrementScriptVersion [\#2039](https://github.com/pypeclub/OpenPype/pull/2039)
- Loader & Library loader: Use tools from OpenPype [\#2038](https://github.com/pypeclub/OpenPype/pull/2038)
- Adding predefined project folders creation in PM [\#2030](https://github.com/pypeclub/OpenPype/pull/2030)
- WebserverModule: Removed interface of webserver module [\#2028](https://github.com/pypeclub/OpenPype/pull/2028)
- TimersManager: Removed interface of timers manager [\#2024](https://github.com/pypeclub/OpenPype/pull/2024)
- Feature Maya import asset from scene inventory [\#2018](https://github.com/pypeclub/OpenPype/pull/2018)

**🐛 Bug fixes**

- Timers manger: Typo fix [\#2058](https://github.com/pypeclub/OpenPype/pull/2058)
- Hiero: Editorial fixes [\#2057](https://github.com/pypeclub/OpenPype/pull/2057)
- Differentiate jpg sequences from thumbnail [\#2056](https://github.com/pypeclub/OpenPype/pull/2056)
- FFmpeg: Split command to list does not work [\#2046](https://github.com/pypeclub/OpenPype/pull/2046)
- Removed shell flag in subprocess call [\#2045](https://github.com/pypeclub/OpenPype/pull/2045)

**Merged pull requests:**

- Bump prismjs from 1.24.0 to 1.25.0 in /website [\#2050](https://github.com/pypeclub/OpenPype/pull/2050)

## [3.4.0](https://github.com/pypeclub/OpenPype/tree/3.4.0) (2021-09-17)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.3.1...3.4.0)

### 📖 Documentation

- Documentation: Ftrack launch argsuments update [\#2014](https://github.com/pypeclub/OpenPype/pull/2014)
- Nuke Quick Start / Tutorial [\#1952](https://github.com/pypeclub/OpenPype/pull/1952)
- Houdini: add Camera, Point Cache, Composite, Redshift ROP and VDB Cache support [\#1821](https://github.com/pypeclub/OpenPype/pull/1821)

**🆕 New features**

- Nuke: Compatibility with Nuke 13 [\#2003](https://github.com/pypeclub/OpenPype/pull/2003)
- Maya: Add Xgen family support [\#1947](https://github.com/pypeclub/OpenPype/pull/1947)
- Feature/webpublisher backend [\#1876](https://github.com/pypeclub/OpenPype/pull/1876)
- Blender: Improved assets handling [\#1615](https://github.com/pypeclub/OpenPype/pull/1615)

**🚀 Enhancements**

- Added possibility to configure of synchronization of workfile version… [\#2041](https://github.com/pypeclub/OpenPype/pull/2041)
- General: Task types in profiles [\#2036](https://github.com/pypeclub/OpenPype/pull/2036)
- Console interpreter: Handle invalid sizes on initialization [\#2022](https://github.com/pypeclub/OpenPype/pull/2022)
- Ftrack: Show OpenPype versions in event server status [\#2019](https://github.com/pypeclub/OpenPype/pull/2019)
- General: Staging icon [\#2017](https://github.com/pypeclub/OpenPype/pull/2017)
- Ftrack: Sync to avalon actions have jobs [\#2015](https://github.com/pypeclub/OpenPype/pull/2015)
- Modules: Connect method is not required [\#2009](https://github.com/pypeclub/OpenPype/pull/2009)
- Settings UI: Number with configurable steps [\#2001](https://github.com/pypeclub/OpenPype/pull/2001)
- Moving project folder structure creation out of ftrack module \#1989 [\#1996](https://github.com/pypeclub/OpenPype/pull/1996)
- Configurable items for providers without Settings [\#1987](https://github.com/pypeclub/OpenPype/pull/1987)
- Global: Example addons [\#1986](https://github.com/pypeclub/OpenPype/pull/1986)
- Standalone Publisher: Extract harmony zip handle workfile template [\#1982](https://github.com/pypeclub/OpenPype/pull/1982)
- Settings UI: Number sliders [\#1978](https://github.com/pypeclub/OpenPype/pull/1978)
- Workfiles: Support more workfile templates [\#1966](https://github.com/pypeclub/OpenPype/pull/1966)
- Launcher: Fix crashes on action click [\#1964](https://github.com/pypeclub/OpenPype/pull/1964)
- Settings: Minor fixes in UI and missing default values [\#1963](https://github.com/pypeclub/OpenPype/pull/1963)
- Blender: Toggle system console works on windows [\#1962](https://github.com/pypeclub/OpenPype/pull/1962)
- Global: Settings defined by Addons/Modules [\#1959](https://github.com/pypeclub/OpenPype/pull/1959)
- CI: change release numbering triggers [\#1954](https://github.com/pypeclub/OpenPype/pull/1954)
- Global: Avalon Host name collector [\#1949](https://github.com/pypeclub/OpenPype/pull/1949)
- Global: Define hosts in CollectSceneVersion [\#1948](https://github.com/pypeclub/OpenPype/pull/1948)
- Add face sets to exported alembics [\#1942](https://github.com/pypeclub/OpenPype/pull/1942)
- OpenPype: Add version validation and `--headless` mode and update progress 🔄 [\#1939](https://github.com/pypeclub/OpenPype/pull/1939)
- \#1894 - adds host to template\_name\_profiles for filtering [\#1915](https://github.com/pypeclub/OpenPype/pull/1915)
- Environments: Tool environments in alphabetical order [\#1910](https://github.com/pypeclub/OpenPype/pull/1910)
- Disregard publishing time. [\#1888](https://github.com/pypeclub/OpenPype/pull/1888)
- Dynamic modules [\#1872](https://github.com/pypeclub/OpenPype/pull/1872)

**🐛 Bug fixes**

- Workfiles tool: Task selection [\#2040](https://github.com/pypeclub/OpenPype/pull/2040)
- Ftrack: Delete old versions missing settings key [\#2037](https://github.com/pypeclub/OpenPype/pull/2037)
- Nuke: typo on a button [\#2034](https://github.com/pypeclub/OpenPype/pull/2034)
- Hiero: Fix "none" named tags [\#2033](https://github.com/pypeclub/OpenPype/pull/2033)
- FFmpeg: Subprocess arguments as list [\#2032](https://github.com/pypeclub/OpenPype/pull/2032)
- General: Fix Python 2 breaking line [\#2016](https://github.com/pypeclub/OpenPype/pull/2016)
- Bugfix/webpublisher task type [\#2006](https://github.com/pypeclub/OpenPype/pull/2006)
- Nuke thumbnails generated from middle of the sequence [\#1992](https://github.com/pypeclub/OpenPype/pull/1992)
- Nuke: last version from path gets correct version [\#1990](https://github.com/pypeclub/OpenPype/pull/1990)
- nuke, resolve, hiero: precollector order lest then 0.5 [\#1984](https://github.com/pypeclub/OpenPype/pull/1984)
- Last workfile with multiple work templates [\#1981](https://github.com/pypeclub/OpenPype/pull/1981)
- Collectors order [\#1977](https://github.com/pypeclub/OpenPype/pull/1977)
- Stop timer was within validator order range. [\#1975](https://github.com/pypeclub/OpenPype/pull/1975)
- Ftrack: arrow submodule has https url source [\#1974](https://github.com/pypeclub/OpenPype/pull/1974)
- Ftrack: Fix hosts attribute in collect ftrack username [\#1972](https://github.com/pypeclub/OpenPype/pull/1972)
- Deadline: Houdini plugins in different hierarchy [\#1970](https://github.com/pypeclub/OpenPype/pull/1970)
- Removed deprecated submodules [\#1967](https://github.com/pypeclub/OpenPype/pull/1967)
- Global: ExtractJpeg can handle filepaths with spaces [\#1961](https://github.com/pypeclub/OpenPype/pull/1961)
- Resolve path when adding to zip [\#1960](https://github.com/pypeclub/OpenPype/pull/1960)

**Merged pull requests:**

- Bump url-parse from 1.5.1 to 1.5.3 in /website [\#1958](https://github.com/pypeclub/OpenPype/pull/1958)
- Bump path-parse from 1.0.6 to 1.0.7 in /website [\#1933](https://github.com/pypeclub/OpenPype/pull/1933)

## [3.3.1](https://github.com/pypeclub/OpenPype/tree/3.3.1) (2021-08-20)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.3.0...3.3.1)

**🐛 Bug fixes**

- TVPaint: Fixed rendered frame indexes [\#1946](https://github.com/pypeclub/OpenPype/pull/1946)
- Maya: Menu actions fix [\#1945](https://github.com/pypeclub/OpenPype/pull/1945)
- standalone: editorial shared object problem [\#1941](https://github.com/pypeclub/OpenPype/pull/1941)
- Bugfix nuke deadline app name [\#1928](https://github.com/pypeclub/OpenPype/pull/1928)

## [3.3.0](https://github.com/pypeclub/OpenPype/tree/3.3.0) (2021-08-17)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.2.0...3.3.0)

### 📖 Documentation

- Standalone Publish of textures family [\#1834](https://github.com/pypeclub/OpenPype/pull/1834)

**🆕 New features**

- Settings UI: Breadcrumbs in settings [\#1932](https://github.com/pypeclub/OpenPype/pull/1932)
- Maya: Scene patching 🩹on submission to Deadline [\#1923](https://github.com/pypeclub/OpenPype/pull/1923)
- Feature AE local render [\#1901](https://github.com/pypeclub/OpenPype/pull/1901)

**🚀 Enhancements**

- Python console interpreter [\#1940](https://github.com/pypeclub/OpenPype/pull/1940)
- Global: Updated logos and Default settings [\#1927](https://github.com/pypeclub/OpenPype/pull/1927)
- Check for missing ✨ Python when using `pyenv` [\#1925](https://github.com/pypeclub/OpenPype/pull/1925)
- Settings: Default values for enum [\#1920](https://github.com/pypeclub/OpenPype/pull/1920)
- Settings UI: Modifiable dict view enhance [\#1919](https://github.com/pypeclub/OpenPype/pull/1919)
- submodules: avalon-core update [\#1911](https://github.com/pypeclub/OpenPype/pull/1911)
- Ftrack: Where I run action enhancement [\#1900](https://github.com/pypeclub/OpenPype/pull/1900)
- Ftrack: Private project server actions [\#1899](https://github.com/pypeclub/OpenPype/pull/1899)
- Support nested studio plugins paths. [\#1898](https://github.com/pypeclub/OpenPype/pull/1898)
- Settings: global validators with options [\#1892](https://github.com/pypeclub/OpenPype/pull/1892)
- Settings: Conditional dict enum positioning [\#1891](https://github.com/pypeclub/OpenPype/pull/1891)
- Expose stop timer through rest api. [\#1886](https://github.com/pypeclub/OpenPype/pull/1886)
- TVPaint: Increment workfile [\#1885](https://github.com/pypeclub/OpenPype/pull/1885)
- Allow Multiple Notes to run on tasks. [\#1882](https://github.com/pypeclub/OpenPype/pull/1882)
- Prepare for pyside2 [\#1869](https://github.com/pypeclub/OpenPype/pull/1869)
- Filter hosts in settings host-enum [\#1868](https://github.com/pypeclub/OpenPype/pull/1868)
- Local actions with process identifier [\#1867](https://github.com/pypeclub/OpenPype/pull/1867)
- Workfile tool start at host launch support [\#1865](https://github.com/pypeclub/OpenPype/pull/1865)
- Anatomy schema validation [\#1864](https://github.com/pypeclub/OpenPype/pull/1864)
- Ftrack prepare project structure [\#1861](https://github.com/pypeclub/OpenPype/pull/1861)
- Maya: support for configurable `dirmap` 🗺️ [\#1859](https://github.com/pypeclub/OpenPype/pull/1859)
- Independent general environments [\#1853](https://github.com/pypeclub/OpenPype/pull/1853)
- TVPaint Start Frame [\#1844](https://github.com/pypeclub/OpenPype/pull/1844)
- Ftrack push attributes action adds traceback to job [\#1843](https://github.com/pypeclub/OpenPype/pull/1843)
- Prepare project action enhance [\#1838](https://github.com/pypeclub/OpenPype/pull/1838)
- nuke: settings create missing default subsets [\#1829](https://github.com/pypeclub/OpenPype/pull/1829)
- Update poetry lock [\#1823](https://github.com/pypeclub/OpenPype/pull/1823)
- Settings: settings for plugins [\#1819](https://github.com/pypeclub/OpenPype/pull/1819)
- Settings list can use template or schema as object type [\#1815](https://github.com/pypeclub/OpenPype/pull/1815)
- Maya: Deadline custom settings  [\#1797](https://github.com/pypeclub/OpenPype/pull/1797)
- Maya: Shader name validation [\#1762](https://github.com/pypeclub/OpenPype/pull/1762)

**🐛 Bug fixes**

- Fix - ftrack family was added incorrectly in some cases [\#1935](https://github.com/pypeclub/OpenPype/pull/1935)
- Fix - Deadline publish on Linux started Tray instead of headless publishing [\#1930](https://github.com/pypeclub/OpenPype/pull/1930)
- Maya: Validate Model Name - repair accident deletion in settings defaults [\#1929](https://github.com/pypeclub/OpenPype/pull/1929)
- Nuke: submit to farm failed due `ftrack` family remove [\#1926](https://github.com/pypeclub/OpenPype/pull/1926)
- Fix - validate takes repre\["files"\] as list all the time [\#1922](https://github.com/pypeclub/OpenPype/pull/1922)
- standalone: validator asset parents [\#1917](https://github.com/pypeclub/OpenPype/pull/1917)
- Nuke: update video file crassing [\#1916](https://github.com/pypeclub/OpenPype/pull/1916)
- Fix - texture validators for workfiles triggers only for textures workfiles [\#1914](https://github.com/pypeclub/OpenPype/pull/1914)
- Settings UI: List order works as expected [\#1906](https://github.com/pypeclub/OpenPype/pull/1906)
- Hiero: loaded clip was not set colorspace from version data [\#1904](https://github.com/pypeclub/OpenPype/pull/1904)
- Pyblish UI: Fix collecting stage processing [\#1903](https://github.com/pypeclub/OpenPype/pull/1903)
- Burnins: Use input's bitrate in h624 [\#1902](https://github.com/pypeclub/OpenPype/pull/1902)
- Bug: fixed python detection [\#1893](https://github.com/pypeclub/OpenPype/pull/1893)
- global: integrate name missing default template [\#1890](https://github.com/pypeclub/OpenPype/pull/1890)
- publisher: editorial plugins fixes [\#1889](https://github.com/pypeclub/OpenPype/pull/1889)
- Normalize path returned from Workfiles. [\#1880](https://github.com/pypeclub/OpenPype/pull/1880)
- Workfiles tool event arguments fix [\#1862](https://github.com/pypeclub/OpenPype/pull/1862)
- imageio: fix grouping  [\#1856](https://github.com/pypeclub/OpenPype/pull/1856)
- Maya: don't add reference members as connections to the container set 📦 [\#1855](https://github.com/pypeclub/OpenPype/pull/1855)
- publisher: missing version in subset prop [\#1849](https://github.com/pypeclub/OpenPype/pull/1849)
- Ftrack type error fix in sync to avalon event handler [\#1845](https://github.com/pypeclub/OpenPype/pull/1845)
- Nuke: updating effects subset fail [\#1841](https://github.com/pypeclub/OpenPype/pull/1841)
- nuke: write render node skipped with crop [\#1836](https://github.com/pypeclub/OpenPype/pull/1836)
- Project folder structure overrides [\#1813](https://github.com/pypeclub/OpenPype/pull/1813)
- Maya: fix yeti settings path in extractor [\#1809](https://github.com/pypeclub/OpenPype/pull/1809)
- Failsafe for cross project containers. [\#1806](https://github.com/pypeclub/OpenPype/pull/1806)
- Houdini colector formatting keys fix [\#1802](https://github.com/pypeclub/OpenPype/pull/1802)
- Settings error dialog on show [\#1798](https://github.com/pypeclub/OpenPype/pull/1798)
- Application launch stdout/stderr in GUI build [\#1684](https://github.com/pypeclub/OpenPype/pull/1684)
- Nuke: re-use instance nodes output path [\#1577](https://github.com/pypeclub/OpenPype/pull/1577)

**Merged pull requests:**

- Fix - make AE workfile publish to Ftrack configurable [\#1937](https://github.com/pypeclub/OpenPype/pull/1937)
- Add support for multiple Deadline ☠️➖ servers [\#1905](https://github.com/pypeclub/OpenPype/pull/1905)
- Maya: add support for `RedshiftNormalMap` node, fix `tx` linear space 🚀 [\#1863](https://github.com/pypeclub/OpenPype/pull/1863)
- Maya: expected files -\> render products ⚙️ overhaul [\#1812](https://github.com/pypeclub/OpenPype/pull/1812)
- PS, AE - send actual context when another webserver is running [\#1811](https://github.com/pypeclub/OpenPype/pull/1811)

## [3.2.0](https://github.com/pypeclub/OpenPype/tree/3.2.0) (2021-07-13)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/2.18.4...3.2.0)

### 📖 Documentation

- Fix: staging and `--use-version` option [\#1786](https://github.com/pypeclub/OpenPype/pull/1786)
- Subset template and TVPaint subset template docs [\#1717](https://github.com/pypeclub/OpenPype/pull/1717)
- Overscan color extract review [\#1701](https://github.com/pypeclub/OpenPype/pull/1701)

**🚀 Enhancements**

- Nuke: ftrack family plugin settings preset [\#1805](https://github.com/pypeclub/OpenPype/pull/1805)
- Standalone publisher last project [\#1799](https://github.com/pypeclub/OpenPype/pull/1799)
- Ftrack Multiple notes as server action [\#1795](https://github.com/pypeclub/OpenPype/pull/1795)
- Settings conditional dict [\#1777](https://github.com/pypeclub/OpenPype/pull/1777)
- Settings application use python 2 only where needed [\#1776](https://github.com/pypeclub/OpenPype/pull/1776)
- Settings UI copy/paste [\#1769](https://github.com/pypeclub/OpenPype/pull/1769)
- Workfile tool widths [\#1766](https://github.com/pypeclub/OpenPype/pull/1766)
- Push hierarchical attributes care about task parent changes [\#1763](https://github.com/pypeclub/OpenPype/pull/1763)
- Application executables with environment variables [\#1757](https://github.com/pypeclub/OpenPype/pull/1757)
- Deadline: Nuke submission additional attributes [\#1756](https://github.com/pypeclub/OpenPype/pull/1756)
- Settings schema without prefill [\#1753](https://github.com/pypeclub/OpenPype/pull/1753)
- Settings Hosts enum [\#1739](https://github.com/pypeclub/OpenPype/pull/1739)
- Validate containers settings [\#1736](https://github.com/pypeclub/OpenPype/pull/1736)
- PS - added loader from sequence [\#1726](https://github.com/pypeclub/OpenPype/pull/1726)
- Autoupdate launcher [\#1725](https://github.com/pypeclub/OpenPype/pull/1725)
- Toggle Ftrack upload in StandalonePublisher [\#1708](https://github.com/pypeclub/OpenPype/pull/1708)
- Nuke: Prerender Frame Range by default [\#1699](https://github.com/pypeclub/OpenPype/pull/1699)
- Smoother edges of color triangle [\#1695](https://github.com/pypeclub/OpenPype/pull/1695)

**🐛 Bug fixes**

- nuke: fixing wrong name of family folder when `used existing frames` [\#1803](https://github.com/pypeclub/OpenPype/pull/1803)
- Collect ftrack family bugs [\#1801](https://github.com/pypeclub/OpenPype/pull/1801)
- Invitee email can be None which break the Ftrack commit. [\#1788](https://github.com/pypeclub/OpenPype/pull/1788)
- Otio unrelated error on import [\#1782](https://github.com/pypeclub/OpenPype/pull/1782)
- FFprobe streams order [\#1775](https://github.com/pypeclub/OpenPype/pull/1775)
- Fix - single file files are str only, cast it to list to count properly [\#1772](https://github.com/pypeclub/OpenPype/pull/1772)
- Environments in app executable for MacOS [\#1768](https://github.com/pypeclub/OpenPype/pull/1768)
- Project specific environments [\#1767](https://github.com/pypeclub/OpenPype/pull/1767)
- Settings UI with refresh button [\#1764](https://github.com/pypeclub/OpenPype/pull/1764)
- Standalone publisher thumbnail extractor fix [\#1761](https://github.com/pypeclub/OpenPype/pull/1761)
- Anatomy others templates don't cause crash [\#1758](https://github.com/pypeclub/OpenPype/pull/1758)
- Backend acre module commit update [\#1745](https://github.com/pypeclub/OpenPype/pull/1745)
- hiero: precollect instances failing when audio selected [\#1743](https://github.com/pypeclub/OpenPype/pull/1743)
- Hiero: creator instance error [\#1742](https://github.com/pypeclub/OpenPype/pull/1742)
- Nuke: fixing render creator for no selection format failing [\#1741](https://github.com/pypeclub/OpenPype/pull/1741)
- StandalonePublisher: failing collector for editorial [\#1738](https://github.com/pypeclub/OpenPype/pull/1738)
- Local settings UI crash on missing defaults [\#1737](https://github.com/pypeclub/OpenPype/pull/1737)
- TVPaint white background on thumbnail [\#1735](https://github.com/pypeclub/OpenPype/pull/1735)
- Ftrack missing custom attribute message [\#1734](https://github.com/pypeclub/OpenPype/pull/1734)
- Launcher project changes [\#1733](https://github.com/pypeclub/OpenPype/pull/1733)
- Ftrack sync status [\#1732](https://github.com/pypeclub/OpenPype/pull/1732)
- TVPaint use layer name for default variant [\#1724](https://github.com/pypeclub/OpenPype/pull/1724)
- Default subset template for TVPaint review and workfile families [\#1716](https://github.com/pypeclub/OpenPype/pull/1716)
- Maya: Extract review hotfix [\#1714](https://github.com/pypeclub/OpenPype/pull/1714)
- Settings: Imageio improving granularity [\#1711](https://github.com/pypeclub/OpenPype/pull/1711)
- Application without executables [\#1679](https://github.com/pypeclub/OpenPype/pull/1679)
- Unreal: launching on Linux [\#1672](https://github.com/pypeclub/OpenPype/pull/1672)

**Merged pull requests:**

- Bump prismjs from 1.23.0 to 1.24.0 in /website [\#1773](https://github.com/pypeclub/OpenPype/pull/1773)
- TVPaint ftrack family [\#1755](https://github.com/pypeclub/OpenPype/pull/1755)

## [2.18.4](https://github.com/pypeclub/OpenPype/tree/2.18.4) (2021-06-24)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/2.18.3...2.18.4)

## [2.18.3](https://github.com/pypeclub/OpenPype/tree/2.18.3) (2021-06-23)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/2.18.2...2.18.3)

## [2.18.2](https://github.com/pypeclub/OpenPype/tree/2.18.2) (2021-06-16)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.1.0...2.18.2)

## [3.1.0](https://github.com/pypeclub/OpenPype/tree/3.1.0) (2021-06-15)

[Full Changelog](https://github.com/pypeclub/OpenPype/compare/3.0.0...3.1.0)

### 📖 Documentation

- Feature Slack integration [\#1657](https://github.com/pypeclub/OpenPype/pull/1657)

**🚀 Enhancements**

- Log Viewer with OpenPype style [\#1703](https://github.com/pypeclub/OpenPype/pull/1703)
- Scrolling in OpenPype info widget [\#1702](https://github.com/pypeclub/OpenPype/pull/1702)
- OpenPype style in modules [\#1694](https://github.com/pypeclub/OpenPype/pull/1694)
- Sort applications and tools alphabetically in Settings UI [\#1689](https://github.com/pypeclub/OpenPype/pull/1689)
- \#683 - Validate Frame Range in Standalone Publisher [\#1683](https://github.com/pypeclub/OpenPype/pull/1683)
- Hiero: old container versions identify with red color [\#1682](https://github.com/pypeclub/OpenPype/pull/1682)
- Project Manger: Default name column width [\#1669](https://github.com/pypeclub/OpenPype/pull/1669)
- Remove outline in stylesheet [\#1667](https://github.com/pypeclub/OpenPype/pull/1667)
- TVPaint: Creator take layer name as default value for subset variant [\#1663](https://github.com/pypeclub/OpenPype/pull/1663)
- TVPaint custom subset template [\#1662](https://github.com/pypeclub/OpenPype/pull/1662)
- Editorial: conform assets validator [\#1659](https://github.com/pypeclub/OpenPype/pull/1659)
- Nuke - Publish simplification [\#1653](https://github.com/pypeclub/OpenPype/pull/1653)
- \#1333 - added tooltip hints to Pyblish buttons [\#1649](https://github.com/pypeclub/OpenPype/pull/1649)

**🐛 Bug fixes**

- Nuke: broken publishing rendered frames [\#1707](https://github.com/pypeclub/OpenPype/pull/1707)
- Standalone publisher Thumbnail export args [\#1705](https://github.com/pypeclub/OpenPype/pull/1705)
- Bad zip can break OpenPype start [\#1691](https://github.com/pypeclub/OpenPype/pull/1691)
- Hiero: published whole edit mov [\#1687](https://github.com/pypeclub/OpenPype/pull/1687)
- Ftrack subprocess handle of stdout/stderr [\#1675](https://github.com/pypeclub/OpenPype/pull/1675)
- Settings list race condifiton and mutable dict list conversion [\#1671](https://github.com/pypeclub/OpenPype/pull/1671)
- Mac launch arguments fix [\#1660](https://github.com/pypeclub/OpenPype/pull/1660)
- Fix missing dbm python module [\#1652](https://github.com/pypeclub/OpenPype/pull/1652)
- Transparent branches in view on Mac [\#1648](https://github.com/pypeclub/OpenPype/pull/1648)
- Add asset on task item [\#1646](https://github.com/pypeclub/OpenPype/pull/1646)
- Project manager save and queue [\#1645](https://github.com/pypeclub/OpenPype/pull/1645)
- New project anatomy values [\#1644](https://github.com/pypeclub/OpenPype/pull/1644)
- Farm publishing: check if published items do exist [\#1573](https://github.com/pypeclub/OpenPype/pull/1573)

**Merged pull requests:**

- Bump normalize-url from 4.5.0 to 4.5.1 in /website [\#1686](https://github.com/pypeclub/OpenPype/pull/1686)


## [3.0.0](https://github.com/pypeclub/openpype/tree/3.0.0)

[Full Changelog](https://github.com/pypeclub/openpype/compare/2.18.1...3.0.0)

### Configuration
- Studio Settings GUI: no more json configuration files.
- OpenPype Modules can be turned on and off.
- Easy to add Application versions.
- Per Project Environment and plugin management.
- Robust profile system for creating reviewables and burnins, with filtering based on Application, Task and data family.
- Configurable publish plugins.
- Options to make any validator or extractor, optional or disabled.
- Color Management is now unified under anatomy settings.
- Subset naming and grouping is fully configurable.
- All project attributes can now be set directly in OpenPype settings.
- Studio Setting can be locked to prevent unwanted artist changes.
- You can now add per project and per task type templates for workfile initialization in most hosts.
- Too many other individual configurable option to list in this changelog :)

### Local Settings
- Local Settings GUI where users can change certain option on individual basis.
    - Application executables.
    - Project roots.
    - Project site sync settings.

### Build, Installation and Deployments
- No requirements on artist machine.
- Fully distributed workflow possible.
- Self-contained installation.
- Available on all three major platforms.
- Automatic artist OpenPype updates.
- Studio OpenPype repository for updates distribution.
- Robust Build system.
- Safe studio update versioning with staging and production options.
- MacOS build generates .app and .dmg installer.
- Windows build with installer creation script.

### Misc
- System and diagnostic info tool in the tray.
- Launching application from Launcher indicates activity.
- All project roots are now named. Single root project are now achieved by having a single named root in the project anatomy.
- Every project root is cast into environment variable as well, so it can be used in DCC instead of absolute path (depends on DCC support for env vars).
- Basic support for task types, on top of task names.
- Timer now change automatically when the context is switched inside running application.
- 'Master" versions have been renamed to "Hero".
- Extract Burnins now supports file sequences and color settings.
- Extract Review support overscan cropping, better letterboxes and background colour fill.
- Delivery tool for copying and renaming any published assets in bulk.
- Harmony, Photoshop and After Effects now connect directly with OpenPype tray instead of spawning their own terminal.

### Project Manager GUI
- Create Projects.
- Create Shots and Assets.
- Create Tasks and assign task types.
- Fill required asset attributes.
- Validations for duplicated or unsupported names.
- Archive Assets.
- Move Asset within hierarchy.

### Site Sync (beta)
- Synchronization of published files between workstations and central storage.
- Ability to add arbitrary storage providers to the Site Sync system.
- Default setup includes Disk and Google Drive providers as examples.
- Access to availability information from Loader and Scene Manager.
- Sync queue GUI with filtering, error and status reporting.
- Site sync can be configured on a per-project basis.
- Bulk upload and download from the loader.

### Ftrack
- Actions have customisable roles.
- Settings on all actions are updated live and don't need openpype restart.
- Ftrack module can now be turned off completely.
- It is enough to specify ftrack server name and the URL will be formed correctly. So instead of mystudio.ftrackapp.com, it's possible to use simply: "mystudio".

### Editorial
- Fully OTIO based editorial publishing.
- Completely re-done Hiero publishing to be a lot simpler and faster.
- Consistent conforming from Resolve, Hiero and Standalone Publisher.

### Backend
- OpenPype and Avalon now always share the same database (in 2.x is was possible to split them).
- Major codebase refactoring to allow for better CI, versioning and control of individual integrations.
- OTIO is bundled with build.
- OIIO is bundled with build.
- FFMPEG is bundled with build.
- Rest API and host WebSocket servers have been unified into a single local webserver.
- Maya look assigner has been integrated into the main codebase.
- Publish GUI has been integrated into the main codebase.
- Studio and Project settings overrides are now stored in Mongo.
- Too many other backend fixes and tweaks to list :), you can see full changelog on github for those.
- OpenPype uses Poetry to manage it's virtual environment when running from code.
- all applications can be marked as python 2 or 3 compatible to make the switch a bit easier.


### Pull Requests since 3.0.0-rc.6


**Implemented enhancements:**

- settings: task types enum entity [\#1605](https://github.com/pypeclub/OpenPype/issues/1605)
- Settings: ignore keys in referenced schema [\#1600](https://github.com/pypeclub/OpenPype/issues/1600)
- Maya: support for frame steps and frame lists [\#1585](https://github.com/pypeclub/OpenPype/issues/1585)
- TVPaint: Publish workfile. [\#1548](https://github.com/pypeclub/OpenPype/issues/1548)
- Loader: Current Asset Button [\#1448](https://github.com/pypeclub/OpenPype/issues/1448)
- Hiero: publish with retiming [\#1377](https://github.com/pypeclub/OpenPype/issues/1377)
- Ask user to restart after changing global environments in settings [\#910](https://github.com/pypeclub/OpenPype/issues/910)
- add option to define paht to workfile template [\#895](https://github.com/pypeclub/OpenPype/issues/895)
- Harmony: move server console to system tray [\#676](https://github.com/pypeclub/OpenPype/issues/676)
- Standalone style [\#1630](https://github.com/pypeclub/OpenPype/pull/1630) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Faster hierarchical values push [\#1627](https://github.com/pypeclub/OpenPype/pull/1627) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Launcher tool style [\#1624](https://github.com/pypeclub/OpenPype/pull/1624) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Loader and Library loader enhancements [\#1623](https://github.com/pypeclub/OpenPype/pull/1623) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Tray style [\#1622](https://github.com/pypeclub/OpenPype/pull/1622) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Maya schemas cleanup [\#1610](https://github.com/pypeclub/OpenPype/pull/1610) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Settings: ignore keys in referenced schema [\#1608](https://github.com/pypeclub/OpenPype/pull/1608) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- settings: task types enum entity [\#1606](https://github.com/pypeclub/OpenPype/pull/1606) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Openpype style [\#1604](https://github.com/pypeclub/OpenPype/pull/1604) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- TVPaint: Publish workfile. [\#1597](https://github.com/pypeclub/OpenPype/pull/1597) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Nuke: add option to define path to workfile template [\#1571](https://github.com/pypeclub/OpenPype/pull/1571) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Crop overscan in Extract Review [\#1569](https://github.com/pypeclub/OpenPype/pull/1569) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Unreal and Blender: Material Workflow [\#1562](https://github.com/pypeclub/OpenPype/pull/1562) ([simonebarbieri](https://github.com/simonebarbieri))
- Harmony: move server console to system tray [\#1560](https://github.com/pypeclub/OpenPype/pull/1560) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Ask user to restart after changing global environments in settings [\#1550](https://github.com/pypeclub/OpenPype/pull/1550) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Hiero: publish with retiming [\#1545](https://github.com/pypeclub/OpenPype/pull/1545) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))

**Fixed bugs:**

- Library loader load asset documents on OpenPype start [\#1603](https://github.com/pypeclub/OpenPype/issues/1603)
- Resolve: unable to load the same footage twice [\#1317](https://github.com/pypeclub/OpenPype/issues/1317)
- Resolve: unable to load footage [\#1316](https://github.com/pypeclub/OpenPype/issues/1316)
- Add required Python 2 modules [\#1291](https://github.com/pypeclub/OpenPype/issues/1291)
- GUi scaling with hires displays [\#705](https://github.com/pypeclub/OpenPype/issues/705)
- Maya: non unicode string in publish validation [\#673](https://github.com/pypeclub/OpenPype/issues/673)
- Nuke: Rendered Frame validation is triggered by multiple collections [\#156](https://github.com/pypeclub/OpenPype/issues/156)
- avalon-core debugging failing [\#80](https://github.com/pypeclub/OpenPype/issues/80)
- Only check arnold shading group if arnold is used [\#72](https://github.com/pypeclub/OpenPype/issues/72)
- Sync server Qt layout fix [\#1621](https://github.com/pypeclub/OpenPype/pull/1621) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Console Listener on Python 2 fix [\#1620](https://github.com/pypeclub/OpenPype/pull/1620) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Bug: Initialize blessed term only in console mode [\#1619](https://github.com/pypeclub/OpenPype/pull/1619) ([antirotor](https://github.com/antirotor))
- Settings template skip paths support wrappers [\#1618](https://github.com/pypeclub/OpenPype/pull/1618) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Maya capture 'isolate\_view' fix + minor corrections [\#1617](https://github.com/pypeclub/OpenPype/pull/1617) ([2-REC](https://github.com/2-REC))
- MacOs Fix launch of standalone publisher [\#1616](https://github.com/pypeclub/OpenPype/pull/1616) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- 'Delivery action' report fix + typos [\#1612](https://github.com/pypeclub/OpenPype/pull/1612) ([2-REC](https://github.com/2-REC))
- List append fix in mutable dict settings [\#1599](https://github.com/pypeclub/OpenPype/pull/1599) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Documentation: Maya: fix review [\#1598](https://github.com/pypeclub/OpenPype/pull/1598) ([antirotor](https://github.com/antirotor))
- Bugfix: Set certifi CA bundle for all platforms [\#1596](https://github.com/pypeclub/OpenPype/pull/1596) ([antirotor](https://github.com/antirotor))

**Merged pull requests:**

- Bump dns-packet from 1.3.1 to 1.3.4 in /website [\#1611](https://github.com/pypeclub/OpenPype/pull/1611) ([dependabot[bot]](https://github.com/apps/dependabot))
- Maya: Render workflow fixes [\#1607](https://github.com/pypeclub/OpenPype/pull/1607) ([antirotor](https://github.com/antirotor))
- Maya: support for frame steps and frame lists [\#1586](https://github.com/pypeclub/OpenPype/pull/1586) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- 3.0.0 - curated changelog [\#1284](https://github.com/pypeclub/OpenPype/pull/1284) ([mkolar](https://github.com/mkolar))

## [2.18.1](https://github.com/pypeclub/openpype/tree/2.18.1) (2021-06-03)

[Full Changelog](https://github.com/pypeclub/openpype/compare/2.18.0...2.18.1)

**Enhancements:**

- Faster hierarchical values push [\#1626](https://github.com/pypeclub/OpenPype/pull/1626)
- Feature Delivery in library loader [\#1549](https://github.com/pypeclub/OpenPype/pull/1549)
- Hiero: Initial frame publish support. [\#1172](https://github.com/pypeclub/OpenPype/pull/1172)

**Fixed bugs:**

- Maya capture 'isolate\_view' fix + minor corrections [\#1614](https://github.com/pypeclub/OpenPype/pull/1614)
- 'Delivery action' report fix +typos [\#1613](https://github.com/pypeclub/OpenPype/pull/1613)
- Delivery in LibraryLoader - fixed sequence issue [\#1590](https://github.com/pypeclub/OpenPype/pull/1590)
- FFmpeg filters in quote marks [\#1588](https://github.com/pypeclub/OpenPype/pull/1588)
- Ftrack delete action cause circular error [\#1581](https://github.com/pypeclub/OpenPype/pull/1581)
- Fix Maya playblast. [\#1566](https://github.com/pypeclub/OpenPype/pull/1566)
- More failsafes prevent errored runs. [\#1554](https://github.com/pypeclub/OpenPype/pull/1554)
- Celaction publishing [\#1539](https://github.com/pypeclub/OpenPype/pull/1539)
- celaction: app not starting [\#1533](https://github.com/pypeclub/OpenPype/pull/1533)

**Merged pull requests:**

- Maya: Render workflow fixes - 2.0 backport [\#1609](https://github.com/pypeclub/OpenPype/pull/1609)
- Maya Hardware support [\#1553](https://github.com/pypeclub/OpenPype/pull/1553)


## [CI/3.0.0-rc.6](https://github.com/pypeclub/openpype/tree/CI/3.0.0-rc.6) (2021-05-27)

[Full Changelog](https://github.com/pypeclub/openpype/compare/CI/3.0.0-rc.5...CI/3.0.0-rc.6)

**Implemented enhancements:**

- Hiero: publish color and transformation soft-effects [\#1376](https://github.com/pypeclub/OpenPype/issues/1376)
- Get rid of `AVALON\_HIERARCHY` and `hiearchy` key on asset [\#432](https://github.com/pypeclub/OpenPype/issues/432)
- Sync to avalon do not store hierarchy key [\#1582](https://github.com/pypeclub/OpenPype/pull/1582) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Tools: launcher scripts for project manager [\#1557](https://github.com/pypeclub/OpenPype/pull/1557) ([antirotor](https://github.com/antirotor))
- Simple tvpaint publish [\#1555](https://github.com/pypeclub/OpenPype/pull/1555) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Feature Delivery in library loader [\#1546](https://github.com/pypeclub/OpenPype/pull/1546) ([kalisp](https://github.com/kalisp))
- Documentation: Dev and system build documentation [\#1543](https://github.com/pypeclub/OpenPype/pull/1543) ([antirotor](https://github.com/antirotor))
- Color entity [\#1542](https://github.com/pypeclub/OpenPype/pull/1542) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Extract review bg color [\#1534](https://github.com/pypeclub/OpenPype/pull/1534) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- TVPaint loader settings [\#1530](https://github.com/pypeclub/OpenPype/pull/1530) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Blender can initialize differente user script paths [\#1528](https://github.com/pypeclub/OpenPype/pull/1528) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Blender and Unreal: Improved Animation Workflow [\#1514](https://github.com/pypeclub/OpenPype/pull/1514) ([simonebarbieri](https://github.com/simonebarbieri))
- Hiero: publish color and transformation soft-effects [\#1511](https://github.com/pypeclub/OpenPype/pull/1511) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))

**Fixed bugs:**

- OpenPype specific version issues [\#1583](https://github.com/pypeclub/OpenPype/issues/1583)
- Ftrack login server can't work without stderr [\#1576](https://github.com/pypeclub/OpenPype/issues/1576)
- Mac application launch [\#1575](https://github.com/pypeclub/OpenPype/issues/1575)
- Settings are not propagated to Nuke write nodes [\#1538](https://github.com/pypeclub/OpenPype/issues/1538)
- Subset names settings not applied for publishing [\#1537](https://github.com/pypeclub/OpenPype/issues/1537)
- Nuke: callback at start not setting colorspace [\#1412](https://github.com/pypeclub/OpenPype/issues/1412)
- Pype 3: Missing icon for Settings [\#1272](https://github.com/pypeclub/OpenPype/issues/1272)
- Blender: cannot initialize Avalon if BLENDER\_USER\_SCRIPTS is already used [\#1050](https://github.com/pypeclub/OpenPype/issues/1050)
- Ftrack delete action cause circular error [\#206](https://github.com/pypeclub/OpenPype/issues/206)
- Build: stop cleaning of pyc files in build directory [\#1592](https://github.com/pypeclub/OpenPype/pull/1592) ([antirotor](https://github.com/antirotor))
- Ftrack login server can't work without stderr [\#1591](https://github.com/pypeclub/OpenPype/pull/1591) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- FFmpeg filters in quote marks [\#1589](https://github.com/pypeclub/OpenPype/pull/1589) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- OpenPype specific version issues [\#1584](https://github.com/pypeclub/OpenPype/pull/1584) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Mac application launch [\#1580](https://github.com/pypeclub/OpenPype/pull/1580) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Ftrack delete action cause circular error [\#1579](https://github.com/pypeclub/OpenPype/pull/1579) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Hiero: publishing issues  [\#1578](https://github.com/pypeclub/OpenPype/pull/1578) ([jezscha](https://github.com/jezscha))
- Nuke: callback at start not setting colorspace [\#1561](https://github.com/pypeclub/OpenPype/pull/1561) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Bugfix  PS subset and quick review [\#1541](https://github.com/pypeclub/OpenPype/pull/1541) ([kalisp](https://github.com/kalisp))
- Settings are not propagated to Nuke write nodes [\#1540](https://github.com/pypeclub/OpenPype/pull/1540) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- OpenPype: Powershell scripts polishing [\#1536](https://github.com/pypeclub/OpenPype/pull/1536) ([antirotor](https://github.com/antirotor))
- Host name collecting fix [\#1535](https://github.com/pypeclub/OpenPype/pull/1535) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Handle duplicated task names in project manager [\#1531](https://github.com/pypeclub/OpenPype/pull/1531) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Validate is file attribute in settings schema [\#1529](https://github.com/pypeclub/OpenPype/pull/1529) ([iLLiCiTiT](https://github.com/iLLiCiTiT))

**Merged pull requests:**

- Bump postcss from 8.2.8 to 8.3.0 in /website [\#1593](https://github.com/pypeclub/OpenPype/pull/1593) ([dependabot[bot]](https://github.com/apps/dependabot))
- User installation documentation [\#1532](https://github.com/pypeclub/OpenPype/pull/1532) ([64qam](https://github.com/64qam))

## [CI/3.0.0-rc.5](https://github.com/pypeclub/openpype/tree/CI/3.0.0-rc.5) (2021-05-19)

[Full Changelog](https://github.com/pypeclub/openpype/compare/2.18.0...CI/3.0.0-rc.5)

**Implemented enhancements:**

- OpenPype: Build - Add progress bars [\#1524](https://github.com/pypeclub/OpenPype/pull/1524) ([antirotor](https://github.com/antirotor))
- Default environments per host imlementation [\#1522](https://github.com/pypeclub/OpenPype/pull/1522) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- OpenPype: use `semver` module for version resolution [\#1513](https://github.com/pypeclub/OpenPype/pull/1513) ([antirotor](https://github.com/antirotor))
- Feature Aftereffects setting cleanup documentation [\#1510](https://github.com/pypeclub/OpenPype/pull/1510) ([kalisp](https://github.com/kalisp))
- Feature Sync server settings enhancement [\#1501](https://github.com/pypeclub/OpenPype/pull/1501) ([kalisp](https://github.com/kalisp))
- Project manager [\#1396](https://github.com/pypeclub/OpenPype/pull/1396) ([iLLiCiTiT](https://github.com/iLLiCiTiT))

**Fixed bugs:**

- Unified schema definition [\#874](https://github.com/pypeclub/OpenPype/issues/874)
- Maya: fix look assignment [\#1526](https://github.com/pypeclub/OpenPype/pull/1526) ([antirotor](https://github.com/antirotor))
- Bugfix Sync server local site issues [\#1523](https://github.com/pypeclub/OpenPype/pull/1523) ([kalisp](https://github.com/kalisp))
- Store as list dictionary check initial value with right type [\#1520](https://github.com/pypeclub/OpenPype/pull/1520) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Maya: wrong collection of playblasted frames [\#1515](https://github.com/pypeclub/OpenPype/pull/1515) ([mkolar](https://github.com/mkolar))
- Convert pyblish logs to string at the moment of logging [\#1512](https://github.com/pypeclub/OpenPype/pull/1512) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- 3.0 | nuke: fixing start\_at with option gui [\#1509](https://github.com/pypeclub/OpenPype/pull/1509) ([jezscha](https://github.com/jezscha))
- Tests: fix pype -\> openpype to make tests work again [\#1508](https://github.com/pypeclub/OpenPype/pull/1508) ([antirotor](https://github.com/antirotor))

**Merged pull requests:**

- OpenPype: disable submodule update with `--no-submodule-update` [\#1525](https://github.com/pypeclub/OpenPype/pull/1525) ([antirotor](https://github.com/antirotor))
- Ftrack without autosync in Pype 3 [\#1519](https://github.com/pypeclub/OpenPype/pull/1519) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Feature Harmony setting cleanup documentation [\#1506](https://github.com/pypeclub/OpenPype/pull/1506) ([kalisp](https://github.com/kalisp))
- Sync Server beginning of documentation [\#1471](https://github.com/pypeclub/OpenPype/pull/1471) ([kalisp](https://github.com/kalisp))
- Blender: publish layout json [\#1348](https://github.com/pypeclub/OpenPype/pull/1348) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))

## [2.18.0](https://github.com/pypeclub/openpype/tree/2.18.0) (2021-05-18)

[Full Changelog](https://github.com/pypeclub/openpype/compare/CI/3.0.0-rc.4...2.18.0)

**Implemented enhancements:**

- Default environments per host imlementation [\#1405](https://github.com/pypeclub/OpenPype/issues/1405)
- Blender: publish layout json [\#1346](https://github.com/pypeclub/OpenPype/issues/1346)
- Ftrack without autosync in Pype 3 [\#1128](https://github.com/pypeclub/OpenPype/issues/1128)
- Launcher: started action indicator [\#1102](https://github.com/pypeclub/OpenPype/issues/1102)
- Launch arguments of applications [\#1094](https://github.com/pypeclub/OpenPype/issues/1094)
- Publish: instance info [\#724](https://github.com/pypeclub/OpenPype/issues/724)
- Review: ability to control review length [\#482](https://github.com/pypeclub/OpenPype/issues/482)
- Colorized recognition of creator result [\#394](https://github.com/pypeclub/OpenPype/issues/394)
- event assign user to started task [\#49](https://github.com/pypeclub/OpenPype/issues/49)
- rebuild containers from reference in maya [\#55](https://github.com/pypeclub/OpenPype/issues/55)
- nuke Load metadata [\#66](https://github.com/pypeclub/OpenPype/issues/66)
- Maya: Safer handling of expected render output names [\#1496](https://github.com/pypeclub/OpenPype/pull/1496) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- TVPaint: Increment workfile version on successfull publish. [\#1489](https://github.com/pypeclub/OpenPype/pull/1489) ([tokejepsen](https://github.com/tokejepsen))
- Use SubsetLoader and multiple contexts for delete\_old\_versions [\#1484](https://github.com/pypeclub/OpenPype/pull/1484) ([tokejepsen](https://github.com/tokejepsen))
- Maya: Use of multiple deadline servers [\#1483](https://github.com/pypeclub/OpenPype/pull/1483) ([antirotor](https://github.com/antirotor))

**Fixed bugs:**

- Igniter version resolution doesn't consider it's own version [\#1505](https://github.com/pypeclub/OpenPype/issues/1505)
- Maya: Safer handling of expected render output names [\#1159](https://github.com/pypeclub/OpenPype/issues/1159)
- Harmony: Invalid render output from non-conventionally named instance [\#871](https://github.com/pypeclub/OpenPype/issues/871)
- Existing subsets hints in creator [\#1503](https://github.com/pypeclub/OpenPype/pull/1503) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- nuke: space in node name breaking process [\#1494](https://github.com/pypeclub/OpenPype/pull/1494) ([jezscha](https://github.com/jezscha))
-  Maya: wrong collection of playblasted frames [\#1517](https://github.com/pypeclub/OpenPype/pull/1517) ([mkolar](https://github.com/mkolar))
- Existing subsets hints in creator [\#1502](https://github.com/pypeclub/OpenPype/pull/1502) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Use instance frame start instead of timeline. [\#1486](https://github.com/pypeclub/OpenPype/pull/1486) ([tokejepsen](https://github.com/tokejepsen))
- Maya: Redshift - set proper start frame on proxy [\#1480](https://github.com/pypeclub/OpenPype/pull/1480) ([antirotor](https://github.com/antirotor))

**Closed issues:**

- Nuke: wrong "star at" value on render load [\#1352](https://github.com/pypeclub/OpenPype/issues/1352)
- DV Resolve - loading/updating - image video [\#915](https://github.com/pypeclub/OpenPype/issues/915)

**Merged pull requests:**

- nuke: fixing start\_at with option gui [\#1507](https://github.com/pypeclub/OpenPype/pull/1507) ([jezscha](https://github.com/jezscha))

## [CI/3.0.0-rc.4](https://github.com/pypeclub/openpype/tree/CI/3.0.0-rc.4) (2021-05-12)

[Full Changelog](https://github.com/pypeclub/openpype/compare/2.17.3...CI/3.0.0-rc.4)

**Implemented enhancements:**

- Resolve: documentation [\#1490](https://github.com/pypeclub/OpenPype/issues/1490)
- Hiero: audio to review [\#1378](https://github.com/pypeclub/OpenPype/issues/1378)
- nks color clips after publish [\#44](https://github.com/pypeclub/OpenPype/issues/44)
- Store data from modifiable dict as list [\#1504](https://github.com/pypeclub/OpenPype/pull/1504) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Use SubsetLoader and multiple contexts for delete\_old\_versions [\#1497](https://github.com/pypeclub/OpenPype/pull/1497) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Hiero: publish audio and add to review [\#1493](https://github.com/pypeclub/OpenPype/pull/1493) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Resolve: documentation [\#1491](https://github.com/pypeclub/OpenPype/pull/1491) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Change integratenew template profiles setting [\#1487](https://github.com/pypeclub/OpenPype/pull/1487) ([kalisp](https://github.com/kalisp))
- Settings tool cleanup [\#1477](https://github.com/pypeclub/OpenPype/pull/1477) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Sorted Applications and Tools in Custom attribute [\#1476](https://github.com/pypeclub/OpenPype/pull/1476) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- PS - group all published instances [\#1416](https://github.com/pypeclub/OpenPype/pull/1416) ([kalisp](https://github.com/kalisp))
- OpenPype: Support for Docker [\#1289](https://github.com/pypeclub/OpenPype/pull/1289) ([antirotor](https://github.com/antirotor))

**Fixed bugs:**

- Harmony: palettes publishing [\#1439](https://github.com/pypeclub/OpenPype/issues/1439)
- Photoshop: validation for already created images [\#1435](https://github.com/pypeclub/OpenPype/issues/1435)
- Nuke Extracts Thumbnail from frame out of shot range [\#963](https://github.com/pypeclub/OpenPype/issues/963)
- Instance in same Context repairing [\#390](https://github.com/pypeclub/OpenPype/issues/390)
- User Inactivity - Start timers sets wrong time [\#91](https://github.com/pypeclub/OpenPype/issues/91)
- Use instance frame start instead of timeline [\#1499](https://github.com/pypeclub/OpenPype/pull/1499) ([mkolar](https://github.com/mkolar))
- Various smaller fixes [\#1498](https://github.com/pypeclub/OpenPype/pull/1498) ([mkolar](https://github.com/mkolar))
- nuke: space in node name breaking process [\#1495](https://github.com/pypeclub/OpenPype/pull/1495) ([jezscha](https://github.com/jezscha))
- Codec determination in extract burnin [\#1492](https://github.com/pypeclub/OpenPype/pull/1492) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Undefined constant in subprocess module [\#1485](https://github.com/pypeclub/OpenPype/pull/1485) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- List entity catch add/remove item changes properly [\#1482](https://github.com/pypeclub/OpenPype/pull/1482) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Resolve: additional fixes of publishing workflow [\#1481](https://github.com/pypeclub/OpenPype/pull/1481) ([jezscha](https://github.com/jezscha))
- Photoshop: validation for already created images [\#1436](https://github.com/pypeclub/OpenPype/pull/1436) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))

**Merged pull requests:**

- Maya: Support for looks on VRay Proxies [\#1443](https://github.com/pypeclub/OpenPype/pull/1443) ([antirotor](https://github.com/antirotor))

## [2.17.3](https://github.com/pypeclub/openpype/tree/2.17.3) (2021-05-06)

[Full Changelog](https://github.com/pypeclub/openpype/compare/CI/3.0.0-rc.3...2.17.3)

**Fixed bugs:**

- Nuke: workfile version synced to db version always  [\#1479](https://github.com/pypeclub/OpenPype/pull/1479) ([jezscha](https://github.com/jezscha))

## [CI/3.0.0-rc.3](https://github.com/pypeclub/openpype/tree/CI/3.0.0-rc.3) (2021-05-05)

[Full Changelog](https://github.com/pypeclub/openpype/compare/CI/3.0.0-rc.2...CI/3.0.0-rc.3)

**Implemented enhancements:**

- Path entity with placeholder [\#1473](https://github.com/pypeclub/OpenPype/pull/1473) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Burnin custom font filepath [\#1472](https://github.com/pypeclub/OpenPype/pull/1472) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Poetry: Move to OpenPype [\#1449](https://github.com/pypeclub/OpenPype/pull/1449) ([antirotor](https://github.com/antirotor))

**Fixed bugs:**

- Mac SSL path needs to be relative to pype\_root [\#1469](https://github.com/pypeclub/OpenPype/issues/1469)
- Resolve: fix loading clips to timeline [\#1421](https://github.com/pypeclub/OpenPype/issues/1421)
- Wrong handling of slashes when loading on mac [\#1411](https://github.com/pypeclub/OpenPype/issues/1411)
- Nuke openpype3 [\#1342](https://github.com/pypeclub/OpenPype/issues/1342)
- Houdini launcher [\#1171](https://github.com/pypeclub/OpenPype/issues/1171)
- Fix SyncServer get\_enabled\_projects should handle global state [\#1475](https://github.com/pypeclub/OpenPype/pull/1475) ([kalisp](https://github.com/kalisp))
- Igniter buttons enable/disable fix [\#1474](https://github.com/pypeclub/OpenPype/pull/1474) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Mac SSL path needs to be relative to pype\_root [\#1470](https://github.com/pypeclub/OpenPype/pull/1470) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Resolve: 17 compatibility issues and load image sequences [\#1422](https://github.com/pypeclub/OpenPype/pull/1422) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))

## [CI/3.0.0-rc.2](https://github.com/pypeclub/openpype/tree/CI/3.0.0-rc.2) (2021-05-04)

[Full Changelog](https://github.com/pypeclub/openpype/compare/2.17.2...CI/3.0.0-rc.2)

**Implemented enhancements:**

- Extract burnins with sequences [\#1467](https://github.com/pypeclub/OpenPype/pull/1467) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Extract burnins with color setting [\#1466](https://github.com/pypeclub/OpenPype/pull/1466) ([iLLiCiTiT](https://github.com/iLLiCiTiT))

**Fixed bugs:**

- Fix groups check in Python 2 [\#1468](https://github.com/pypeclub/OpenPype/pull/1468) ([iLLiCiTiT](https://github.com/iLLiCiTiT))

## [2.17.2](https://github.com/pypeclub/openpype/tree/2.17.2) (2021-05-04)

[Full Changelog](https://github.com/pypeclub/openpype/compare/CI/3.0.0-rc.1...2.17.2)

**Implemented enhancements:**

- Forward/Backward compatible apps and tools with OpenPype 3 [\#1463](https://github.com/pypeclub/OpenPype/pull/1463) ([iLLiCiTiT](https://github.com/iLLiCiTiT))

## [CI/3.0.0-rc.1](https://github.com/pypeclub/openpype/tree/CI/3.0.0-rc.1) (2021-05-04)

[Full Changelog](https://github.com/pypeclub/openpype/compare/2.17.1...CI/3.0.0-rc.1)

**Implemented enhancements:**

- Only show studio settings to admins [\#1406](https://github.com/pypeclub/OpenPype/issues/1406)
- Ftrack specific settings save warning messages [\#1458](https://github.com/pypeclub/OpenPype/pull/1458) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Faster settings actions [\#1446](https://github.com/pypeclub/OpenPype/pull/1446) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Feature/sync server priority [\#1444](https://github.com/pypeclub/OpenPype/pull/1444) ([kalisp](https://github.com/kalisp))
- Faster settings UI loading [\#1442](https://github.com/pypeclub/OpenPype/pull/1442) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Igniter re-write [\#1441](https://github.com/pypeclub/OpenPype/pull/1441) ([mkolar](https://github.com/mkolar))
- Wrap openpype build into installers [\#1419](https://github.com/pypeclub/OpenPype/pull/1419) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Extract review first documentation [\#1404](https://github.com/pypeclub/OpenPype/pull/1404) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Blender PySide2 install guide [\#1403](https://github.com/pypeclub/OpenPype/pull/1403) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Nuke: deadline submission with gpu [\#1394](https://github.com/pypeclub/OpenPype/pull/1394) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Igniter: Reverse item filter for OpenPype version [\#1349](https://github.com/pypeclub/OpenPype/pull/1349) ([antirotor](https://github.com/antirotor))

**Fixed bugs:**

- OpenPype Mongo URL definition [\#1450](https://github.com/pypeclub/OpenPype/issues/1450)
- Various typos and smaller fixes [\#1464](https://github.com/pypeclub/OpenPype/pull/1464) ([mkolar](https://github.com/mkolar))
- Validation of dynamic items in settings [\#1462](https://github.com/pypeclub/OpenPype/pull/1462) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- List can handle new items correctly [\#1459](https://github.com/pypeclub/OpenPype/pull/1459) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Settings actions process fix [\#1457](https://github.com/pypeclub/OpenPype/pull/1457) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Add to overrides actions fix [\#1456](https://github.com/pypeclub/OpenPype/pull/1456) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- OpenPype Mongo URL definition [\#1455](https://github.com/pypeclub/OpenPype/pull/1455) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Global settings save/load out of system settings [\#1447](https://github.com/pypeclub/OpenPype/pull/1447) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Keep metadata on remove overrides [\#1445](https://github.com/pypeclub/OpenPype/pull/1445) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Nuke: fixing undo for loaded mov and sequence [\#1432](https://github.com/pypeclub/OpenPype/pull/1432) ([jezscha](https://github.com/jezscha))
- ExtractReview skip empty strings from settings [\#1431](https://github.com/pypeclub/OpenPype/pull/1431) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Bugfix Sync server tweaks [\#1430](https://github.com/pypeclub/OpenPype/pull/1430) ([kalisp](https://github.com/kalisp))
- Hiero: missing thumbnail in review [\#1429](https://github.com/pypeclub/OpenPype/pull/1429) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Bugfix Maya in deadline for OpenPype [\#1428](https://github.com/pypeclub/OpenPype/pull/1428) ([kalisp](https://github.com/kalisp))
- AE - validation for duration was 1 frame shorter [\#1427](https://github.com/pypeclub/OpenPype/pull/1427) ([kalisp](https://github.com/kalisp))
- Houdini menu filename [\#1418](https://github.com/pypeclub/OpenPype/pull/1418) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Fix Avalon plugins attribute overrides [\#1413](https://github.com/pypeclub/OpenPype/pull/1413) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Nuke: submit to Deadline fails [\#1409](https://github.com/pypeclub/OpenPype/pull/1409) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- Validate MongoDB Url on start [\#1407](https://github.com/pypeclub/OpenPype/pull/1407) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Nuke: fix set colorspace with new settings [\#1386](https://github.com/pypeclub/OpenPype/pull/1386) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- MacOs build and install issues [\#1380](https://github.com/pypeclub/OpenPype/pull/1380) ([mkolar](https://github.com/mkolar))

**Closed issues:**

- test [\#1452](https://github.com/pypeclub/OpenPype/issues/1452)

**Merged pull requests:**

- TVPaint frame range definition [\#1425](https://github.com/pypeclub/OpenPype/pull/1425) ([iLLiCiTiT](https://github.com/iLLiCiTiT))
- Only show studio settings to admins [\#1420](https://github.com/pypeclub/OpenPype/pull/1420) ([create-issue-branch[bot]](https://github.com/apps/create-issue-branch))
- TVPaint documentation [\#1305](https://github.com/pypeclub/OpenPype/pull/1305) ([64qam](https://github.com/64qam))

## [2.17.1](https://github.com/pypeclub/openpype/tree/2.17.1) (2021-04-30)

[Full Changelog](https://github.com/pypeclub/openpype/compare/2.17.0...2.17.1)

**Enhancements:**

- Nuke: deadline submission with gpu [\#1414](https://github.com/pypeclub/OpenPype/pull/1414)
- TVPaint frame range definition [\#1424](https://github.com/pypeclub/OpenPype/pull/1424)
- PS - group all published instances [\#1415](https://github.com/pypeclub/OpenPype/pull/1415)
- Add task name to context pop up. [\#1383](https://github.com/pypeclub/OpenPype/pull/1383)
- Enhance review letterbox feature. [\#1371](https://github.com/pypeclub/OpenPype/pull/1371)

**Fixed bugs:**

- Houdini menu filename [\#1417](https://github.com/pypeclub/OpenPype/pull/1417)
- AE - validation for duration was 1 frame shorter [\#1426](https://github.com/pypeclub/OpenPype/pull/1426)

**Merged pull requests:**

- Maya: Vray - problem getting all file nodes for look publishing [\#1399](https://github.com/pypeclub/OpenPype/pull/1399)
- Maya: Support for Redshift proxies [\#1360](https://github.com/pypeclub/OpenPype/pull/1360)

## [2.17.0](https://github.com/pypeclub/openpype/tree/2.17.0) (2021-04-20)

[Full Changelog](https://github.com/pypeclub/openpype/compare/CI/3.0.0-beta.2...2.17.0)

**Enhancements:**

- Forward compatible ftrack group [\#1243](https://github.com/pypeclub/OpenPype/pull/1243)
- Settings in mongo as dict [\#1221](https://github.com/pypeclub/OpenPype/pull/1221)
- Maya: Make tx option configurable with presets [\#1328](https://github.com/pypeclub/OpenPype/pull/1328)
- TVPaint asset name validation [\#1302](https://github.com/pypeclub/OpenPype/pull/1302)
- TV Paint: Set initial project settings. [\#1299](https://github.com/pypeclub/OpenPype/pull/1299)
- TV Paint: Validate mark in and out. [\#1298](https://github.com/pypeclub/OpenPype/pull/1298)
- Validate project settings [\#1297](https://github.com/pypeclub/OpenPype/pull/1297)
- After Effects: added SubsetManager [\#1234](https://github.com/pypeclub/OpenPype/pull/1234)
- Show error message in pyblish UI [\#1206](https://github.com/pypeclub/OpenPype/pull/1206)

**Fixed bugs:**

- Hiero: fixing source frame from correct object [\#1362](https://github.com/pypeclub/OpenPype/pull/1362)
- Nuke: fix colourspace, prerenders and nuke panes opening [\#1308](https://github.com/pypeclub/OpenPype/pull/1308)
- AE remove orphaned instance from workfile - fix self.stub [\#1282](https://github.com/pypeclub/OpenPype/pull/1282)
- Nuke: deadline submission with search replaced env values from preset [\#1194](https://github.com/pypeclub/OpenPype/pull/1194)
- Ftrack custom attributes in bulks [\#1312](https://github.com/pypeclub/OpenPype/pull/1312)
- Ftrack optional pypclub role [\#1303](https://github.com/pypeclub/OpenPype/pull/1303)
- After Effects: remove orphaned instances [\#1275](https://github.com/pypeclub/OpenPype/pull/1275)
- Avalon schema names [\#1242](https://github.com/pypeclub/OpenPype/pull/1242)
- Handle duplication of Task name [\#1226](https://github.com/pypeclub/OpenPype/pull/1226)
- Modified path of plugin loads for Harmony and TVPaint [\#1217](https://github.com/pypeclub/OpenPype/pull/1217)
- Regex checks in profiles filtering [\#1214](https://github.com/pypeclub/OpenPype/pull/1214)
- Bulk mov strict task [\#1204](https://github.com/pypeclub/OpenPype/pull/1204)
- Update custom ftrack session attributes [\#1202](https://github.com/pypeclub/OpenPype/pull/1202)
- Nuke: write node colorspace ignore `default\(\)` label [\#1199](https://github.com/pypeclub/OpenPype/pull/1199)
- Nuke: reverse search to make it more versatile [\#1178](https://github.com/pypeclub/OpenPype/pull/1178)



## [2.16.0](https://github.com/pypeclub/pype/tree/2.16.0) (2021-03-22)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.15.3...2.16.0)

**Enhancements:**

- Nuke: deadline submit limit group filter [\#1167](https://github.com/pypeclub/pype/pull/1167)
- Maya: support for Deadline Group and Limit Groups - backport 2.x [\#1156](https://github.com/pypeclub/pype/pull/1156)
- Maya: fixes for Redshift support [\#1152](https://github.com/pypeclub/pype/pull/1152)
- Nuke: adding preset for a Read node name to all img and mov Loaders [\#1146](https://github.com/pypeclub/pype/pull/1146)
- nuke deadline submit with environ var from presets overrides [\#1142](https://github.com/pypeclub/pype/pull/1142)
- Change timers after task change [\#1138](https://github.com/pypeclub/pype/pull/1138)
- Nuke: shortcuts for Pype menu [\#1127](https://github.com/pypeclub/pype/pull/1127)
- Nuke: workfile template [\#1124](https://github.com/pypeclub/pype/pull/1124)
- Sites local settings by site name [\#1117](https://github.com/pypeclub/pype/pull/1117)
- Reset loader's asset selection on context change [\#1106](https://github.com/pypeclub/pype/pull/1106)
- Bulk mov render publishing [\#1101](https://github.com/pypeclub/pype/pull/1101)
- Photoshop: mark publishable instances [\#1093](https://github.com/pypeclub/pype/pull/1093)
- Added ability to define BG color for extract review [\#1088](https://github.com/pypeclub/pype/pull/1088)
- TVPaint extractor enhancement [\#1080](https://github.com/pypeclub/pype/pull/1080)
- Photoshop: added support for .psb in workfiles [\#1078](https://github.com/pypeclub/pype/pull/1078)
- Optionally add task to subset name [\#1072](https://github.com/pypeclub/pype/pull/1072)
- Only extend clip range when collecting. [\#1008](https://github.com/pypeclub/pype/pull/1008)
- Collect audio for farm reviews. [\#1073](https://github.com/pypeclub/pype/pull/1073)


**Fixed bugs:**

- Fix path spaces in jpeg extractor [\#1174](https://github.com/pypeclub/pype/pull/1174)
- Maya: Bugfix: superclass for CreateCameraRig [\#1166](https://github.com/pypeclub/pype/pull/1166)
- Maya: Submit to Deadline - fix typo in condition [\#1163](https://github.com/pypeclub/pype/pull/1163)
- Avoid dot in repre extension [\#1125](https://github.com/pypeclub/pype/pull/1125)
- Fix versions variable usage in standalone publisher [\#1090](https://github.com/pypeclub/pype/pull/1090)
- Collect instance data fix subset query [\#1082](https://github.com/pypeclub/pype/pull/1082)
- Fix getting the camera name. [\#1067](https://github.com/pypeclub/pype/pull/1067)
- Nuke: Ensure "NUKE\_TEMP\_DIR" is not part of the Deadline job environment. [\#1064](https://github.com/pypeclub/pype/pull/1064)

## [2.15.3](https://github.com/pypeclub/pype/tree/2.15.3) (2021-02-26)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.15.2...2.15.3)

**Enhancements:**

- Maya: speedup renderable camera collection [\#1053](https://github.com/pypeclub/pype/pull/1053)
- Harmony - add regex search to filter allowed task names for collectin… [\#1047](https://github.com/pypeclub/pype/pull/1047)

**Fixed bugs:**

- Ftrack integrate hierarchy fix [\#1085](https://github.com/pypeclub/pype/pull/1085)
- Explicit subset filter in anatomy instance data [\#1059](https://github.com/pypeclub/pype/pull/1059)
- TVPaint frame offset [\#1057](https://github.com/pypeclub/pype/pull/1057)
- Auto fix unicode strings [\#1046](https://github.com/pypeclub/pype/pull/1046)

## [2.15.2](https://github.com/pypeclub/pype/tree/2.15.2) (2021-02-19)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.15.1...2.15.2)

**Enhancements:**

- Maya: Vray scene publishing [\#1013](https://github.com/pypeclub/pype/pull/1013)

**Fixed bugs:**

- Fix entity move under project [\#1040](https://github.com/pypeclub/pype/pull/1040)
- smaller nuke fixes from production [\#1036](https://github.com/pypeclub/pype/pull/1036)
- TVPaint thumbnail extract fix [\#1031](https://github.com/pypeclub/pype/pull/1031)

## [2.15.1](https://github.com/pypeclub/pype/tree/2.15.1) (2021-02-12)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.15.0...2.15.1)

**Enhancements:**

- Delete version as loader action [\#1011](https://github.com/pypeclub/pype/pull/1011)
- Delete old versions [\#445](https://github.com/pypeclub/pype/pull/445)

**Fixed bugs:**

- PS - remove obsolete functions from pywin32 [\#1006](https://github.com/pypeclub/pype/pull/1006)
- Clone description of review session objects. [\#922](https://github.com/pypeclub/pype/pull/922)

## [2.15.0](https://github.com/pypeclub/pype/tree/2.15.0) (2021-02-09)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.14.6...2.15.0)

**Enhancements:**

- Resolve - loading and updating clips [\#932](https://github.com/pypeclub/pype/pull/932)
- Release/2.15.0 [\#926](https://github.com/pypeclub/pype/pull/926)
- Photoshop: add option for template.psd and prelaunch hook  [\#894](https://github.com/pypeclub/pype/pull/894)
- Nuke: deadline presets [\#993](https://github.com/pypeclub/pype/pull/993)
- Maya: Alembic only set attributes that exists. [\#986](https://github.com/pypeclub/pype/pull/986)
- Harmony: render local and handle fixes [\#981](https://github.com/pypeclub/pype/pull/981)
- PSD Bulk export of ANIM group [\#965](https://github.com/pypeclub/pype/pull/965)
- AE - added prelaunch hook for opening last or workfile from template [\#944](https://github.com/pypeclub/pype/pull/944)
- PS - safer handling of loading of workfile [\#941](https://github.com/pypeclub/pype/pull/941)
- Maya: Handling Arnold referenced AOVs [\#938](https://github.com/pypeclub/pype/pull/938)
- TVPaint: switch layer IDs for layer names during identification [\#903](https://github.com/pypeclub/pype/pull/903)
- TVPaint audio/sound loader [\#893](https://github.com/pypeclub/pype/pull/893)
- Clone review session with children. [\#891](https://github.com/pypeclub/pype/pull/891)
- Simple compositing data packager for freelancers [\#884](https://github.com/pypeclub/pype/pull/884)
- Harmony deadline submission [\#881](https://github.com/pypeclub/pype/pull/881)
- Maya: Optionally hide image planes from reviews. [\#840](https://github.com/pypeclub/pype/pull/840)
- Maya: handle referenced AOVs for Vray [\#824](https://github.com/pypeclub/pype/pull/824)
- DWAA/DWAB support on windows [\#795](https://github.com/pypeclub/pype/pull/795)
- Unreal: animation, layout and setdress updates [\#695](https://github.com/pypeclub/pype/pull/695)

**Fixed bugs:**

- Maya: Looks - disable hardlinks [\#995](https://github.com/pypeclub/pype/pull/995)
- Fix Ftrack custom attribute update [\#982](https://github.com/pypeclub/pype/pull/982)
- Prores ks in burnin script [\#960](https://github.com/pypeclub/pype/pull/960)
- terminal.py crash on import [\#839](https://github.com/pypeclub/pype/pull/839)
- Extract review handle bizarre pixel aspect ratio [\#990](https://github.com/pypeclub/pype/pull/990)
- Nuke: add nuke related env var to sumbission  [\#988](https://github.com/pypeclub/pype/pull/988)
- Nuke: missing preset's variable  [\#984](https://github.com/pypeclub/pype/pull/984)
- Get creator by name fix [\#979](https://github.com/pypeclub/pype/pull/979)
- Fix update of project's tasks on Ftrack sync [\#972](https://github.com/pypeclub/pype/pull/972)
- nuke: wrong frame offset in mov loader  [\#971](https://github.com/pypeclub/pype/pull/971)
- Create project structure action fix multiroot [\#967](https://github.com/pypeclub/pype/pull/967)
- PS: remove pywin installation from hook [\#964](https://github.com/pypeclub/pype/pull/964)
- Prores ks in burnin script [\#959](https://github.com/pypeclub/pype/pull/959)
- Subset family is now stored in subset document [\#956](https://github.com/pypeclub/pype/pull/956)
- DJV new version arguments [\#954](https://github.com/pypeclub/pype/pull/954)
- TV Paint: Fix single frame Sequence [\#953](https://github.com/pypeclub/pype/pull/953)
- nuke: missing `file` knob update  [\#933](https://github.com/pypeclub/pype/pull/933)
- Photoshop: Create from single layer was failing [\#920](https://github.com/pypeclub/pype/pull/920)
- Nuke: baking mov with correct colorspace inherited from write  [\#909](https://github.com/pypeclub/pype/pull/909)
- Launcher fix actions discover [\#896](https://github.com/pypeclub/pype/pull/896)
- Get the correct file path for the updated mov. [\#889](https://github.com/pypeclub/pype/pull/889)
- Maya: Deadline submitter - shared data access violation [\#831](https://github.com/pypeclub/pype/pull/831)
- Maya: Take into account vray master AOV switch [\#822](https://github.com/pypeclub/pype/pull/822)

**Merged pull requests:**

- Refactor blender to 3.0 format [\#934](https://github.com/pypeclub/pype/pull/934)

## [2.14.6](https://github.com/pypeclub/pype/tree/2.14.6) (2021-01-15)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.14.5...2.14.6)

**Fixed bugs:**

- Nuke: improving of hashing path  [\#885](https://github.com/pypeclub/pype/pull/885)

**Merged pull requests:**

- Hiero: cut videos with correct secons  [\#892](https://github.com/pypeclub/pype/pull/892)
- Faster sync to avalon preparation [\#869](https://github.com/pypeclub/pype/pull/869)

## [2.14.5](https://github.com/pypeclub/pype/tree/2.14.5) (2021-01-06)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.14.4...2.14.5)

**Merged pull requests:**

- Pype logger refactor [\#866](https://github.com/pypeclub/pype/pull/866)

## [2.14.4](https://github.com/pypeclub/pype/tree/2.14.4) (2020-12-18)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.14.3...2.14.4)

**Merged pull requests:**

- Fix - AE - added explicit cast to int [\#837](https://github.com/pypeclub/pype/pull/837)

## [2.14.3](https://github.com/pypeclub/pype/tree/2.14.3) (2020-12-16)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.14.2...2.14.3)

**Fixed bugs:**

- TVPaint repair invalid metadata [\#809](https://github.com/pypeclub/pype/pull/809)
- Feature/push hier value to nonhier action [\#807](https://github.com/pypeclub/pype/pull/807)
- Harmony: fix palette and image sequence loader [\#806](https://github.com/pypeclub/pype/pull/806)

**Merged pull requests:**

- respecting space in path [\#823](https://github.com/pypeclub/pype/pull/823)

## [2.14.2](https://github.com/pypeclub/pype/tree/2.14.2) (2020-12-04)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.14.1...2.14.2)

**Enhancements:**

- Collapsible wrapper in settings [\#767](https://github.com/pypeclub/pype/pull/767)

**Fixed bugs:**

- Harmony: template extraction and palettes thumbnails on mac [\#768](https://github.com/pypeclub/pype/pull/768)
- TVPaint store context to workfile metadata \(764\) [\#766](https://github.com/pypeclub/pype/pull/766)
- Extract review audio cut fix [\#763](https://github.com/pypeclub/pype/pull/763)

**Merged pull requests:**

- AE: fix publish after background load [\#781](https://github.com/pypeclub/pype/pull/781)
- TVPaint store members key [\#769](https://github.com/pypeclub/pype/pull/769)

## [2.14.1](https://github.com/pypeclub/pype/tree/2.14.1) (2020-11-27)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.14.0...2.14.1)

**Enhancements:**

- Settings required keys in modifiable dict [\#770](https://github.com/pypeclub/pype/pull/770)
- Extract review may not add audio to output [\#761](https://github.com/pypeclub/pype/pull/761)

**Fixed bugs:**

- After Effects: frame range, file format and render source scene fixes [\#760](https://github.com/pypeclub/pype/pull/760)
- Hiero: trimming review with clip event number  [\#754](https://github.com/pypeclub/pype/pull/754)
- TVPaint: fix updating of loaded subsets [\#752](https://github.com/pypeclub/pype/pull/752)
- Maya: Vray handling of default aov [\#748](https://github.com/pypeclub/pype/pull/748)
- Maya: multiple renderable cameras in layer didn't work [\#744](https://github.com/pypeclub/pype/pull/744)
- Ftrack integrate custom attributes fix [\#742](https://github.com/pypeclub/pype/pull/742)

## [2.14.0](https://github.com/pypeclub/pype/tree/2.14.0) (2020-11-23)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.13.7...2.14.0)

**Enhancements:**

- Render publish plugins abstraction [\#687](https://github.com/pypeclub/pype/pull/687)
- Shot asset build trigger status [\#736](https://github.com/pypeclub/pype/pull/736)
- Maya: add camera rig publishing option [\#721](https://github.com/pypeclub/pype/pull/721)
- Sort instances by label in pyblish gui  [\#719](https://github.com/pypeclub/pype/pull/719)
- Synchronize ftrack hierarchical and shot attributes [\#716](https://github.com/pypeclub/pype/pull/716)
- 686 standalonepublisher editorial from image sequences [\#699](https://github.com/pypeclub/pype/pull/699)
- Ask user to select non-default camera from scene or create a new. [\#678](https://github.com/pypeclub/pype/pull/678)
- TVPaint: image loader with options [\#675](https://github.com/pypeclub/pype/pull/675)
- Maya: Camera name can be added to burnins. [\#674](https://github.com/pypeclub/pype/pull/674)
- After Effects: base integration with loaders [\#667](https://github.com/pypeclub/pype/pull/667)
- Harmony: Javascript refactoring and overall stability improvements [\#666](https://github.com/pypeclub/pype/pull/666)

**Fixed bugs:**

- Bugfix Hiero Review / Plate representation publish [\#743](https://github.com/pypeclub/pype/pull/743)
- Asset fetch second fix [\#726](https://github.com/pypeclub/pype/pull/726)
- TVPaint extract review fix [\#740](https://github.com/pypeclub/pype/pull/740)
- After Effects: Review were not being sent to ftrack [\#738](https://github.com/pypeclub/pype/pull/738)
- Maya: vray proxy was not loading [\#722](https://github.com/pypeclub/pype/pull/722)
- Maya: Vray expected file fixes [\#682](https://github.com/pypeclub/pype/pull/682)
- Missing audio on farm submission. [\#639](https://github.com/pypeclub/pype/pull/639)

**Deprecated:**

- Removed artist view from pyblish gui [\#717](https://github.com/pypeclub/pype/pull/717)
- Maya: disable legacy override check for cameras [\#715](https://github.com/pypeclub/pype/pull/715)

**Merged pull requests:**

- Application manager [\#728](https://github.com/pypeclub/pype/pull/728)
- Feature \#664 3.0 lib refactor [\#706](https://github.com/pypeclub/pype/pull/706)
- Lib from illicit part 2 [\#700](https://github.com/pypeclub/pype/pull/700)
- 3.0 lib refactor - path tools [\#697](https://github.com/pypeclub/pype/pull/697)

## [2.13.7](https://github.com/pypeclub/pype/tree/2.13.7) (2020-11-19)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.13.6...2.13.7)

**Fixed bugs:**

- Standalone Publisher: getting fps from context instead of nonexistent entity  [\#729](https://github.com/pypeclub/pype/pull/729)

## [2.13.6](https://github.com/pypeclub/pype/tree/2.13.6) (2020-11-15)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.13.5...2.13.6)

**Fixed bugs:**

- Maya workfile version wasn't syncing with renders properly [\#711](https://github.com/pypeclub/pype/pull/711)
- Maya: Fix for publishing multiple cameras with review from the same scene [\#710](https://github.com/pypeclub/pype/pull/710)

## [2.13.5](https://github.com/pypeclub/pype/tree/2.13.5) (2020-11-12)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.13.4...2.13.5)

**Enhancements:**

- 3.0 lib refactor [\#664](https://github.com/pypeclub/pype/issues/664)

**Fixed bugs:**

- Wrong thumbnail file was picked when publishing sequence in standalone publisher [\#703](https://github.com/pypeclub/pype/pull/703)
- Fix: Burnin data pass and FFmpeg tool check [\#701](https://github.com/pypeclub/pype/pull/701)

## [2.13.4](https://github.com/pypeclub/pype/tree/2.13.4) (2020-11-09)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.13.3...2.13.4)

**Enhancements:**

- AfterEffects integration with Websocket [\#663](https://github.com/pypeclub/pype/issues/663)

**Fixed bugs:**

- Photoshop uhiding hidden layers [\#688](https://github.com/pypeclub/pype/issues/688)
- \#688 - Fix publishing hidden layers [\#692](https://github.com/pypeclub/pype/pull/692)

**Closed issues:**

- Nuke Favorite directories "shot dir" "project dir" - not working [\#684](https://github.com/pypeclub/pype/issues/684)

**Merged pull requests:**

- Nuke Favorite directories "shot dir" "project dir" - not working \#684 [\#685](https://github.com/pypeclub/pype/pull/685)

## [2.13.3](https://github.com/pypeclub/pype/tree/2.13.3) (2020-11-03)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.13.2...2.13.3)

**Enhancements:**

- TV paint base integration [\#612](https://github.com/pypeclub/pype/issues/612)

**Fixed bugs:**

- Fix ffmpeg executable path with spaces [\#680](https://github.com/pypeclub/pype/pull/680)
- Hotfix: Added default version number [\#679](https://github.com/pypeclub/pype/pull/679)

## [2.13.2](https://github.com/pypeclub/pype/tree/2.13.2) (2020-10-28)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.13.1...2.13.2)

**Fixed bugs:**

- Nuke: wrong conditions when fixing legacy write nodes [\#665](https://github.com/pypeclub/pype/pull/665)

## [2.13.1](https://github.com/pypeclub/pype/tree/2.13.1) (2020-10-23)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.13.0...2.13.1)

**Enhancements:**

- move maya look assigner to pype menu [\#292](https://github.com/pypeclub/pype/issues/292)

**Fixed bugs:**

- Layer name is not propagating to metadata in Photoshop [\#654](https://github.com/pypeclub/pype/issues/654)
- Loader in Photoshop fails with "can't set attribute" [\#650](https://github.com/pypeclub/pype/issues/650)
- Nuke Load mp4 wrong frame range [\#661](https://github.com/pypeclub/pype/issues/661)
- Hiero: Review video file adding one frame to the end [\#659](https://github.com/pypeclub/pype/issues/659)

## [2.13.0](https://github.com/pypeclub/pype/tree/2.13.0) (2020-10-18)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.12.5...2.13.0)

**Enhancements:**

- Deadline Output Folder [\#636](https://github.com/pypeclub/pype/issues/636)
- Nuke Camera Loader [\#565](https://github.com/pypeclub/pype/issues/565)
- Deadline publish job shows publishing output folder [\#649](https://github.com/pypeclub/pype/pull/649)
- Get latest version in lib [\#642](https://github.com/pypeclub/pype/pull/642)
- Improved publishing of multiple representation from SP [\#638](https://github.com/pypeclub/pype/pull/638)
- Launch TvPaint shot work file from within Ftrack [\#631](https://github.com/pypeclub/pype/pull/631)
- Add mp4 support for RV action. [\#628](https://github.com/pypeclub/pype/pull/628)
- Maya: allow renders to have version synced with workfile [\#618](https://github.com/pypeclub/pype/pull/618)
- Renaming nukestudio host folder to hiero [\#617](https://github.com/pypeclub/pype/pull/617)
- Harmony: More efficient publishing [\#615](https://github.com/pypeclub/pype/pull/615)
- Ftrack server action improvement [\#608](https://github.com/pypeclub/pype/pull/608)
- Deadline user defaults to pype username if present [\#607](https://github.com/pypeclub/pype/pull/607)
- Standalone publisher now has icon [\#606](https://github.com/pypeclub/pype/pull/606)
- Nuke render write targeting knob improvement [\#603](https://github.com/pypeclub/pype/pull/603)
- Animated pyblish gui [\#602](https://github.com/pypeclub/pype/pull/602)
- Maya: Deadline - make use of asset dependencies optional [\#591](https://github.com/pypeclub/pype/pull/591)
- Nuke: Publishing, loading and updating alembic cameras [\#575](https://github.com/pypeclub/pype/pull/575)
- Maya: add look assigner to pype menu even if scriptsmenu is not available [\#573](https://github.com/pypeclub/pype/pull/573)
- Store task types in the database [\#572](https://github.com/pypeclub/pype/pull/572)
- Maya: Tiled EXRs to scanline EXRs render option [\#512](https://github.com/pypeclub/pype/pull/512)
- Fusion basic integration [\#452](https://github.com/pypeclub/pype/pull/452)

**Fixed bugs:**

- Burnin script did not propagate ffmpeg output [\#640](https://github.com/pypeclub/pype/issues/640)
- Pyblish-pype spacer in terminal wasn't transparent [\#646](https://github.com/pypeclub/pype/pull/646)
- Lib subprocess without logger [\#645](https://github.com/pypeclub/pype/pull/645)
- Nuke: prevent crash if we only have single frame in sequence [\#644](https://github.com/pypeclub/pype/pull/644)
- Burnin script logs better output [\#641](https://github.com/pypeclub/pype/pull/641)
- Missing audio on farm submission. [\#639](https://github.com/pypeclub/pype/pull/639)
- review from imagesequence error [\#633](https://github.com/pypeclub/pype/pull/633)
- Hiero: wrong order of fps clip instance data collecting  [\#627](https://github.com/pypeclub/pype/pull/627)
- Add source for review instances. [\#625](https://github.com/pypeclub/pype/pull/625)
- Task processing in event sync [\#623](https://github.com/pypeclub/pype/pull/623)
- sync to avalon doesn t remove renamed task [\#619](https://github.com/pypeclub/pype/pull/619)
- Intent publish setting wasn't working with default value [\#562](https://github.com/pypeclub/pype/pull/562)
- Maya: Updating a look where the shader name changed, leaves the geo without a shader [\#514](https://github.com/pypeclub/pype/pull/514)

**Merged pull requests:**

- Avalon module without Qt [\#581](https://github.com/pypeclub/pype/pull/581)
- Ftrack module without Qt [\#577](https://github.com/pypeclub/pype/pull/577)

## [2.12.5](https://github.com/pypeclub/pype/tree/2.12.5) (2020-10-14)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.12.4...2.12.5)

**Enhancements:**

- Launch TvPaint shot work file from within Ftrack [\#629](https://github.com/pypeclub/pype/issues/629)

**Merged pull requests:**

- Harmony: Disable application launch logic [\#637](https://github.com/pypeclub/pype/pull/637)

## [2.12.4](https://github.com/pypeclub/pype/tree/2.12.4) (2020-10-08)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.12.3...2.12.4)

**Enhancements:**

- convert nukestudio to hiero host [\#616](https://github.com/pypeclub/pype/issues/616)
- Fusion basic integration  [\#451](https://github.com/pypeclub/pype/issues/451)

**Fixed bugs:**

- Sync to avalon doesn't remove renamed task [\#605](https://github.com/pypeclub/pype/issues/605)
- NukeStudio: FPS collecting into clip instances [\#624](https://github.com/pypeclub/pype/pull/624)

**Merged pull requests:**

- NukeStudio: small fixes [\#622](https://github.com/pypeclub/pype/pull/622)
- NukeStudio: broken order of plugins [\#620](https://github.com/pypeclub/pype/pull/620)

## [2.12.3](https://github.com/pypeclub/pype/tree/2.12.3) (2020-10-06)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.12.2...2.12.3)

**Enhancements:**

- Nuke Publish Camera [\#567](https://github.com/pypeclub/pype/issues/567)
- Harmony: open xstage file no matter of its name [\#526](https://github.com/pypeclub/pype/issues/526)
- Stop integration of unwanted data [\#387](https://github.com/pypeclub/pype/issues/387)
- Move avalon-launcher functionality to pype [\#229](https://github.com/pypeclub/pype/issues/229)
- avalon workfiles api [\#214](https://github.com/pypeclub/pype/issues/214)
- Store task types [\#180](https://github.com/pypeclub/pype/issues/180)
- Avalon Mongo Connection split [\#136](https://github.com/pypeclub/pype/issues/136)
- nk camera workflow [\#71](https://github.com/pypeclub/pype/issues/71)
- Hiero integration added [\#590](https://github.com/pypeclub/pype/pull/590)
- Anatomy instance data collection is substantially faster for many instances [\#560](https://github.com/pypeclub/pype/pull/560)

**Fixed bugs:**

- test issue [\#596](https://github.com/pypeclub/pype/issues/596)
- Harmony: empty scene contamination [\#583](https://github.com/pypeclub/pype/issues/583)
- Edit publishing in SP doesn't respect shot selection for publishing [\#542](https://github.com/pypeclub/pype/issues/542)
- Pathlib breaks compatibility with python2 hosts [\#281](https://github.com/pypeclub/pype/issues/281)
- Updating a look where the shader name changed leaves the geo without a shader [\#237](https://github.com/pypeclub/pype/issues/237)
- Better error handling [\#84](https://github.com/pypeclub/pype/issues/84)
- Harmony: function signature [\#609](https://github.com/pypeclub/pype/pull/609)
- Nuke: gizmo publishing error [\#594](https://github.com/pypeclub/pype/pull/594)
- Harmony: fix clashing namespace of called js functions [\#584](https://github.com/pypeclub/pype/pull/584)
- Maya: fix maya scene type preset exception [\#569](https://github.com/pypeclub/pype/pull/569)

**Closed issues:**

- Nuke Gizmo publishing [\#597](https://github.com/pypeclub/pype/issues/597)
- nuke gizmo publishing error [\#592](https://github.com/pypeclub/pype/issues/592)
- Publish EDL [\#579](https://github.com/pypeclub/pype/issues/579)
- Publish render from SP [\#576](https://github.com/pypeclub/pype/issues/576)
- rename ftrack custom attribute group to `pype` [\#184](https://github.com/pypeclub/pype/issues/184)

**Merged pull requests:**

- Audio file existence check [\#614](https://github.com/pypeclub/pype/pull/614)
- NKS small fixes [\#587](https://github.com/pypeclub/pype/pull/587)
- Standalone publisher editorial plugins interfering [\#580](https://github.com/pypeclub/pype/pull/580)

## [2.12.2](https://github.com/pypeclub/pype/tree/2.12.2) (2020-09-25)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.12.1...2.12.2)

**Enhancements:**

- pype config GUI [\#241](https://github.com/pypeclub/pype/issues/241)

**Fixed bugs:**

- Harmony: Saving heavy scenes will crash [\#507](https://github.com/pypeclub/pype/issues/507)
- Extract review a representation name with `\*\_burnin` [\#388](https://github.com/pypeclub/pype/issues/388)
- Hierarchy data was not considering active isntances [\#551](https://github.com/pypeclub/pype/pull/551)

## [2.12.1](https://github.com/pypeclub/pype/tree/2.12.1) (2020-09-15)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.12.0...2.12.1)

**Fixed bugs:**

- Pype: changelog.md is outdated [\#503](https://github.com/pypeclub/pype/issues/503)
- dependency security alert ! [\#484](https://github.com/pypeclub/pype/issues/484)
- Maya: RenderSetup is missing update [\#106](https://github.com/pypeclub/pype/issues/106)
- \<pyblish plugin\> extract effects creates new instance [\#78](https://github.com/pypeclub/pype/issues/78)

## [2.12.0](https://github.com/pypeclub/pype/tree/2.12.0) (2020-09-10)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.11.8...2.12.0)

**Enhancements:**

- Less mongo connections [\#509](https://github.com/pypeclub/pype/pull/509)
- Nuke: adding image loader  [\#499](https://github.com/pypeclub/pype/pull/499)
- Move launcher window to top if launcher action is clicked [\#450](https://github.com/pypeclub/pype/pull/450)
- Maya:  better tile rendering support in Pype [\#446](https://github.com/pypeclub/pype/pull/446)
- Implementation of non QML launcher [\#443](https://github.com/pypeclub/pype/pull/443)
- Optional skip review on renders. [\#441](https://github.com/pypeclub/pype/pull/441)
- Ftrack: Option to push status from task to latest version [\#440](https://github.com/pypeclub/pype/pull/440)
- Properly containerize image plane loads. [\#434](https://github.com/pypeclub/pype/pull/434)
- Option to keep the review files. [\#426](https://github.com/pypeclub/pype/pull/426)
- Isolate view on instance members. [\#425](https://github.com/pypeclub/pype/pull/425)
- Maya: Publishing of tile renderings on Deadline [\#398](https://github.com/pypeclub/pype/pull/398)
- Feature/little bit better logging gui [\#383](https://github.com/pypeclub/pype/pull/383)

**Fixed bugs:**

- Maya: Fix tile order for Draft Tile Assembler [\#511](https://github.com/pypeclub/pype/pull/511)
- Remove extra dash [\#501](https://github.com/pypeclub/pype/pull/501)
- Fix: strip dot from repre names in single frame renders [\#498](https://github.com/pypeclub/pype/pull/498)
- Better handling of destination during integrating [\#485](https://github.com/pypeclub/pype/pull/485)
- Fix: allow thumbnail creation for single frame renders [\#460](https://github.com/pypeclub/pype/pull/460)
- added missing argument to launch\_application in ftrack app handler [\#453](https://github.com/pypeclub/pype/pull/453)
- Burnins: Copy bit rate of input video to match quality. [\#448](https://github.com/pypeclub/pype/pull/448)
- Standalone publisher is now independent from tray [\#442](https://github.com/pypeclub/pype/pull/442)
- Bugfix/empty enumerator attributes [\#436](https://github.com/pypeclub/pype/pull/436)
- Fixed wrong order of "other" category collapssing in publisher [\#435](https://github.com/pypeclub/pype/pull/435)
- Multiple reviews where being overwritten to one. [\#424](https://github.com/pypeclub/pype/pull/424)
- Cleanup plugin fail on instances without staging dir [\#420](https://github.com/pypeclub/pype/pull/420)
- deprecated -intra parameter in ffmpeg to new `-g` [\#417](https://github.com/pypeclub/pype/pull/417)
- Delivery action can now work with entered path [\#397](https://github.com/pypeclub/pype/pull/397)

**Merged pull requests:**

- Review on instance.data  [\#473](https://github.com/pypeclub/pype/pull/473)

## [2.11.8](https://github.com/pypeclub/pype/tree/2.11.8) (2020-08-27)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.11.7...2.11.8)

**Enhancements:**

- DWAA support for Maya [\#382](https://github.com/pypeclub/pype/issues/382)
- Isolate View on Playblast [\#367](https://github.com/pypeclub/pype/issues/367)
- Maya: Tile rendering [\#297](https://github.com/pypeclub/pype/issues/297)
- single pype instance running [\#47](https://github.com/pypeclub/pype/issues/47)
- PYPE-649: projects don't guarantee backwards compatible environment [\#8](https://github.com/pypeclub/pype/issues/8)
- PYPE-663: separate venv for each deployed version [\#7](https://github.com/pypeclub/pype/issues/7)

**Fixed bugs:**

- pyblish pype - other group is collapsed before plugins are done [\#431](https://github.com/pypeclub/pype/issues/431)
- Alpha white edges in harmony on PNGs [\#412](https://github.com/pypeclub/pype/issues/412)
- harmony image loader picks wrong representations [\#404](https://github.com/pypeclub/pype/issues/404)
- Clockify crash when response contain symbol not allowed by UTF-8 [\#81](https://github.com/pypeclub/pype/issues/81)

## [2.11.7](https://github.com/pypeclub/pype/tree/2.11.7) (2020-08-21)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.11.6...2.11.7)

**Fixed bugs:**

- Clean Up Baked Movie [\#369](https://github.com/pypeclub/pype/issues/369)
- celaction last workfile [\#459](https://github.com/pypeclub/pype/pull/459)

## [2.11.6](https://github.com/pypeclub/pype/tree/2.11.6) (2020-08-18)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.11.5...2.11.6)

**Enhancements:**

- publisher app [\#56](https://github.com/pypeclub/pype/issues/56)

## [2.11.5](https://github.com/pypeclub/pype/tree/2.11.5) (2020-08-13)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.11.4...2.11.5)

**Enhancements:**

- Switch from master to equivalent [\#220](https://github.com/pypeclub/pype/issues/220)
- Standalone publisher now only groups sequence if the extension is known [\#439](https://github.com/pypeclub/pype/pull/439)

**Fixed bugs:**

- Logs have been disable for editorial by default to speed up publishing [\#433](https://github.com/pypeclub/pype/pull/433)
- additional fixes for celaction [\#430](https://github.com/pypeclub/pype/pull/430)
- Harmony: invalid variable scope in validate scene settings [\#428](https://github.com/pypeclub/pype/pull/428)
- new representation name for audio was not accepted [\#427](https://github.com/pypeclub/pype/pull/427)

## [2.11.4](https://github.com/pypeclub/pype/tree/2.11.4) (2020-08-10)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.11.3...2.11.4)

**Enhancements:**

- WebSocket server [\#135](https://github.com/pypeclub/pype/issues/135)
- standalonepublisher: editorial family features expansion \[master branch\] [\#411](https://github.com/pypeclub/pype/pull/411)

## [2.11.3](https://github.com/pypeclub/pype/tree/2.11.3) (2020-08-04)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.11.2...2.11.3)

**Fixed bugs:**

- Harmony: publishing performance issues [\#408](https://github.com/pypeclub/pype/pull/408)

## [2.11.2](https://github.com/pypeclub/pype/tree/2.11.2) (2020-07-31)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.11.1...2.11.2)

**Fixed bugs:**

- Ftrack to Avalon bug [\#406](https://github.com/pypeclub/pype/issues/406)

## [2.11.1](https://github.com/pypeclub/pype/tree/2.11.1) (2020-07-29)

[Full Changelog](https://github.com/pypeclub/pype/compare/2.11.0...2.11.1)

**Merged pull requests:**

- Celaction: metadata json folder fixes on path  [\#393](https://github.com/pypeclub/pype/pull/393)
- CelAction - version up method taken fro pype.lib  [\#391](https://github.com/pypeclub/pype/pull/391)

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


\* *This Changelog was automatically generated by [github_changelog_generator](https://github.com/github-changelog-generator/github-changelog-generator)*
