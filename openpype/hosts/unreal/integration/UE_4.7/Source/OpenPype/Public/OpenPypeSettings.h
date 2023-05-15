// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "Object.h"
#include "OpenPypeSettings.generated.h"

#define OPENPYPE_SETTINGS_FILEPATH IPluginManager::Get().FindPlugin("OpenPype")->GetBaseDir() / TEXT("Config") / TEXT("DefaultOpenPypeSettings.ini")

UCLASS(Config=OpenPypeSettings, DefaultConfig)
class OPENPYPE_API UOpenPypeSettings : public UObject
{
	GENERATED_UCLASS_BODY()
	
	UFUNCTION(BlueprintCallable, BlueprintPure, Category = Settings)
	FColor GetFolderFColor() const
	{
		return FolderColor;
	}
	
	UFUNCTION(BlueprintCallable, BlueprintPure, Category = Settings)
	FLinearColor GetFolderFLinearColor() const
	{
		return FLinearColor(FolderColor);
	}

protected:

	UPROPERTY(config, EditAnywhere, Category = Folders)
	FColor FolderColor = FColor(25,45,223);
};