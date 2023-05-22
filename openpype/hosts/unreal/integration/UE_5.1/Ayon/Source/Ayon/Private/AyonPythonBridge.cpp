// Copyright 2023, Ayon, All rights reserved.
#include "AyonPythonBridge.h"

UAyonPythonBridge* UAyonPythonBridge::Get()
{
	TArray<UClass*> AyonPythonBridgeClasses;
	GetDerivedClasses(UAyonPythonBridge::StaticClass(), AyonPythonBridgeClasses);
	int32 NumClasses = AyonPythonBridgeClasses.Num();
	if (NumClasses > 0)
	{
		return Cast<UAyonPythonBridge>(AyonPythonBridgeClasses[NumClasses - 1]->GetDefaultObject());
	}
	return nullptr;
};