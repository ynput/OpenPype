
// Copyright 2023, Ayon, All rights reserved.

#include "OpenPypeCommands.h"

#define LOCTEXT_NAMESPACE "FOpenPypeModule"

void FOpenPypeCommands::RegisterCommands()
{
	UI_COMMAND(OpenPypeLoaderTool, "Load", "Open loader tool", EUserInterfaceActionType::Button, FInputChord());
	UI_COMMAND(OpenPypeCreatorTool, "Create", "Open creator tool", EUserInterfaceActionType::Button, FInputChord());
	UI_COMMAND(OpenPypeSceneInventoryTool, "Scene inventory", "Open scene inventory tool", EUserInterfaceActionType::Button, FInputChord());
	UI_COMMAND(OpenPypePublishTool, "Publish", "Open publisher", EUserInterfaceActionType::Button, FInputChord());
}

#undef LOCTEXT_NAMESPACE
