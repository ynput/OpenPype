// Copyright 1998-2019 Epic Games, Inc. All Rights Reserved.

#pragma once

#include "Engine.h"


class FOpenPypeModule : public IModuleInterface
{
public:
	virtual void StartupModule() override;
	virtual void ShutdownModule() override;

private:

	void AddMenuEntry(FMenuBuilder& MenuBuilder);
	void AddToobarEntry(FToolBarBuilder& ToolbarBuilder);
	void MenuPopup();
	void MenuDialog();

};
