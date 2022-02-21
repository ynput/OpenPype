#include "AvalonPythonBridge.h"

UAvalonPythonBridge* UAvalonPythonBridge::Get()
{
	TArray<UClass*> AvalonPythonBridgeClasses;
	GetDerivedClasses(UAvalonPythonBridge::StaticClass(), AvalonPythonBridgeClasses);
	int32 NumClasses = AvalonPythonBridgeClasses.Num();
	if (NumClasses > 0)
	{
		return Cast<UAvalonPythonBridge>(AvalonPythonBridgeClasses[NumClasses - 1]->GetDefaultObject());
	}
	return nullptr;
};