#pragma once

#include "Engine.h"
#include "AvalonPublishInstance.generated.h"


UCLASS(Blueprintable)
class AVALON_API UAvalonPublishInstance : public UObject
{
	GENERATED_BODY()

public:
	UAvalonPublishInstance(const FObjectInitializer& ObjectInitalizer);

	UPROPERTY(EditAnywhere, BlueprintReadOnly)
		TArray<FString> assets;
private:
	void OnAssetAdded(const FAssetData& AssetData);
	void OnAssetRemoved(const FAssetData& AssetData);
	void OnAssetRenamed(const FAssetData& AssetData, const FString& str);
};