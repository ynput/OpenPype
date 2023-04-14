// Copyright 2023, Ayon, All rights reserved.

#include "AyonSettings.h"

#include "Interfaces/IPluginManager.h"

/**
 * Mainly is used for initializing default values if the DefaultAyonSettings.ini file does not exist in the saved config
 */
UAyonSettings::UAyonSettings(const FObjectInitializer& ObjectInitializer)
{

	const FString ConfigFilePath = AYON_SETTINGS_FILEPATH;

	// This has to be probably in the future set using the UE Reflection system
	FColor Color;
	GConfig->GetColor(TEXT("/Script/Ayon.AyonSettings"), TEXT("FolderColor"), Color, ConfigFilePath);

	FolderColor = Color;
}
