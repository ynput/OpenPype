#pragma once

#include "Engine.h"
#include "OpenPypePublishInstance.generated.h"


UCLASS(Blueprintable)
class OPENPYPE_API UOpenPypePublishInstance : public UObject
{
	GENERATED_BODY()

public:
	UOpenPypePublishInstance(const FObjectInitializer& ObjectInitalizer);

	UPROPERTY(EditAnywhere, BlueprintReadOnly)
		TArray<FString> assets;
private:
	void OnAssetAdded(const FAssetData& AssetData);
	void OnAssetRemoved(const FAssetData& AssetData);
	void OnAssetRenamed(const FAssetData& AssetData, const FString& str);
};