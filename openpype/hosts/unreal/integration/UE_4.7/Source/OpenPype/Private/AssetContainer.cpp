// Fill out your copyright notice in the Description page of Project Settings.

#include "AssetContainer.h"
#include "AssetRegistryModule.h"
#include "Misc/PackageName.h"
#include "Engine.h"
#include "Containers/UnrealString.h"

UAssetContainer::UAssetContainer(const FObjectInitializer& ObjectInitializer)
: UAssetUserData(ObjectInitializer)
{
	FAssetRegistryModule& AssetRegistryModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
	FString path = UAssetContainer::GetPathName();
	UE_LOG(LogTemp, Warning, TEXT("UAssetContainer %s"), *path);
	FARFilter Filter;
	Filter.PackagePaths.Add(FName(*path));
	
	AssetRegistryModule.Get().OnAssetAdded().AddUObject(this, &UAssetContainer::OnAssetAdded);
	AssetRegistryModule.Get().OnAssetRemoved().AddUObject(this, &UAssetContainer::OnAssetRemoved);
	AssetRegistryModule.Get().OnAssetRenamed().AddUObject(this, &UAssetContainer::OnAssetRenamed);
}

void UAssetContainer::OnAssetAdded(const FAssetData& AssetData)
{
	TArray<FString> split;

	// get directory of current container
	FString selfFullPath = UAssetContainer::GetPathName();
	FString selfDir = FPackageName::GetLongPackagePath(*selfFullPath);

	// get asset path and class
	FString assetPath = AssetData.GetFullName();
	FString assetFName = AssetData.AssetClass.ToString();
	
	// split path
	assetPath.ParseIntoArray(split, TEXT(" "), true);

	FString assetDir = FPackageName::GetLongPackagePath(*split[1]);
	
	// take interest only in paths starting with path of current container
	if (assetDir.StartsWith(*selfDir))
	{
		// exclude self
		if (assetFName != "AssetContainer")
		{
			assets.Add(assetPath);
			assetsData.Add(AssetData);
			UE_LOG(LogTemp, Log, TEXT("%s: asset added to %s"), *selfFullPath, *selfDir);
		}
	}
}

void UAssetContainer::OnAssetRemoved(const FAssetData& AssetData)
{
	TArray<FString> split;

	// get directory of current container
	FString selfFullPath = UAssetContainer::GetPathName();
	FString selfDir = FPackageName::GetLongPackagePath(*selfFullPath);

	// get asset path and class
	FString assetPath = AssetData.GetFullName();
	FString assetFName = AssetData.AssetClass.ToString();

	// split path
	assetPath.ParseIntoArray(split, TEXT(" "), true);

	FString assetDir = FPackageName::GetLongPackagePath(*split[1]);

	// take interest only in paths starting with path of current container
	FString path = UAssetContainer::GetPathName();
	FString lpp = FPackageName::GetLongPackagePath(*path);

	if (assetDir.StartsWith(*selfDir))
	{
		// exclude self
		if (assetFName != "AssetContainer")
		{
			// UE_LOG(LogTemp, Warning, TEXT("%s: asset removed"), *lpp);
			assets.Remove(assetPath);
			assetsData.Remove(AssetData);
		}
	}
}

void UAssetContainer::OnAssetRenamed(const FAssetData& AssetData, const FString& str)
{
	TArray<FString> split;

	// get directory of current container
	FString selfFullPath = UAssetContainer::GetPathName();
	FString selfDir = FPackageName::GetLongPackagePath(*selfFullPath);

	// get asset path and class
	FString assetPath = AssetData.GetFullName();
	FString assetFName = AssetData.AssetClass.ToString();

	// split path
	assetPath.ParseIntoArray(split, TEXT(" "), true);

	FString assetDir = FPackageName::GetLongPackagePath(*split[1]);
	if (assetDir.StartsWith(*selfDir))
	{
		// exclude self
		if (assetFName != "AssetContainer")
		{

			assets.Remove(str);
			assets.Add(assetPath);
			assetsData.Remove(AssetData);
			// UE_LOG(LogTemp, Warning, TEXT("%s: asset renamed %s"), *lpp, *str);
		}
	}
}

