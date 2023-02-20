// Copyright 2023, Ayon, All rights reserved.

#include "OpenPypeSettings.h"

#include "Interfaces/IPluginManager.h"

/**
 * Mainly is used for initializing default values if the DefaultOpenPypeSettings.ini file does not exist in the saved config
 */
UOpenPypeSettings::UOpenPypeSettings(const FObjectInitializer& ObjectInitializer)
{
	
	const FString ConfigFilePath = OPENPYPE_SETTINGS_FILEPATH;

	// This has to be probably in the future set using the UE Reflection system
	FColor Color;
	GConfig->GetColor(TEXT("/Script/OpenPype.OpenPypeSettings"), TEXT("FolderColor"), Color, ConfigFilePath);

	FolderColor = Color;
}