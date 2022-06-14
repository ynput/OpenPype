#include "OpenPypePythonBridge.h"

UOpenPypePythonBridge* UOpenPypePythonBridge::Get()
{
	TArray<UClass*> OpenPypePythonBridgeClasses;
	GetDerivedClasses(UOpenPypePythonBridge::StaticClass(), OpenPypePythonBridgeClasses);
	int32 NumClasses = OpenPypePythonBridgeClasses.Num();
	if (NumClasses > 0)
	{
		return Cast<UOpenPypePythonBridge>(OpenPypePythonBridgeClasses[NumClasses - 1]->GetDefaultObject());
	}
	return nullptr;
};