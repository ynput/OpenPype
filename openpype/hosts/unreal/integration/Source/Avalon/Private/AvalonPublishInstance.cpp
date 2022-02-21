#pragma once

#include "AvalonPublishInstance.h"
#include "AssetRegistryModule.h"


UAvalonPublishInstance::UAvalonPublishInstance(const FObjectInitializer& ObjectInitializer)
	: UObject(ObjectInitializer)
{
	FAssetRegistryModule& AssetRegistryModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
	FString path = UAvalonPublishInstance::GetPathName();
	FARFilter Filter;
	Filter.PackagePaths.Add(FName(*path));

	AssetRegistryModule.Get().OnAssetAdded().AddUObject(this, &UAvalonPublishInstance::OnAssetAdded);
	AssetRegistryModule.Get().OnAssetRemoved().AddUObject(this, &UAvalonPublishInstance::OnAssetRemoved);
	AssetRegistryModule.Get().OnAssetRenamed().AddUObject(this, &UAvalonPublishInstance::OnAssetRenamed);
}

void UAvalonPublishInstance::OnAssetAdded(const FAssetData& AssetData)
{
	TArray<FString> split;

	// get directory of current container
	FString selfFullPath = UAvalonPublishInstance::GetPathName();
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
		if (assetFName != "AvalonPublishInstance")
		{
			assets.Add(assetPath);
			UE_LOG(LogTemp, Log, TEXT("%s: asset added to %s"), *selfFullPath, *selfDir);
		}
	}
}

void UAvalonPublishInstance::OnAssetRemoved(const FAssetData& AssetData)
{
	TArray<FString> split;

	// get directory of current container
	FString selfFullPath = UAvalonPublishInstance::GetPathName();
	FString selfDir = FPackageName::GetLongPackagePath(*selfFullPath);

	// get asset path and class
	FString assetPath = AssetData.GetFullName();
	FString assetFName = AssetData.AssetClass.ToString();

	// split path
	assetPath.ParseIntoArray(split, TEXT(" "), true);

	FString assetDir = FPackageName::GetLongPackagePath(*split[1]);

	// take interest only in paths starting with path of current container
	FString path = UAvalonPublishInstance::GetPathName();
	FString lpp = FPackageName::GetLongPackagePath(*path);

	if (assetDir.StartsWith(*selfDir))
	{
		// exclude self
		if (assetFName != "AvalonPublishInstance")
		{
			// UE_LOG(LogTemp, Warning, TEXT("%s: asset removed"), *lpp);
			assets.Remove(assetPath);
		}
	}
}

void UAvalonPublishInstance::OnAssetRenamed(const FAssetData& AssetData, const FString& str)
{
	TArray<FString> split;

	// get directory of current container
	FString selfFullPath = UAvalonPublishInstance::GetPathName();
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
