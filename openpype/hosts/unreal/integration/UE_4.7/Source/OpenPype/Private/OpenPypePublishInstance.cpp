#pragma once

#include "OpenPypePublishInstance.h"
#include "AssetRegistryModule.h"


UOpenPypePublishInstance::UOpenPypePublishInstance(const FObjectInitializer& ObjectInitializer)
	: UObject(ObjectInitializer)
{
	FAssetRegistryModule& AssetRegistryModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
	FString path = UOpenPypePublishInstance::GetPathName();
	FARFilter Filter;
	Filter.PackagePaths.Add(FName(*path));

	AssetRegistryModule.Get().OnAssetAdded().AddUObject(this, &UOpenPypePublishInstance::OnAssetAdded);
	AssetRegistryModule.Get().OnAssetRemoved().AddUObject(this, &UOpenPypePublishInstance::OnAssetRemoved);
	AssetRegistryModule.Get().OnAssetRenamed().AddUObject(this, &UOpenPypePublishInstance::OnAssetRenamed);
}

void UOpenPypePublishInstance::OnAssetAdded(const FAssetData& AssetData)
{
	TArray<FString> split;

	// get directory of current container
	FString selfFullPath = UOpenPypePublishInstance::GetPathName();
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
		if (assetFName != "OpenPypePublishInstance")
		{
			assets.Add(assetPath);
			UE_LOG(LogTemp, Log, TEXT("%s: asset added to %s"), *selfFullPath, *selfDir);
		}
	}
}

void UOpenPypePublishInstance::OnAssetRemoved(const FAssetData& AssetData)
{
	TArray<FString> split;

	// get directory of current container
	FString selfFullPath = UOpenPypePublishInstance::GetPathName();
	FString selfDir = FPackageName::GetLongPackagePath(*selfFullPath);

	// get asset path and class
	FString assetPath = AssetData.GetFullName();
	FString assetFName = AssetData.AssetClass.ToString();

	// split path
	assetPath.ParseIntoArray(split, TEXT(" "), true);

	FString assetDir = FPackageName::GetLongPackagePath(*split[1]);

	// take interest only in paths starting with path of current container
	FString path = UOpenPypePublishInstance::GetPathName();
	FString lpp = FPackageName::GetLongPackagePath(*path);

	if (assetDir.StartsWith(*selfDir))
	{
		// exclude self
		if (assetFName != "OpenPypePublishInstance")
		{
			// UE_LOG(LogTemp, Warning, TEXT("%s: asset removed"), *lpp);
			assets.Remove(assetPath);
		}
	}
}

void UOpenPypePublishInstance::OnAssetRenamed(const FAssetData& AssetData, const FString& str)
{
	TArray<FString> split;

	// get directory of current container
	FString selfFullPath = UOpenPypePublishInstance::GetPathName();
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
			// UE_LOG(LogTemp, Warning, TEXT("%s: asset renamed %s"), *lpp, *str);
		}
	}
}
