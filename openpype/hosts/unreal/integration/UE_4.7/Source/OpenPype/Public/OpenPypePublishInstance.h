#pragma once

#include "Engine.h"
#include "OpenPypePublishInstance.generated.h"


UCLASS(Blueprintable)
class OPENPYPE_API UOpenPypePublishInstance : public UPrimaryDataAsset
{
	GENERATED_UCLASS_BODY()
	
public:
	
	/**
	/**
	 *	Retrieves all the assets which are monitored by the Publish Instance (Monitors assets in the directory which is
	 *	placed in)
	 *
	 *	@return - Set of UObjects. Careful! They are returning raw pointers. Seems like an issue in UE5
	 */
	UFUNCTION(BlueprintCallable, BlueprintPure)
	TSet<UObject*> GetInternalAssets() const
	{
		//For some reason it can only return Raw Pointers? Seems like an issue which they haven't fixed.
		TSet<UObject*> ResultSet;

		for (const auto& Asset : AssetDataInternal)
			ResultSet.Add(Asset.LoadSynchronous());

		return ResultSet;
	}

	/**
	 *	Retrieves all the assets which have been added manually by the Publish Instance
	 *
	 *	@return - TSet of assets (UObjects). Careful! They are returning raw pointers. Seems like an issue in UE5
	 */
	UFUNCTION(BlueprintCallable, BlueprintPure)
	TSet<UObject*> GetExternalAssets() const
	{
		//For some reason it can only return Raw Pointers? Seems like an issue which they haven't fixed.
		TSet<UObject*> ResultSet;

		for (const auto& Asset : AssetDataExternal)
			ResultSet.Add(Asset.LoadSynchronous());

		return ResultSet;
	}

	/**
	 * Function for returning all the assets in the container combined.
	 * 
	 * @return Returns all the internal and externally added assets into one set (TSet of UObjects). Careful! They are
	 * returning raw pointers. Seems like an issue in UE5
	 *
	 * @attention If the bAddExternalAssets variable is false, external assets won't be included!
	 */
	UFUNCTION(BlueprintCallable, BlueprintPure)
	TSet<UObject*> GetAllAssets() const
	{
		const TSet<TSoftObjectPtr<UObject>>& IteratedSet = bAddExternalAssets ? AssetDataInternal.Union(AssetDataExternal) : AssetDataInternal;
		
		//Create a new TSet only with raw pointers.
		TSet<UObject*> ResultSet;

		for (auto& Asset : IteratedSet)
			ResultSet.Add(Asset.LoadSynchronous());

		return ResultSet;
	}


private:

	UPROPERTY(VisibleAnywhere, Category="Assets")
	TSet<TSoftObjectPtr<UObject>> AssetDataInternal;
	
	/**
	 * This property allows exposing the array to include other assets from any other directory than what it's currently
	 * monitoring. NOTE: that these assets have to be added manually! They are not automatically registered or added!
	 */
	UPROPERTY(EditAnywhere, Category = "Assets")
	bool bAddExternalAssets = false;

	UPROPERTY(EditAnywhere, meta=(EditCondition="bAddExternalAssets"), Category="Assets")
	TSet<TSoftObjectPtr<UObject>> AssetDataExternal;


	void OnAssetCreated(const FAssetData& InAssetData);
	void OnAssetRemoved(const FAssetData& InAssetData);
	void OnAssetUpdated(const FAssetData& InAssetData);

	bool IsUnderSameDir(const UObject* InAsset) const;

#ifdef WITH_EDITOR
	
	void SendNotification(const FString& Text) const;
	virtual void PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent) override;

#endif
	
};

