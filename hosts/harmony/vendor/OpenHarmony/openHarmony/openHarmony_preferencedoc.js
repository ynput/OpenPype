//////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////
//
//                            openHarmony Library
//
//
//         Developped by Mathieu Chaptel, Chris Fourney
//
//
//   This library is an open source implementation of a Document Object Model
//   for Toonboom Harmony. It also implements patterns similar to JQuery
//   for traversing this DOM.
//
//   Its intended purpose is to simplify and streamline toonboom scripting to
//   empower users and be easy on newcomers, with default parameters values,
//   and by hiding the heavy lifting required by the official API.
//
//   This library is provided as is and is a work in progress. As such, not every
//   function has been implemented or is garanteed to work. Feel free to contribute
//   improvements to its official github. If you do make sure you follow the provided
//   template and naming conventions and document your new methods properly.
//
//   This library doesn't overwrite any of the objects and classes of the official
//   Toonboom API which must remains available.
//
//   This library is made available under the Mozilla Public license 2.0.
//   https://www.mozilla.org/en-US/MPL/2.0/
//
//   The repository for this library is available at the address:
//   https://github.com/cfourney/OpenHarmony/
//
//
//   For any requests feel free to contact m.chaptel@gmail.com
//
//
//
//
//////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////

//
// This document was outputted by this function.
//
//
// include("openHarmony.js")
//
// printOutDoc();
//
// function printOutDoc(){
// 	var doc = "";
// 	var prefs = $.app.preferences
// 	var categories = prefs.categories
// 	for (var i in categories){
// 		var docString = ["\n\n/\**\n * Preferences in the "+categories[i]+" category.", " @name preferences#"+categories[i]];
// 		categoryPrefs = prefs.details
// 		for (var j in categoryPrefs){
// 			var pref = categoryPrefs[j]
// 			if (pref.category != categories[i])continue;
// 			if (pref.descriptionText == undefined) pref.descriptionText = ""
// 			if (pref.description == undefined) pref.description = pref.descriptionText
// 			docString.push(" @property {"+pref.type+"} "+pref.keyword+"="+pref.value+" "+pref.description);
// 		}
// 		docString.push ("/");
// 		doc += docString.join("\n *");
// 	}
//
// 	MessageLog.trace(doc);
// }


/**
 * The preferences of Harmony can be accessed with the following keywords.
 * @class preferences
 * @hideconstructor 
 * @namespace
 * @example
 * // To access the preferences of Harmony, grab the preference object in the $.oApp class:
 * var prefs = $.app.preferences;
 * 
 * // It's then possible to access all available preferences of the software:
 * for (var i in prefs){
 *   log (i+" "+prefs[i]);
 * }
 * 
 * // accessing the preference value can be done directly by using the dot notation:
 * prefs.USE_OVERLAY_UNDERLAY_ART = true;
 * log (prefs.USE_OVERLAY_UNDERLAY_ART);
 * 
 * //the details objects of the preferences object allows access to more information about each preference
 * var details = prefs.details
 * log(details.USE_OVERLAY_UNDERLAY_ART.category+" "+details.USE_OVERLAY_UNDERLAY_ART.id+" "+details.USE_OVERLAY_UNDERLAY_ART.type);
 * 
 * for (var i in details){
 *   log(i+" "+JSON.stringify(details[i]))       // each object inside detail is a complete oPreference instance
 * }
 * 
 * // the preference object also holds a categories array with the list of all categories
 * log (prefs.categories)
 */

/**
 * Preferences in the Internal category.
 * @name preferences#Internal
 * @property {string} PREFERENCE_SET=Cutout Animation 
 * @property {TUPencilDeformationQualityItem} DEFAULT_PENCIL_DEFORMATION_QUALITY=Low Default Pencil Line Deformation Quality
 * @property {bool} DEFAULT_PRESERVE_LINE_THICKNESS=false 
 * @property {int} TV_DEFAULT_VIEW=3 
 * @property {double} DBL_STEP_2DPOSITION_X=0.1 Internal
 * @property {double} DBL_STEP_2DPOSITION_Y=0.1 Internal
 * @property {double} DBL_STEP_3DPOSITION_X=0.1 Internal
 * @property {double} DBL_STEP_3DPOSITION_Y=0.1 Internal
 * @property {double} DBL_STEP_3DPOSITION_Z=0.1 Internal
 * @property {double} DBL_STEP_CUSTOMNAME_FIELD_CHART=1 Internal
 * @property {double} DBL_STEP_APPLYFOCUS_MULTIPLIER=0.1 Internal
 * @property {double} DBL_STEP_COLORCARD_OFFSET_Z=0.2 Internal
 * @property {double} DBL_STEP_COLORSCALE_RED=0.1 Internal
 * @property {double} DBL_STEP_COLORSCALE_GREEN=0.1 Internal
 * @property {double} DBL_STEP_COLORSCALE_BLUE=0.1 Internal
 * @property {double} DBL_STEP_COLORSCALE_ALPHA=0.1 Internal
 * @property {double} DBL_STEP_COLORSCALE_HUE=0.1 Internal
 * @property {double} DBL_STEP_COLORSCALE_SATURATION=0.1 Internal
 * @property {double} DBL_STEP_COLORSCALE_VALUE=0.1 Internal
 * @property {double} DBL_STEP_COLORSCREEN_RED_MIN=0.1 Internal
 * @property {double} DBL_STEP_COLORSCREEN_RED_MAX=0.1 Internal
 * @property {double} DBL_STEP_COLORSCREEN_GREEN_MIN=0.1 Internal
 * @property {double} DBL_STEP_COLORSCREEN_GREEN_MAX=0.1 Internal
 * @property {double} DBL_STEP_COLORSCREEN_BLUE_MIN=0.1 Internal
 * @property {double} DBL_STEP_COLORSCREEN_BLUE_MAX=0.1 Internal
 * @property {double} DBL_STEP_COLORSCREEN_MATCH=0.1 Internal
 * @property {double} DBL_STEP_COLORTOBW_PERCENT=1 Internal
 * @property {double} DBL_STEP_COMPOSITE3D_MULTIPLIER=0.1 Internal
 * @property {double} DBL_STEP_CONTRAST_MIDPOINT=0.1 Internal
 * @property {double} DBL_STEP_CONTRAST_PIXEL_ADJUST=0.1 Internal
 * @property {double} DBL_STEP_CONTRAST_DARK_ADJUST=0.1 Internal
 * @property {double} DBL_STEP_BRIGHTNESSCONTRAST_BRIGHTNESS_ADJUST=1 Internal
 * @property {double} DBL_STEP_BRIGHTNESSCONTRAST_CONTRAST_ADJUST=1 Internal
 * @property {double} DBL_STEP_CROP_OFFSET_X=0.1 Internal
 * @property {double} DBL_STEP_CROP_OFFSET_Y=0.1 Internal
 * @property {double} DBL_STEP_DIRBLUR_RADIUS=0.1 Internal
 * @property {double} DBL_STEP_DIRBLUR_ANGLE=1 Internal
 * @property {double} DBL_STEP_DIRBLUR_FALLOFF_RATE=0.1 Internal
 * @property {double} DBL_STEP_DITHER_MAGNITUDE=0.1 Internal
 * @property {double} DBL_STEP_EXTERNAL_NUM_PARAM=1 Internal
 * @property {double} DBL_STEP_FADE_TRANSPARENCY=1 Internal
 * @property {double} DBL_STEP_GRADIENT_OFFSET_Z=0.2 Internal
 * @property {double} DBL_STEP_GRAIN_NOISE=0.01 Internal
 * @property {double} DBL_STEP_GRAIN_SMOOTH=0.01 Internal
 * @property {double} DBL_STEP_MATTEBLUR_RADIUS=0.1 Internal
 * @property {double} DBL_STEP_MATTEBLUR_ANGLE=1 Internal
 * @property {double} DBL_STEP_MATTEBLUR_FALLOFF_RATE=0.1 Internal
 * @property {double} DBL_STEP_PIXELATE_FACTOR=0.001 Internal
 * @property {double} DBL_STEP_RADIALBLUR_RADIUS=0.1 Internal
 * @property {double} DBL_STEP_RAWELEMENT_AA_EXPONENT=1 Internal
 * @property {double} DBL_STEP_ELEMENT_MODULE_LINE_SMOOTHING_ERROR=1 Internal
 * @property {double} DBL_STEP_REFRACT_M=1 Internal
 * @property {double} DBL_STEP_REFRACT_B=1 Internal
 * @property {double} DBL_STEP_REFRACT_N=0.1 Internal
 * @property {double} DBL_STEP_REMTRANSPARENCY_THRESHOLD=1 Internal
 * @property {double} DBL_STEP_RESIZEMATTE_RADIUS=0.1 Internal
 * @property {double} DBL_STEP_VARBLUR_BLACK_RADIUS=0.1 Internal
 * @property {double} DBL_STEP_VARBLUR_WHITE_RADIUS=0.1 Internal
 * @property {double} DBL_STEP_SCALEATTR_X=0.01 Internal
 * @property {double} DBL_STEP_SCALEATTR_Y=0.01 Internal
 * @property {double} DBL_STEP_SCALEATTR_Z=0.01 Internal
 * @property {double} DBL_STEP_SCALEATTR_XY=0.01 Internal
 * @property {double} DBL_STEP_CAMERA_ANGLE=1 Internal
 * @property {double} DBL_STEP_CAMERA_FOV=0.5 Internal
 * @property {double} DBL_STEP_CAMERA_NEAR_PLANE=1 Internal
 * @property {double} DBL_STEP_CAMERA_FAR_PLANE=1 Internal
 * @property {double} DBL_STEP_ANGLE=1 Internal
 * @property {double} DBL_STEP_ANGLE_SKEW=1 Internal
 * @property {double} DBL_STEP_SET_FOCUS=0.1 Internal
 * @property {double} DBL_STEP_SCALE_LINE_THICKNESS=0.01 
 * @property {double} DBL_STEP_LINE_THICKNESS=0.1 
 * @property {double} DBL_STEP_GLUE_BIAS=0.1 Internal
 * @property {double} DBL_STEP_GLUE_TENSION=0.1 Internal
 * @property {double} DBL_STEP_NB_FRAMES_TAIL=1 Internal
 * @property {double} DBL_STEP_NB_SAMPLES=5 Internal
 * @property {double} DBL_STEP_FALLOFF=0.1 Internal
 * @property {double} DBL_STEP_BLURRINESS=0.1 Internal
 * @property {double} DBL_STEP_BLUR_VARIANCE=0.1 Internal
 * @property {double} DBL_STEP_RADIAL_BLUR_QUALITY=0.01 Internal
 * @property {double} DBL_STEP_INTERPOLATION=0.1 Internal
 * @property {double} STEP_TURBULENCE_FREQUENCY=0.1 Internal
 * @property {double} STEP_TURBULENCE_SEED=0.1 Internal
 * @property {double} STEP_TURBULENCE_EVOLUTION=0.1 Internal
 * @property {double} STEP_TURBULENCE_EVOLUTION_FREQUENCY=0.1 Internal
 * @property {double} STEP_TURBULENCE_GAIN=0.01 Internal
 * @property {double} STEP_TURBULENCE_LACUNARITY=0.01 Internal
 * @property {double} DBL_STEP_GAMMA_ADJUST=0.01 Internal
 * @property {double} DBL_STEP_COLOR_GAMMA=0.1 Internal
 * @property {double} DBL_STEP_LENGTH=0.1 Internal
 * @property {double} DBL_STEP_ASPECT_RATIO=0.1 Internal
 * @property {double} Z_PARTITION_RANGE=0.1 Internal
 * @property {string} FILE_SYSTEM_SAVED_PATH= Internal
 * @property {string} SCENE_LEVEL_SAVED_PATH= Internal
 * @property {string} NEW_SCENE_SAVED_PATH= Internal
 * @property {string} RECENT_SCENES_LIST= Internal
 * @property {double} DBL_STEP_CONSTRAINT_ACTIVE=1 Internal
 * @property {double} DBL_STEP_DYN_TENSION=1 Internal
 * @property {double} DBL_STEP_DYN_INERTIA=1 Internal
 * @property {double} DBL_STEP_CONSTRAINT_RATIO=1 Internal
 * @property {double} DBL_STEP_CONSTRAINT_RATIOFLOAT=0.1 Internal
 * @property {bool} DEBUG_VERIFY_DRAWING_FILES_EXIST=false Test that drawing files exist
 */

/**
 * Preferences in the General category.
 * @name preferences#General
 * @property {bool} ACCEPT_UNICODE_NAME=false Accept unicode name
 * @property {shortcut} OPEN_KEY=Ctrl+O Open
 * @property {shortcut} OPEN_ELEMENTS_KEY=Ctrl+E Open Elements
 * @property {shortcut} SAVE_ALL_KEY=Ctrl+S Save All
 * @property {shortcut} HELP_KEY=F1 Help
 * @property {shortcut} DELETE_KEY=Del Delete
 * @property {shortcut} DESELECT_ALL_KEY=Esc Deselect All
 * @property {shortcut} SELECT_ALL_KEY=Ctrl+A Select All
 * @property {bool} SAVE_SCENE=true Save Scene
 * @property {bool} SAVE_PALETTE_LISTS=true Save Palette Lists
 * @property {bool} SAVE_PALETTES=true Save Palettes
 * @property {bool} SAVE_DRAWINGS=true Save Drawings
 * @property {bool} AUTO_SAVE_LAYOUT=true Automatically Save Workspace
 * @property {bool} STAGE_AUTOSAVE_PROJECT_ENABLED=false Auto Save Scene
 * @property {bool} STAGE_AUTOSAVE_ASK_BEFORE=false Ask Before Auto Saving
 * @property {double} STAGE_AUTOSAVE_PROJECT_INTERVAL_MINUTES=10 Auto Save Interval
 * @property {double} STAGE_AUTOSAVE_PROJECT_INACTIVITY_DELAY_SECONDS=1 Auto Save Inactivity Interval
 * @property {bool} undefined=false Automatically save the scan drawing each time.
 * @property {double} DEFAULT_SCALE_FACTOR=1 Scale value for imported 3d models.
 * @property {bool} TB_PREVENT_OVERWRITE_OF_UNKNOWN_PLUGINS=false Prevent save if plugin nodes are unrecognized.
 * @property {bool} COMPRESS_KEY_FRAMES_ON_SAVE=true Compress key frames on save
 * @property {bool} FOCUS_ON_MOUSE_ENTER=true Focus On Mouse Enter
 * @property {bool} SHORTCUT_ZOOM_ON_MOUSE=false Shortcut Zooms On Mouse
 * @property {bool} AUTO_RENDER=true Automatic Render
 * @property {bool} INVERSE_CLOSE_PREVIOUS_EDITORS=false Close Previous Editors
 * @property {bool} SHOW_CONTROL_POINTS_ON_SELECTED_LAYERS=false Enables the automatic display of control points on selected layers
 * @property {bool} USE_OVERLAY_UNDERLAY_ART=true Enables the use of overlay and underlay arts
 * @property {bool} TIMELINE_REDUCE_INDENTATION=true Reduce the indentation of the timeline.
 * @property {bool} TIMELINE_SHOW_SCENE_MARKER=true Display the end of scene marker.
 * @property {bool} ADVANCED_DISPLAY_IN_VIEWS=true Shows the display selector in views
 * @property {bool} Z_ORDER_COMPATIBILITY_WITH_7_3=false Enables the z-order compatibility with version 7.3 or older.
 * @property {bool} RESTORE_SELECTED_DRAWING_ON_UNDO=false Restore the previously edited drawing when undoing commands
 * @property {bool} DISPLAY_ONLY_DIFFS_IN_MERGE_EDITOR=false Display only element differences in the merge editor.
 * @property {bool} CUSTOMIZE_GROUP_FUNCTIONALITY=false Customize the group node functionality.
 * @property {bool} PEG_ENFORCE_MINMAX_ANGLE=false Rotation Angle Enforced by Peg
 * @property {bool} PLAY_ENABLE_ANALOG_SCRUBBING=false Enable Analog Sound Scrubbing
 * @property {int} SOUND_ANALOG_JOG_SPEED=5 Analog Jog Speed
 * @property {int} SOUND_ANALOG_JOG_DAMPENING=10 Analog Jog Dampening
 * @property {bool} AUTO_APPLY=true Enable Auto Apply
 * @property {bool} AUTO_LOCK=true Enable Automatic Locking of Drawings
 * @property {bool} AUTO_LOCK_PALETTES=false Enable Automatic Getting the Rights to Modify of Palettes.
 * @property {bool} AUTO_LOCK_PALETTE_LISTS=true Enable Automatic Getting the Rights to Modify of Palette Lists.
 * @property {bool} PEG_DEFAULT_SEPARATE_POSITION=true Default Separate Position for Pegs
 * @property {bool} PEG_DEFAULT_SEPARATE_SCALE=true Default Separate Scale for Pegs
 * @property {bool} PEG_DEFAULT_BEZIER=true Default Bezier
 * @property {bool} PEG_DEFAULT_BEZIER_VELOCITY=true Default Bezier Velocity
 * @property {bool} READ_DEFAULT_SEPARATE_POSITION=true Default Separate Position for Elements
 * @property {bool} READ_DEFAULT_SEPARATE_SCALE=true Default Separate Scale for Elements
 * @property {bool} READ_USE_DRAWING_PIVOT=false Read use drawing pivot
 * @property {bool} RENDERER_CONSERVATIVETEXTUREMANAGEMENT=true Conservative Texture Management
 * @property {bool} RENDERER_SMOOTHTEXTURES=false Smooth Textures
 * @property {bool} CUSTOMIZE_RENDER_SCRIPTS=true Give access to full script customization interface.
 * @property {bool} OPENGL_ALTERNATE_CLEAR_STENCIL=false Alternate Clear Stencil
 * @property {int} OPENGL_MAX_TVG_TEXTURE_SIZE=1024 Maximum Texture Size for TVG
 * @property {int} OPENGL_MAXIMUM_MOVIE_TRACK_TEXTURE_SIZE=512 Maximum OpenGL Movie Track Preview Size
 * @property {bool} DISPLAY_CARD_COORDINATES=true Display Scalar or Cardinal Coordinates
 * @property {bool} DRAWING_CYCLE=true Cycle
 * @property {bool} EDITORS_ALWAYS_ON_TOP=true Editors always on top
 * @property {bool} DETACHED_HAVE_MENU_BAR=true Detached views have a menu bar
 * @property {bool} SNAP_KEYFRAME=false Snap Keyframe
 * @property {int} LEVELS_OF_UNDO=50 Levels of Undo
 * @property {int} RENDERER_TEXTUREREDUCTIONSIZE=2048 Texture Reduction Size
 * @property {double} MIN_FOV=1 Minimum FOV
 * @property {double} MAX_FOV=179 Maximum FOV
 * @property {double} FIELD_CHART_X=12 Field Chart X
 * @property {double} FIELD_CHART_Y=12 Field Chart Y
 * @property {double} FIELD_CHART_Z=12 Field Chart Z
 * @property {color} CURRENT_VIEW_BORDER_COLOR=#ff0000ff Current View Border Colour
 * @property {color} CURRENT_VIEW_BORDER_TEMPLATE_EDITION_COLOR=#00ff00ff Current View Border in Template Edit
 * @property {bool} SHOW_WELCOME_SCREEN_ON_STARTUP=true Show Welcome Screen on Startup
 * @property {bool} SHOW_WELCOME_IMAGE_ON_STARTUP=false Show Welcome Image on Startup
 * @property {bool} CREATE_BUNDLES=false On Mac OS X, determine if the new scene created are bundle.
 * @property {string} UNIX_HTML_BROWSER= HTML Browser for Unix
 * @property {bool} VECT_SHOW_STROKES=false Show the strokes
 * @property {color} EXPORTVIDDLG_BACKGROUND_COLOR=#ffffffff Export Video Bg Colour
 * @property {color} TIMECODE_BGCOLOR=#000000ff 
 * @property {color} TIMECODE_COLOR=#ffffffff 
 * @property {font} TIMECODE_FONT=arial 
 * @property {int} TIMECODE_HEIGHT=10 
 * @property {position} TIMECODE_POSITION=BOTTOM_CENTER 
 * @property {bool} SCRIPT_BUSY_WARNING=false Display script in progress warning
 * @property {int} VECTOR_LAYER_DEFAULT_RESOLUTION_FACTOR=100 Default vector layer resolution factor used when creating a new project.
 * @property {int} BITMAP_LAYER_DEFAULT_RESOLUTION_FACTOR=100 Default bitmap layer resolution factor used when creating a new project.
 * @property {int} BITMAP_LAYER_DEFAULT_CANVAS_WIDTH_FACTOR=200 Default bitmap layer canvas width factor used when creating a new project.
 * @property {int} BITMAP_LAYER_DEFAULT_CANVAS_HEIGHT_FACTOR=200 Default bitmap layer canvas height factor used when creating a new project.
 * @property {string} WEBCC_URL= Web Control Center URL
 * @property {bool} WEBCC_SSL_SELF_SIGNED=false Accept Web Control Center's self-signed certificate
 * @property {bool} ENGLISH_CONTEXT_SENSITIVE_HELP=false Enabling this displays all context sensitive help in english.
 * @property {bool} CAMERA_VIEW_DISABLE_RENDER_PREVIEW=false Disable the render preview buttons in the camera view status bar.
 * @property {bool} ENABLE_LOG_IO=false Used to enable the internal logging mechanism, to track file creation/removal.
 * @property {bool} ENABLE_MIDDLE_BUTTON_PANS_VIEW=false Used to enable the middle mouse button to pan Camera and Drawing views.
 * @property {TUDefaultColorEditorItem} DEFAULT_COLOR_EDITOR=separate Default Colour Editor
 * @property {int} SCR_EVENT_PROCESSING_INTERVAL=-1 Set an interval above zero to allow event processing while scripts are running.
 */

/**
 * Preferences in the Sceneplanning category.
 * @name preferences#Sceneplanning
 * @property {shortcut} SP_TOGGLE_SNAP_KEYFRAME=X Toggle Snap Keyframe
 * @property {bool} ELEMENT_CAN_BE_ANIMATED_DEFAULT_VALUE=false Default value of the can be animated flag on element node
 * @property {bool} SP_BBOX_HIGHLIGHTING=false Bounding Box Selection
 * @property {bool} SP_SHOW_LOCKED_DRAWINGS_IN_OUTLINE=false Show Locked Drawing in Outline
 * @property {bool} SP_CONSTANT_SEGMENT=true Constant Segments
 * @property {bool} SP_ENABLE_WASH_BACKGROUND=false Enable Wash Background in Sceneplanning
 * @property {bool} SP_ENABLE_WASH_BACKGROUND_DRAWING_MODE=false Enable Wash Background in Sceneplanning Drawing Mode
 * @property {double} SP_WASH_PREVIEW_PERCENTAGE=0.2 Dirty Preview: wash % (between 0.0-1.0)
 * @property {bool} SP_ENABLE_PREVIEW_WASH=false Enable Wash Background in Preview Mode
 * @property {bool} SP_USE_PIVOT_OFFSET_FOR_CONTROL_POINTS_SPLINE=true Use the current pivot for offset on the control points spline
 * @property {int} SP_THUMBNAIL_SIZE=64 Thumbnail Size
 * @property {bool} NV_ALTERNATE_WIDE_CABLE_APPREARANCE=true Two Colour Cables for Pass Through Connections
 * @property {int} SP_IK_NB_OF_ITERATIONS=20 Maximum number of iterations for IK
 * @property {bool} SP_IK_HIERARCHY_STOP_AT_FIRST_INTERSECTION=true Stop at first intersection for IK
 * @property {bool} SP_IK_HIERARCHY_ALL_CHAIN=false Advanced manipulation mode for IK
 * @property {int} SP_SMALL_FILES_RESOLUTION=1024 Resolution for small pixmaps files
 * @property {bool} SP_OVERRIDE_SMALL_FILES=true Decide if the resolution of the small bitmap files are overriden by the preference value.
 * @property {int} SP_WASH_BACKGROUND_PERCENTAGE=70 Wash Background Percentage
 * @property {double} SP_TV_SAFETY=0.1 Safe Area
 * @property {double} SP_ROTATION_CONTROL_SIZE=0.5 Rotation Control Size
 * @property {int} SP_TRANSFORM_TOOL_SIZE=200 Transform tools size in pixels
 * @property {int} SP_PIVOTS_AND_CONTROL_POINTS_SIZE=12 Pivots and control points size
 * @property {double} SP_PIVOT_SIZE_1=0.01 Pivot Size 1
 * @property {double} SP_PIVOT_SIZE_2=0.025 Pivot Size 2
 * @property {double} SP_PIVOT_SIZE_3=0.0025 Pivot Size 3
 * @property {double} SP_TENSION=0 Control Point Tension
 * @property {double} SP_CONTINUITY=0 Control Point Continuity
 * @property {double} SP_BIAS=0 Control Point Bias
 * @property {double} SP_SIDE_TOP_VIEW_DEFAULT_ZOOM=0.5 Top/Side View Default Zoom
 * @property {double} SP_IK_MAXIMUM_ERROR=0.01 Maximum error for IK
 * @property {double} SP_IK_OUT_OF_REACH_RETRY_INCREMENT=0.05 Retry increment for IK when it's out of reach.
 * @property {double} SP_TRANSLATE_SCALE_FACTOR=1 Sceneplanning nudge increment.
 * @property {color} SP_BORDER_COLOR=#262626ff Border Colour
 * @property {color} SP_CAMERA_COLOR=#242424ff Camera Colour
 * @property {color} SP_AXIS_COLOR=#ffffffff Axis Colour
 * @property {color} SP_SPLINE_COLOR=#ff7f00ff Spline Colour
 * @property {color} SP_CURRENT_FRAME_COLOR=#00ff00ff Current Colour
 * @property {color} SP_CONTROL_POINT_COLOR=#ffff00ff Control Point Colour
 * @property {color} SP_KEYFRAME_COLOR=#ff0000ff Keyframe Colour
 * @property {color} SP_PIVOT_DARK_COLOR=#335faaff Dark Pivot Colour
 * @property {color} SP_PIVOT_LIGHT_COLOR=#c1d8ffff Light Pivot Colour
 * @property {color} SP_PEG_PIVOT_DARK_COLOR=#aa5f33ff Dark Peg Pivot Colour
 * @property {color} SP_PEG_PIVOT_LIGHT_COLOR=#ffd8c1ff Light Peg Pivot Colour
 * @property {color} SP_ROTATION_CONTROL_COLOR_1=#ff0000ff Rotation Control Colour 1
 * @property {color} SP_ROTATION_CONTROL_COLOR_2=#00ff00ff Rotation Control Colour 2
 * @property {color} SP_SCALE_CONTROL_COLOR=#ff0000ff Scale Control Colour
 * @property {color} SP_SKEW_CONTROL_COLOR=#ff0000ff Skew Control Colour
 * @property {color} SP_IK_CONTROL_COLOR=#ff0000ff IK Control Colour
 * @property {color} SP_IK_MIN_CONTROL_COLOR=#00ff00ff IK Min Control Colour
 * @property {color} SP_IK_MAX_CONTROL_COLOR=#ff0000ff IK Max Control Colour
 * @property {CX_FullAnimationModeIds} SP_ANIMATION_MODE=KEYFRAME_MODE Default Sceneplanning Mode
 * @property {TUFrameViewDefaultZoomItem} SP_FRAME_VIEW_DEFAULT_ZOOM=Fit to View Default Camera View Default Zoom
 * @property {bool} SP_TRANSFORM_TOOL_CREATE_ALL_KEYFRAMES=true Transform Tool create keyframe on all functions
 * @property {bool} SP_TRANSFORM_TOOL_FORCE_KEY_FRAME_AT_FRAME_ONE=true Transform Tool create keyframe at frame one
 * @property {bool} CAMERA_PASTE_FORCE_KEY_FRAME=true Pasting creates start/end keyframes
 * @property {bool} DRAWING_TOOL_BAR_FLAT=false Drawing Tools tool bar will appear flat and customizable.
 * @property {bool} DARK_STYLE_SHEET=true Use a dark look.
 * @property {bool} TB_USE_TOUCH_INTERFACE=false Enable the gestural touch interface for the OpenGL views.
 * @property {bool} TB_TOUCH_INVERT_SCROLL=false Invert the scroll direction.
 * @property {double} TB_TOUCH_SPEED=2 Touch Sensitivity.
 * @property {bool} USE_QT_WINTAB=true Use Qt built in Wintab API
 */

/**
 * Preferences in the Timeline category.
 * @name preferences#Timeline
 * @property {bool} TIMELINE_SHOW_SOUND=true Show Sound Layers
 * @property {bool} TIMELINE_SHOW_SOUND_WAVEFORMS=true Show Sound Waveforms
 * @property {bool} TIMELINE_SHOW_GROUP=true Show Group Layers
 * @property {bool} TIMELINE_SHOW_EFFECT=true Show Effect Layers
 * @property {bool} TIMELINE_SHOW_COMPOSITE=true Show Composite Layers
 * @property {bool} TIMELINE_PASTE_FORCE_KEY_FRAME=true Pasting creates start/end keyframes
 * @property {color} TIMELINE_MARK_KEY_DRAWING_COLOR=#ff0000ff Colour of the key drawing marker.
 * @property {color} TIMELINE_MARK_BREAK_DRAWING_COLOR=#0091ffff Colour of the break drawing marker.
 */

/**
 * Preferences in the Node View category.
 * @name preferences#Node View
 * @property {bool} NV_WORLD_VIEW_STARTING_STATE=true World View Starting State
 * @property {color} NV_BACKGROUND_COLOR=#787878ff Background Colour
 * @property {int} NV_DEFAULT_THUMBNAIL_RESOLUTION=64 Default thumbnail resolution
 * @property {color} NV_DEFAULT_THUMBNAIL_BACKGROUND_COLOR=#ffffffff Default thumbnail background color
 * @property {color} NV_PROXY_PORT_LIGHT_COLOR=#cacacaff Proxy Port Light Colour
 * @property {color} NV_PROXY_PORT_DARK_COLOR=#5e5e5eff Proxy Port Dark Colour
 * @property {color} NV_MODULE_LIGHT_COLOR=#4678baff Node Light Colour
 * @property {color} NV_MODULE_DARK_COLOR=#3a4a87ff Node Dark Colour
 * @property {color} NV_MODULE_SHADOW_COLOR=#000000ff Node Shadow Colour
 * @property {color} NV_MODULE_EDITOR_LIGHT_COLOR=#ffea4cff Node Editor Button Light Colour
 * @property {color} NV_MODULE_EDITOR_DARK_COLOR=#a0911eff Node Editor Button Dark Colour
 * @property {color} NV_MODULE_DISPLAY_LIGHT_COLOR=#f0f9f8ff Node Display Light Colour
 * @property {color} NV_MODULE_DISPLAY_DARK_COLOR=#bac6c8ff Node Display Dark Colour
 * @property {color} NV_MODULE_GROUP_LIGHT_COLOR=#c3e0f8ff Group Light Colour
 * @property {color} NV_MODULE_GROUP_DARK_COLOR=#768896ff Group Dark Colour
 * @property {color} NV_MODULE_MOVE_LIGHT_COLOR=#8bbe55ff Move Nodes Light Colour
 * @property {color} NV_MODULE_MOVE_DARK_COLOR=#576a36ff Move Nodes Dark Colour
 * @property {color} NV_MODULE_IO_LIGHT_COLOR=#7399c3ff I/O Nodes Light Colour
 * @property {color} NV_MODULE_IO_DARK_COLOR=#304262ff I/O Nodes Dark Colour
 * @property {color} NV_MODULE_NO_FLATTEN_LIGHT_COLOR=#7292e2ff Composite Nodes Light Colour When Not Flattening the Output
 * @property {color} NV_MODULE_NO_FLATTEN_DARK_COLOR=#313c66ff Composite Nodes Dark Colour When Not Flattening the Output
 * @property {color} NV_MODULE_CAMERA_LIGHT_COLOR=#9dd3c9ff Camera Nodes Light Colour
 * @property {color} NV_MODULE_CAMERA_DARK_COLOR=#719798ff Camera Nodes Dark Colour
 * @property {color} NV_PORT_MATRIX_LIGHT_COLOR=#7fc820ff Peg Port Light Colour
 * @property {color} NV_PORT_MATRIX_DARK_COLOR=#465f2aff Peg Port Dark Colour
 * @property {color} NV_PORT_IMAGE_LIGHT_COLOR=#3dadddff Image Port Light Colour
 * @property {color} NV_WIDE_CABLE_INNER_COLOR=#286eb4ff Wide Cable Inner Line
 * @property {color} NV_PORT_IMAGE_DARK_COLOR=#31445aff Image Port Dark Colour
 * @property {color} NV_PORT_KEEP_IMAGE_LIGHT_COLOR=#e6d72eff Flagged Nodes Image Port Light Colour
 * @property {color} NV_PORT_KEEP_IMAGE_DARK_COLOR=#967929ff Flagged Nodes Image Port Dark Colour
 * @property {color} NV_Z_PORT_LIGHT_COLOR=#4be6e6ff Output Z Input Port Light Colour
 * @property {color} NV_Z_PORT_DARK_COLOR=#2d8282ff Output Z Input Port Dark Colour
 * @property {color} NV_MODULE_GROUP_EFFECT_LIGHT_COLOR=#ffbe22ff Node Group Effect Light Colour
 * @property {color} NV_MODULE_GROUP_EFFECT_DARK_COLOR=#b78818ff Node Group Effect Dark Colour
 * @property {double} NV_MAGNIFIER_SCALE_FACTOR=5 Zoom Factor
 * @property {double} NV_MAGNIFIER_WIDTH_MULTIPLE=6 Zoom Factor
 * @property {double} NV_MAGNIFIER_ASPECT_RATIO=1.5 Aspect Ratio
 * @property {double} NV_MAGNIFIER_OPACITY=80 Opacity
 * @property {TUDirectionFlagsItem} NV_PORT_IN_ORDERING=RIGHT_TO_LEFT Port Input Ordering
 * @property {TUDirectionFlagsItem} NV_PORT_OUT_ORDERING=RIGHT_TO_LEFT Port Output Ordering
 * @property {TUCableTypeItem} NV_CABLE_TYPE=BEZIER Cable Type
 * @property {TUCornerTypeItem} NV_WORLD_VIEW_STARTING_CORNER=SE World View Starting Corner
 * @property {double} NV_ANTIALIASING_EXPONENT=1 Value of Antialiasing Exponent
 * @property {TUAntialiasQualityItem} NV_ANTIALIASING_QUALITY=HIGH Setting of Antialiasing Quality
 * @property {TUAlignmentRuleItem} NV_ALIGNMENT_RULE=CENTER_FIRST_PAGE Alignment Rule
 * @property {TUUseDrawingPivotMethodItem} NV_EMBEDDED_PIVOT=APPLY_ON_READ_TRANSFORM Embedded Pivot
 * @property {TUPremultiplyItem} NV_TRANSPARENCY_TYPE=N Transparency Type
 * @property {bool} NV_ENABLE_EXTERNAL_READ=false Enables the NV_EXTERNAL_READ_THRESHOLD preference
 * @property {bool} NV_READ_COLOR=true Read Colour
 * @property {bool} NV_READ_TRANSPARENCY=true Read Transparency
 * @property {double} NV_EXTERNAL_READ_THRESHOLD=1.5 Size threshold of input image to use external read node compute.
 * @property {double} NV_COLOR_CARD_Z_OFFSET=-12 The Z offset default value of colour card.
 * @property {bool} NV_PAN_ON_MIDDLE_MOUSE_BUTTON=true Pan on Middle Mouse
 * @property {bool} NV_DOUBLE_CLICK_OPENS_EDITOR=false Double Mouse Click opens Editor
 * @property {TUDrawingModeItem} NV_OVERLAY_VECTORBITMAP=Vector Sets Overlay Art to either Bitmap or Vector
 * @property {TUDrawingModeItem} NV_LINEART_VECTORBITMAP=Vector Sets Line Art to either Bitmap or Vector
 * @property {TUDrawingModeItem} NV_COLOURART_VECTORBITMAP=Vector Sets Colour Art to either Bitmap or Vector
 * @property {TUDrawingModeItem} NV_UNDERLAY_VECTORBITMAP=Vector Sets Underlay to either Bitmap or Vector
 * @property {bool} COMPOSITE_DEFAULT_PASS_THROUGH=true Default Pass Through Composite
 */

/**
 * Preferences in the Exposure Sheet category.
 * @name preferences#Exposure Sheet
 * @property {int} XSHEET_DEFAULT_COLUMN_WIDTH=100 Default Column Width
 * @property {int} XSHEET_MIN_ZOOM=5 Xsheet Minimum Zoom Level
 * @property {int} XSHEET_MAX_ZOOM=16 Xsheet Maximum Zoom Level
 * @property {bool} XSHEET_NAME_BY_FRAME=false When enabled, new drawings will be named based on the current frame position, otherwise drawings will be named based on creation order.
 * @property {bool} XSHEET_APPLYNEXT_LEFTRIGHT=false Edit Columns Left to Right
 * @property {bool} XSHEET_APPLYNEXT_RIGHTLEFT=true Edit Columns Right to Left
 * @property {bool} XSHEET_SHOW_SELECTION=false Show Selection
 * @property {bool} XSHEET_SHOW_DRAWING_COLS=true Show Drawing Columns
 * @property {bool} XSHEET_SHOW_FUNCTION_COLS=true Show Function Columns
 * @property {bool} XSHEET_SHOW_3DPATH_COLS=true Show 3D Path Columns
 * @property {bool} XSHEET_SHOW_3DROTATION_COLS=true Show 3D Rotation Columns
 * @property {bool} XSHEET_SHOW_SOUND_COLS=true Show Sound Columns
 * @property {bool} XSHEET_SHOW_ANNOTATION_COLS=true Show Annotation Columns
 * @property {bool} XSHEET_ANNOTATION_FRAME_MARKER=false Show Frame Marker in Annotation Columns
 * @property {double} XS_ANNOTATION_HARDNESS=10 Annotation Column Antialiasing Value
 * @property {color} XSHEET_BACKGROUND_COLOR_DARK=#171717ff Background Colour
 * @property {color} XSHEET_BACKGROUND_COLOR=#cbcbcbff Background Colour
 * @property {color} XSHEET_CURRENT_FRAME_COLOR=#5d5d5dff Current Frame Colour
 * @property {color} XSHEET_FRAME_BEAT_COLOR=#0000faff Frame per beat Colour
 * @property {color} XSHEET_BEAT_BAR_COLOR=#fa0000ff Beat Per bar Colour
 * @property {color} XSHEET_CURRENT_DRAWING_COLOR=#8a0000ff Current Drawing Colour
 * @property {color} XSHEET_LIGHT_TABLE_COLOR=#f2d5d1ff Light Table Colour
 * @property {color} XSHEET_ONION_SKIN_COLOR=#b6d7f7ff Onion Skin Colour
 * @property {int} XSHEET_DEFAULT_HOLD_VALUE=1 Xsheet Default Hold Value
 * @property {bool} XSHEET_GESTURAL_DRAG_ENABLED=true Xsheet Gestural Drag
 * @property {bool} XSHEET_CENTRE_ON_CURRENT_FRAME=false Xsheet Centre on Current Frame
 * @property {color} XSHEET_STOP_MOTION_KEYFRAME_COLOR=#8c0000ff Xsheet Stop-Motion Keyframe Colour
 * @property {color} DRAWING_TV_COLOR=#ffffffff Drawing Column Colour
 * @property {color} TIMING_TV_COLOR=#f5dcb9ff Timing Column Colour
 * @property {color} 3D_PATH_TV_COLOR=#dededeff 3D Path Column Colour
 * @property {color} BEZIER_TV_COLOR=#c7c6bbff Bezier Column Colour
 * @property {color} VELOBASED_TV_COLOR=#f5fff0ff Velobased Column Colour
 * @property {color} EASE_TV_COLOR=#d5cdc3ff Ease Column Colour
 * @property {color} EXPR_TV_COLOR=#c4d1dfff Expression Column Colour
 * @property {color} SOUND_TV_COLOR=#8a8a8aff Sound Column Colour
 * @property {color} ANNOTATION_TV_COLOR=#ffffffff Annotation Column Colour
 * @property {TUXSheetAddColumnsItem} XSHEET_ADD_COLUMNS=BOTTOM Default Xsheet insertion option
 * @property {int} XSHEET_LINE_HOLD=3 Threshold exposure for hiding the holding line.
 */

/**
 * Preferences in the Color Management category.
 * @name preferences#Color Management
 * @property {bool} COLOR_ENABLE_INTERACTIVE_COLOR_RECOVERY=true Enable Interactive Colour Recovery
 * @property {bool} COLOR_ENABLE_COLOR_RECOVERY=true Enable Colour Recovery
 * @property {bool} IS_SWATCH_MODE=false Use swatch mode to display the palettes
 * @property {bool} IS_BITMAP_SWATCH_MODE=true Use swatch mode to display the bitmap palettes
 * @property {bool} SB_IS_HSV_MODE=true Colour view sliders displayed in HSV mode.
 * @property {bool} SYNC_VECTOR_WITH_BITMAP_COLOUR=false Attempt to maintain sync between the selected vector and bitmap colour
 * @property {bool} COLOR_USE_ELEMENT_PALETTE_LIST=false Use element palette lists.
 * @property {color} COLOR_REPLACEMENT_COLOR=#ff0000ff Replacement Colour
 */

/**
 * Preferences in the Drawing Mode category.
 * @name preferences#Drawing Mode
 * @property {bool} DRAWING_CREATE_EXTEND_EXPOSURE=true When a new drawing is created, automatically extend the exposure of previous drawings
 * @property {shortcut} DRAWING_COLOR_DROPPER_TOOL_KEY=Alt+D Dropper Tool
 * @property {shortcut} DRAWING_ZOOM_TOOL_KEY=Alt+Z Zoom Tool
 * @property {TUSideTypeItem} DRAWING_VIEW_THUMBNAILS_LOCATION=LEFT Thumbnail View location
 * @property {bool} DRAWING_VIEW_DO_NOT_ZOOM_WHEN_RESIZE=true The Drawing View Does not Zoom When Resized
 * @property {bool} DRAWING_GRID_ON_BY_DEFAULT=false Grid On By Default
 * @property {bool} DRAWING_LIGHTTABLE_ENABLE_SHADE=true Light Table: Enable Shade
 * @property {bool} DRAWING_LIGHTTABLE_ENABLE_SHADE_FRAME_VIEW=true Shade other drawing in camera view
 * @property {bool} DRAWING_ENHANCED_ONION_SKIN=false Shows Auto Light Table on Every Drawing Visible in the Onion Skin
 * @property {bool} DRAWING_AUTOSAVE_PENSTYLE=true Auto Save Pencil Styles
 * @property {bool} DRAWING_USE_ROTATION_LEVER=false Use Rotation Lever Handle for Select Tool and Transform Tool.
 * @property {TUOnionSkinRenderModeItem} DRAWING_ONIONSKIN_RENDER_MODE=SHADE Onion Skin Render Mode (Normal, Shade or Outline) 
 * @property {TUOnionSkinDrawingModeItem} DRAWING_ONIONSKIN_DRAWING_MODE=byFrames Onion Skin Drawing Mode (byFrames or byDrawing) 
 * @property {bool} DRAWING_SELECT_TOOL_IS_LASSO=true Select Tool Is Lasso
 * @property {bool} TOOL_BOUNDING_BOX_MOVABLE=false Select Tool Bounding Box is Movable
 * @property {bool} DRAWING_SYNCHRONIZE_ERASER=false Synchronize Eraser
 * @property {bool} DRAWING_DEFAULT_COLOR_PICKER_IS_MULTIWHEEL=false Default Colour Picker interface is Multiwheel
 * @property {bool} DRAWING_MOUSEMOVE_INTERPOLATION=true Interpolates the input points from the tablet (or the mouse) to generate a smooth curve.
 * @property {DT_StabilizerMode} DRAWING_STABILIZER_MODE=NoStabilizer 
 * @property {DT_StabilizerMode} DRAWING_STABILIZER_ACTIVE_MODE=NoStabilizer 
 * @property {bool} DRAWING_BRUSH_SIZE_CURSOR_ON=false Display real brush cursor
 * @property {bool} DRAWING_NEW_COLOR=false Create the new colour in the palette
 * @property {bool} DRAWING_TOOL_MODE_OVERRIDE=true Tool overrides may also change internal tool mode
 * @property {bool} DRAWING_SHOW_CURRENT_DRAWING_ON_TOP=false Show current drawing on top.
 * @property {bool} DRAWING_STICKY_EYEDROPPER=false Sticky Eyedropper
 * @property {int} DRAWING_CLOSE_GAP_VALUE=0 Auto Gap Closing on Startup
 * @property {bool} DRAWING_CLOSE_GAP_VALUE_IN_PIXEL=true Auto Gap Closing in Pixel Unit.
 * @property {double} DRAWING_MORPHING_QUALITY=0.2 Morphing quality
 * @property {int} DRAWING_PENCIL_TO_BRUSH_CANVAS_SIZE=4096 Pencil to Brush vectorization canvas size.
 * @property {double} DRAWING_ONIONSKIN_MINIMUM_WASH_PERCENT=0.4 Onion Skin : Minimum Wash Value (0.0-1.0)
 * @property {double} DRAWING_ONIONSKIN_MAXIMUM_WASH_PERCENT=0.8 Onion Skin : Maximum Wash Value (0.0-1.0)
 * @property {double} DRAWING_ONIONSKIN_MIN_OPACITY=0.2 This preference controls the minimum % of opacity for the onion skin.
 * @property {double} DRAWING_ONIONSKIN_MAX_OPACITY=0.8 This preference controls the maximum % of opacity for the onion skin.
 * @property {double} DRAWING_LIGHTTABLE_OPACITY=0.5 This preference controls the % of opacity for the light table.
 * @property {double} DRAWING_LIGHTTABLE_WASH=0.2 Light Table: wash % (between 0.0-1.0)
 * @property {double} DRAWING_PENCIL_LINES_OPACITY=100 Pencil Lines Opacity: (between 0 and 100)
 * @property {color} DRAWING_BACKLITE_COLOR=#3e4c7dff Backlight Colour
 * @property {double} DRAWING_HIGHLIGHT_COLOR_ALPHA=1 Colour Highlight Mode Opacity
 * @property {color} DRAWING_BACKGROUND_DARK=#e1e1e1ff Background Colour
 * @property {color} DRAWING_BACKGROUND=#ffffffff Background Colour
 * @property {color} BRUSH_PREVIEW_BACKGROUND_DARK=#e1e1e1ff Brush Preview Background Colour
 * @property {color} BRUSH_PREVIEW_BACKGROUND=#ffffffff Brush Preview Background Colour
 * @property {color} DRAWING_GRID_COLOR=#8c8c8cff Grid Colour
 * @property {color} DRAWING_ONION_SKIN_COLOR_AFTER=#377837ff Onion Skin: Colour After
 * @property {color} DRAWING_ONION_SKIN_COLOR_BEFORE=#ff0000ff Onion Skin: Colour Before
 * @property {color} DRAWING_ONION_SKIN_COLOR_PREVELEMENT1=#bc7d00ff Onion Skin: Colour Previous Element
 * @property {color} DRAWING_ONION_SKIN_COLOR_PREVELEMENT2=#e19600ff Onion Skin: Colour Previous 2nd Element
 * @property {color} DRAWING_ONION_SKIN_COLOR_PREVELEMENT3=#f8c800ff Onion Skin: Colour Previous 3rd Element
 * @property {color} DRAWING_ONION_SKIN_COLOR_PREVELEMENT4=#ffea00ff Onion Skin: Colour Previous 4th Element
 * @property {color} DRAWING_ONION_SKIN_COLOR_NEXTELEMENT1=#0000ffff Onion Skin: Colour Next Element
 * @property {color} DRAWING_ONION_SKIN_COLOR_NEXTELEMENT2=#3b58ffff Onion Skin: Colour Next 2nd Element
 * @property {color} DRAWING_ONION_SKIN_COLOR_NEXTELEMENT3=#87afffff Onion Skin: Colour Next 3rd Element
 * @property {color} DRAWING_ONION_SKIN_COLOR_NEXTELEMENT4=#c1d7ffff Onion Skin: Colour Next 4th Element
 * @property {bool} DRAWING_ADJUST_PIXEL_RESOLUTION_TO_CAMERA_FOR_NEW_DRAWINGS=false Pixel Density Proportional to Camera
 * @property {color} PALETTE_MANAGER_COLOR=#ffffffff Palette Manager Background Colour
 * @property {color} PALETTE_MANAGER_COLOR_DARK=#171717ff Palette Manager Background Colour
 * @property {color} CAMERA_VIEW_DRAWING_TOOL_LABEL_COLOR=#f2f2c8ff Camera View Label Colour
 * @property {color} DRAWING_NEW_COLOR_DEFAULT_VALUE=#464646ff Drawing Mode: New Default Colour
 * @property {TUDrawingToolItem} DRAWING_INITIAL_TOOL=Close Gap Initial Drawing Tool
 * @property {TUDrawingToolItem} PAINT_MODE_DRAWING_INITIAL_TOOL=PAINT Initial Drawing Tool
 * @property {color} DRAWING_SMOOTH_BRUSH_COLOR=#ffff00ff Overlay brush colour used with smoothing tool.
 * @property {bool} DT_SELECT_TOOL_SNAP_TO_GRID=true Select tool can snap to grid.
 * @property {bool} DT_CONTOUR_EDITOR_SNAP_AND_ALIGN=true Contour Editor tool can snap and align to boxes.
 * @property {bool} DT_CONTOUR_EDITOR_TOOL_SNAP_TO_GRID=true Contour Editor tool can snap to grid.
 * @property {bool} DT_SHAPE_TOOL_SNAP_TO_GRID=true Shape tools can snap to grid.
 * @property {bool} DT_PIVOT_TOOL_SNAP_TO_GRID=true Pivot tool can snap to grid.
 * @property {bool} DRAWING_ENABLE_PAPER_ZOOM=false Paper zoom flag.
 * @property {double} DRAWING_PAPER_ZOOM_PIXELS_PER_INCH=72 Paper zoom number of pixels per inch (ppi).
 * @property {int} DRAWING_PAPER_ZOOM_MAX_ZOOM=4 Paper zoom maximum zoom level.
 * @property {double} DRAWING_PAPER_ZOOM_MAGNIFY_ZOOM=2 Magnifier zoom factor.
 * @property {int} DRAWING_PAPER_ZOOM_MAGNIFY_WIDTH=150 Magnifier zoom window width.
 * @property {int} DRAWING_PAPER_ZOOM_MAGNIFY_HEIGHT=150 Magnifier zoom window height.
 * @property {int} DRAWING_PAPER_ZOOM_MAGNIFY_OFFSETX=-90 Magnifier zoom window horizontal offset.
 * @property {int} DRAWING_PAPER_ZOOM_MAGNIFY_OFFSETY=90 Magnifier zoom window vertical offset.
 * @property {double} QUICK_ZOOM_MAGNIFY_ZOOM=4 Quick Close Up zoom factor.
 * @property {DT_PencilTipModeItem} DRAWING_CUTTER_TIP_MODE=BevelTip 
 * @property {DT_PencilTipModeItem} DRAWING_CONTOUR_EDITOR_TIP_MODE=RoundTip 
 * @property {DT_PencilTipModeItem} DRAWING_ERASER_TIP_MODE=BevelTip 
 * @property {DT_PencilTipModeItem} DRAWING_INK_TIP_MODE=BevelTip 
 */

/**
 * Preferences in the Highlighting category.
 * @name preferences#Highlighting
 * @property {double} NODE_HIGHLIGHT_INTENSITY=0.3 Node Intensity
 * @property {double} CURRENT_FRAME_HIGHLIGHT_INTENSITY=0.3 Current Frame Intensity
 * @property {double} ALL_FRAMES_HIGHLIGHT_INTENSITY=0.3 All Frames Intensity
 * @property {double} FRAME_RANGE_HIGHLIGHT_INTENSITY=0.3 Frame Range Intensity
 * @property {double} SPLINE_POSITION_HIGHLIGHT_INTENSITY=0.3 Spline Position Intensity
 * @property {color} NODE_HIGHLIGHT_COLOR=#0000ffff Node Colour
 * @property {color} ELEMENT_HIGHLIGHT_COLOR=#ff00ffff Element Colour
 * @property {double} ELEMENT_HIGHLIGHT_INTENSITY=0.3 Element Intensity
 * @property {color} CURRENT_FRAME_HIGHLIGHT_COLOR=#ffff00ff Current Frame Colour
 * @property {color} FRAME_RANGE_HIGHLIGHT_COLOR=#00ff00ff Range Frame Colour
 * @property {color} ALL_FRAMES_HIGHLIGHT_COLOR=#ff0000ff All Frames Colour
 */

/**
 * Preferences in the Element Manager category.
 * @name preferences#Element Manager
 * @property {int} SCAN_TYPE=2 Scan Type
 * @property {string} PIXMAP_FORMAT=SCAN Pixmap Format
 * @property {bool} ADVANCED_ELEMENT_TRADITIONAL=false Advanced Element Properties
 * @property {bool} ADVANCED_ELEMENT_BASIC_ANIMATE=false More advanced element property than essentials
 * @property {bool} ADVANCED_ELEMENT_AUTO_RENAME=true Automatically rename an element when renaming the node/layer referencing that element
 */

/**
 * Preferences in the Function Editor category.
 * @name preferences#Function Editor
 * @property {bool} FE_GRID_ON=true Show Grid
 * @property {int} FE_LOAD_LIMIT=50 Number of functions displayed in the canvas.
 * @property {bool} FE_3DPATH_CONST_Z_DEFAULT=false 3D Path Constant Z Default
 * @property {color} FE_BG_COLOR=#787878ff Background Colour
 * @property {color} FE_GRID_COLOR=#888888ff Grid Colour
 * @property {color} FE_BG_CURVE_COLOR=#b4b4b4ff Background Curve Colour
 * @property {color} FE_BG_X_CURVE_COLOR=#ff0000ff Background X Curve Colour
 * @property {color} FE_BG_Y_CURVE_COLOR=#00ff00ff Background Y Curve Colour
 * @property {color} FE_BG_Z_CURVE_COLOR=#0000ffff Background Z Curve Colour
 * @property {color} FE_BG_VELO_CURVE_COLOR=#b4b4b4ff Background velocity Curve Colour
 * @property {color} FE_FG_CURVE_COLOR=#000000ff Foreground Curve
 */

/**
 * Preferences in the Library category.
 * @name preferences#Library
 * @property {bool} LIBRARY_AUTO_GENERATE_THUMBNAILS=true Auto Generate Thumbnails
 * @property {bool} LIBRARY_PASTE_CREATE_NEW_DRAWING=false Create new drawings
 * @property {TUPaletteOperationItem} LIBRARY_PASTE_PALETTE=USE_COPY Template palette operation preferences
 */

/**
 * Preferences in the Playback View category.
 * @name preferences#Playback View
 * @property {bool} PLAY_ENABLE_SOUND=false Enable sound
 * @property {bool} PLAY_ENABLE_SCRUBBING=false Enable sound scrubbing
 * @property {bool} PLAY_ENABLE_PREROLL=false Enable preroll playback
 * @property {int} PLAY_PREROLL_FRAMES=24 Set number of preroll frames
 * @property {bool} PLAY_ENABLE_LOOP=false Enable loop playback
 */

/**
 * Preferences in the Scanning category.
 * @name preferences#Scanning
 * @property {int} SCANNING_PEGGING=2 Pegging mode of the scanner
 * @property {int} SCANNING_PEGSIDE=0 Side of the peg
 * @property {int} SCANNING_DPI=300 Scanning dpi value
 * @property {double} SCANNING_GAMMA=1.05 Gamma value
 * @property {int} SCANNING_THRESHOLD=100 The threshold value from 1 to 255
 * @property {int} SCANNING_WHITEPOINT=190 The white point value from 1 to 255
 * @property {int} SCANNING_BLACKPOINT=70 The black point value from 1 to 255
 * @property {int} SCANNING_SCANNER=0 
 * @property {int} SCANNING_PAPERSIZE=1 Paper size of the scanned object
 * @property {bool} SCANNING_OPTREG=true The optical registration value
 * @property {bool} SCANNING_FLIPDRAWING=false Do we flip the drawing
 * @property {bool} SCANNING_SCANANDADVANCE=false Advance to the next frame
 * @property {bool} SCANNING_OVERDRAWING=false Do we overwrite drawing?
 * @property {int} SCANNING_SCANDEPTH=0 Scan depth
 * @property {string} SCANNING_SCANNER_NAME= Scanner name
 */

/**
 * Preferences in the Render category.
 * @name preferences#Render
 * @property {bool} SOFT_RENDER_ENABLE_BLUR=true Enable blur.
 * @property {bool} SOFT_RENDER_ENABLE_LINE_TEXTURE=true Enable line texture.
 * @property {bool} SOFT_RENDER_ENABLE_FOCUS=true Enable focus.
 * @property {int} SOFT_RENDER_IMAGE_MEMORY_PERCENT=25 Cache size for intermediate preview images (percentage of system RAM)
 * @property {string} SOFT_RENDER_CACHE_PATH= Cache path and size on disk for intermediate preview images
 * @property {bool} SOFT_RENDER_ENABLE_DISK_CACHE=false Enable the cache on disk for intermediate preview images
 * @property {int} SOFT_RENDER_THREADS=0 Number of rendering threads for all type of soft rendering. A value of zero automatically sets the number of threads based on the number of CPU cores. 
 * @property {bool} SOFT_RENDER_GPU=true Enable the GPU
 * @property {bool} SOFT_RENDER_LOAD_OPENCL=true Enable the GPU (requires a restart of the application)
 * @property {bool} RENDER_ENABLE_TONE_AND_HIGHLIGHT=true Disabling this will produce a drawing performance improvement in the OpenGL views.
 * @property {bool} RENDER_ENABLE_CUTTER=true Disabling cutters and mask effects will produce a drawing performance improvement in the openGL views.
 * @property {bool} RENDER_ENABLE_TEXTURES_AND_GRADIENTS_IN_DRAWINGS=true Disabling this will produce a drawing performance improvement in the OpenGL views.
 * @property {bool} RENDER_ENABLE_TEXTURES_IN_PENCIL_LINES=true Disabling this will produce a drawing performance improvement in the OpenGL views.
 * @property {bool} RENDER_ENABLE_COLOUR_OVERRIDE=true Disabling this will produce a drawing performance improvement in the OpenGL views.
 * @property {bool} RENDER_ENABLE_VARIABLE_LINE_THICKNESS=false Disabling this will produce a drawing performance improvement in the OpenGL views.
 * @property {bool} RENDER_ENABLE_GLUE_MODULE=true 
 * @property {bool} OPENGL_ENABLE_PLAYBACK_CACHE=true Enable image caching for opengl playback
 * @property {int} OPENGL_PLAYBACK_CACHE_SIZE_MB=2000 Cache size for playback images in Mb
 * @property {bool} OPENGL_ENABLE_CACHELOCK_NODE=true Enable rendering caching of GL cache lock nodes
 * @property {int} OPENGL_LOCK_NODE_CACHE_SIZE_MB=128 Cache size for OpenGL lock node caching in Mb
 * @property {bool} OPENGL_ENABLE_COMPOSITE_NODE_CACHE=true Enable rendering caching of non-passthrough composite nodes
 * @property {int} OPENGL_COMPOSITE_NODE_CACHE_SIZE_MB=256 Cache size for OpenGL composite node caching in Mb
 * @property {bool} OPENGL_ENABLE_CAMERAVIEW_CACHE=false Enable rendering caching of camera view
 * @property {bool} OPENGL_ENABLE_PERSISTENT_CACHE_NODE=true Enable rendering caching of persistent cache nodes
 * @property {int} OPENGL_RIG_CACHE_SIZE_MB=2048 Maximum size used by the OpenGL Node Cache in RAM
 * @property {int} OPENGL_RIG_CACHE_DISK_SIZE_MB=10240 Maximum size used by the OpenGL Node Cache on disk
 * @property {bool} OPENGL_RIG_CACHE_WAL_MODE=false WAL journal mode used by the OpenGL Node Cache on disk
 * @property {bool} OPENGL_SUPPORT_TRIPLE_BUFFER=true Support triple buffering
 * @property {bool} OPENGL_SUPPORT_DESKTOP_EFFECTS=false Support desktop effects
 * @property {bool} OPTIMIZED_DRAWING_LOADER__USE_OPTIMIZED=false Use optimized drawings for OpenGL rendering
 * @property {double} OPTIMIZED_DRAWING_LOADER__DISCRETIZATION_SCALE=0.25 Discretization scale used for calculation of optimized drawing.
 * @property {int} OPTIMIZED_DRAWING_LOADER__QUALITY_FACTOR=1 Quality factor used for calculation of optimized drawing.
 * @property {double} DEFORMATION_DRAWING_DISCRETIZATION_SCALE=0.25 Discretization scale used for calculation of deformed drawing.
 * @property {int} DEFORMATION_DRAWING_CACHE_SIZE=200 Number of deformed drawings to save in cache.
 * @property {bool} OPENGL_ENABLE_FSAA=true Enable Full Scene Anti-Aliasing
 * @property {int} OPENGL_SUPERSAMPLING_FSAA=4 Number of samples used for Full Scene Anti-Aliasing
 * @property {bool} OPENGL_GENERATE_MIPMAP=true Generate anti-aliased mipmap textures.
 * @property {bool} BITMAP_PREMULTIPLY_ALPHA=true Premultiply alpha to colour channels for Bitmap Layer.
 * @property {bool} USE_PBUFFER_FOR_PICKING=true Use PBuffer for Picking
 * @property {bool} PDF_SUPPORT_CMYK=true Support CMYK in Import
 * @property {bool} PDF_SUPPORT_SEPARATE_LAYERS=true Support Separate Layers in Import
 * @property {double} IK_MIN_MAX_ANGLE_CONSTRAINT_WEIGHT=0.0005 Weight of minmax angle constraint
 * @property {bool} OPENSG_RENDER_FIRST=false Render OpenSG elements first during composition.
 * @property {bool} FBX_TRIANGULATE_IMPORT=true Triangulate Fbx mesh during import.
 */

/**
 * Preferences in the ToolProperties category.
 * @name preferences#ToolProperties
 * @property {int} TP_BRUSH_PENSTYLELIST_DISPLAY_MODE=2 Brush Tool Properties Pen Style List Default View Mode.
 * @property {int} TP_SHAPE_PENSTYLELIST_DISPLAY_MODE=0 (Rectangle/Ellipse/Line) Tool Properties Pen Style List Default View Mode.
 * @property {int} TP_POLYLINE_PENSTYLELIST_DISPLAY_MODE=0 Polyline Tool Properties Pen Style List Default View Mode.
 */

/**
 * Preferences in the Backdrops category.
 * @name preferences#Backdrops
 * @property {color} BACKDROP_INNER_STROKE_COLOR=#373737ff 
 * @property {color} BACKDROP_RESIZE_COLOR=#373737ff 
 * @property {int} BACKDROP_SELECTED_TRANSPARENCY=220 
 * @property {int} BACKDROP_UNSELECTED_TRANSPARENCY=170 
 * @property {int} BACKDROP_DEFAULT_TITLE_SIZE=14 
 * @property {int} BACKDROP_DEFAULT_DESCRIPTION_SIZE=14 
 * @property {int} BACKDROP_COLOR_LIST_SIZE=17 
 * @property {color} BACKDROP_COLOR_0=#9a0707ff 
 * @property {color} BACKDROP_COLOR_1=#c11717ff 
 * @property {color} BACKDROP_COLOR_2=#843a16ff 
 * @property {color} BACKDROP_COLOR_3=#e16b14ff 
 * @property {color} BACKDROP_COLOR_4=#dcaa32ff 
 * @property {color} BACKDROP_COLOR_5=#81c615ff 
 * @property {color} BACKDROP_COLOR_6=#7b8d03ff 
 * @property {color} BACKDROP_COLOR_7=#077f04ff 
 * @property {color} BACKDROP_COLOR_8=#084c18ff 
 * @property {color} BACKDROP_COLOR_9=#0d6b58ff 
 * @property {color} BACKDROP_COLOR_10=#023cbeff 
 * @property {color} BACKDROP_COLOR_11=#460fe3ff 
 * @property {color} BACKDROP_COLOR_12=#6c0e9cff 
 * @property {color} BACKDROP_COLOR_13=#a521a3ff 
 * @property {color} BACKDROP_COLOR_14=#e30fa0ff 
 * @property {color} BACKDROP_COLOR_15=#e30f69ff 
 * @property {color} BACKDROP_COLOR_16=#323232ff 
 */

/**
 * Preferences in the user category.
 * @name preferences#user
 * @property {bool} ADVANCED_PALETTELIST=false 
 * @property {string} AMG_VIEW_RESOURCE_FOLDER= 
 * @property {bool} ANIMATE_WAS_NEVER_RUN=false 
 * @property {bool} COLORVIEW_SHOW_PALETTELIST=true 
 * @property {int} COLOR_SELECTION_STARTINGBUTTON=0 
 * @property {double} DBL_MEDIAN_MODULE_STEP_RADIUS=0.1 
 * @property {double} DBL_MEDIAN_MODULE_STEP_RADIUS_MAX=2160 
 * @property {double} DBL_MEDIAN_MODULE_STEP_RADIUS_MIN=0 
 * @property {double} DBL_SHAKE_ANGLE_PARAMETER=0.1 
 * @property {double} DBL_SHAKE_NORMAL_PARAMETER=0.01 
 * @property {double} DBL_SHAKE_POSITION_PARAMETER=0.1 
 * @property {double} DBL_STEP_MATTEBLUR_COLOUR_GAIN=0.1 
 * @property {double} DBL_STEP_MATTEBLUR_COLOUR_GAIN_MAX=1.79769e+308 
 * @property {double} DBL_STEP_MATTEBLUR_COLOUR_GAIN_MIN=0 
 * @property {bool} DRAWING_CLOSE_GAP_ON=false 
 * @property {string} DRAWING_PRESSURE_CURVE= 
 * @property {bool} DRAWING_STABILIZER_CATCH_UP=true 
 * @property {bool} DRAWING_STABILIZER_SHOW_STRING=true 
 * @property {double} DRAWING_STABILIZER_SMOOTHING=0 
 * @property {bool} DRAWING_STABILIZER_WITH_ERASER=false 
 * @property {int} DeformationConvertDrawingsTextureSize=1024 
 * @property {color} DeformationDeformedControlHandle=#19592aff 
 * @property {color} DeformationDeformedHandle=#00ff00ff 
 * @property {color} DeformationDeformedSelectedChild=#dcff00ff 
 * @property {color} DeformationDeformedSelectedSkeleton=#ffffffff 
 * @property {color} DeformationDeformedSkeleton=#00ff00ff 
 * @property {color} DeformationModuleDarkColor=#576a36ff 
 * @property {color} DeformationModuleLightColor=#25a919ff 
 * @property {color} DeformationRestingControlHandle=#951f39ff 
 * @property {color} DeformationRestingHandle=#ff0000ff 
 * @property {color} DeformationRestingSelectedChild=#ff7f00ff 
 * @property {color} DeformationRestingSelectedSkeleton=#ffffffff 
 * @property {color} DeformationRestingSkeleton=#ff0000ff 
 * @property {double} DeformationScalingFieldSize=2 
 * @property {double} DeformationScalingPixelSize=64 
 * @property {bool} DeformationScalingUsePixelSize=false 
 * @property {string} EXPORTMMX_AUDIOCONFIG= 
 * @property {int} EXPORTMMX_CUSTOMRESX=0 
 * @property {string} EXPORTMMX_DISPLAY=Display 
 * @property {bool} EXPORTMMX_EXPORTALL=false 
 * @property {string} EXPORTMMX_LASTSCENE_NAME=
 * @property {string} EXPORTMMX_OUTPUTFILE=
 * @property {string} EXPORTMMX_OUTPUTFORMAT=mov 
 * @property {int} EXPORTMMX_RANGESTART=1 
 * @property {int} EXPORTMMX_RANGESTOP=318 
 * @property {int} EXPORTMMX_RESOLUTION=2 
 * @property {string} EXPORTMMX_VIDEOAUDIOCONFIG=Enable Sound(true)Enable Video(true)QT(000000000000000000000000000003BE7365616E000000010000000600000000000001AF76696465000000010000001000000000000000227370746C000000010000000000000000726C652000000000002000000300000000207470726C000000010000000000000000000002000000000000000018000000246472617400000001000000000000000000000000000000000000000000000000000000156D70736F00000001000000000000000000000000186D66726100000001000000000000000000000000000000187073667200000001000000000000000000000000000000156266726100000001000000000000000000000000166D70657300000001000000000000000000000000002868617264000000010000000000000000000000000000000000000000000000000000000000000016656E647300000001000000000000000000000000001663666C67000000010000000000000000004400000018636D66720000000100000000000000006170706C00000014636C757400000001000000000000000000000014636465630000000100000000000000000000001C766572730000000100000000000000000003001C000100000000001574726E6300000001000000000000000000000001066973697A00000001000000090000000000000018697764740000000100000000000000000000000000000018696867740000000100000000000000000000000000000018707764740000000100000000000000000000000000000018706867740000000100000000000000000000000000000034636C617000000001000000000000000000000000000000000000000000000000000000000000000000000000000000000000001C706173700000000100000000000000000000000000000000000000187363616D000000010000000000000000000000000000001564696E74000000010000000000000000000000001575656E66000000010000000000000000000000008C736F756E0000000100000005000000000000001873736374000000010000000000000000736F777400000018737372740000000100000000000000005622000000000016737373730000000100000000000000000010000000167373636300000001000000000000000000010000001C76657273000000010000000000000000000300140001000000000015656E76690000000100000000000000000100000015656E736F000000010000000000000000010000003F7361766500000001000000020000000000000015666173740000000100000000000000000100000016737374790000000100000000000000000001) 
 * @property {string} EXPORTMMX_VIDEOCONFIG= 
 * @property {bool} EXPORT_IMAGE_ALLFRAMES=false 
 * @property {int} EXPORT_IMAGE_EXPORTFROM=1 
 * @property {int} EXPORT_IMAGE_EXPORTTO=47 
 * @property {string} EXPORT_IMAGE_LAST_SCENE_NAME=
 * @property {bool} EXPORT_IMAGE_PREVIEW=false 
 * @property {bool} GUIDE_ALIGN_ENABLED=true 
 * @property {bool} GUIDE_ERASER_ENABLED=false 
 * @property {bool} GUIDE_FULL_DISPLAY_ENABLED=true 
 * @property {int} GUIDE_GRID_DENSITY=10 
 * @property {bool} GUIDE_GRID_ENABLED=false 
 * @property {bool} GUIDE_LOCK_ENABLED=true 
 * @property {bool} IMPORTIMGDLG_IMAGE_ADDTOLAYER=false 
 * @property {int} IMPORTIMGDLG_IMAGE_ALIGNMENT=4 
 * @property {bool} IMPORTIMGDLG_IMAGE_BITMAP_ART=true 
 * @property {int} IMPORTIMGDLG_IMAGE_BITMAP_LAYER_ALIGNMENT=6 
 * @property {int} IMPORTIMGDLG_IMAGE_BITMAP_LAYER_TRANSPARENCY=2 
 * @property {bool} IMPORTIMGDLG_IMAGE_ELEMENTONFILENAME=false 
 * @property {string} IMPORTIMGDLG_IMAGE_LASTIMPORT=
 * @property {string} IMPORTIMGDLG_IMAGE_LAYERNAME= 
 * @property {bool} IMPORTIMGDLG_IMAGE_NEWLAYER=true 
 * @property {string} IMPORTIMGDLG_IMAGE_NEWLAYERNAME=
 * @property {bool} IMPORTIMGDLG_IMAGE_ONEELEMENT=true 
 * @property {int} IMPORTIMGDLG_IMAGE_TRANSPARENCY=2 
 * @property {string} IMPORTIMGDLG_IMAGE_VECTORIZATION=Grey 
 * @property {bool} IMPORTIMGDLG_IMAGE_VECTORIZE=false 
 * @property {double} LENSFLARE_ANGLE_STEP=1 
 * @property {double} LENSFLARE_BLUR_STEP=0.1 
 * @property {double} LENSFLARE_INTENSITY_STEP=1 
 * @property {double} LENSFLARE_POSITION_STEP=0.01 
 * @property {double} LENSFLARE_SIZE_STEP=0.1 
 * @property {double} LENSFLARE_SPACING_STEP=0.1 
 * @property {bool} NAVIGATE_USING_NODE_VIEW_PARENTING=false 
 * @property {bool} PALETTE_BROWSER_RECOLOR_SELECTED=false 
 * @property {double} PARTICLE_ANGLE_STEP=1 
 * @property {double} PARTICLE_FIELD_STEP=0.05 
 * @property {double} PARTICLE_MAGNITUDE_STEP=0.01 
 * @property {double} PARTICLE_UNIT_STEP=1 
 * @property {int} PENSTYLE_BITMAP_BRUSH_LIST_SEL=-1 
 * @property {int} PENSTYLE_BITMAP_ERASER_LIST_SEL=-1 
 * @property {int} PENSTYLE_BRUSH_LIST_SEL=0 
 * @property {int} PENSTYLE_ERASER_LIST_SEL=-1 
 * @property {int} PENSTYLE_PENCIL_LIST_SEL=0 
 * @property {int} PENSTYLE_STAMP_LIST_SEL=-1 
 * @property {int} PENSTYLE_TEXTURE_QUALITY=100 
 * @property {bool} PLAYBACK_IN_PERSPECTIVE_VIEW_ENABLED=false 
 * @property {bool} PLAYBACK_IN_SIDE_VIEW_ENABLED=false 
 * @property {bool} PLAYBACK_IN_TOP_VIEW_ENABLED=false 
 * @property {bool} PLAYBACK_IN_XSHEET_VIEW_ENABLED=false 
 * @property {color} ParticleNV_actionColor=#b547ffff 
 * @property {color} ParticleNV_bakerColor=#e2d06eff 
 * @property {color} ParticleNV_regionColor=#09e1a3ff 
 * @property {color} ParticleNV_regionCompositeColor=#99c87dff 
 * @property {color} ParticleNV_shapeColor=#00c8c8ff 
 * @property {color} ParticleNV_systemCompositeColor=#4b78f4ff 
 * @property {color} ParticleNV_visualizerColor=#9a18ffff 
 * @property {bool} ParticleShowParticlesAsDotsInOpenGL=false 
 * @property {int} RENDER_TEXTUREMEMORY=1591 
 * @property {int} RIG_CACHE_DEFAULT_RENDER_POLICY=2 
 * @property {int} RIG_CACHE_RESOLUTION_LEVEL=9 
 * @property {int} ShiftAndTracePegPosition=0 
 * @property {bool} ShiftAndTraceShowCrossHair=true 
 * @property {bool} ShiftAndTraceShowManipulator=true 
 * @property {bool} ShiftAndTraceShowOutline=false 
 * @property {bool} ShiftAndTraceShowPegs=true 
 * @property {string} TB_EXTERNAL_SCRIPT_PACKAGES_FOLDER=
 * @property {string} TEMPLATE_LIBRARY_PATH0= 
 * @property {int} TEMPLATE_LIBRARY_PATH_NB=1 
 * @property {int} TIMELINE_EXTRATRACK_CELL_WIDTH_NO_HDPI=8 
 * @property {int} TIMELINE_TRACK_CELL_WIDTH_NO_HDPI=8 
 * @property {bool} TL_LAYERCONNECTION_VISIBLE=false 
 * @property {bool} TL_LAYERDATAVIEW_VISIBLE=false 
 * @property {bool} TOOL_APPLY_TO_ALL_LAYERS=true 
 * @property {bool} TOOL_AUTO_FILL_ELLIPSE=false 
 * @property {bool} TOOL_AUTO_FILL_PEN=false 
 * @property {bool} TOOL_AUTO_FILL_POLYLINE=false 
 * @property {bool} TOOL_AUTO_FILL_RECT=false 
 * @property {bool} TOOL_AUTO_FILL_STROKE=false 
 * @property {bool} TOOL_LINE_MODE_STROKE=false 
 * @property {int} TOOL_MERGE_WITH_TOP_LAYER_MODE=0 
 * @property {bool} TOOL_SNAP_MODE_STROKE=false 
 * @property {double} TOOL_STROKE_SMOOTH_VALUE=3 
 * @property {bool} TOOL_TRIM_EXTRA_PEN=false 
 * @property {bool} TOOL_TRIM_EXTRA_POLYLINE=false 
 * @property {bool} TOOL_TRIM_EXTRA_STROKE=false 
 * @property {bool} TOOL_TRIM_MATCH_PEN=false 
 * @property {bool} TOOL_TRIM_MATCH_POLYLINE=false 
 * @property {bool} TOOL_TRIM_MATCH_STROKE=false 
 * @property {int} TP_PENCIL_PANEL_PENSTYLELIST_DISPLAY_MODE=2 
 * @property {int} TP_PEN_PENSTYLELIST_DISPLAY_MODE=2 
 * @property {bool} WM_SHOW_WS_WEB_MESSAGE=true 
 * @property {bool} deformationCreatePosedDeformation=true 
 * @property {int} particleImageEmitterHorizontalPreviewResolution=360 
 */