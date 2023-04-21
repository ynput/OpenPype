// Copyright 2023, Ayon, All rights reserved.
// Deprecation warning: this is left here just for backwards compatibility
// and will be removed in next versions of Ayon.
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
