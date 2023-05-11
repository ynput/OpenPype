// Fill out your copyright notice in the Description page of Project Settings.

#include "AyonAssetContainer.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Misc/PackageName.h"
#include "Containers/UnrealString.h"

UAyonAssetContainer::UAyonAssetContainer(const FObjectInitializer& ObjectInitializer)
: UAssetUserData(ObjectInitializer)
{
	FAssetRegistryModule& AssetRegistryModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
	FString path = UAyonAssetContainer::GetPathName();
	UE_LOG(LogTemp, Warning, TEXT("UAyonAssetContainer %s"), *path);
	FARFilter Filter;
	Filter.PackagePaths.Add(FName(*path));

	AssetRegistryModule.Get().OnAssetAdded().AddUObject(this, &UAyonAssetContainer::OnAssetAdded);
	AssetRegistryModule.Get().OnAssetRemoved().AddUObject(this, &UAyonAssetContainer::OnAssetRemoved);
	AssetRegistryModule.Get().OnAssetRenamed().AddUObject(this, &UAyonAssetContainer::OnAssetRenamed);
}

void UAyonAssetContainer::OnAssetAdded(const FAssetData& AssetData)
{
	TArray<FString> split;

	// get directory of current container
	FString selfFullPath = UAyonAssetContainer::GetPathName();
	FString selfDir = FPackageName::GetLongPackagePath(*selfFullPath);

	// get asset path and class
	FString assetPath = AssetData.GetFullName();
	FString assetFName = AssetData.ObjectPath.ToString();
	UE_LOG(LogTemp, Log, TEXT("asset name %s"), *assetFName);
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

void UAyonAssetContainer::OnAssetRemoved(const FAssetData& AssetData)
{
	TArray<FString> split;

	// get directory of current container
	FString selfFullPath = UAyonAssetContainer::GetPathName();
	FString selfDir = FPackageName::GetLongPackagePath(*selfFullPath);

	// get asset path and class
	FString assetPath = AssetData.GetFullName();
	FString assetFName = AssetData.ObjectPath.ToString();

	// split path
	assetPath.ParseIntoArray(split, TEXT(" "), true);

	FString assetDir = FPackageName::GetLongPackagePath(*split[1]);

	// take interest only in paths starting with path of current container
	FString path = UAyonAssetContainer::GetPathName();
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

void UAyonAssetContainer::OnAssetRenamed(const FAssetData& AssetData, const FString& str)
{
	TArray<FString> split;

	// get directory of current container
	FString selfFullPath = UAyonAssetContainer::GetPathName();
	FString selfDir = FPackageName::GetLongPackagePath(*selfFullPath);

	// get asset path and class
	FString assetPath = AssetData.GetFullName();
	FString assetFName = AssetData.ObjectPath.ToString();

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
