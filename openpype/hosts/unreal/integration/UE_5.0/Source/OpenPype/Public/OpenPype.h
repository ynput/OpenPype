// Copyright 1998-2019 Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Modules/ModuleManager.h"

#include "IWebSocket.h"       // Socket definition


class FOpenPypeModule : public IModuleInterface
{
public:
	virtual void StartupModule() override;
	virtual void ShutdownModule() override;

private:
	void RegisterMenus();
	void MapCommands();

	void MenuPopup();
	void MenuDialog();

	void TestMethod();

private:
	TSharedPtr<class FUICommandList> PluginCommands;
};
