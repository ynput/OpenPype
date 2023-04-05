// Copyright 2023, Ayon, All rights reserved.

#pragma once

#include "CoreMinimal.h"
#include "Framework/Commands/Commands.h"
#include "AyonStyle.h"

class FAyonCommands : public TCommands<FAyonCommands>
{
public:

	FAyonCommands()
		: TCommands<FAyonCommands>(TEXT("Ayon"), NSLOCTEXT("Contexts", "Ayon", "Ayon Tools"), NAME_None, FAyonStyle::GetStyleSetName())
	{
	}

	// TCommands<> interface
	virtual void RegisterCommands() override;

public:
	TSharedPtr< FUICommandInfo > AyonTools;
	TSharedPtr< FUICommandInfo > AyonToolsDialog;
};
