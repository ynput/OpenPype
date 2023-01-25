// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Framework/Commands/Commands.h"
#include "OpenPypeStyle.h"

class FOpenPypeCommands : public TCommands<FOpenPypeCommands>
{
public:

	FOpenPypeCommands()
		: TCommands<FOpenPypeCommands>(TEXT("OpenPype"), NSLOCTEXT("Contexts", "OpenPype", "OpenPype Tools"), NAME_None, FOpenPypeStyle::GetStyleSetName())
	{
	}

	// TCommands<> interface
	virtual void RegisterCommands() override;

public:
	TSharedPtr< FUICommandInfo > OpenPypeTools;
	TSharedPtr< FUICommandInfo > OpenPypeToolsDialog;
};
