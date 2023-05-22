// Copyright 2023, Ayon, All rights reserved.
// Deprecation warning: this is left here just for backwards compatibility
// and will be removed in next versions of Ayon.
#include "AyonPublishInstanceFactory.h"
#include "AyonPublishInstance.h"

UAyonPublishInstanceFactory::UAyonPublishInstanceFactory(const FObjectInitializer& ObjectInitializer)
	: UFactory(ObjectInitializer)
{
	SupportedClass = UAyonPublishInstance::StaticClass();
	bCreateNew = false;
	bEditorImport = true;
}

UObject* UAyonPublishInstanceFactory::FactoryCreateNew(UClass* InClass, UObject* InParent, FName InName, EObjectFlags Flags, UObject* Context, FFeedbackContext* Warn)
{
	check(InClass->IsChildOf(UAyonPublishInstance::StaticClass()));
	return NewObject<UAyonPublishInstance>(InParent, InClass, InName, Flags);
}

bool UAyonPublishInstanceFactory::ShouldShowInNewMenu() const {
	return false;
}
