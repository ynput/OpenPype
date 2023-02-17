#include "OpenPypePublishInstanceFactory.h"
#include "OpenPypePublishInstance.h"

UOpenPypePublishInstanceFactory::UOpenPypePublishInstanceFactory(const FObjectInitializer& ObjectInitializer)
	: UFactory(ObjectInitializer)
{
	SupportedClass = UOpenPypePublishInstance::StaticClass();
	bCreateNew = false;
	bEditorImport = true;
}

UObject* UOpenPypePublishInstanceFactory::FactoryCreateNew(UClass* InClass, UObject* InParent, FName InName, EObjectFlags Flags, UObject* Context, FFeedbackContext* Warn)
{
	check(InClass->IsChildOf(UOpenPypePublishInstance::StaticClass()));
	return NewObject<UOpenPypePublishInstance>(InParent, InClass, InName, Flags);
}

bool UOpenPypePublishInstanceFactory::ShouldShowInNewMenu() const {
	return false;
}
