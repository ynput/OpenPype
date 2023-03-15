// Copyright 2023, Ayon, All rights reserved.

#pragma once

#include "Engine.h"
#include "IWebSocket.h"       // Socket definition


class FOpenPypeModule : public IModuleInterface
{
public:
	virtual void StartupModule() override;
	virtual void ShutdownModule() override;

private:
	void RegisterSettings();
	bool HandleSettingsSaved();

	void AddMenuEntry(FMenuBuilder& MenuBuilder);
	void AddToobarEntry(FToolBarBuilder& ToolbarBuilder);
	void MenuPopup();
	void MenuDialog();

	void CreateSocket();
	void ConnectToSocket();

private:
	TSharedPtr<IWebSocket> Socket;
};
