// Copyright 2023, Ayon, All rights reserved.

#pragma once

#include "CoreMinimal.h"


class FAyonModule : public IModuleInterface
{
public:
	virtual void StartupModule() override;
	virtual void ShutdownModule() override;

private:
	void RegisterMenus();
	void RegisterSettings();
	bool HandleSettingsSaved();

	void MenuPopup();
	void MenuDialog();

private:
	TSharedPtr<class FUICommandList> PluginCommands;
};
