import os

from pyblish import api


# Collection
collect_json_CollectJSON = api.CollectorOrder + 0.1
collect_source_CollectScene = api.CollectorOrder + 0.1
collect_scene_version_CollectSceneVersion = api.CollectorOrder + 0.1
collect_existing_files_CollectExistingFiles = api.CollectorOrder + 0.25
collect_reviews_CollectReviews = api.CollectorOrder + 0.3
collect_sorting_CollectSorting = api.CollectorOrder + 0.49

# Validation
persist_publish_state_PersistPublishState = api.ValidatorOrder
validate_executables_ValidateFFmpeg = api.ValidatorOrder
validate_processing_ValidateProcessing = api.ValidatorOrder
validate_scene_version_ValidateSceneVersion = api.ValidatorOrder
validate_review_ValidateReview = api.ValidatorOrder

# Extraction
extract_scene_save_ExtractSceneSave = api.ExtractorOrder - 0.49
extract_review_ExtractReview = api.ExtractorOrder
extract_review_ExtractReviewTranscode = api.ExtractorOrder + 0.02
extract_review_ExtractReviewTranscodeNukeStudio = (
    api.ExtractorOrder + 0.02
)

# Integration
extract_json_ExtractJSON = api.IntegratorOrder + 1
copy_to_clipboard_action_Report = api.IntegratorOrder + 1

# AfterEffects
aftereffects_collect_render_items_CollectRenderItems = api.CollectorOrder
aftereffects_collect_scene_CollectScene = api.CollectorOrder

aftereffects_validate_output_path_ValidateOutputPath = api.ValidatorOrder
aftereffects_validate_scene_path_ValidateScenePath = api.ValidatorOrder
aftereffects_validate_unique_comp_renders_ValidateUniqueCompRenders = (
    api.ValidatorOrder
)

aftereffects_append_deadline_data_AppendDeadlineData = api.ExtractorOrder
aftereffects_append_ftrack_audio_AppendFtrackAudio = api.ExtractorOrder
aftereffects_extract_local_ExtractLocal = api.ExtractorOrder

# CelAction
celaction_collect_scene_CollectScene = api.CollectorOrder
celaction_collect_render_CollectRender = api.CollectorOrder + 0.1
celaction_bait_append_ftrack_data_AppendFtrackData = (
    api.CollectorOrder + 0.1
)
celaction_bait_append_ftrack_asset_name_AppendFtrackAssetName = (
    api.CollectorOrder + 0.1
)

celaction_bait_validate_scene_path_ValidateScenePath = (
    api.ValidatorOrder
)

celaction_bait_append_ftrack_data_AppendFtrackAudio = (
    api.ExtractorOrder
)
celaction_extract_deadline_ExtractDeadline = api.ExtractorOrder
celaction_extract_render_images_ExtractRenderImages = api.ExtractorOrder
celaction_extract_render_images_ExtractRenderMovie = api.ExtractorOrder + 0.1
celaction_extract_deadline_movie_ExtractDeadlineMovie = (
    api.ExtractorOrder + 0.4
)

celaction_bait_integrate_local_render_IntegrateLocal = (
    api.IntegratorOrder
)

# Deadline
deadline_OnJobFinished_collect_output_CollectOutput = api.CollectorOrder
deadline_OnJobSubmitted_collect_movie_CollectMovie = api.CollectorOrder
deadline_OnJobSubmitted_collect_render_CollectRender = api.CollectorOrder
deadline_collect_family_CollectFamily = api.CollectorOrder + 0.1
deadline_collect_houdini_parameters_CollectHoudiniParameters = (
    deadline_collect_family_CollectFamily + 0.01
)
deadline_collect_maya_parameters_CollectMayaParameters = (
    deadline_collect_family_CollectFamily + 0.01
)
deadline_collect_nuke_parameters_CollectNukeParameters = (
    deadline_collect_family_CollectFamily + 0.01
)
deadline_collect_houdini_render_CollectHoudiniRender = api.CollectorOrder + 0.4

deadline_validate_houdini_parameters_ValidateHoudiniParameters = (
    api.ValidatorOrder
)
deadline_validate_maya_parameters_ValidateMayaParameters = api.ValidatorOrder
deadline_validate_nuke_parameters_ValidateNukeParameters = api.ValidatorOrder

deadline_extract_ftrack_path_ExtractFtrackPath = api.ExtractorOrder
deadline_extract_houdini_ExtractHoudini = api.ExtractorOrder
deadline_extract_job_name_ExtractJobName = api.ExtractorOrder
deadline_extract_maya_ExtractMaya = api.ExtractorOrder
deadline_extract_nuke_ExtractNuke = api.ExtractorOrder
deadline_extract_suspended_ExtractSuspended = api.ExtractorOrder

deadline_integrate_collection_IntegrateCollection = api.IntegratorOrder - 0.1
deadline_bait_integrate_ftrack_thumbnail_IntegrateFtrackThumbnail = (
    api.IntegratorOrder
)
deadline_bait_update_ftrack_status_UpdateFtrackStatus = (
    api.IntegratorOrder + 0.4
)


# Ftrack
ftrack_collect_nukestudio_CollectNukeStudioEntities = api.CollectorOrder + 0.1
ftrack_collect_nukestudio_CollectNukeStudioProjectData = (
    api.CollectorOrder + 0.1
)
ftrack_collect_version_CollectVersion = api.CollectorOrder + 0.2
ftrack_collect_family_CollectFamily = api.CollectorOrder + 0.4

ftrack_validate_assets_ValidateAssets = api.ValidatorOrder
ftrack_validate_nuke_settings_ValidateNukeSettings = api.ValidatorOrder
ftrack_validate_nukestudio_ValidateNukeStudioProjectData = api.ValidatorOrder
ftrack_validate_nukestudio_tasks_ValidateNukeStudioTasks = api.ValidatorOrder

ftrack_extract_components_ExtractCache = api.ExtractorOrder
ftrack_extract_components_ExtractCamera = api.ExtractorOrder
ftrack_extract_components_ExtractGeometry = api.ExtractorOrder
ftrack_extract_components_ExtractGizmo = api.ExtractorOrder
ftrack_extract_components_ExtractImg = api.ExtractorOrder
ftrack_extract_components_ExtractLUT = api.ExtractorOrder
ftrack_extract_components_ExtractMovie = api.ExtractorOrder
ftrack_extract_components_ExtractAudio = api.ExtractorOrder
ftrack_extract_components_ExtractReview = api.ExtractorOrder
ftrack_extract_components_ExtractScene = api.ExtractorOrder
ftrack_extract_entities_ExtractProject = api.ExtractorOrder
ftrack_extract_entities_ExtractEpisode = (
    ftrack_extract_entities_ExtractProject + 0.01
)
ftrack_extract_entities_ExtractSequence = (
    ftrack_extract_entities_ExtractEpisode + 0.01
)
ftrack_extract_entities_ExtractShot = (
    ftrack_extract_entities_ExtractSequence + 0.01
)
ftrack_extract_entities_ExtractLinkAssetbuilds = (
    ftrack_extract_entities_ExtractShot + 0.01
)
ftrack_extract_entities_ExtractAssetDataNukeStudio = (
    ftrack_extract_entities_ExtractShot + 0.01
)
ftrack_extract_entities_ExtractTasks = (
    ftrack_extract_entities_ExtractShot + 0.01
)
ftrack_extract_entities_ExtractCommit = (
    ftrack_extract_entities_ExtractTasks + 0.01
)
ftrack_extract_entities_ExtractNukeStudio = (
    ftrack_extract_entities_ExtractTasks + 0.01
)
ftrack_extract_thumbnail_ExtractThumbnailImg = api.ExtractorOrder + 0.1
ftrack_extract_review_ExtractReview = api.ExtractorOrder + 0.2
ftrack_extract_components_ExtractComponents = api.ExtractorOrder + 0.4

ftrack_integrate_status_IntegrateStatus = api.IntegratorOrder

ftrack_other_link_source_OtherLinkSource = api.IntegratorOrder + 1

# Hiero
hiero_collect_items_CollectItems = api.CollectorOrder

hiero_validate_names_ValidateNames = api.ValidatorOrder

hiero_extract_transcode_BumpyboxExtractTranscodeH264 = api.ExtractorOrder - 0.1
hiero_extract_transcode_BumpyboxExtractTranscodeJPEG = api.ExtractorOrder - 0.1
hiero_extract_audio_ExtractAudio = api.ExtractorOrder
hiero_extract_ftrack_shot_ExtractFtrackShot = api.ExtractorOrder
hiero_extract_nuke_script_ExtractNukeScript = api.ExtractorOrder
hiero_extract_transcode_ExtractTranscode = api.ExtractorOrder
hiero_extract_ftrack_components_ExtractFtrackComponents = (
    api.ExtractorOrder + 0.1
)
hiero_extract_ftrack_tasks_ExtractFtrackTasks = api.ExtractorOrder + 0.1
hiero_extract_ftrack_thumbnail_ExtractFtrackThumbnail = (
    api.ExtractorOrder + 0.1
)

# Houdini
houdini_collect_Collect = api.CollectorOrder

houdini_validate_alembic_ValidateAlembic = api.ValidatorOrder
houdini_validate_dynamics_ValidateDynamics = api.ValidatorOrder
houdini_validate_geometry_ValidateGeometry = api.ValidatorOrder
houdini_validate_mantra_camera_ValidateMantraCamera = api.ValidatorOrder
houdini_validate_mantra_settings_ValidateMantraSettings = api.ValidatorOrder
houdini_validate_output_path_ValidateOutputPath = api.ValidatorOrder

houdini_extract_scene_save_ExtractSceneSave = api.ExtractorOrder - 0.1
houdini_extract_local_ExtractLocal = api.ExtractorOrder

# Maya
maya_collect_framerate_CollectFramerate = api.CollectorOrder - 0.5
maya_collect_files_CollectFiles = api.CollectorOrder
maya_collect_render_setups_CollectRenderSetups = api.CollectorOrder
maya_collect_sets_CollectSets = api.CollectorOrder
maya_collect_sets_CollectSetsProcess = maya_collect_sets_CollectSets + 0.01
maya_collect_sets_CollectSetsPublish = maya_collect_sets_CollectSets + 0.01
maya_collect_playblasts_CollectPlayblasts = api.CollectorOrder
maya_collect_playblasts_CollectPlayblastsProcess = (
    maya_collect_playblasts_CollectPlayblasts + 0.01
)
maya_collect_playblasts_CollectPlayblastsPublish = (
    maya_collect_playblasts_CollectPlayblasts + 0.01
)

maya_modeling_validate_intermediate_shapes_ValidateIntermediateShapes = (
    api.ValidatorOrder
)
maya_modeling_validate_points_ValidatePoints = (
    api.ValidatorOrder
)
maya_modeling_validate_hierarchy_ValidateHierarchy = (
    api.ValidatorOrder
)
maya_modeling_validate_shape_name_ValidateShapeName = (
    api.ValidatorOrder
)
maya_modeling_validate_transforms_ValidateTransforms = (
    api.ValidatorOrder
)
maya_modeling_validate_display_layer_ValidateDisplayLayer = (
    api.ValidatorOrder
)
maya_modeling_validate_smooth_display_ValidateSmoothDisplay = (
    api.ValidatorOrder
)
maya_validate_arnold_setings_ValidateArnoldSettings = api.ValidatorOrder
maya_validate_name_ValidateName = api.ValidatorOrder
maya_validate_render_camera_ValidateRenderCamera = api.ValidatorOrder
maya_validate_render_layer_settings_ValidateRenderLayerSettings = (
    api.ValidatorOrder
)
maya_validate_vray_settings_ValidateVraySettings = api.ValidatorOrder

maya_validate_scene_modified_ValidateSceneModified = api.ExtractorOrder - 0.49
maya_extract_alembic_ExtractAlembic = api.ExtractorOrder
maya_extract_formats_ExtractFormats = api.ExtractorOrder
maya_lookdev_extract_construction_history_ExtractConstructionHistory = (
    maya_extract_formats_ExtractFormats - 0.01
)
maya_modeling_extract_construction_history_ExtractConstructionHistory = (
    maya_extract_formats_ExtractFormats - 0.01
)
maya_rigging_extract_disconnect_animation_ExtractDisconnectAnimation = (
    maya_extract_formats_ExtractFormats - 0.01
)
maya_extract_playblast_ExtractPlayblast = api.ExtractorOrder
maya_extract_render_layer_ExtractRenderLayer = api.ExtractorOrder

# Nuke
nuke_collect_selection_CollectSelection = api.CollectorOrder - 0.1
nuke_collect_backdrops_CollectBackdrops = api.CollectorOrder + 0.1
nuke_collect_framerate_CollectFramerate = api.CollectorOrder
nuke_collect_reads_CollectReads = api.CollectorOrder
nuke_collect_write_geo_CollectWriteGeo = api.CollectorOrder
nuke_collect_writes_CollectWrites = api.CollectorOrder
nuke_collect_write_geo_CollectCacheProcess = api.CollectorOrder + 0.01
nuke_collect_write_geo_CollectCachePublish = api.CollectorOrder + 0.01
nuke_collect_writes_CollectWritesProcess = api.CollectorOrder + 0.01
nuke_collect_writes_CollectWritesPublish = api.CollectorOrder + 0.01
nuke_collect_groups_CollectGroups = api.CollectorOrder + 0.1

nuke_validate_datatype_ValidateDatatype = api.ValidatorOrder
nuke_validate_frame_rate_ValidateFrameRate = api.ValidatorOrder
nuke_validate_group_node_ValidateGroupNode = api.ValidatorOrder
nuke_validate_proxy_mode_ValidateProxyMode = api.ValidatorOrder
nuke_validate_read_node_ValidateReadNode = api.ValidatorOrder
nuke_validate_write_node_ValidateWriteNode = api.ValidatorOrder
nuke_validate_write_node_ValidateReviewNodeDuplicate = api.ValidatorOrder
nuke_validate_writegeo_node_ValidateWriteGeoNode = api.ValidatorOrder

nuke_extract_output_directory_ExtractOutputDirectory = api.ExtractorOrder - 0.1
nuke_extract_backdrop_ExtractBackdrop = api.ExtractorOrder
nuke_extract_group_ExtractGroup = api.ExtractorOrder
nuke_extract_write_Extract = api.ExtractorOrder
nuke_extract_write_ExtractCache = api.ExtractorOrder
nuke_extract_write_ExtractCamera = api.ExtractorOrder
nuke_extract_write_ExtractGeometry = api.ExtractorOrder
nuke_extract_write_ExtractWrite = api.ExtractorOrder
nuke_extract_review_ExtractReview = api.ExtractorOrder + 0.01

# NukeStudio
nukestudio_collect_CollectFramerate = api.CollectorOrder
nukestudio_collect_CollectTrackItems = api.CollectorOrder
nukestudio_collect_CollectTasks = api.CollectorOrder + 0.01

nukestudio_validate_names_ValidateNames = api.ValidatorOrder
nukestudio_validate_names_ValidateNamesFtrack = api.ValidatorOrder
nukestudio_validate_projectroot_ValidateProjectRoot = api.ValidatorOrder
nukestudio_validate_resolved_paths_ValidateResolvedPaths = api.ValidatorOrder
nukestudio_validate_task_ValidateImageSequence = api.ValidatorOrder
nukestudio_validate_task_ValidateOutputRange = api.ValidatorOrder
nukestudio_validate_track_item_ValidateTrackItem = api.ValidatorOrder
nukestudio_validate_track_item_ValidateTrackItemFtrack = api.ValidatorOrder
nukestudio_validate_viewer_lut_ValidateViewerLut = api.ValidatorOrder

nukestudio_extract_review_ExtractReview = api.ExtractorOrder
nukestudio_extract_tasks_ExtractTasks = api.ExtractorOrder

# RoyalRender
royalrender_collect_CollectMayaSets = api.CollectorOrder + 0.1
royalrender_collect_CollectNukeWrites = api.CollectorOrder + 0.1

royalrender_extract_maya_ExtractMaya = api.ExtractorOrder
royalrender_extract_maya_alembic_ExtractMovie = api.ExtractorOrder
royalrender_extract_nuke_ExtractNuke = api.ExtractorOrder

# TVPaint
tvpaint_extract_deadline_ExtractDeadline = api.ExtractorOrder - 0.1
tvpaint_collect_scene_arg_CollectSceneArg = api.CollectorOrder - 0.05
tvpaint_collect_render_CollectRender = api.CollectorOrder + 0.1

tvpaint_validate_scene_path_ValidateScenePath = api.ValidatorOrder

tvpaint_extract_hobsoft_scene_ExtractHobsoftScene = api.ExtractorOrder


def get_order(module, name):
    path = get_variable_name(module, name)

    if path not in globals().keys():
        raise KeyError("\"{0}\" could not be found in inventory.".format(path))

    return globals()[path]


def get_variable_name(module, name):
    plugins_directory = os.path.abspath(
        os.path.join(__file__, "..", "plugins")
    )

    module = os.path.relpath(module, plugins_directory)
    path = "{0}{1}".format(module, name)
    path = path.replace(".py", "_")
    path = path.replace(os.sep, "_")

    return path
