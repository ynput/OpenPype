// Copyright 2023, Ayon, All rights reserved.

#include "OpenPypeCommands.h"

#define LOCTEXT_NAMESPACE "FOpenPypeModule"

void FOpenPypeCommands::RegisterCommands()
{
	UI_COMMAND(OpenPypeTools, "OpenPype Tools", "Pipeline tools", EUserInterfaceActionType::Button, FInputChord());
	UI_COMMAND(OpenPypeToolsDialog, "OpenPype Tools Dialog", "Pipeline tools dialog", EUserInterfaceActionType::Button, FInputChord());
}

#undef LOCTEXT_NAMESPACE
