#include "OpenPypePublishInstanceFactory.h"
#include "OpenPypePublishInstance.h"

UOpenPypePublishInstanceFactory::UOpenPypePublishInstanceFactory(const FObjectInitializer& ObjectInitializer)
	: UFactory(ObjectInitializer)
{
	SupportedClass = UOpenPypePublishInstance::StaticClass();
	bCreateNew = false;
	bEditorImport = true;
}

UObject* UOpenPypePublishInstanceFactory::FactoryCreateNew(UClass* Class, UObject* InParent, FName Name, EObjectFlags Flags, UObject* Context, FFeedbackContext* Warn)
{
	UOpenPypePublishInstance* OpenPypePublishInstance = NewObject<UOpenPypePublishInstance>(InParent, Class, Name, Flags);
	return OpenPypePublishInstance;
}

bool UOpenPypePublishInstanceFactory::ShouldShowInNewMenu() const {
	return false;
}
