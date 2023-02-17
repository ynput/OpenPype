// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "UObject/NoExportTypes.h"
#include "Engine/AssetUserData.h"
#include "AssetData.h"
#include "AssetContainer.generated.h"

/**
 * 
 */
UCLASS(Blueprintable)
class OPENPYPE_API UAssetContainer : public UAssetUserData
{
	GENERATED_BODY()
	
public:

	UAssetContainer(const FObjectInitializer& ObjectInitalizer);
	// ~UAssetContainer();

	UPROPERTY(EditAnywhere, BlueprintReadOnly)
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


