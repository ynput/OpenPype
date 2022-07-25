#include "AssetContainerFactory.h"
#include "AssetContainer.h"

UAssetContainerFactory::UAssetContainerFactory(const FObjectInitializer& ObjectInitializer)
	: UFactory(ObjectInitializer)
{
	SupportedClass = UAssetContainer::StaticClass();
	bCreateNew = false;
	bEditorImport = true;
}

UObject* UAssetContainerFactory::FactoryCreateNew(UClass* Class, UObject* InParent, FName Name, EObjectFlags Flags, UObject* Context, FFeedbackContext* Warn)
{
	UAssetContainer* AssetContainer = NewObject<UAssetContainer>(InParent, Class, Name, Flags);
	return AssetContainer;
}

bool UAssetContainerFactory::ShouldShowInNewMenu() const {
	return false;
}
