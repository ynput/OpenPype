#include "AyonAssetContainerFactory.h"
#include "AyonAssetContainer.h"

UAyonAssetContainerFactory::UAyonAssetContainerFactory(const FObjectInitializer& ObjectInitializer)
	: UFactory(ObjectInitializer)
{
	SupportedClass = UAyonAssetContainer::StaticClass();
	bCreateNew = false;
	bEditorImport = true;
}

UObject* UAyonAssetContainerFactory::FactoryCreateNew(UClass* Class, UObject* InParent, FName Name, EObjectFlags Flags, UObject* Context, FFeedbackContext* Warn)
{
	UAyonAssetContainer* AssetContainer = NewObject<UAyonAssetContainer>(InParent, Class, Name, Flags);
	return AssetContainer;
}

bool UAyonAssetContainerFactory::ShouldShowInNewMenu() const {
	return false;
}
