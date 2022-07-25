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
// printOutDoc();
//
// function printOutDoc(){
// 	var doc = "";
// 	var responders = Action.getResponderList()
// 	for (var i in responders){
// 		var docString = ["\n\n/\**\n * Actions available in the "+responders[i]+" responder.", " @name actions#"+responders[i]];
// 		var actions = Action.getActionList(responders[i]);
// 		for (var j in actions){
// 			docString.push(" @property {QAction} "+actions[j]);
// 		}
// 		docString.push ("/");
// 		doc += docString.join("\n *");
// 	}
//
// 	MessageLog.trace(doc);
// }


/**
 * Actions are used by the Harmony interface to represent something the user can ask the software to do. This is a list of all the available names and responders available.
 * @class actions
 * @hideconstructor 
 * @namespace
 * @example
 * // To check wether an action is available, call the synthax:
 * Action.validate (<actionName>, <responder>);
 * 
 * // To launch an action, call the synthax:
 * Action.perform (<actionName>, <responder>, parameters);
 */

/**
 * Actions available in the ExportGifResponder responder.
 * @name actions#ExportGifResponder
 * @property {QAction} onActionExportGif()
 */

/**
 * Actions available in the ExposureFillResponder responder.
 * @name actions#ExposureFillResponder
 * @property {QAction} onActionExposureFillUsingRenderChange()
 */

/**
 * Actions available in the GameSkinResponder responder.
 * @name actions#GameSkinResponder
 */

/**
 * Actions available in the GuideToolResponder responder.
 * @name actions#GuideToolResponder
 */

/**
 * Actions available in the MatteGeneratorResponder responder.
 * @name actions#MatteGeneratorResponder
 * @property {QAction} onActionNull()
 * @property {QAction} onActionNullAddHint()
 * @property {QAction} onActionGenerateMatte()
 * @property {QAction} onActionGenerateHints()
 * @property {QAction} onActionMakeMatteVerticesAnimatable()
 * @property {QAction} onActionMergeInnerOuterContours()
 * @property {QAction} onActionRemoveUnusedMatteDisplacements()
 * @property {QAction} onActionShowOptionsInCameraView()
 * @property {QAction} onActionRemoveSelectedHints()
 * @property {QAction} onActionRemoveSelectedVertices()
 * @property {QAction} onActionRemoveSelectedVertexAnimation()
 * @property {QAction} onActionEnableNormalMode()
 * @property {QAction} onActionEnableSetupMode()
 * @property {QAction} onActionEnableAddVertexMode()
 * @property {QAction} onActionEnableAddHintMode()
 * @property {QAction} onActionToggleShowOuterContour()
 * @property {QAction} onActionToggleShowInnerContour()
 * @property {QAction} onActionToggleShowPointId()
 * @property {QAction} onActionToggleShowHints()
 * @property {QAction} onActionToggleShowOverlayAnnotation()
 * @property {QAction} onActionToggleShowInflate()
 * @property {QAction} onActionAlignMatteHandles()
 * @property {QAction} onActionShortenMatteHandles()
 * @property {QAction} onActionExpandOuterContour()
 * @property {QAction} onActionExpandInnerContour()
 * @property {QAction} onActionReduceOuterContour()
 * @property {QAction} onActionReduceInnerContour()
 * @property {QAction} onActionToggleAutoKey()
 * @property {QAction} onActionToggleFixAdjacentKeyframes()
 * @property {QAction} onActionReloadView()
 * @property {QAction} onActionDefineResourceFolder()
 * @property {QAction} onActionExportResourceFolder()
 * @property {QAction} onActionResetResourceFolder()
 */

/**
 * Actions available in the ModuleLibraryIconView responder.
 * @name actions#ModuleLibraryIconView
 */

/**
 * Actions available in the ModuleLibraryListView responder.
 * @name actions#ModuleLibraryListView
 */

/**
 * Actions available in the ModuleLibraryTemplatesResponder responder.
 * @name actions#ModuleLibraryTemplatesResponder
 */

/**
 * Actions available in the Node View responder.
 * @name actions#Node View
 * @property {QAction} onActionResetView()
 * @property {QAction} onActionTag()
 * @property {QAction} onActionUntag()
 * @property {QAction} onActionUntagAll()
 * @property {QAction} onActionUntagAllOthers()
 * @property {QAction} onActionZoomIn()
 * @property {QAction} onActionZoomOut()
 * @property {QAction} onActionResetZoom()
 * @property {QAction} onActionResetPan()
 * @property {QAction} onActionShowAllModules()
 * @property {QAction} onActionPasteSpecial()
 * @property {QAction} onActionPasteSpecialAgain()
 * @property {QAction} onActionCloneElement()
 * @property {QAction} onActionCloneElement_DrawingsOnly()
 * @property {QAction} onActionCopyQualifiedName()
 * @property {QAction} onActionDuplicateElement()
 * @property {QAction} onActionSelEnable()
 * @property {QAction} onActionEnableAll()
 * @property {QAction} onActionSelDisable()
 * @property {QAction} onActionDisableAllUnselected()
 * @property {QAction} onActionRecomputeAll()
 * @property {QAction} onActionRecomputeSelected()
 * @property {QAction} onActionSelCreateGroup()
 * @property {QAction} onActionSelCreateGroupWithComposite()
 * @property {QAction} onActionSelMoveToParentGroup()
 * @property {QAction} onActionSelMergeInto()
 * @property {QAction} onActionClearPublishedAttributes()
 * @property {QAction} onActionPrintNetwork()
 * @property {QAction} onActionUpToParent()
 * @property {QAction} onActionShowHideWorldView()
 * @property {QAction} onActionMoveWorldNE()
 * @property {QAction} onActionMoveWorldNW()
 * @property {QAction} onActionMoveWorldSE()
 * @property {QAction} onActionMoveWorldSW()
 * @property {QAction} onActionEnterGroup()
 * @property {QAction} onActionCreateGroup()
 * @property {QAction} onActionCreatePeg()
 * @property {QAction} onActionCreateParentPeg()
 * @property {QAction} onActionCreateDisplay()
 * @property {QAction} onActionCreateRead()
 * @property {QAction} onActionCreateComposite()
 * @property {QAction} onActionCreateBackdrop()
 * @property {QAction} onActionToggleDefinePublishMode()
 * @property {QAction} onActionNavigateGroup()
 * @property {QAction} onActionGotoPortAbove()
 * @property {QAction} onActionGotoPortUnder()
 * @property {QAction} onActionGotoPortLeft()
 * @property {QAction} onActionGotoPortRight()
 * @property {QAction} onActionToggleDefineAttributeInfo()
 * @property {QAction} onActionCreateFavorite(QString)
 * @property {QAction} onActionCreateModule(QString)
 * @property {QAction} onActionCableLine()
 * @property {QAction} onActionCableStraight()
 * @property {QAction} onActionCableBezier()
 * @property {QAction} onActionRecenter()
 * @property {QAction} onActionFocusOnSelectionNV()
 * @property {QAction} onActionFocusOnParentNodeNV()
 * @property {QAction} onActionFocusOnChildNodeNV()
 * @property {QAction} onActionToggleSelectedThumbNail()
 * @property {QAction} onActionShowAllThumbNail()
 * @property {QAction} onActionHideAllThumbNails()
 * @property {QAction} onActionShowSelectedThumbNail()
 * @property {QAction} onActionHideSelectedThumbNail()
 * @property {QAction} onActionNaviSelectChild()
 * @property {QAction} onActionNaviSelectChilds()
 * @property {QAction} onActionNaviSelectParent()
 * @property {QAction} onActionNaviSelectPreviousBrother()
 * @property {QAction} onActionNaviSelectNextBrother()
 * @property {QAction} onActionNaviSelectInnerChildren()
 * @property {QAction} onActionNaviSelectParentWithEffects()
 * @property {QAction} onActionNaviSelectChildWithEffects()
 * @property {QAction} onActionSelectLinkedLayers()
 * @property {QAction} onActionSetDrawingAsSubLayer()
 * @property {QAction} onActionUnlinkSubLayer()
 * @property {QAction} onActionAddSubLayer()
 * @property {QAction} onActionRenameWaypoint()
 * @property {QAction} onActionCreateWaypointFromContextMenu()
 * @property {QAction} onActionCreateWaypointFromShortcut()
 */

/**
 * Actions available in the ParticleCoreGuiResponder responder.
 * @name actions#ParticleCoreGuiResponder
 * @property {QAction} onActionInsertParticleTemplate(QString)
 * @property {QAction} onActionToggleShowAsDots()
 */

/**
 * Actions available in the PluginHelpViewResponder responder.
 * @name actions#PluginHelpViewResponder
 * @property {QAction} onActionShowShortcuts()
 */

/**
 * Actions available in the Script responder.
 * @name actions#Script
 */

/**
 * Actions available in the ScriptManagerResponder responder.
 * @name actions#ScriptManagerResponder
 */

/**
 * Actions available in the ScriptViewResponder responder.
 * @name actions#ScriptViewResponder
 * @property {QAction} onActionNewScriptFile()
 * @property {QAction} onActionImportScript()
 * @property {QAction} onActionDeleteScript()
 * @property {QAction} onActionRefreshScripts()
 * @property {QAction} onActionRun()
 * @property {QAction} onActionDebug()
 * @property {QAction} onActionStopExecution()
 * @property {QAction} onActionOpenHelp()
 * @property {QAction} onActionSetTarget()
 * @property {QAction} onActionSetExternalEditor()
 * @property {QAction} onActionCallExternalEditor()
 */

/**
 * Actions available in the ShiftAndTraceToolResponder responder.
 * @name actions#ShiftAndTraceToolResponder
 * @property {QAction} onActionEnableShiftAndTrace()
 * @property {QAction} onActionSelectShiftAndTraceTool()
 * @property {QAction} onActionToggleShowManipulator()
 * @property {QAction} onActionToggleShowPegs()
 * @property {QAction} onActionToggleShowOutline()
 * @property {QAction} onActionSetPegPosition(int)
 * @property {QAction} onActionShiftAndTraceToolRotateOverride()
 * @property {QAction} onActionShiftAndTraceToolScaleOverride()
 * @property {QAction} onActionShiftAndTraceToolResetCurrentPosition()
 * @property {QAction} onActionShiftAndTraceToolResetAllPositions()
 * @property {QAction} onActionResetCurrentShiftPosition()
 * @property {QAction} onActionResetAllShiftPositions()
 * @property {QAction} onActionShowCrossHair()
 * @property {QAction} onActionAddCrossHairMode()
 * @property {QAction} onActionRemoveCrossHair()
 */

/**
 * Actions available in the artLayerResponder responder.
 * @name actions#artLayerResponder
 * @property {QAction} onActionPreviewModeToggle()
 * @property {QAction} onActionOverlayArtSelected()
 * @property {QAction} onActionLineArtSelected()
 * @property {QAction} onActionColorArtSelected()
 * @property {QAction} onActionUnderlayArtSelected()
 * @property {QAction} onActionToggleLineColorArt()
 * @property {QAction} onActionToggleOverlayUnderlayArt()
 */

/**
 * Actions available in the brushSettingsResponder responder.
 * @name actions#brushSettingsResponder
 */

/**
 * Actions available in the cameraView responder.
 * @name actions#cameraView
 * @property {QAction} onActionRenameDrawing()
 * @property {QAction} onActionRenameDrawingWithPrefix()
 * @property {QAction} onActionDeleteDrawings()
 * @property {QAction} onActionToggleShowSymbolPivot()
 * @property {QAction} onActionShowGrid()
 * @property {QAction} onActionNormalGrid()
 * @property {QAction} onAction12FieldGrid()
 * @property {QAction} onAction16FieldGrid()
 * @property {QAction} onActionWorldGrid()
 * @property {QAction} onActionGridUnderlay()
 * @property {QAction} onActionGridOverlay()
 * @property {QAction} onActionFieldGridBox()
 * @property {QAction} onActionHideLineTexture()
 * @property {QAction} onActionAutoLightTable()
 * @property {QAction} onActionGetRightToModifyDrawings()
 * @property {QAction} onActionReleaseRightToModifyDrawings()
 * @property {QAction} onActionChooseSelectToolOverride()
 * @property {QAction} onActionChooseContourEditorToolOverride()
 * @property {QAction} onActionChooseCenterlineEditorToolOverride()
 * @property {QAction} onActionChooseDeformToolOverride()
 * @property {QAction} onActionChoosePerspectiveToolOverride()
 * @property {QAction} onActionChooseCutterToolOverride()
 * @property {QAction} onActionChooseMorphToolOverride()
 * @property {QAction} onActionChooseBrushToolOverride()
 * @property {QAction} onActionChooseRepositionAllDrawingsToolOverride()
 * @property {QAction} onActionChooseEraserToolOverride()
 * @property {QAction} onActionChooseRepaintBrushToolOverride()
 * @property {QAction} onActionChoosePencilToolOverride()
 * @property {QAction} onActionChooseLineToolOverride()
 * @property {QAction} onActionChoosePolylineToolOverride()
 * @property {QAction} onActionChooseRectangleToolOverride()
 * @property {QAction} onActionChooseEllipseToolOverride()
 * @property {QAction} onActionChoosePaintToolOverride()
 * @property {QAction} onActionChooseInkToolOverride()
 * @property {QAction} onActionChoosePaintUnpaintedToolOverride()
 * @property {QAction} onActionChooseRepaintToolOverride()
 * @property {QAction} onActionChooseStrokeToolOverride()
 * @property {QAction} onActionChooseCloseGapToolOverride()
 * @property {QAction} onActionChooseUnpaintToolOverride()
 * @property {QAction} onActionChooseDropperToolOverride()
 * @property {QAction} onActionChooseEditTransformToolOverride()
 * @property {QAction} onActionChooseGrabberToolOverride()
 * @property {QAction} onActionChooseZoomToolOverride()
 * @property {QAction} onActionChooseRotateToolOverride()
 * @property {QAction} onActionChooseThirdPersonNavigation3dToolOverride()
 * @property {QAction} onActionChooseFirstPersonNavigation3dToolOverride()
 * @property {QAction} onActionChooseShiftAndTraceToolOverride()
 * @property {QAction} onActionChooseNoToolOverride()
 * @property {QAction} onActionChooseResizePenStyleToolOverride()
 * @property {QAction} onActionZoomIn()
 * @property {QAction} onActionZoomOut()
 * @property {QAction} onActionRotateCW()
 * @property {QAction} onActionRotateCCW()
 * @property {QAction} onActionToggleQuickCloseUp()
 * @property {QAction} onActionResetZoom()
 * @property {QAction} onActionResetRotation()
 * @property {QAction} onActionResetPan()
 * @property {QAction} onActionResetView()
 * @property {QAction} onActionRecenter()
 * @property {QAction} onActionMorphSwitchKeyDrawing()
 * @property {QAction} onActionShowPaletteManager()
 * @property {QAction} onActionShowColorEditor()
 * @property {QAction} onActionShowColorPicker()
 * @property {QAction} onActionShowColorModel()
 * @property {QAction} onActionShowThumbnailPanel()
 * @property {QAction} onActionPlayByFrame()
 * @property {QAction} onActionPreviousDrawing()
 * @property {QAction} onActionNextDrawing()
 * @property {QAction} onActionPreviousColumn()
 * @property {QAction} onActionNextColumn()
 * @property {QAction} onActionCreateEmptyDrawing()
 * @property {QAction} onActionDuplicateDrawing()
 * @property {QAction} onActionShowScanInfo()
 * @property {QAction} onActionSetThumbnailSize(int)
 * @property {QAction} onActionSelectedElementSwapToNextDrawing()
 * @property {QAction} onActionSelectedElementSwapToPrevDrawing()
 * @property {QAction} onActionToggleShiftAndTracePegView()
 * @property {QAction} onActionToggleShiftAndTraceManipulator()
 * @property {QAction} onActionShowMorphingInspector()
 * @property {QAction} onActionRemoveFromDrawingList()
 * @property {QAction} onActionResetDrawingPosition()
 * @property {QAction} onActionToggleDrawingOnPeg()
 * @property {QAction} onActionToggleDrawingOnPeg(VL_DrawingListWidget*)
 * @property {QAction} onActionToggleDrawingVisibility()
 * @property {QAction} onActionToggleDrawingVisibility(VL_DrawingListWidget*)
 * @property {QAction} onActionMoveDrawingUp()
 * @property {QAction} onActionMoveDrawingDown()
 * @property {QAction} onActionReturnToNormalMode()
 * @property {QAction} onActionLinkSelectedDrawings()
 * @property {QAction} onActionMainGotoNextFrame()
 * @property {QAction} onActionMainGotoPreviousFrame()
 * @property {QAction} onActionMainGotoFirstFrame()
 * @property {QAction} onActionMainGotoLastFrame()
 * @property {QAction} onActionRenameDrawing()
 * @property {QAction} onActionRenameDrawingWithPrefix()
 * @property {QAction} onActionNaviSelectChild()
 * @property {QAction} onActionNaviSelectChilds()
 * @property {QAction} onActionInsertControlPoint()
 * @property {QAction} onActionSelectControlPoint()
 * @property {QAction} onActionNaviSelectNextBrother()
 * @property {QAction} onActionNaviSelectParent()
 * @property {QAction} onActionNaviSelectPreviousBrother()
 * @property {QAction} onActionNaviSelectParentWithEffects()
 * @property {QAction} onActionNaviSelectChildWithEffects()
 * @property {QAction} onActionAutoLightTable()
 * @property {QAction} onActionSetSmallFilesResolution()
 * @property {QAction} onActionInvalidateCanvas()
 * @property {QAction} onActionChooseSpSelectToolOverride()
 * @property {QAction} onActionChooseSpTranslateToolOverride()
 * @property {QAction} onActionChooseSpRotateToolOverride()
 * @property {QAction} onActionChooseSpScaleToolOverride()
 * @property {QAction} onActionChooseSpSkewToolOverride()
 * @property {QAction} onActionChooseSpMaintainSizeToolOverride()
 * @property {QAction} onActionChooseSpTransformToolOverride()
 * @property {QAction} onActionChooseSpInverseKinematicsToolOverride()
 * @property {QAction} onActionChooseSpOffsetZToolOverride()
 * @property {QAction} onActionChooseSpSplineOffsetToolOverride()
 * @property {QAction} onActionChooseSpSmoothEditingToolOverride()
 * @property {QAction} onActionUnlockAll()
 * @property {QAction} onActionUnlock()
 * @property {QAction} onActionLockAll()
 * @property {QAction} onActionLockAllOthers()
 * @property {QAction} onActionLock()
 * @property {QAction} onActionTag()
 * @property {QAction} onActionUntag()
 * @property {QAction} onActionToggleCameraCone()
 * @property {QAction} onActionToggleCameraMask()
 * @property {QAction} onActionTogglePreventFromDrawing()
 * @property {QAction} onActionFocusOnSelectionCV()
 * @property {QAction} onActionTogglePlayback()
 * @property {QAction} onActionOnionOnSelection()
 * @property {QAction} onActionOnionOffSelection()
 * @property {QAction} onActionOnionOffAllOther()
 * @property {QAction} onActionOnionOnAll()
 * @property {QAction} onActionOnionOffAll()
 * @property {QAction} onActionOpenGLView()
 * @property {QAction} onActionRenderView()
 * @property {QAction} onActionMatteView()
 * @property {QAction} onActionDepthView()
 * @property {QAction} onActionNodeCacheEnable()
 * @property {QAction} onActionNodeCacheQuality()
 * @property {QAction} onActionNodeCacheHide()
 * @property {QAction} onActionNodeCacheDisable()
 * @property {QAction} onActionMorphSwitchKeyDrawing()
 * @property {QAction} onActionRender()
 * @property {QAction} onActionAutoRender()
 * @property {QAction} onActionEnterSymbol()
 * @property {QAction} onActionLeaveSymbol()
 */

/**
 * Actions available in the colorOperationsResponder responder.
 * @name actions#colorOperationsResponder
 * @property {QAction} onActionRepaintColorInDrawing()
 */

/**
 * Actions available in the coordControlView responder.
 * @name actions#coordControlView
 */

/**
 * Actions available in the drawingSelectionResponder responder.
 * @name actions#drawingSelectionResponder
 */

/**
 * Actions available in the drawingView responder.
 * @name actions#drawingView
 * @property {QAction} onActionRenameDrawing()
 * @property {QAction} onActionRenameDrawingWithPrefix()
 * @property {QAction} onActionDeleteDrawings()
 * @property {QAction} onActionToggleShowSymbolPivot()
 * @property {QAction} onActionShowGrid()
 * @property {QAction} onActionNormalGrid()
 * @property {QAction} onAction12FieldGrid()
 * @property {QAction} onAction16FieldGrid()
 * @property {QAction} onActionWorldGrid()
 * @property {QAction} onActionGridUnderlay()
 * @property {QAction} onActionGridOverlay()
 * @property {QAction} onActionFieldGridBox()
 * @property {QAction} onActionHideLineTexture()
 * @property {QAction} onActionAutoLightTable()
 * @property {QAction} onActionGetRightToModifyDrawings()
 * @property {QAction} onActionReleaseRightToModifyDrawings()
 * @property {QAction} onActionChooseSelectToolOverride()
 * @property {QAction} onActionChooseContourEditorToolOverride()
 * @property {QAction} onActionChooseCenterlineEditorToolOverride()
 * @property {QAction} onActionChooseDeformToolOverride()
 * @property {QAction} onActionChoosePerspectiveToolOverride()
 * @property {QAction} onActionChooseCutterToolOverride()
 * @property {QAction} onActionChooseMorphToolOverride()
 * @property {QAction} onActionChooseBrushToolOverride()
 * @property {QAction} onActionChooseRepositionAllDrawingsToolOverride()
 * @property {QAction} onActionChooseEraserToolOverride()
 * @property {QAction} onActionChooseRepaintBrushToolOverride()
 * @property {QAction} onActionChoosePencilToolOverride()
 * @property {QAction} onActionChooseLineToolOverride()
 * @property {QAction} onActionChoosePolylineToolOverride()
 * @property {QAction} onActionChooseRectangleToolOverride()
 * @property {QAction} onActionChooseEllipseToolOverride()
 * @property {QAction} onActionChoosePaintToolOverride()
 * @property {QAction} onActionChooseInkToolOverride()
 * @property {QAction} onActionChoosePaintUnpaintedToolOverride()
 * @property {QAction} onActionChooseRepaintToolOverride()
 * @property {QAction} onActionChooseStrokeToolOverride()
 * @property {QAction} onActionChooseCloseGapToolOverride()
 * @property {QAction} onActionChooseUnpaintToolOverride()
 * @property {QAction} onActionChooseDropperToolOverride()
 * @property {QAction} onActionChooseEditTransformToolOverride()
 * @property {QAction} onActionChooseGrabberToolOverride()
 * @property {QAction} onActionChooseZoomToolOverride()
 * @property {QAction} onActionChooseRotateToolOverride()
 * @property {QAction} onActionChooseThirdPersonNavigation3dToolOverride()
 * @property {QAction} onActionChooseFirstPersonNavigation3dToolOverride()
 * @property {QAction} onActionChooseShiftAndTraceToolOverride()
 * @property {QAction} onActionChooseNoToolOverride()
 * @property {QAction} onActionChooseResizePenStyleToolOverride()
 * @property {QAction} onActionZoomIn()
 * @property {QAction} onActionZoomOut()
 * @property {QAction} onActionRotateCW()
 * @property {QAction} onActionRotateCCW()
 * @property {QAction} onActionToggleQuickCloseUp()
 * @property {QAction} onActionResetZoom()
 * @property {QAction} onActionResetRotation()
 * @property {QAction} onActionResetPan()
 * @property {QAction} onActionResetView()
 * @property {QAction} onActionRecenter()
 * @property {QAction} onActionMorphSwitchKeyDrawing()
 * @property {QAction} onActionShowPaletteManager()
 * @property {QAction} onActionShowColorEditor()
 * @property {QAction} onActionShowColorPicker()
 * @property {QAction} onActionShowColorModel()
 * @property {QAction} onActionShowThumbnailPanel()
 * @property {QAction} onActionPlayByFrame()
 * @property {QAction} onActionPreviousDrawing()
 * @property {QAction} onActionNextDrawing()
 * @property {QAction} onActionPreviousColumn()
 * @property {QAction} onActionNextColumn()
 * @property {QAction} onActionCreateEmptyDrawing()
 * @property {QAction} onActionDuplicateDrawing()
 * @property {QAction} onActionShowScanInfo()
 * @property {QAction} onActionSetThumbnailSize(int)
 * @property {QAction} onActionSelectedElementSwapToNextDrawing()
 * @property {QAction} onActionSelectedElementSwapToPrevDrawing()
 * @property {QAction} onActionToggleShiftAndTracePegView()
 * @property {QAction} onActionToggleShiftAndTraceManipulator()
 * @property {QAction} onActionShowMorphingInspector()
 * @property {QAction} onActionRemoveFromDrawingList()
 * @property {QAction} onActionResetDrawingPosition()
 * @property {QAction} onActionToggleDrawingOnPeg()
 * @property {QAction} onActionToggleDrawingOnPeg(VL_DrawingListWidget*)
 * @property {QAction} onActionToggleDrawingVisibility()
 * @property {QAction} onActionToggleDrawingVisibility(VL_DrawingListWidget*)
 * @property {QAction} onActionMoveDrawingUp()
 * @property {QAction} onActionMoveDrawingDown()
 * @property {QAction} onActionReturnToNormalMode()
 * @property {QAction} onActionLinkSelectedDrawings()
 */

/**
 * Actions available in the exportCoreResponder responder.
 * @name actions#exportCoreResponder
 * @property {QAction} onActionGenerateLayoutImage()
 */

/**
 * Actions available in the graph3dresponder responder.
 * @name actions#graph3dresponder
 * @property {QAction} onActionShowSubnodeShape()
 * @property {QAction} onActionHideSubnodeShape()
 * @property {QAction} onActionEnableSubnode()
 * @property {QAction} onActionDisableSubnode()
 * @property {QAction} onActionCreateSubNodeTransformation()
 * @property {QAction} onActionAddSubTransformationFilter()
 * @property {QAction} onActionSelectParent()
 * @property {QAction} onActionSelectChild()
 * @property {QAction} onActionSelectNextSibling()
 * @property {QAction} onActionSelectPreviousSibling()
 * @property {QAction} onActionDumpSceneGraphInformation()
 */

/**
 * Actions available in the ikResponder responder.
 * @name actions#ikResponder
 * @property {QAction} onActionSetIKNail()
 * @property {QAction} onActionSetIKHoldOrientation()
 * @property {QAction} onActionSetIKHoldX()
 * @property {QAction} onActionSetIKHoldY()
 * @property {QAction} onActionSetIKMinAngle()
 * @property {QAction} onActionSetIKMaxAngle()
 * @property {QAction} onActionRemoveAllConstraints()
 */

/**
 * Actions available in the libraryView responder.
 * @name actions#libraryView
 */

/**
 * Actions available in the logView responder.
 * @name actions#logView
 */

/**
 * Actions available in the miniPegModuleResponder responder.
 * @name actions#miniPegModuleResponder
 * @property {QAction} onActionResetDeform()
 * @property {QAction} onActionCopyRestingPositionToCurrentPosition()
 * @property {QAction} onActionConvertEllipseToShape()
 * @property {QAction} onActionSelectRigTool()
 * @property {QAction} onActionInsertDeformationAbove()
 * @property {QAction} onActionInsertDeformationUnder()
 * @property {QAction} onActionToggleEnableDeformation()
 * @property {QAction} onActionToggleShowAllManipulators()
 * @property {QAction} onActionToggleShowAllROI()
 * @property {QAction} onActionToggleShowSimpleManipulators()
 * @property {QAction} onActionConvertSelectionToCurve()
 * @property {QAction} onActionStraightenSelection()
 * @property {QAction} onActionShowSelectedDeformers()
 * @property {QAction} onActionShowDeformer(QString)
 * @property {QAction} onActionHideDeformer(QString)
 * @property {QAction} onActionCreateKinematicOutput()
 * @property {QAction} onActionConvertDeformedDrawingsToDrawings()
 * @property {QAction} onActionConvertDeformedDrawingsAndCreateDeformation()
 * @property {QAction} onActionUnsetLocalFlag()
 * @property {QAction} onActionCopyCurvePositionToOffset()
 * @property {QAction} onActionAddDeformationModuleByName(QString)
 * @property {QAction} onActionCreateNewDeformationChain()
 * @property {QAction} onActionRenameTransformation()
 * @property {QAction} onActionSetTransformation()
 * @property {QAction} onActionSetMasterElementModule()
 * @property {QAction} onActionToggleShowManipulator()
 */

/**
 * Actions available in the moduleLibraryView responder.
 * @name actions#moduleLibraryView
 * @property {QAction} onActionReceiveFocus()
 * @property {QAction} onActionNewCategory()
 * @property {QAction} onActionRenameCategory()
 * @property {QAction} onActionRemoveCategory()
 * @property {QAction} onActionRemoveUserModule()
 * @property {QAction} onActionRefresh()
 */

/**
 * Actions available in the moduleResponder responder.
 * @name actions#moduleResponder
 * @property {QAction} onActionAddModuleByName(QString)
 * @property {QAction} onActionAddModule(int,int)
 */

/**
 * Actions available in the onionSkinResponder responder.
 * @name actions#onionSkinResponder
 * @property {QAction} onActionOnionSkinToggle()
 * @property {QAction} onActionOnionSkinToggleCenterline()
 * @property {QAction} onActionOnionSkinToggleFramesToDrawingsMode()
 * @property {QAction} onActionOnionSkinNoPrevDrawings()
 * @property {QAction} onActionOnionSkin1PrevDrawing()
 * @property {QAction} onActionOnionSkin2PrevDrawings()
 * @property {QAction} onActionOnionSkin3PrevDrawings()
 * @property {QAction} onActionOnionSkinNoNextDrawings()
 * @property {QAction} onActionOnionSkin1NextDrawing()
 * @property {QAction} onActionOnionSkin2NextDrawings()
 * @property {QAction} onActionOnionSkin3NextDrawings()
 * @property {QAction} onActionSetMarksOnionSkinInBetween()
 * @property {QAction} onActionSetMarksOnionSkinInBreakdown()
 * @property {QAction} onActionSetMarksOnionSkinInKey()
 * @property {QAction} onActionSetDrawingEnhancedOnionSkin()
 * @property {QAction} onActionOnionSkinReduceNextDrawing()
 * @property {QAction} onActionOnionSkinAddNextDrawing()
 * @property {QAction} onActionOnionSkinReducePrevDrawing()
 * @property {QAction} onActionOnionSkinAddPrevDrawing()
 * @property {QAction} onActionToggleOnionSkinForCustomMarkedType(QString)
 * @property {QAction} onActionOnionSkinSelectedLayerOnly()
 * @property {QAction} onActionOnionSkinRenderStyle(int)
 * @property {QAction} onActionOnionSkinDrawingMode(int)
 * @property {QAction} onActionOnionSkinToggleBaseMode()
 * @property {QAction} onActionOnionSkinToggleAdvancedMode()
 * @property {QAction} onActionOnionSkinToggleColorWash()
 * @property {QAction} onActionOnionSkinLinkSliders()
 * @property {QAction} onActionOnionSkinToggleAdvancedNext(int)
 * @property {QAction} onActionOnionSkinToggleAdvancedPrev(int)
 * @property {QAction} onActionOnionSkinAdvancedNextSliderChanged(int,int)
 * @property {QAction} onActionOnionSkinAdvancedPrevSliderChanged(int,int)
 * @property {QAction} onActionMaxOpacitySliderChanged(int)
 */

/**
 * Actions available in the onionSkinView responder.
 * @name actions#onionSkinView
 */

/**
 * Actions available in the opacityPanel responder.
 * @name actions#opacityPanel
 * @property {QAction} onActionNewOpacityTexture()
 * @property {QAction} onActionDeleteOpacityTexture()
 * @property {QAction} onActionRenameOpacityTexture()
 * @property {QAction} onActionCurToPrefPalette()
 * @property {QAction} onActionPrefToCurPalette()
 */

/**
 * Actions available in the paletteView responder.
 * @name actions#paletteView
 */

/**
 * Actions available in the pencilPanel responder.
 * @name actions#pencilPanel
 * @property {QAction} onActionNewPencilTemplate()
 * @property {QAction} onActionDeletePencilTemplate()
 * @property {QAction} onActionRenamePencilTemplate()
 * @property {QAction} onActionShowSmallThumbnail()
 * @property {QAction} onActionShowLargeThumbnail()
 * @property {QAction} onActionShowStroke()
 */

/**
 * Actions available in the scene responder.
 * @name actions#scene
 * @property {QAction} onActionHideSelection()
 * @property {QAction} onActionShowHidden()
 * @property {QAction} onActionRehideSelection()
 * @property {QAction} onActionInsertPositionKeyframe()
 * @property {QAction} onActionInsertKeyframe()
 * @property {QAction} onActionSetKeyFrames()
 * @property {QAction} onActionInsertControlPointAtFrame()
 * @property {QAction} onActionSetConstant()
 * @property {QAction} onActionSetNonConstant()
 * @property {QAction} onActionToggleContinuity()
 * @property {QAction} onActionToggleLockInTime()
 * @property {QAction} onActionResetTransformation()
 * @property {QAction} onActionResetAll()
 * @property {QAction} onActionResetAllExceptZ()
 * @property {QAction} onActionSelectPrevObject()
 * @property {QAction} onActionSelectNextObject()
 * @property {QAction} onActionToggleNoFBDragging()
 * @property {QAction} onActionToggleAutoApply()
 * @property {QAction} onActionToggleAutoLock()
 * @property {QAction} onActionToggleAutoLockPalettes()
 * @property {QAction} onActionToggleAutoLockPaletteLists()
 * @property {QAction} onActionToggleEnableWrite()
 * @property {QAction} onActionShowHideManager()
 * @property {QAction} onActionToggleControl()
 * @property {QAction} onActionHideAllControls()
 * @property {QAction} onActionPreviousDrawing()
 * @property {QAction} onActionNextDrawing()
 * @property {QAction} onActionPreviousColumn()
 * @property {QAction} onActionNextColumn()
 * @property {QAction} onActionShowSubNode(bool)
 * @property {QAction} onActionGotoDrawing1()
 * @property {QAction} onActionGotoDrawing2()
 * @property {QAction} onActionGotoDrawing3()
 * @property {QAction} onActionGotoDrawing4()
 * @property {QAction} onActionGotoDrawing5()
 * @property {QAction} onActionGotoDrawing6()
 * @property {QAction} onActionGotoDrawing7()
 * @property {QAction} onActionGotoDrawing8()
 * @property {QAction} onActionGotoDrawing9()
 * @property {QAction} onActionGotoDrawing10()
 * @property {QAction} onActionToggleVelocityEditor()
 * @property {QAction} onActionCreateScene()
 * @property {QAction} onActionChooseSelectToolInNormalMode()
 * @property {QAction} onActionChooseSelectToolInColorMode()
 * @property {QAction} onActionChoosePaintToolInPaintMode()
 * @property {QAction} onActionChooseInkTool()
 * @property {QAction} onActionChoosePaintToolInRepaintMode()
 * @property {QAction} onActionChoosePaintToolInUnpaintMode()
 * @property {QAction} onActionChoosePaintToolInPaintUnpaintedMode()
 * @property {QAction} onActionChooseBrushToolInBrushMode()
 * @property {QAction} onActionChooseBrushToolInRepaintBrushMode()
 * @property {QAction} onActionToggleDrawBehindMode()
 * @property {QAction} onActionWhatsThis()
 * @property {QAction} onActionEditProperties()
 */

/**
 * Actions available in the sceneUI responder.
 * @name actions#sceneUI
 * @property {QAction} onActionSaveLayouts()
 * @property {QAction} onActionSaveWorkspaceAs()
 * @property {QAction} onActionShowLayoutManager()
 * @property {QAction} onActionFullscreen()
 * @property {QAction} onActionRaiseArea(QString,bool)
 * @property {QAction} onActionRaiseArea(QString)
 * @property {QAction} onActionSetLayout(QString,int)
 * @property {QAction} onActionLockScene()
 * @property {QAction} onActionLockSceneVersion()
 * @property {QAction} onActionPaintModePaletteManager()
 * @property {QAction} onActionPaintModeLogView()
 * @property {QAction} onActionPaintModeModelView()
 * @property {QAction} onActionPaintModeToolPropertiesView()
 * @property {QAction} onActionUndo()
 * @property {QAction} onActionUndo(int)
 * @property {QAction} onActionRedo()
 * @property {QAction} onActionRedo(int)
 * @property {QAction} onActionShowCurrentDrawingOnTop()
 * @property {QAction} onActionShowWelcomeScreen()
 * @property {QAction} onActionShowWelcomeScreenQuit()
 * @property {QAction} onActionSaveLayoutInScene()
 * @property {QAction} onActionNewView(int)
 * @property {QAction} onActionNewView(QString)
 * @property {QAction} onActionNewViewChecked(QString)
 * @property {QAction} onActionToggleRenderer()
 * @property {QAction} onActionToggleBBoxHighlighting()
 * @property {QAction} onActionToggleShowLockedDrawingsInOutline()
 * @property {QAction} onActionCancelSoftRender()
 * @property {QAction} onActionCheckFiles()
 * @property {QAction} onActionCleanPaletteLists()
 * @property {QAction} onActionDeleteVersions()
 * @property {QAction} onActionMacroManager()
 * @property {QAction} onActionRestoreDefaultLayout()
 * @property {QAction} onActionExit()
 * @property {QAction} onActionExitDelayed()
 * @property {QAction} onActionAddVectorDrawing()
 * @property {QAction} onActionAddSound()
 * @property {QAction} onActionAddPeg()
 * @property {QAction} onActionToggleShowMergeSelectionDialog()
 * @property {QAction} onActionToggleShowScanDialog()
 * @property {QAction} onActionSetPreviewResolution(int)
 * @property {QAction} onActionSetTempoMarker()
 * @property {QAction} onActionSingleFlip()
 * @property {QAction} onActionNewScene()
 * @property {QAction} onActionNewSceneDelayed()
 * @property {QAction} onActionOpen()
 * @property {QAction} onActionOpenDelayed()
 * @property {QAction} onActionOpenScene()
 * @property {QAction} onActionOpenSceneDelayed()
 * @property {QAction} onActionOpenScene(QString)
 * @property {QAction} onActionSaveEverything()
 * @property {QAction} onActionSaveEverythingIncludingSceneMachineFrames()
 * @property {QAction} onActionSaveAsScene()
 * @property {QAction} onActionSaveVersion()
 * @property {QAction} onActionSaveDialog()
 * @property {QAction} onActionImportDrawings()
 * @property {QAction} onActionImport3dmodels()
 * @property {QAction} onActionImportTimings()
 * @property {QAction} onActionScanDrawings()
 * @property {QAction} onActionImportLocalLibrary()
 * @property {QAction} onActionImportSound()
 * @property {QAction} onActionMmxImport()
 * @property {QAction} onActionFlashExport()
 * @property {QAction} onActionFLVExport()
 * @property {QAction} onActionMmxExport()
 * @property {QAction} onActionSoundtrackExport()
 * @property {QAction} onActionComposite()
 * @property {QAction} onActionCompositeBatchOnly()
 * @property {QAction} onActionSaveOpenGLFrames()
 * @property {QAction} onActionToggleFlipForCustomMarkedType(QString)
 * @property {QAction} onActionCreateFullImport()
 * @property {QAction} onActionPerformFullImport()
 * @property {QAction} onActionPerformPartialImport()
 * @property {QAction} onActionPerformPartialUpdate()
 * @property {QAction} onActionToggleToolBar(QString)
 * @property {QAction} onActionSetDefaultDisplay(QString)
 * @property {QAction} onActionCloseScene()
 * @property {QAction} onActionCloseSceneDelayed()
 * @property {QAction} onActionCloseThenReopen()
 * @property {QAction} onActionOpenDrawings()
 * @property {QAction} onActionOpenDrawingsDelayed()
 * @property {QAction} onActionOpenDrawingsModify()
 * @property {QAction} onActionOpenElements()
 * @property {QAction} onActionOpenElementsDelayed()
 * @property {QAction} onActionClearRecentSceneList()
 * @property {QAction} onActionOpenBackgroundFile()
 * @property {QAction} onActionUnloadBackground()
 * @property {QAction} onActionScaleBackgroundUp()
 * @property {QAction} onActionScaleBackgroundDown()
 * @property {QAction} onActionResetBackgroundPosition()
 * @property {QAction} onActionSetDrawingMarksFlipKey()
 * @property {QAction} onActionSetDrawingMarksFlipBreakdown()
 * @property {QAction} onActionSetDrawingMarksFlipInBetween()
 * @property {QAction} onActionChooseSelectTool()
 * @property {QAction} onActionChooseContourEditorTool()
 * @property {QAction} onActionChooseCenterlineEditorTool()
 * @property {QAction} onActionChooseDeformTool()
 * @property {QAction} onActionChoosePerspectiveTool()
 * @property {QAction} onActionChooseEnvelopeTool()
 * @property {QAction} onActionChooseCutterTool()
 * @property {QAction} onActionChooseMorphTool()
 * @property {QAction} onActionChoosePivotTool()
 * @property {QAction} onActionChooseBrushTool()
 * @property {QAction} onActionChooseRepositionAllDrawingsTool()
 * @property {QAction} onActionChooseEraserTool()
 * @property {QAction} onActionChooseRepaintBrushTool()
 * @property {QAction} onActionChoosePencilTool()
 * @property {QAction} onActionChoosePencilEditorTool()
 * @property {QAction} onActionChooseLineTool()
 * @property {QAction} onActionChoosePolylineTool()
 * @property {QAction} onActionChooseRectangleTool()
 * @property {QAction} onActionChooseEllipseTool()
 * @property {QAction} onActionChoosePaintTool()
 * @property {QAction} onActionChooseInkTool()
 * @property {QAction} onActionChoosePaintUnpaintedTool()
 * @property {QAction} onActionChooseRepaintTool()
 * @property {QAction} onActionChooseStampTool()
 * @property {QAction} onActionChooseStrokeTool()
 * @property {QAction} onActionChooseCloseGapTool()
 * @property {QAction} onActionChooseUnpaintTool()
 * @property {QAction} onActionChooseDropperTool()
 * @property {QAction} onActionChooseEditTransformTool()
 * @property {QAction} onActionChooseGrabberTool()
 * @property {QAction} onActionChooseZoomTool()
 * @property {QAction} onActionChooseRotateTool()
 * @property {QAction} onActionChooseThirdPersonNavigation3dTool()
 * @property {QAction} onActionChooseFirstPersonNavigation3dTool()
 * @property {QAction} onActionChooseShiftAndTraceTool()
 * @property {QAction} onActionChooseNoTool()
 * @property {QAction} onActionChooseResizePenStyleTool()
 * @property {QAction} onActionChooseSpSelectTool()
 * @property {QAction} onActionChooseSpTranslateTool()
 * @property {QAction} onActionChooseSpRotateTool()
 * @property {QAction} onActionChooseSpScaleTool()
 * @property {QAction} onActionChooseSpSkewTool()
 * @property {QAction} onActionChooseSpMaintainSizeTool()
 * @property {QAction} onActionChooseSpTransformTool()
 * @property {QAction} onActionChooseSpInverseKinematicsTool()
 * @property {QAction} onActionChooseSpOffsetZTool()
 * @property {QAction} onActionChooseSpSplineOffsetTool()
 * @property {QAction} onActionChooseSpSmoothEditingTool()
 * @property {QAction} onActionChooseMoveBackgroundTool()
 * @property {QAction} onActionChooseTextTool()
 * @property {QAction} onActionActivatePreset(int)
 * @property {QAction} onActionToggleKeyframeMode()
 * @property {QAction} onActionAnimatedKeyframeMode()
 * @property {QAction} onActionAnimatedOnRangeKeyframeMode()
 * @property {QAction} onActionStaticKeyframeMode()
 * @property {QAction} onActionSetKeyframeMode()
 * @property {QAction} onActionSetAllKeyframesMode()
 * @property {QAction} onActionSetConstantSegMode()
 * @property {QAction} onActionMainPlay()
 * @property {QAction} onActionMainPlayFw()
 * @property {QAction} onActionMainPlayBw()
 * @property {QAction} onActionMainPlayPreviewFw()
 * @property {QAction} onActionMainPlayPreviewSwf()
 * @property {QAction} onActionMainStopPlaying()
 * @property {QAction} onActionMainToggleLoopPlay()
 * @property {QAction} onActionMainToggleEnableCacheForPlay()
 * @property {QAction} onActionMainToggleEnableSoundForPlay()
 * @property {QAction} onActionMainToggleEnableSoundScrubbing()
 * @property {QAction} onActionChooseSpRepositionTool()
 * @property {QAction} onActionMainSetPlaybackStartFrame()
 * @property {QAction} onActionMainSetPlaybackStopFrame()
 * @property {QAction} onActionMainGotoFrame()
 * @property {QAction} onActionMainSetPlaybackSpeed()
 * @property {QAction} onActionMainGotoFirstFrame()
 * @property {QAction} onActionMainGotoPreviousFrame()
 * @property {QAction} onActionMainGotoLastFrame()
 * @property {QAction} onActionMainGotoNextFrame()
 * @property {QAction} onActionToggleSideViewPlayback()
 * @property {QAction} onActionToggleTopViewPlayback()
 * @property {QAction} onActionTogglePersViewPlayback()
 * @property {QAction} onActionReshapeMultipleKeyframes()
 * @property {QAction} onActionJogForward()
 * @property {QAction} onActionJogBackward()
 * @property {QAction} onActionShuttleForward()
 * @property {QAction} onActionShuttleBackward()
 * @property {QAction} onActionShuttleReset()
 * @property {QAction} onActionConformationImport()
 * @property {QAction} onActionShowPreferenceDialog()
 * @property {QAction} onActionShowShortcutsDialog()
 * @property {QAction} onActionManageLocalCaches()
 * @property {QAction} onActionReadChangedDrawings()
 * @property {QAction} onActionReadChangedDrawingsNoWarning()
 * @property {QAction} onActionPaletteOperations()
 * @property {QAction} onActionToggleDebugMode()
 * @property {QAction} onActionHelp()
 * @property {QAction} onActionHtmlHelp(QString)
 * @property {QAction} onActionOpenBook(QString)
 * @property {QAction} onActionAbout()
 * @property {QAction} onActionCEIP()
 * @property {QAction} onActionShowLicense()
 * @property {QAction} onActionShowReadme()
 * @property {QAction} onActionOpenURL(QString,int)
 * @property {QAction} onActionOpenURL(QString)
 * @property {QAction} onActionTerminate()
 * @property {QAction} onActionToggleGoogleAnalytics()
 */

/**
 * Actions available in the scriptResponder responder.
 * @name actions#scriptResponder
 * @property {QAction} onActionExecuteScript(QString)
 * @property {QAction} onActionExecuteScriptWithValidator(QString,AC_ActionInfo*)
 * @property {QAction} onActionActivateTool(int)
 * @property {QAction} onActionActivateToolByName(QString)
 */

/**
 * Actions available in the selectionResponder responder.
 * @name actions#selectionResponder
 */

/**
 * Actions available in the sessionResponder responder.
 * @name actions#sessionResponder
 * @property {QAction} onActionFixSymbolCompositeAndDisplay()
 */

/**
 * Actions available in the timelineView responder.
 * @name actions#timelineView
 * @property {QAction} onActionPropagateLayerSelection()
 */

/**
 * Actions available in the toolProperties responder.
 * @name actions#toolProperties
 * @property {QAction} onActionNewBrush()
 * @property {QAction} onActionDeleteBrush()
 * @property {QAction} onActionRenameBrush()
 * @property {QAction} onActionEditBrush()
 * @property {QAction} onActionImportBrushes()
 * @property {QAction} onActionExportBrushes()
 * @property {QAction} onActionShowSmallThumbnail()
 * @property {QAction} onActionShowLargeThumbnail()
 * @property {QAction} onActionShowStroke()
 */

/**
 * Actions available in the toolPropertiesView responder.
 * @name actions#toolPropertiesView
 */

/**
 * Actions available in the xsheetView responder.
 * @name actions#xsheetView
 * @property {QAction} onActionPrintXsheet()
 * @property {QAction} onActionResetCellsSize()
 * @property {QAction} onActionZoomIn()
 * @property {QAction} onActionZoomOut()
 * @property {QAction} onActionZoomExtents()
 * @property {QAction} onActionResetZoom()
 * @property {QAction} onActionResetPan()
 * @property {QAction} onActionResetView()
 * @property {QAction} onActionShowUnhideObjectsEditor()
 * @property {QAction} onActionUnhideAllColumns()
 * @property {QAction} onActionXsheetHoldValueMenu(int)
 * @property {QAction} onActionSendToFunctionView()
 * @property {QAction} onActionToggleShowGrouping()
 * @property {QAction} onActionToggleMinimalHeaders()
 * @property {QAction} onActionDisplayShowDlg()
 * @property {QAction} onActionToggleInsertMode()
 * @property {QAction} onActionToggleGesturalDrag()
 * @property {QAction} onActionToggleThumbnails()
 * @property {QAction} onActionToggleIsShowDrawingCols()
 * @property {QAction} onActionToggleIsShowFunctionCols()
 * @property {QAction} onActionToggleIsShowPath3dCols()
 * @property {QAction} onActionToggleIsShow3dRotationCols()
 * @property {QAction} onActionToggleIsShowSoundCols()
 * @property {QAction} onActionToggleSidePanel()
 * @property {QAction} onActionXsheetHeldFramesLine(int)
 * @property {QAction} onActionXsheetEmptyCellsX(int)
 * @property {QAction} onActionXsheetLabelsFrames(int)
 * @property {QAction} onActionSelectedElementSwapToNextDrawing()
 * @property {QAction} onActionSelectedElementSwapToPrevDrawing()
 * @property {QAction} onActionToggleSelection()
 * @property {QAction} onActionTag()
 * @property {QAction} onActionUntag()
 * @property {QAction} onActionUntagAllOthers()
 * @property {QAction} onActionTagPublic()
 * @property {QAction} onActionUntagPublic()
 * @property {QAction} onActionUntagPublicAllOthers()
 */