// Copyright Epic Games, Inc. All Rights Reserved.

#include "OpenPypeCommands.h"

#define LOCTEXT_NAMESPACE "OpenPypeModule"

void FOpenPypeCommands::RegisterCommands()
{
	UI_COMMAND(OpenPypeLoaderTool, "Load", "Open loader tool", EUserInterfaceActionType::Button, FInputChord());
	UI_COMMAND(OpenPypeCreatorTool, "Create", "Open creator tool", EUserInterfaceActionType::Button, FInputChord());
	UI_COMMAND(OpenPypeSceneInventoryTool, "Scene inventory", "Open scene inventory tool", EUserInterfaceActionType::Button, FInputChord());
	UI_COMMAND(OpenPypePublishTool, "Publish", "Open publisher", EUserInterfaceActionType::Button, FInputChord());
}

#undef LOCTEXT_NAMESPACE
