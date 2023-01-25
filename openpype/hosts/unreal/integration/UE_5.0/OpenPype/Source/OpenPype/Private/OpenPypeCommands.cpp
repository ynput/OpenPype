// Copyright Epic Games, Inc. All Rights Reserved.

#include "OpenPypeCommands.h"

#define LOCTEXT_NAMESPACE "FOpenPypeModule"

void FOpenPypeCommands::RegisterCommands()
{
	UI_COMMAND(OpenPypeTools, "OpenPype Tools", "Pipeline tools", EUserInterfaceActionType::Button, FInputChord());
	UI_COMMAND(OpenPypeToolsDialog, "OpenPype Tools Dialog", "Pipeline tools dialog", EUserInterfaceActionType::Button, FInputChord());
}

#undef LOCTEXT_NAMESPACE
