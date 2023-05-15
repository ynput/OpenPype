// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "UObject/NoExportTypes.h"
#include "Engine/AssetUserData.h"
#include "AssetData.h"
#include "AyonAssetContainer.generated.h"

/**
 * 
 */
UCLASS(Blueprintable)
class AYON_API UAyonAssetContainer : public UAssetUserData
{
	GENERATED_BODY()
	
public:

	UAyonAssetContainer(const FObjectInitializer& ObjectInitalizer);
	// ~UAyonAssetContainer();

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Assets")
		TArray<FString> assets;

	// There seems to be no reflection option to expose array of FAssetData
	/*
	UPROPERTY(Transient, BlueprintReadOnly, Category = "Python", meta=(DisplayName="Assets Data"))
		TArray<FAssetData> assetsData;
	*/
private:
	TArray<FAssetData> assetsData;
	void OnAssetAdded(const FAssetData& AssetData);
	void OnAssetRemoved(const FAssetData& AssetData);
	void OnAssetRenamed(const FAssetData& AssetData, const FString& str);
};


