#include "AvalonPublishInstanceFactory.h"
#include "AvalonPublishInstance.h"

UAvalonPublishInstanceFactory::UAvalonPublishInstanceFactory(const FObjectInitializer& ObjectInitializer)
	: UFactory(ObjectInitializer)
{
	SupportedClass = UAvalonPublishInstance::StaticClass();
	bCreateNew = false;
	bEditorImport = true;
}

UObject* UAvalonPublishInstanceFactory::FactoryCreateNew(UClass* Class, UObject* InParent, FName Name, EObjectFlags Flags, UObject* Context, FFeedbackContext* Warn)
{
	UAvalonPublishInstance* AvalonPublishInstance = NewObject<UAvalonPublishInstance>(InParent, Class, Name, Flags);
	return AvalonPublishInstance;
}

bool UAvalonPublishInstanceFactory::ShouldShowInNewMenu() const {
	return false;
}
