#include "OpenPypePythonBridge.h"

UOpenPypePythonBridge* UOpenPypePythonBridge::Get()
{
	TArray<UClass*> OpenPypePythonBridgeClasses;
	GetDerivedClasses(UAvalonPythonBridge::StaticClass(), OpenPypePythonBridgeClasses);
	int32 NumClasses = OpenPypePythonBridgeClasses.Num();
	if (NumClasses > 0)
	{
		return Cast<UOpenPypePythonBridge>(AvalonPythonBridgeClasses[NumClasses - 1]->GetDefaultObject());
	}
	return nullptr;
};