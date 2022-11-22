#pragma once

#include "Engine.h"
#include "OpenPypePublishInstance.generated.h"


UCLASS(Blueprintable)
class OPENPYPE_API UOpenPypePublishInstance : public UPrimaryDataAsset
{
	GENERATED_UCLASS_BODY()
	
public:
	
	UPROPERTY(VisibleAnywhere,BlueprintReadOnly)
	TSet<UObject*> AssetDataInternal;
	
	/**
	 * This property allows exposing the array to include other assets from any other directory than what it's currently
	 * monitoring. NOTE: that these assets have to be added manually! They are not automatically registered or added!
	 */
	UPROPERTY(EditAnywhere, BlueprintReadOnly)
	bool bAddExternalAssets = false;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(EditCondition="bAddExternalAssets"))
	TSet<UObject*> AssetDataExternal;

	/**
	 * Function for returning all the assets in the container.
	 * 
	 * @return Returns all the internal and externally added assets into one set (TSet).
	 */
	UFUNCTION(BlueprintCallable, Category = Python)
	TSet<UObject*> GetAllAssets() const
	{
		return AssetDataInternal.Union(AssetDataExternal);
	};


private:

	void OnAssetCreated(const FAssetData& InAssetData);
	void OnAssetRemoved(const FAssetData& InAssetData);
	void OnAssetUpdated(const FAssetData& InAssetData);

	bool IsUnderSameDir(const UObject* InAsset) const;

#ifdef WITH_EDITOR
	
	void SendNotification(const FString& Text) const;
	virtual void PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent) override;

#endif
	
};

