#pragma once

#include "CoreMinimal.h"
#include "Factories/Factory.h"
#include "OpenPypePublishInstanceFactory.generated.h"

/**
 *
 */
UCLASS()
class OPENPYPE_API UOpenPypePublishInstanceFactory : public UFactory
{
	GENERATED_BODY()

public:
	UOpenPypePublishInstanceFactory(const FObjectInitializer& ObjectInitializer);
	virtual UObject* FactoryCreateNew(UClass* Class, UObject* InParent, FName Name, EObjectFlags Flags, UObject* Context, FFeedbackContext* Warn) override;
	virtual bool ShouldShowInNewMenu() const override;
};